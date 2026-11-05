"""Cryptographic Exception Token generation and signature verification."""
import hmac
import hashlib
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from app.config import settings
from app.models.domain import ExceptionToken


# Strict list of rules that CANNOT be excepted under any circumstance
ZERO_TOLERANCE_RULES = {"CTL-SAF-04"}  # PII/PCI-DSS leakage


def generate_exception_token(
    model_id: str,
    rule_id: str,
    approver: str,
    approver_role: str,
    reason: str,
    compensating_control: str,
    duration_days: int = 14,
) -> ExceptionToken:
    """Generate a cryptographically signed exception token."""
    if rule_id in ZERO_TOLERANCE_RULES:
        raise ValueError(f"Rule '{rule_id}' has zero tolerance. Cryptographic exceptions are strictly forbidden.")

    token_id = f"EXC-{uuid.uuid4().hex[:12].upper()}"
    now = datetime.now(timezone.utc)
    expires_at = (now + timedelta(days=duration_days)).isoformat()

    # Canonical message string for HMAC
    message_payload = {
        "token_id": token_id,
        "model_id": model_id,
        "rule_id": rule_id,
        "approver": approver,
        "approver_role": approver_role,
        "reason": reason,
        "compensating_control": compensating_control,
        "created_at": now.isoformat(),
        "expires_at": expires_at,
    }
    canonical_str = json.dumps(message_payload, sort_keys=True)
    signature = hmac.new(
        settings.AUDIT_HMAC_KEY.encode("utf-8"),
        canonical_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return ExceptionToken(
        token_id=token_id,
        model_id=model_id,
        rule_id=rule_id,
        approver=approver,
        approver_role=approver_role,
        reason=reason,
        compensating_control=compensating_control,
        created_at=now.isoformat(),
        expires_at=expires_at,
        signature=signature,
    )


def verify_exception_token(token: ExceptionToken) -> Tuple[bool, str]:
    """Verify cryptographic signature and expiration of an exception token."""
    if token.rule_id in ZERO_TOLERANCE_RULES:
        return False, f"Rule '{token.rule_id}' is zero-tolerance and cannot be waived."

    # Check expiration
    try:
        expires_dt = datetime.fromisoformat(token.expires_at)
        if datetime.now(timezone.utc) > expires_dt:
            return False, f"Exception token '{token.token_id}' expired at {token.expires_at}."
    except Exception as e:
        return False, f"Invalid token expiration format: {str(e)}"

    # Reconstruct canonical payload
    message_payload = {
        "token_id": token.token_id,
        "model_id": token.model_id,
        "rule_id": token.rule_id,
        "approver": token.approver,
        "approver_role": token.approver_role,
        "reason": token.reason,
        "compensating_control": token.compensating_control,
        "created_at": token.created_at,
        "expires_at": token.expires_at,
    }
    canonical_str = json.dumps(message_payload, sort_keys=True)
    expected_sig = hmac.new(
        settings.AUDIT_HMAC_KEY.encode("utf-8"),
        canonical_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(token.signature, expected_sig):
        return False, f"Invalid cryptographic signature for exception token '{token.token_id}'. Possible tampering detected."

    return True, "Valid exception token."
