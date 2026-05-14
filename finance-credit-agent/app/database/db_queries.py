"""
app/database/db_queries.py
──────────────────────────
CRUD operations for all database tables.
Provides a clean interface for all nodes and services.
"""

from __future__ import annotations

import logging
from datetime import datetime, date
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.database.db_setup import (
    AuditLog,
    EmailHistory,
    EscalationRecord,
    InvoiceRecord,
    get_db,
    get_session_factory,
)
from app.models.email_output import AuditRecord
from app.models.invoice import Invoice

logger = logging.getLogger(__name__)


def _get_session() -> Session:
    return get_session_factory()()


# ── Invoice CRUD ──────────────────────────────────────────────────────────────

def upsert_invoice(invoice: Invoice) -> None:
    """Insert or update an invoice record."""
    db = _get_session()
    try:
        existing = db.query(InvoiceRecord).filter(
            InvoiceRecord.invoice_id == invoice.invoice_id
        ).first()

        data = {
            "client_name": invoice.client_name,
            "client_email": invoice.client_email,
            "amount_due": invoice.amount_due,
            "currency": invoice.currency,
            "due_date": str(invoice.due_date),
            "invoice_date": str(invoice.invoice_date),
            "days_overdue": invoice.days_overdue or 0,
            "escalation_stage": invoice.escalation_stage,
            "status": invoice.status,
            "risk_score": invoice.risk_score,
            "payment_terms": invoice.payment_terms,
            "contact_phone": invoice.contact_phone,
            "notes": invoice.notes,
            "updated_at": datetime.utcnow(),
        }

        if existing:
            for k, v in data.items():
                setattr(existing, k, v)
        else:
            record = InvoiceRecord(invoice_id=invoice.invoice_id, **data)
            db.add(record)

        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to upsert invoice {invoice.invoice_id}: {e}")
        raise
    finally:
        db.close()


def get_all_invoices() -> List[Dict[str, Any]]:
    """Fetch all invoices from the DB as plain dicts."""
    db = _get_session()
    try:
        records = db.query(InvoiceRecord).order_by(InvoiceRecord.days_overdue.desc()).all()
        return [_invoice_to_dict(r) for r in records]
    finally:
        db.close()


def get_overdue_invoices() -> List[Dict[str, Any]]:
    db = _get_session()
    try:
        records = db.query(InvoiceRecord).filter(
            InvoiceRecord.days_overdue > 0
        ).order_by(InvoiceRecord.days_overdue.desc()).all()
        return [_invoice_to_dict(r) for r in records]
    finally:
        db.close()


def _invoice_to_dict(r: InvoiceRecord) -> Dict[str, Any]:
    return {
        "id": r.id,
        "invoice_id": r.invoice_id,
        "client_name": r.client_name,
        "client_email": r.client_email,
        "amount_due": r.amount_due,
        "currency": r.currency,
        "due_date": r.due_date,
        "invoice_date": r.invoice_date,
        "days_overdue": r.days_overdue,
        "escalation_stage": r.escalation_stage,
        "status": r.status,
        "risk_score": r.risk_score,
        "payment_terms": r.payment_terms,
        "contact_phone": r.contact_phone,
        "notes": r.notes,
        "created_at": str(r.created_at),
        "updated_at": str(r.updated_at),
    }


# ── Audit Log CRUD ────────────────────────────────────────────────────────────

def insert_audit_log(record: AuditRecord) -> None:
    """Write a single audit record to the audit_logs table."""
    db = _get_session()
    try:
        log = AuditLog(
            run_id=record.run_id,
            timestamp=record.timestamp,
            invoice_id=record.invoice_id,
            client_name=record.client_name,
            client_email=record.client_email,
            escalation_stage=record.escalation_stage,
            days_overdue=record.days_overdue,
            email_subject=record.email_subject,
            email_body=record.email_body,
            send_status=record.send_status,
            error_message=record.error_message,
            escalation_status=record.escalation_status,
            risk_score=record.risk_score,
            dry_run=record.dry_run,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to insert audit log for {record.invoice_id}: {e}")
        raise
    finally:
        db.close()


def get_audit_logs(limit: int = 500, run_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Fetch audit logs, newest first."""
    db = _get_session()
    try:
        q = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
        if run_id:
            q = q.filter(AuditLog.run_id == run_id)
        records = q.limit(limit).all()
        return [
            {
                "id": r.id,
                "run_id": r.run_id,
                "timestamp": str(r.timestamp),
                "invoice_id": r.invoice_id,
                "client_name": r.client_name,
                "client_email": r.client_email,
                "escalation_stage": r.escalation_stage,
                "days_overdue": r.days_overdue,
                "email_subject": r.email_subject,
                "send_status": r.send_status,
                "error_message": r.error_message,
                "escalation_status": r.escalation_status,
                "risk_score": r.risk_score,
                "dry_run": r.dry_run,
            }
            for r in records
        ]
    finally:
        db.close()


# ── Email History CRUD ────────────────────────────────────────────────────────

def insert_email_history(email_out: Any, run_id: str, dry_run: bool, status: str, error: Optional[str] = None) -> None:
    db = _get_session()
    try:
        record = EmailHistory(
            run_id=run_id,
            invoice_id=email_out.invoice_id,
            client_name=email_out.client_name,
            recipient_email=email_out.client_email,
            subject=email_out.subject,
            body=email_out.body,
            escalation_stage=email_out.escalation_stage,
            tone=email_out.tone,
            amount_due=email_out.amount_due,
            days_overdue=email_out.days_overdue,
            dry_run=dry_run,
            send_status=status,
            error_message=error,
        )
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to insert email history: {e}")
    finally:
        db.close()


def get_email_history(limit: int = 200) -> List[Dict[str, Any]]:
    db = _get_session()
    try:
        records = db.query(EmailHistory).order_by(EmailHistory.sent_at.desc()).limit(limit).all()
        return [
            {
                "id": r.id,
                "run_id": r.run_id,
                "sent_at": str(r.sent_at),
                "invoice_id": r.invoice_id,
                "client_name": r.client_name,
                "recipient_email": r.recipient_email,
                "subject": r.subject,
                "escalation_stage": r.escalation_stage,
                "tone": r.tone,
                "amount_due": r.amount_due,
                "days_overdue": r.days_overdue,
                "dry_run": r.dry_run,
                "send_status": r.send_status,
                "error_message": r.error_message,
            }
            for r in records
        ]
    finally:
        db.close()


# ── Escalation CRUD ───────────────────────────────────────────────────────────

def insert_escalation(invoice: Invoice, run_id: str) -> None:
    db = _get_session()
    try:
        record = EscalationRecord(
            run_id=run_id,
            invoice_id=invoice.invoice_id,
            client_name=invoice.client_name,
            client_email=invoice.client_email,
            amount_due=invoice.amount_due,
            days_overdue=invoice.days_overdue or 0,
            risk_score=invoice.risk_score,
            notes=f"Auto-escalated: {invoice.days_overdue} days overdue. Stage 5.",
        )
        db.add(record)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to insert escalation for {invoice.invoice_id}: {e}")
    finally:
        db.close()


def get_escalations(resolved: Optional[bool] = None) -> List[Dict[str, Any]]:
    db = _get_session()
    try:
        q = db.query(EscalationRecord).order_by(EscalationRecord.timestamp.desc())
        if resolved is not None:
            q = q.filter(EscalationRecord.resolved == resolved)
        records = q.all()
        return [
            {
                "id": r.id,
                "run_id": r.run_id,
                "timestamp": str(r.timestamp),
                "invoice_id": r.invoice_id,
                "client_name": r.client_name,
                "client_email": r.client_email,
                "amount_due": r.amount_due,
                "days_overdue": r.days_overdue,
                "risk_score": r.risk_score,
                "notes": r.notes,
                "resolved": r.resolved,
            }
            for r in records
        ]
    finally:
        db.close()


# ── Dashboard Stats ───────────────────────────────────────────────────────────

def get_dashboard_stats() -> Dict[str, Any]:
    """Aggregate statistics for the Streamlit dashboard KPI cards."""
    db = _get_session()
    try:
        total_invoices = db.query(InvoiceRecord).count()
        overdue_invoices = db.query(InvoiceRecord).filter(InvoiceRecord.days_overdue > 0).count()
        emails_sent = db.query(EmailHistory).count()
        escalated = db.query(EscalationRecord).count()

        # Overdue by stage
        stage_counts = {}
        for stage in range(1, 6):
            count = db.query(InvoiceRecord).filter(
                InvoiceRecord.escalation_stage == stage
            ).count()
            stage_counts[f"stage_{stage}"] = count

        return {
            "total_invoices": total_invoices,
            "overdue_invoices": overdue_invoices,
            "emails_sent": emails_sent,
            "escalated_cases": escalated,
            "stage_distribution": stage_counts,
        }
    finally:
        db.close()
