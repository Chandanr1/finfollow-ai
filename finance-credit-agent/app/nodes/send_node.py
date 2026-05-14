"""
app/nodes/send_node.py
───────────────────────
LangGraph Node 7: Send or mock-send validated emails.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.config.constants import EMAIL_STATUS_FAILED, EMAIL_STATUS_MOCK, EMAIL_STATUS_SENT, EMAIL_STATUS_SKIPPED
from app.database.db_queries import insert_email_history
from app.models.agent_state import AgentState
from app.models.email_output import AuditRecord, EmailOutput
from app.services.email_service import EmailSendError, send_email

logger = logging.getLogger(__name__)


def send_node(state: AgentState) -> Dict[str, Any]:
    """
    Send all validated emails.
    Records send status for each email.
    """
    validated: List[EmailOutput] = state.get("validated_emails", []) or []
    dry_run: bool = state.get("dry_run", True)
    run_id: str = state.get("run_id", "unknown")

    if not validated:
        logger.info("[send_node] No validated emails to send.")
        return {"sent_emails": [], "failed_sends": []}

    sent: List[AuditRecord] = []
    failed: List[AuditRecord] = []

    for email_out in validated:
        # Stage 5: skip email entirely
        if email_out.requires_legal_review:
            record = AuditRecord(
                invoice_id=email_out.invoice_id,
                client_name=email_out.client_name,
                client_email=email_out.client_email,
                escalation_stage=email_out.escalation_stage,
                days_overdue=email_out.days_overdue,
                send_status=EMAIL_STATUS_SKIPPED,
                escalation_status="ESCALATED_LEGAL",
                risk_score=email_out.risk_score,
                dry_run=dry_run,
                run_id=run_id,
            )
            sent.append(record)
            logger.info(f"[send_node] SKIPPED (legal) — Invoice={email_out.invoice_id}")
            continue

        try:
            success, status_msg = send_email(email_out, dry_run=dry_run)
            status = EMAIL_STATUS_MOCK if dry_run else EMAIL_STATUS_SENT

            record = AuditRecord(
                invoice_id=email_out.invoice_id,
                client_name=email_out.client_name,
                client_email=email_out.client_email,
                escalation_stage=email_out.escalation_stage,
                days_overdue=email_out.days_overdue,
                email_subject=email_out.subject,
                email_body=email_out.body,
                send_status=status,
                escalation_status="NORMAL",
                risk_score=email_out.risk_score,
                dry_run=dry_run,
                run_id=run_id,
            )

            # Persist to email_history
            insert_email_history(email_out, run_id, dry_run, status)

            sent.append(record)
            logger.info(
                f"[send_node] {status} — Invoice={email_out.invoice_id} | "
                f"Stage={email_out.escalation_stage}"
            )

        except (EmailSendError, Exception) as e:
            error_msg = str(e)
            record = AuditRecord(
                invoice_id=email_out.invoice_id,
                client_name=email_out.client_name,
                client_email=email_out.client_email,
                escalation_stage=email_out.escalation_stage,
                days_overdue=email_out.days_overdue,
                email_subject=email_out.subject,
                send_status=EMAIL_STATUS_FAILED,
                error_message=error_msg,
                escalation_status="NORMAL",
                risk_score=email_out.risk_score,
                dry_run=dry_run,
                run_id=run_id,
            )
            insert_email_history(email_out, run_id, dry_run, EMAIL_STATUS_FAILED, error_msg)
            failed.append(record)
            logger.error(f"[send_node] FAILED — Invoice={email_out.invoice_id} | Error={error_msg}")

    logger.info(f"[send_node] Sent: {len(sent)}, Failed: {len(failed)}")
    return {"sent_emails": sent, "failed_sends": failed}
