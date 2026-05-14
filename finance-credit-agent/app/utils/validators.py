"""
app/utils/validators.py
───────────────────────
Data validation helpers for invoices and email outputs.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any, Dict, List, Tuple


def validate_email_address(email: str) -> Tuple[bool, str]:
    """Returns (is_valid, error_message)."""
    if not email or not isinstance(email, str):
        return False, "Email is empty or not a string"
    email = email.strip().lower()
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        return False, f"Invalid email format: {email}"
    # Block obviously invalid domains
    blocked_domains = ["test.com", "example.com", "placeholder.com", "dummy.com"]
    domain = email.split("@")[-1]
    if domain in blocked_domains:
        return False, f"Blocked test domain: {domain}"
    return True, ""


def validate_invoice_row(row: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate a raw CSV/Excel row before Pydantic parsing.
    Returns (is_valid, list_of_errors).
    """
    errors = []
    required = ["invoice_id", "client_name", "client_email", "amount_due", "due_date", "invoice_date"]

    for field in required:
        if field not in row or row[field] is None or str(row[field]).strip() == "":
            errors.append(f"Missing required field: '{field}'")

    if "amount_due" in row:
        try:
            val = float(row["amount_due"])
            if val <= 0:
                errors.append(f"amount_due must be > 0, got: {val}")
        except (TypeError, ValueError):
            errors.append(f"amount_due is not a valid number: {row.get('amount_due')}")

    if "client_email" in row:
        ok, err = validate_email_address(str(row.get("client_email", "")))
        if not ok:
            errors.append(f"Invalid client_email: {err}")

    return len(errors) == 0, errors


def validate_email_output(email_out: Any) -> Tuple[bool, List[str]]:
    """
    Validate that a generated email output contains meaningful data.
    Returns (is_valid, list_of_errors).
    """
    errors = []

    if not email_out.subject or len(email_out.subject) < 10:
        errors.append("Email subject is too short or empty")

    if not email_out.body or len(email_out.body) < 100:
        errors.append("Email body is too short — LLM may have failed")

    if email_out.invoice_id.lower() not in email_out.body.lower():
        errors.append(f"Invoice ID '{email_out.invoice_id}' not found in email body")

    ok, err = validate_email_address(email_out.client_email)
    if not ok:
        errors.append(f"Invalid recipient email: {err}")

    if email_out.amount_due <= 0:
        errors.append("Amount due must be positive")

    return len(errors) == 0, errors
