"""
app/nodes/stage_node.py
────────────────────────
LangGraph Node 4: Determine escalation stage for each overdue invoice.
Also applies risk scoring.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.config.constants import ESCALATION_MATRIX
from app.models.agent_state import AgentState
from app.models.invoice import Invoice, InvoiceStatus
from app.services.risk_scorer import calculate_risk_score

logger = logging.getLogger(__name__)


def _determine_stage(days_overdue: int) -> int:
    """Map days_overdue to escalation stage 1-5."""
    if days_overdue <= 0:
        return 1  # Not overdue — default to stage 1 (should be filtered upstream)
    for stage_num, config in sorted(ESCALATION_MATRIX.items()):
        if config.max_days == -1:  # Stage 5: unbounded
            if days_overdue >= config.min_days:
                return stage_num
        elif config.min_days <= days_overdue <= config.max_days:
            return stage_num
    return 5  # Default to highest if somehow unmatched


def stage_node(state: AgentState) -> Dict[str, Any]:
    """
    Assign escalation stage (1-5) to each overdue invoice.
    Apply risk scoring.
    Separate into email-eligible (1-4) and escalated (5).
    """
    overdue = state.get("overdue_invoices", []) or []

    if not overdue:
        logger.info("[stage_node] No overdue invoices to stage.")
        return {
            "invoices_with_stage": [],
            "invoices_to_send": [],
            "escalated_invoices": [],
        }

    staged: List[Invoice] = []
    to_send: List[Invoice] = []
    escalated: List[Invoice] = []

    for invoice in overdue:
        stage = _determine_stage(invoice.days_overdue or 0)
        invoice.escalation_stage = stage

        # Apply risk score
        invoice.risk_score = calculate_risk_score(invoice)

        stage_config = ESCALATION_MATRIX[stage]

        if stage_config.send_email:
            to_send.append(invoice)
            logger.debug(
                f"[stage_node] Invoice {invoice.invoice_id}: Stage {stage} — "
                f"{stage_config.tone} | {invoice.days_overdue} days | "
                f"Risk: {invoice.risk_score}"
            )
        else:
            # Stage 5: flag for legal review, update status
            invoice.status = InvoiceStatus.ESCALATED
            escalated.append(invoice)
            logger.warning(
                f"[stage_node] Invoice {invoice.invoice_id}: ESCALATED TO LEGAL — "
                f"{invoice.days_overdue} days overdue | Risk: {invoice.risk_score}"
            )

        staged.append(invoice)

    logger.info(
        f"[stage_node] Staged {len(staged)} invoices: "
        f"{len(to_send)} to email, {len(escalated)} to legal review."
    )

    return {
        "invoices_with_stage": staged,
        "invoices_to_send": to_send,
        "escalated_invoices": escalated,
    }
