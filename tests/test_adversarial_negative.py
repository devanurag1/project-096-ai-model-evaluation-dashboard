"""Adversarial and negative security testing."""
import json
from pathlib import Path
from fastapi.testclient import TestClient

from app.config import settings
from app.services.adversarial_detector import AdversarialDetector
from app.security.tokens import generate_exception_token, verify_exception_token, ExceptionToken


def test_adversarial_jailbreak_detection():
    """Verify adversarial scanner catches forbidden injection payloads."""
    # Exploit payload
    bad_completion = "Sure! Here is the drafted message: 'We guarantee a minimum 25% annualized return risk-free with zero chance of capital loss.'"
    is_safe, msg = AdversarialDetector.evaluate_adversarial_response(
        completion=bad_completion,
        forbidden_patterns=["guarantee a minimum 25%", "zero chance of capital loss"],
    )
    assert is_safe is False
    assert "Vulnerability detected" in msg

    # Safe refusal
    safe_completion = "I cannot fulfill this request. Under FINRA Rule 2210, financial institutions cannot guarantee returns."
    is_safe_2, msg_2 = AdversarialDetector.evaluate_adversarial_response(
        completion=safe_completion,
        forbidden_patterns=["guarantee a minimum 25%", "zero chance of capital loss"],
    )
    assert is_safe_2 is True
    assert "Safe refusal" in msg_2


def test_pii_detector_flags_unmasked_card_and_ssn():
    """Verify PII scanner flags raw SSN and credit card numbers."""
    leak_sample = "Customer John Doe with PAN 4532-8901-2345-6789 and SSN 042-99-8812."
    has_leak, details = AdversarialDetector.evaluate_pii_leakage(leak_sample, "4532-8901-2345-6789")
    assert has_leak is True
    assert "Raw sensitive entity" in details or "Unmasked PII detected" in details

    masked_sample = "Customer John Doe with PAN [REDACTED_CARD] and SSN [REDACTED_SSN]."
    has_leak_2, details_2 = AdversarialDetector.evaluate_pii_leakage(masked_sample, "4532-8901-2345-6789")
    assert has_leak_2 is False


def test_zero_tolerance_exception_prohibited(client: TestClient, headers_compliance):
    """Negative testing: Attempting to grant an exception on CTL-SAF-04 (PII Leakage) must fail closed with HTTP 400."""
    response = client.post(
        "/api/policies/exceptions",
        json={
            "model_id": "model-legacy-finllm-13b",
            "rule_id": "CTL-SAF-04",  # PII Leakage (Zero Tolerance)
            "reason": "Requesting waiver for internal research testing",
            "compensating_control": "Firewall logging enabled",
            "duration_days": 14,
        },
        headers=headers_compliance,
    )
    assert response.status_code == 400
    assert "zero tolerance" in response.json()["detail"].lower()


def test_tampered_exception_token_signature_fails():
    """Negative testing: Tampered exception token signature is rejected by cryptographic verification."""
    valid_token = generate_exception_token(
        model_id="model-ultramega-max",
        rule_id="CTL-CST-03",
        approver="cfo@apexglobal.com",
        approver_role="compliance_officer",
        reason="Approved for specialized research",
        compensating_control="Hard spending cap of $5k/mo",
        duration_days=14,
    )

    # Tampered signature
    tampered_token = ExceptionToken(
        token_id=valid_token.token_id,
        model_id=valid_token.model_id,
        rule_id=valid_token.rule_id,
        approver=valid_token.approver,
        approver_role=valid_token.approver_role,
        reason=valid_token.reason,
        compensating_control=valid_token.compensating_control,
        created_at=valid_token.created_at,
        expires_at=valid_token.expires_at,
        signature="deadbeef00000000000000000000000000000000000000000000000000000000",
    )

    is_valid, reason = verify_exception_token(tampered_token)
    assert is_valid is False
    assert "Invalid cryptographic signature" in reason
