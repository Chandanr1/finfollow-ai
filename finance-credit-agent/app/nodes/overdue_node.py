"""
app/nodes/overdue_node.py
──────────────────────────
LangGraph Node 3: Detect overdue invoices.
Calculates days_overdue relative to today's date.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Dict, List

from app.models.agent_state import AgentState
from app.models.invoice import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)


def overdue_node(state: AgentState) -> Dict[str, Any]:
    """
    Calculate days overdue for each invoice.
    Filters to only overdue invoices (days_overdue > 0).
    """
    batch = state.get("invoice_batch")
    if not batch or not batch.invoices:
        return {"overdue_invoices": [], "errors": ["No invoices to process"]}

    today = date.today()
    overdue: List[Invoice] = []

    for invoice in batch.invoices:
        delta = (today - invoice.due_date).days
        if delta > 0:
            invoice.days_overdue = delta
            invoice.status = InvoiceStatus.OVERDUE
            overdue.append(invoice)
        else:
            invoice.days_overdue = 0
            # Not overdue — still update in batch

    logger.info(
        f"[overdue_node] {len(overdue)} overdue invoices out of "
        f"{len(batch.invoices)} total (today={today})"
    )

    return {"overdue_invoices": overdue}
