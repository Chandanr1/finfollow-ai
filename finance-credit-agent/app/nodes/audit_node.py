"""
app/nodes/audit_node.py
────────────────────────
LangGraph Node 8: Write full audit trail to database.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.database.db_queries import insert_audit_log, upsert_invoice
from app.models.agent_state import AgentState
from app.models.email_output import AuditRecord
from app.models.invoice import Invoice, InvoiceStatus

logger = logging.getLogger(__name__)


def audit_node(state: AgentState) -> Dict[str, Any]:
    """
    Persist audit records for all sent, failed, and skipped emails.
    Also update invoice status in DB.
    """
    sent: List[AuditRecord] = state.get("sent_emails", []) or []
    failed: List[AuditRecord] = state.get("failed_sends", []) or []
    escalated: List[Invoice] = state.get("escalated_invoices", []) or []
    run_id = state.get("run_id", "unknown")

    all_records = sent + failed
    audit_records: List[AuditRecord] = []

    # Write audit logs for sent/failed
    for record in all_records:
        try:
            insert_audit_log(record)
            audit_records.append(record)
            logger.debug(f"[audit_node] Logged: {record.invoice_id} — {record.send_status}")
        except Exception as e:
            logger.error(f"[audit_node] Failed to log audit record for {record.invoice_id}: {e}")

    # Write audit logs for escalated (stage 5)
    for invoice in escalated:
        try:
            escalation_record = AuditRecord(
                invoice_id=invoice.invoice_id,
                client_name=invoice.client_name,
                client_email=invoice.client_email,
                escalation_stage=invoice.escalation_stage or 5,
                days_overdue=invoice.days_overdue or 0,
                send_status="SKIPPED",
                error_message=None,
                escalation_status="ESCALATED_LEGAL",
                risk_score=invoice.risk_score,
                dry_run=state.get("dry_run", True),
                run_id=run_id,
            )
            insert_audit_log(escalation_record)
            audit_records.append(escalation_record)

            # Update invoice status in DB
            invoice.status = InvoiceStatus.ESCALATED
            upsert_invoice(invoice)

        except Exception as e:
            logger.error(f"[audit_node] Failed to log escalation for {invoice.invoice_id}: {e}")

    logger.info(f"[audit_node] Logged {len(audit_records)} audit records for run_id={run_id}")
    return {"audit_records": audit_records}
