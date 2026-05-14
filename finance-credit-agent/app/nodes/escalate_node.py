"""
app/nodes/escalate_node.py
───────────────────────────
LangGraph Node 9: Handle Stage 5 escalations.
Records legal escalations in the escalations DB table.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.database.db_queries import insert_escalation
from app.models.agent_state import AgentState
from app.models.invoice import Invoice

logger = logging.getLogger(__name__)


def escalate_node(state: AgentState) -> Dict[str, Any]:
    """
    Process all Stage 5 escalated invoices.
    Records them in the escalations table for manual review.
    """
    escalated: List[Invoice] = state.get("escalated_invoices", []) or []
    run_id = state.get("run_id", "unknown")

    if not escalated:
        logger.info("[escalate_node] No escalated invoices.")
        return {"escalation_records": []}

    escalation_records = []

    for invoice in escalated:
        try:
            insert_escalation(invoice, run_id)
            record = {
                "invoice_id": invoice.invoice_id,
                "client_name": invoice.client_name,
                "amount_due": invoice.amount_due,
                "days_overdue": invoice.days_overdue,
                "risk_score": invoice.risk_score,
                "status": "ESCALATED_TO_LEGAL",
            }
            escalation_records.append(record)
            logger.warning(
                f"[escalate_node] Legal escalation recorded: Invoice={invoice.invoice_id} | "
                f"Client={invoice.client_name} | Days={invoice.days_overdue} | "
                f"Amount={invoice.currency} {invoice.amount_due:,.2f} | "
                f"Risk={invoice.risk_score}"
            )
        except Exception as e:
            logger.error(f"[escalate_node] Failed to record escalation for {invoice.invoice_id}: {e}")

    logger.info(f"[escalate_node] {len(escalation_records)} legal escalations recorded.")
    return {"escalation_records": escalation_records}
