"""
app/utils/sanitizer.py
──────────────────────
Input sanitization and prompt injection protection.

Security Strategy:
- Strip dangerous characters from all user-provided strings
- Detect and reject prompt injection attempts
- Validate all invoice field types before LLM consumption
"""

from __future__ import annotations

import html
import logging
import re
from typing import Any, Dict

from app.config.constants import PROMPT_INJECTION_PATTERNS

logger = logging.getLogger(__name__)


class PromptInjectionError(ValueError):
    """Raised when a potential prompt injection is detected."""


def sanitize_string(value: str, max_length: int = 500) -> str:
    """
    Remove dangerous characters and truncate string.
    Safe for embedding in LLM prompts.
    """
    if not isinstance(value, str):
        return str(value)

    # Strip leading/trailing whitespace
    cleaned = value.strip()

    # HTML-escape to prevent HTML injection
    cleaned = html.escape(cleaned)

    # Remove null bytes and control characters (except newline/tab)
    cleaned = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", cleaned)

    # Remove potential template injection markers
    for marker in ["{%", "%}", "{{", "}}", "${", "$(", "`"]:
        cleaned = cleaned.replace(marker, "")

    # Truncate to max length
    return cleaned[:max_length]


def detect_prompt_injection(text: str) -> bool:
    """
    Return True if the text contains suspected prompt injection patterns.
    Used as a guardrail before embedding user data in LLM prompts.
    """
    lowered = text.lower()
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.lower() in lowered:
            logger.warning(f"Prompt injection pattern detected: '{pattern}' in input")
            return True
    return False


def sanitize_invoice_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize a raw invoice row dict from CSV/Excel before parsing.
    Raises PromptInjectionError if injection is detected.
    """
    sanitized = {}
    string_fields = ["invoice_id", "client_name", "client_email", "payment_terms", "notes", "contact_phone", "currency"]

    for key, value in row.items():
        if key in string_fields and isinstance(value, str):
            # Check for injection before sanitizing
            if detect_prompt_injection(value):
                raise PromptInjectionError(
                    f"Potential prompt injection detected in field '{key}': '{value[:50]}...'"
                )
            sanitized[key] = sanitize_string(value, max_length=200 if key == "client_name" else 500)
        else:
            sanitized[key] = value

    return sanitized


def sanitize_email_address(email: str) -> str:
    """
    Normalize and validate an email address string.
    Returns lowercase stripped email or raises ValueError.
    """
    email = str(email).strip().lower()
    if not re.match(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$", email):
        raise ValueError(f"Invalid email address: {email}")
    return email


def safe_format_currency(amount: float, currency: str = "USD") -> str:
    """Format a currency amount safely for display in emails."""
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "INR": "₹", "CAD": "CA$", "AUD": "A$"}
    symbol = symbols.get(currency.upper(), "$")
    return f"{symbol}{amount:,.2f}"


def validate_no_fake_data(email_body: str, invoice_id: str, client_name: str, amount_due: float) -> bool:
    """
    Validate that the LLM output contains real invoice data, not hallucinated values.
    """
    checks = [
        invoice_id.lower() in email_body.lower(),
        client_name.split()[0].lower() in email_body.lower(),  # at least first name
        str(int(amount_due)) in email_body or f"{amount_due:,.2f}" in email_body or f"{amount_due:.0f}" in email_body,
    ]

    failed_checks = sum(1 for c in checks if not c)
    if failed_checks > 1:
        logger.warning(
            f"Email body may contain fake/hallucinated data for invoice {invoice_id}: "
            f"{failed_checks}/3 data checks failed."
        )
        return False
    return True
