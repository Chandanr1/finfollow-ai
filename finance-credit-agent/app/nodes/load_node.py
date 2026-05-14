"""
app/nodes/load_node.py
───────────────────────
LangGraph Node 1: Load invoices from CSV/Excel file.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from app.models.agent_state import AgentState
from app.services.invoice_loader import load_invoices_from_file

logger = logging.getLogger(__name__)


def load_node(state: AgentState) -> Dict[str, Any]:
    """
    Load raw invoice data from the source file.
    Updates state with: invoice_batch, raw_invoices, errors.
    """
    source_file = state.get("source_file", "data/sample_invoices.csv")
    logger.info(f"[load_node] Loading from: {source_file}")

    try:
        batch = load_invoices_from_file(source_file)

        logger.info(
            f"[load_node] Loaded {len(batch.invoices)} invoices, "
            f"{batch.error_count} errors."
        )

        return {
            "invoice_batch": batch,
            "raw_invoices": [inv.model_dump() for inv in batch.invoices],
            "errors": list(state.get("errors", []) or []) + batch.errors,
        }

    except FileNotFoundError as e:
        logger.error(f"[load_node] File not found: {e}")
        return {"fatal_error": str(e), "errors": [str(e)]}
    except Exception as e:
        logger.error(f"[load_node] Unexpected error: {e}", exc_info=True)
        return {"fatal_error": str(e), "errors": [str(e)]}
