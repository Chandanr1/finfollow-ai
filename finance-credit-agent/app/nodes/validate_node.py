"""
app/nodes/validate_node.py
───────────────────────────
LangGraph Node 2: Validate loaded invoice data.
Persists valid invoices to the database.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.database.db_queries import upsert_invoice
from app.models.agent_state import AgentState
from app.models.invoice import Invoice

logger = logging.getLogger(__name__)


def validate_node(state: AgentState) -> Dict[str, Any]:
    """
    Validate the loaded invoice batch.
    - Checks for empty batch
    - Persists each invoice to DB
    - Returns updated state
    """
    batch = state.get("invoice_batch")
    if not batch or not batch.invoices:
        err = "No valid invoices found after loading. Check source file and data quality."
        logger.error(f"[validate_node] {err}")
        return {"fatal_error": err}

    invoices: List[Invoice] = batch.invoices
    logger.info(f"[validate_node] Validating {len(invoices)} invoices...")

    valid_invoices = []
    errors = list(state.get("errors", []) or [])

    for invoice in invoices:
        try:
            # Persist to database (upsert)
            upsert_invoice(invoice)
            valid_invoices.append(invoice)
        except Exception as e:
            err_msg = f"DB upsert failed for {invoice.invoice_id}: {e}"
            logger.warning(f"[validate_node] {err_msg}")
            errors.append(err_msg)

    logger.info(f"[validate_node] {len(valid_invoices)} invoices validated and persisted.")

    # Update the batch with only successfully persisted invoices
    batch.invoices = valid_invoices
    return {
        "invoice_batch": batch,
        "errors": errors,
    }
