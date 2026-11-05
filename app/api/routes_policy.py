"""API routes for policy rules, thresholds, and cryptographic exception tokens."""
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.domain import ExceptionToken
from app.models.schemas import PolicyThresholdUpdateRequest, ExceptionGrantRequest
from app.policies.engine import policy_engine
from app.policies.matrix import get_control_matrix
from app.security.tokens import generate_exception_token, ZERO_TOLERANCE_RULES
from app.services.eval_service import eval_service
from app.audit.ledger import audit_ledger
from app.security.auth import AuthenticatedUser
from app.api.dependencies import get_current_user, get_correlation_id, require_permission


router = APIRouter(prefix="/api/policies", tags=["Policy Engine & Governance"])


@router.get("", response_model=List[Dict[str, Any]])
def list_active_rules(
    user: AuthenticatedUser = Depends(require_permission("policies:read")),
):
    """List active governance rules and current threshold boundaries."""
    return policy_engine.list_rules()


@router.get("/matrix", response_model=List[Dict[str, Any]])
def view_control_matrix(
    user: AuthenticatedUser = Depends(require_permission("policies:read")),
):
    """View the enterprise Control Matrix specification."""
    return get_control_matrix()


@router.post("/thresholds")
def update_threshold(
    req: PolicyThresholdUpdateRequest,
    user: AuthenticatedUser = Depends(require_permission("policies:update")),
    correlation_id: str = Depends(get_correlation_id),
):
    """Update a policy rule threshold boundary (Requires Compliance Officer or Admin)."""
    try:
        success = policy_engine.update_threshold(req.rule_id, req.new_threshold)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Rule '{req.rule_id}' not found.",
            )

        # Audit threshold change
        audit_ledger.append(
            actor=user.email,
            role=user.role.value,
            action="POLICY_THRESHOLD_UPDATE",
            resource=f"policy_rule/{req.rule_id}",
            result="ALLOWED",
            reason=f"Updated threshold to {req.new_threshold}: {req.justification}",
            correlation_id=correlation_id,
            payload={
                "rule_id": req.rule_id,
                "new_threshold": req.new_threshold,
                "justification": req.justification,
            },
        )
        return {
            "status": "SUCCESS",
            "rule_id": req.rule_id,
            "new_threshold": req.new_threshold,
            "message": "Policy threshold updated and recorded in audit ledger.",
        }
    except ValueError as e:
        # e.g., zero-tolerance rule modification attempt
        audit_ledger.append(
            actor=user.email,
            role=user.role.value,
            action="POLICY_THRESHOLD_UPDATE",
            resource=f"policy_rule/{req.rule_id}",
            result="DENIED",
            reason=f"Attempted forbidden threshold update on zero-tolerance rule: {str(e)}",
            correlation_id=correlation_id,
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/exceptions", response_model=ExceptionToken)
def issue_exception_token(
    req: ExceptionGrantRequest,
    user: AuthenticatedUser = Depends(require_permission("exceptions:grant")),
    correlation_id: str = Depends(get_correlation_id),
):
    """Generate a cryptographically signed Exception Token (Compliance Officer only)."""
    if req.rule_id in ZERO_TOLERANCE_RULES:
        audit_ledger.append(
            actor=user.email,
            role=user.role.value,
            action="EXCEPTION_GRANT_ATTEMPT",
            resource=f"model/{req.model_id}:{req.rule_id}",
            result="DENIED",
            reason="Attempted exception on zero-tolerance rule CTL-SAF-04 (PII Leakage). Fail-closed.",
            correlation_id=correlation_id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rule '{req.rule_id}' has strict zero tolerance. Cryptographic exceptions are prohibited by enterprise policy.",
        )

    model = eval_service.get_model(req.model_id)
    if not model:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Model candidate '{req.model_id}' not found.",
        )

    try:
        token = generate_exception_token(
            model_id=req.model_id,
            rule_id=req.rule_id,
            approver=user.email,
            approver_role=user.role.value,
            reason=req.reason,
            compensating_control=req.compensating_control,
            duration_days=req.duration_days,
        )
        eval_service.store_exception_token(
            token=token,
            actor=user.email,
            role=user.role.value,
            correlation_id=correlation_id,
        )
        return token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate exception token: {str(e)}",
        )
