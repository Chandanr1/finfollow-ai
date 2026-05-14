"""
app/nodes/email_gen_node.py
────────────────────────────
LangGraph Node 5: Generate AI emails using LangChain + OpenAI GPT-4o-mini.
Uses structured prompts, output parsing, and retry logic.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.config.settings import get_settings
from app.models.agent_state import AgentState
from app.models.email_output import EmailOutput
from app.models.invoice import Invoice
from app.prompts.output_parser import build_fallback_email, parse_llm_json_response
from app.prompts.stage_prompts import get_tone_prompt
from app.prompts.system_prompt import get_email_generation_prompt

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_llm():
    """Lazily initialise the LangChain LLM (avoids import-time API key check)."""
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(
        model=settings.openai_model,
        temperature=settings.openai_temperature,
        max_tokens=settings.openai_max_tokens,
        openai_api_key=settings.openai_api_key,
        request_timeout=30,
        max_retries=2,
    )


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(Exception),
    reraise=False,
)
def _generate_single_email(invoice: Invoice, llm, prompt_template) -> Optional[EmailOutput]:
    """
    Generate a single email for one invoice via LLM.
    Returns EmailOutput or None if all retries fail.
    """
    stage = invoice.escalation_stage or 1
    payment_link = f"{settings.company_payment_url}/{invoice.invoice_id}"

    tone_prompt = get_tone_prompt(
        stage,
        days_overdue=invoice.days_overdue,
        invoice_id=invoice.invoice_id,
    )

    prompt_vars = {
        # System variables
        "company_name": settings.company_name,
        "payment_url": settings.company_payment_url,
        "contact_email": settings.company_contact_email,
        "contact_phone": settings.company_contact_phone,
        # Invoice variables
        "invoice_id": invoice.invoice_id,
        "client_name": invoice.client_name,
        "client_email": invoice.client_email,
        "amount_due": f"{invoice.amount_due:,.2f}",
        "currency": invoice.currency,
        "due_date": str(invoice.due_date),
        "invoice_date": str(invoice.invoice_date),
        "days_overdue": invoice.days_overdue,
        "payment_terms": invoice.payment_terms,
        "escalation_stage": stage,
        # Tone
        "tone_instructions": tone_prompt,
        "payment_link": payment_link,
    }

    messages = prompt_template.format_messages(**prompt_vars)
    response = llm.invoke(messages)
    raw_text = response.content

    logger.debug(f"[email_gen_node] Raw LLM response for {invoice.invoice_id}: {raw_text[:200]}...")

    parsed = parse_llm_json_response(raw_text, invoice.invoice_id)
    if parsed:
        # Ensure critical fields match the actual invoice (anti-hallucination check)
        parsed.invoice_id = invoice.invoice_id
        parsed.client_name = invoice.client_name
        parsed.client_email = invoice.client_email
        parsed.amount_due = invoice.amount_due
        parsed.days_overdue = invoice.days_overdue or 0
        parsed.escalation_stage = stage
        parsed.payment_link = payment_link
        parsed.risk_score = invoice.risk_score

    return parsed


def email_gen_node(state: AgentState) -> Dict[str, Any]:
    """
    Generate AI emails for all email-eligible invoices (stages 1-4).
    Uses LLM with structured prompts and fallback logic.
    """
    invoices_to_send: List[Invoice] = state.get("invoices_to_send", []) or []

    if not invoices_to_send:
        logger.info("[email_gen_node] No invoices to generate emails for.")
        return {"generated_emails": [], "failed_emails": []}

    # Check if API key is configured
    is_mock_mode = (
        not settings.openai_api_key
        or settings.openai_api_key.startswith("sk-placeholder")
        or settings.openai_api_key.startswith("sk-your")
    )

    if is_mock_mode:
        logger.warning(
            "[email_gen_node] OpenAI API key not configured — using fallback email templates."
        )

    generated: List[EmailOutput] = []
    failed: List[Dict[str, Any]] = []

    # Initialise LLM and prompt template (only if real mode)
    llm = None
    prompt_template = None
    if not is_mock_mode:
        try:
            llm = _get_llm()
            prompt_template = get_email_generation_prompt()
        except Exception as e:
            logger.error(f"[email_gen_node] LLM initialisation failed: {e}. Using fallback.")
            is_mock_mode = True

    for invoice in invoices_to_send:
        stage = invoice.escalation_stage or 1
        try:
            if is_mock_mode:
                # Use fallback template (no LLM call)
                email_out = build_fallback_email(invoice, stage, "Mock mode")
            else:
                email_out = _generate_single_email(invoice, llm, prompt_template)
                if email_out is None:
                    logger.warning(
                        f"[email_gen_node] LLM failed for {invoice.invoice_id}, using fallback."
                    )
                    email_out = build_fallback_email(invoice, stage, "LLM parse failed")

            generated.append(email_out)
            logger.info(
                f"[email_gen_node] Generated email for {invoice.invoice_id} "
                f"(Stage {stage}) — Subject: {email_out.subject[:60]}"
            )

        except Exception as e:
            error_msg = f"Email generation failed for {invoice.invoice_id}: {e}"
            logger.error(f"[email_gen_node] {error_msg}")
            failed.append({"invoice_id": invoice.invoice_id, "error": error_msg})
            # Still try fallback
            try:
                fallback = build_fallback_email(invoice, stage, str(e))
                generated.append(fallback)
                logger.info(f"[email_gen_node] Fallback email generated for {invoice.invoice_id}")
            except Exception as fe:
                logger.error(f"[email_gen_node] Fallback also failed: {fe}")

    logger.info(
        f"[email_gen_node] Generated {len(generated)} emails, "
        f"{len(failed)} failures."
    )

    return {
        "generated_emails": generated,
        "failed_emails": failed,
    }
