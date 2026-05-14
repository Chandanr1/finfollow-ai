"""
app/agents/email_agent.py
──────────────────────────
Top-level agent orchestrator.
Wires together: database init, graph execution, LangSmith tracing, and result reporting.
"""

from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from app.config.settings import get_settings
from app.database.db_setup import init_db
from app.graph.graph_builder import get_compiled_graph
from app.models.agent_state import AgentState
from app.utils.logger import AgentLogger, setup_logging

logger = logging.getLogger(__name__)
settings = get_settings()


def _setup_langsmith() -> None:
    """Configure LangSmith tracing if enabled."""
    if settings.langsmith_enabled:
        os.environ["LANGCHAIN_TRACING_V2"] = "true"
        os.environ["LANGCHAIN_API_KEY"] = settings.langchain_api_key or ""
        os.environ["LANGCHAIN_PROJECT"] = settings.langchain_project
        logger.info(f"[agent] LangSmith tracing enabled — project: {settings.langchain_project}")
    else:
        os.environ["LANGCHAIN_TRACING_V2"] = "false"


def run_agent(
    source_file: str = "data/sample_invoices.csv",
    dry_run: Optional[bool] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute the full Finance Credit Follow-Up Agent workflow.

    Args:
        source_file: Path to CSV or Excel invoice file.
        dry_run: If True, mock-send emails. Defaults to settings.email_dry_run.
        run_id: Optional run identifier. Auto-generated if not provided.

    Returns:
        Final agent state dict with run_stats.
    """
    # Setup
    setup_logging(settings.log_level)
    _setup_langsmith()
    init_db()

    if run_id is None:
        run_id = f"run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}"

    if dry_run is None:
        dry_run = settings.email_dry_run

    agent_logger = AgentLogger(run_id)

    logger.info(
        f"[agent] Starting Finance Credit Agent — "
        f"run_id={run_id} | dry_run={dry_run} | source={source_file}"
    )

    # Build initial state
    initial_state: AgentState = {
        "run_id": run_id,
        "run_started_at": datetime.utcnow().isoformat(),
        "dry_run": dry_run,
        "source_file": source_file,
        "errors": [],
        "fatal_error": None,
        "raw_invoices": [],
        "invoice_batch": None,
        "overdue_invoices": [],
        "invoices_with_stage": [],
        "invoices_to_send": [],
        "escalated_invoices": [],
        "generated_emails": [],
        "validated_emails": [],
        "failed_emails": [],
        "sent_emails": [],
        "failed_sends": [],
        "audit_records": [],
        "escalation_records": [],
        "run_stats": None,
    }

    # Execute LangGraph workflow
    graph = get_compiled_graph()

    try:
        final_state = graph.invoke(initial_state)
    except Exception as e:
        logger.error(f"[agent] Graph execution failed: {e}", exc_info=True)
        final_state = {**initial_state, "fatal_error": str(e)}

    # Log run summary
    run_stats = final_state.get("run_stats") or {}
    agent_logger.log_run_summary(run_stats)

    # Log escalations
    for inv in (final_state.get("escalated_invoices") or []):
        agent_logger.log_escalation(
            inv.invoice_id, inv.client_name, inv.days_overdue or 0
        )

    logger.info(f"[agent] Run complete — {run_stats}")
    return final_state
