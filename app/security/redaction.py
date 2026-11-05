"""PII Redaction and Data Sanitization Service."""
import re
from typing import Any, Dict, List, Union

# Compiled regex patterns for regulated sensitive financial identifiers
PATTERNS = {
    "CREDIT_CARD": re.compile(r"\b(?:\d[ -]*?){13,16}\b"),
    "SSN": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "BANK_ROUTING": re.compile(r"\b(?:0[1-9]|[12][0-9]|3[0-2]|6[1-9]|7[0-2]|80)\d{7}\b"),
    "BANK_ACCOUNT": re.compile(r"\b\d{8,17}\b"),
    "EMAIL": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "PHONE": re.compile(r"\b(?:\+?1[-. ]?)?\(?\d{3}\)?[-. ]?\d{3}[-. ]?\d{4}\b"),
}


def mask_sensitive_patterns(text: str) -> str:
    """Mask sensitive PII and financial patterns in a given string."""
    if not isinstance(text, str):
        return text

    # Apply specific format patterns first
    redacted = text
    redacted = PATTERNS["SSN"].sub("[REDACTED_SSN]", redacted)
    redacted = PATTERNS["CREDIT_CARD"].sub("[REDACTED_CARD]", redacted)
    redacted = PATTERNS["EMAIL"].sub("[REDACTED_EMAIL]", redacted)
    redacted = PATTERNS["PHONE"].sub("[REDACTED_PHONE]", redacted)
    return redacted


def detect_pii(text: str) -> List[Dict[str, str]]:
    """Scan text for presence of unmasked PII entities."""
    detections = []
    if not isinstance(text, str):
        return detections

    if PATTERNS["SSN"].search(text):
        detections.append({"entity": "SSN", "category": "GLBA_TAX_ID"})
    if PATTERNS["CREDIT_CARD"].search(text):
        detections.append({"entity": "CREDIT_CARD", "category": "PCI_DSS_PAN"})
    if PATTERNS["EMAIL"].search(text):
        detections.append({"entity": "EMAIL", "category": "CUSTOMER_CONTACT"})
    if PATTERNS["PHONE"].search(text):
        detections.append({"entity": "PHONE", "category": "CUSTOMER_CONTACT"})
    return detections


def sanitize_payload(payload: Union[Dict[str, Any], List[Any], str, Any]) -> Any:
    """Recursively sanitize nested dictionaries or lists before logging."""
    if isinstance(payload, str):
        return mask_sensitive_patterns(payload)
    elif isinstance(payload, dict):
        sanitized = {}
        for k, v in payload.items():
            # Never log raw credentials or secret tokens
            if any(secret_term in k.lower() for secret_term in ["token", "secret", "password", "key", "authorization"]):
                sanitized[k] = "[REDACTED_SECRET]"
            else:
                sanitized[k] = sanitize_payload(v)
        return sanitized
    elif isinstance(payload, list):
        return [sanitize_payload(item) for item in payload]
    return payload
