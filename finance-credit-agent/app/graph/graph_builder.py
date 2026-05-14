"""
app/graph/graph_builder.py
───────────────────────────
LangGraph StateGraph assembly.
Defines nodes, edges, conditional routing, and compiles the agent graph.
"""

from __future__ import annotations

import logging
from typing import Any, Dict

from langgraph.graph import END, StateGraph

from app.models.agent_state import AgentState
from app.nodes.audit_node import audit_node
from app.nodes.email_gen_node import email_gen_node
from app.nodes.email_validate_node import email_validate_node
from app.nodes.escalate_node import escalate_node
from app.nodes.load_node import load_node
from app.nodes.overdue_node import overdue_node
from app.nodes.send_node import send_node
from app.nodes.stage_node import stage_node
from app.nodes.validate_node import validate_node

logger = logging.getLogger(__name__)


def _should_continue_after_load(state: AgentState) -> str:
    """Route: abort if fatal error during loading."""
    if state.get("fatal_error"):
        logger.error(f"[router] Fatal error detected: {state['fatal_error']}")
        return "abort"
    return "continue"


def _should_continue_after_validate(state: AgentState) -> str:
    """Route: abort if no invoices survived validation."""
    if state.get("fatal_error"):
        return "abort"
    batch = state.get("invoice_batch")
    if not batch or not batch.invoices:
        return "abort"
    return "continue"


def _should_continue_after_overdue(state: AgentState) -> str:
    """Route: skip email generation if no overdue invoices."""
    overdue = state.get("overdue_invoices", []) or []
    if not overdue:
        logger.info("[router] No overdue invoices — skipping email generation.")
        return "no_overdue"
    return "continue"


def _finalize_node(state: AgentState) -> Dict[str, Any]:
    """Terminal node: compute run statistics."""
    sent = state.get("sent_emails", []) or []
    failed = state.get("failed_sends", []) or []
    escalated = state.get("escalated_invoices", []) or []
    errors = state.get("errors", []) or []
    batch = state.get("invoice_batch")

    run_stats = {
        "total_invoices": len(batch.invoices) if batch else 0,
        "overdue_invoices": len(state.get("overdue_invoices", []) or []),
        "emails_sent": sum(1 for r in sent if r.send_status in ("SENT", "MOCK_SENT")),
        "emails_failed": len(failed),
        "escalated_cases": len(escalated),
        "error_count": len(errors),
        "dry_run": state.get("dry_run", True),
        "run_id": state.get("run_id", "unknown"),
    }

    logger.info(f"[finalize_node] Run complete: {run_stats}")
    return {"run_stats": run_stats}


def _abort_node(state: AgentState) -> Dict[str, Any]:
    """Terminal node for fatal error path."""
    error = state.get("fatal_error", "Unknown fatal error")
    logger.error(f"[abort_node] Workflow aborted: {error}")
    return {
        "run_stats": {
            "status": "ABORTED",
            "error": error,
            "total_invoices": 0,
            "emails_sent": 0,
        }
    }


def _no_overdue_node(state: AgentState) -> Dict[str, Any]:
    """Terminal node when no overdue invoices found."""
    batch = state.get("invoice_batch")
    total = len(batch.invoices) if batch else 0
    logger.info(f"[no_overdue_node] All {total} invoices are current — no emails needed.")
    return {
        "run_stats": {
            "status": "COMPLETE",
            "total_invoices": total,
            "overdue_invoices": 0,
            "emails_sent": 0,
            "escalated_cases": 0,
        }
    }


def build_graph() -> Any:
    """
    Build and compile the LangGraph StateGraph.

    Workflow:
    load → validate → overdue → stage → email_gen → email_validate
         → send → audit → escalate → finalize

    With conditional routing for error handling.
    """
    graph = StateGraph(AgentState)

    # ── Register nodes ────────────────────────────────────────
    graph.add_node("load", load_node)
    graph.add_node("validate", validate_node)
    graph.add_node("overdue", overdue_node)
    graph.add_node("stage", stage_node)
    graph.add_node("email_gen", email_gen_node)
    graph.add_node("email_validate", email_validate_node)
    graph.add_node("send", send_node)
    graph.add_node("audit", audit_node)
    graph.add_node("escalate", escalate_node)
    graph.add_node("finalize", _finalize_node)
    graph.add_node("abort", _abort_node)
    graph.add_node("no_overdue", _no_overdue_node)

    # ── Entry point ───────────────────────────────────────────
    graph.set_entry_point("load")

    # ── Edges with conditional routing ───────────────────────
    graph.add_conditional_edges(
        "load",
        _should_continue_after_load,
        {
            "continue": "validate",
            "abort": "abort",
        },
    )

    graph.add_conditional_edges(
        "validate",
        _should_continue_after_validate,
        {
            "continue": "overdue",
            "abort": "abort",
        },
    )

    graph.add_conditional_edges(
        "overdue",
        _should_continue_after_overdue,
        {
            "continue": "stage",
            "no_overdue": "no_overdue",
        },
    )

    # Linear edges for the main happy path
    graph.add_edge("stage", "email_gen")
    graph.add_edge("email_gen", "email_validate")
    graph.add_edge("email_validate", "send")
    graph.add_edge("send", "audit")
    graph.add_edge("audit", "escalate")
    graph.add_edge("escalate", "finalize")

    # Terminal nodes
    graph.add_edge("finalize", END)
    graph.add_edge("abort", END)
    graph.add_edge("no_overdue", END)

    compiled = graph.compile()
    logger.info("[graph_builder] LangGraph workflow compiled successfully.")
    return compiled


# Pre-built graph instance (singleton for performance)
_compiled_graph = None


def get_compiled_graph():
    """Return cached compiled graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph
