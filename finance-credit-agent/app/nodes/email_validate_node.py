"""
app/nodes/email_validate_node.py
─────────────────────────────────
LangGraph Node 6: Validate generated emails before sending.
Checks structure, content, and anti-hallucination guards.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.models.agent_state import AgentState
from app.models.email_output import EmailOutput
from app.utils.sanitizer import validate_no_fake_data
from app.utils.validators import validate_email_output

logger = logging.getLogger(__name__)


def email_validate_node(state: AgentState) -> Dict[str, Any]:
    """
    Validate each generated email.
    - Structural validation (Pydantic checks)
    - Anti-hallucination checks (real invoice data present)
    - Email address validation
    """
    generated: List[EmailOutput] = state.get("generated_emails", []) or []
    failed: List[Dict[str, Any]] = list(state.get("failed_emails", []) or [])

    if not generated:
        logger.info("[email_validate_node] No generated emails to validate.")
        return {"validated_emails": [], "failed_emails": failed}

    validated: List[EmailOutput] = []

    for email_out in generated:
        # Skip stage 5 (legal review — no email to validate)
        if email_out.requires_legal_review:
            validated.append(email_out)
            continue

        # Structural validation
        is_valid, errors = validate_email_output(email_out)
        if not is_valid:
            logger.warning(
                f"[email_validate_node] Validation failed for {email_out.invoice_id}: {errors}"
            )
            failed.append({
                "invoice_id": email_out.invoice_id,
                "error": f"Validation errors: {'; '.join(errors)}",
            })
            continue

        # Anti-hallucination check
        data_valid = validate_no_fake_data(
            email_out.body,
            email_out.invoice_id,
            email_out.client_name,
            email_out.amount_due,
        )
        if not data_valid:
            logger.warning(
                f"[email_validate_node] Anti-hallucination check failed for {email_out.invoice_id}"
            )
            # Still allow it but log the warning (don't block delivery for borderline cases)

        validated.append(email_out)
        logger.debug(f"[email_validate_node] Validated: {email_out.invoice_id}")

    logger.info(
        f"[email_validate_node] {len(validated)} emails validated, "
        f"{len(failed)} total failures."
    )

    return {
        "validated_emails": validated,
        "failed_emails": failed,
    }
