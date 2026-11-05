"""Tests for cryptographic audit ledger immutability and tamper detection."""
import uuid
from app.audit.ledger import AuditLedger, GENESIS_HASH
from app.security.redaction import mask_sensitive_patterns, sanitize_payload


def test_audit_ledger_hash_chain_continuity(tmp_path):
    """Verify sequential entries form unbroken SHA-256 hash chain with valid HMAC signatures."""
    ledger_file = tmp_path / "chain_test.jsonl"
    ledger = AuditLedger(ledger_path=ledger_file, hmac_key="test-key")

    rec1 = ledger.append(
        actor="dev1@apex.com",
        role="eval_engineer",
        action="MODEL_EVAL",
        resource="model/gpt4o",
        result="ALLOWED",
        reason="Passed all gates",
        correlation_id="C-1",
    )
    assert rec1.sequence_id == 1
    assert rec1.prev_hash == GENESIS_HASH

    rec2 = ledger.append(
        actor="dev2@apex.com",
        role="eval_engineer",
        action="MODEL_EVAL",
        resource="model/llama3",
        result="ALLOWED",
        reason="Passed all gates",
        correlation_id="C-2",
    )
    assert rec2.sequence_id == 2
    assert rec2.prev_hash != GENESIS_HASH

    # Verify integrity
    is_valid, msg, broken_seq = ledger.verify_integrity()
    assert is_valid is True
    assert broken_seq is None


def test_tamper_detection_pinpoints_altered_record(tmp_path):
    """Verify modifying a historical record breaks hash chain and pinpoints sequence ID."""
    ledger_file = tmp_path / "tamper_test.jsonl"
    ledger = AuditLedger(ledger_path=ledger_file, hmac_key="test-key")

    for i in range(1, 6):
        ledger.append(
            actor=f"user{i}@apex.com",
            role="eval_engineer",
            action="EVAL_RUN",
            resource=f"run/{i}",
            result="ALLOWED",
            reason=f"Run {i}",
            correlation_id=f"CORR-{i}",
        )

    # Tamper with record #2
    ledger.simulate_tamper(sequence_id=2)

    is_valid, msg, broken_seq = ledger.verify_integrity()
    assert is_valid is False
    assert broken_seq == 2
    assert "Hash chain broken at record #2" in msg or "HMAC signature invalid" in msg


def test_payload_redaction_before_audit_recording():
    """Verify secrets and PII are redacted before entering audit logs."""
    dirty_payload = {
        "api_key": "secret-super-key-12345",
        "authorization_token": "bearer-abc-999",
        "customer_ssn": "042-99-8812",
        "note": "Payment made with card 4532-8901-2345-6789",
    }
    cleaned = sanitize_payload(dirty_payload)
    assert cleaned["api_key"] == "[REDACTED_SECRET]"
    assert cleaned["authorization_token"] == "[REDACTED_SECRET]"
    assert "[REDACTED_SSN]" in cleaned["customer_ssn"]
    assert "[REDACTED_CARD]" in cleaned["note"]
