"""
app/models/agent_state.py
─────────────────────────
LangGraph AgentState — the shared state passed between all graph nodes.
Using TypedDict for full LangGraph compatibility.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from app.models.invoice import Invoice, InvoiceBatch
from app.models.email_output import EmailOutput, AuditRecord


class AgentState(TypedDict, total=False):
    """
    Shared mutable state for the LangGraph workflow.
    Every node reads from and writes into this state object.
    LangGraph merges state updates automatically.
    """

    # ── Run metadata ─────────────────────────────────────────
    run_id: str                          # Unique ID for this agent run
    run_started_at: str                  # ISO timestamp
    dry_run: bool                        # If True, mock-send emails
    source_file: str                     # Path to the loaded CSV/Excel

    # ── Invoice data flow ────────────────────────────────────
    raw_invoices: List[Dict[str, Any]]   # Raw rows from pandas
    invoice_batch: Optional[InvoiceBatch]  # Validated InvoiceBatch
    overdue_invoices: List[Invoice]      # Invoices past their due date
    invoices_with_stage: List[Invoice]   # After escalation stage assignment
    invoices_to_send: List[Invoice]      # Stage 1–4 (email-eligible)
    escalated_invoices: List[Invoice]    # Stage 5 (legal review)

    # ── Email generation ─────────────────────────────────────
    generated_emails: List[EmailOutput]  # LLM-generated emails
    validated_emails: List[EmailOutput]  # Emails passing validation
    failed_emails: List[Dict[str, Any]]  # Emails that failed generation/validation

    # ── Send results ─────────────────────────────────────────
    sent_emails: List[AuditRecord]       # Successfully sent/mock-sent
    failed_sends: List[AuditRecord]      # Failed send attempts

    # ── Audit ────────────────────────────────────────────────
    audit_records: List[AuditRecord]     # All audit records this run
    escalation_records: List[Dict[str, Any]]  # Legal escalation records

    # ── Error tracking ───────────────────────────────────────
    errors: List[str]                    # Non-fatal errors accumulated
    fatal_error: Optional[str]           # If set, stop the graph

    # ── Stats (for dashboard update) ─────────────────────────
    run_stats: Optional[Dict[str, Any]]  # Summary stats after run
