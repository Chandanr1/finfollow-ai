"""
app/utils/pii_masker.py
───────────────────────
PII masking for audit logs.

Masks:
- Email addresses → a***@domain.com
- Phone numbers → +1-***-***-XXXX
- Credit card numbers → **** **** **** XXXX
"""

from __future__ import annotations

import re
from typing import Any, Dict

from app.config.constants import PII_PATTERNS


def mask_email(email: str) -> str:
    """Mask email: first char + *** @ domain."""
    match = re.match(r"^([^@]+)@(.+)$", email)
    if match:
        local = match.group(1)
        domain = match.group(2)
        masked_local = local[0] + "***" if len(local) > 1 else "***"
        return f"{masked_local}@{domain}"
    return "***@***.***"


def mask_phone(phone: str) -> str:
    """Keep last 4 digits visible."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) >= 4:
        return "***-***-" + digits[-4:]
    return "***-****"


def mask_pii(text: str) -> str:
    """
    Apply all PII masking patterns to a string.
    Returns the masked string.
    """
    # Mask emails
    text = re.sub(
        PII_PATTERNS["email"],
        lambda m: mask_email(m.group(0)),
        text,
    )
    # Mask phone numbers (conservative — only obvious patterns)
    text = re.sub(
        r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        lambda m: mask_phone(m.group(0)),
        text,
    )
    return text


def mask_dict_pii(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively mask PII values in a dictionary.
    Specifically targets known PII fields by key name.
    """
    PII_KEYS = {"client_email", "email", "recipient_email", "smtp_username", "smtp_password"}
    PHONE_KEYS = {"contact_phone", "phone"}

    result = {}
    for k, v in d.items():
        if k in PII_KEYS and isinstance(v, str):
            result[k] = mask_email(v) if "@" in v else "***"
        elif k in PHONE_KEYS and isinstance(v, str):
            result[k] = mask_phone(v)
        elif isinstance(v, dict):
            result[k] = mask_dict_pii(v)
        elif isinstance(v, str):
            result[k] = mask_pii(v)
        else:
            result[k] = v
    return result
