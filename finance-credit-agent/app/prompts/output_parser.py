"""
app/prompts/output_parser.py
─────────────────────────────
LangChain output parser using Pydantic structured output.
Provides robust parsing with retry and fallback logic.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Optional

from app.models.email_output import EmailOutput

logger = logging.getLogger(__name__)


def parse_llm_json_response(raw_response: str, invoice_id: str) -> Optional[EmailOutput]:
    """
    Parse LLM raw text output into a structured EmailOutput.

    Strategy:
    1. Try direct JSON parse
    2. Try extracting JSON from markdown code blocks
    3. Try regex-based extraction
    4. Return None on failure (triggers retry/fallback)
    """
    # Clean up common LLM formatting artifacts
    cleaned = raw_response.strip()

    # Strategy 1: Direct JSON parse
    try:
        data = json.loads(cleaned)
        return EmailOutput(**data)
    except (json.JSONDecodeError, Exception):
        pass

    # Strategy 2: Extract from markdown code block ```json ... ```
    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
    if code_block_match:
        try:
            data = json.loads(code_block_match.group(1))
            return EmailOutput(**data)
        except Exception:
            pass

    # Strategy 3: Find first { ... } JSON object
    json_match = re.search(r"\{[\s\S]*\}", cleaned)
    if json_match:
        try:
            data = json.loads(json_match.group(0))
            return EmailOutput(**data)
        except Exception as e:
            logger.error(f"JSON extraction failed for invoice {invoice_id}: {e}")

    logger.error(f"All parsing strategies failed for invoice {invoice_id}. Raw: {raw_response[:200]}")
    return None


def build_fallback_email(invoice: "Invoice", stage: int, error: str) -> EmailOutput:
    """
    Generate a safe fallback email when LLM fails.
    Uses a hardcoded professional template with real invoice data.
    """
    from app.config.settings import get_settings
    from app.config.constants import ESCALATION_MATRIX
    settings = get_settings()

    stage_config = ESCALATION_MATRIX.get(stage)
    tone = stage_config.tone if stage_config else "professional"

    subject = f"Payment Reminder: Invoice {invoice.invoice_id} — {invoice.currency} {invoice.amount_due:,.2f} Overdue ({invoice.days_overdue} days)"

    body = f"""Dear {invoice.client_name},

We are writing to draw your attention to Invoice {invoice.invoice_id} which remains outstanding.

Invoice Details:
- Invoice Number: {invoice.invoice_id}
- Amount Due: {invoice.currency} {invoice.amount_due:,.2f}
- Due Date: {invoice.due_date}
- Days Overdue: {invoice.days_overdue}

Please arrange payment immediately using the link below:
{settings.company_payment_url}/{invoice.invoice_id}

If you have already made this payment, please disregard this notice and send confirmation to {settings.company_contact_email}.

For queries, please contact our accounts team:
Email: {settings.company_contact_email}
Phone: {settings.company_contact_phone}

Best regards,
Finance Collections Team
{settings.company_name}

Note: This is an automated reminder. Please do not reply directly to this email.
"""

    return EmailOutput(
        invoice_id=invoice.invoice_id,
        client_name=invoice.client_name,
        client_email=invoice.client_email,
        subject=subject,
        body=body,
        escalation_stage=stage,
        tone=tone,
        amount_due=invoice.amount_due,
        days_overdue=invoice.days_overdue or 0,
        requires_legal_review=(stage == 5),
        payment_link=f"{settings.company_payment_url}/{invoice.invoice_id}",
        risk_score=None,
    )
