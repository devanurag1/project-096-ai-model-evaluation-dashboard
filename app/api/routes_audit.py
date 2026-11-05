"""API routes for immutable audit ledger and cryptographic verification."""
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from app.models.domain import AuditRecord
from app.models.schemas import AuditVerificationResponse
from app.audit.ledger import audit_ledger, GENESIS_HASH
from app.services.metrics_service import metrics_service
from app.security.auth import AuthenticatedUser
from app.api.dependencies import get_current_user, get_correlation_id, require_permission


router = APIRouter(prefix="/api/audit", tags=["Audit & Ledger Integrity"])


@router.get("/records", response_model=List[AuditRecord])
def list_audit_records(
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    user: AuthenticatedUser = Depends(require_permission("audit:read")),
):
    """View tamper-evident audit records in descending chronological order."""
    return audit_ledger.list_records(limit=limit, offset=offset)


@router.get("/verify", response_model=AuditVerificationResponse)
def verify_audit_chain(
    user: AuthenticatedUser = Depends(require_permission("audit:verify")),
):
    """
    Cryptographically verify SHA-256 hash-chain continuity and HMAC signatures.
    Returns proof of uncompromised audit trail or highlights exact broken block.
    """
    is_valid, msg, broken_seq = audit_ledger.verify_integrity()
    records = audit_ledger.list_records(limit=1)
    latest_hash = records[0].payload_hash if records else GENESIS_HASH

    return AuditVerificationResponse(
        is_valid=is_valid,
        total_records=audit_ledger.count(),
        genesis_hash=GENESIS_HASH,
        latest_hash=latest_hash,
        broken_link_sequence_id=broken_seq,
        verification_message=msg,
        checked_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/tamper-test")
def simulate_adversarial_tamper(
    sequence_id: int = Query(..., ge=1),
    user: AuthenticatedUser = Depends(require_permission("audit:export")),
    correlation_id: str = Depends(get_correlation_id),
):
    """
    Simulate an adversarial attack mutating a historical audit record on disk.
    Demonstrates that verify_audit_chain immediately catches the tampering.
    """
    metrics_service.record_blocked_bypass()
    success = audit_ledger.simulate_tamper(sequence_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Record sequence #{sequence_id} not found.",
        )

    # Immediately verify to demonstrate failure detection
    is_valid, msg, broken_seq = audit_ledger.verify_integrity()

    return {
        "status": "TAMPER_SIMULATED",
        "target_sequence_id": sequence_id,
        "is_chain_valid_post_tamper": is_valid,
        "tamper_detected_at_sequence": broken_seq,
        "detection_message": msg,
    }
