"""
app/database/db_setup.py
────────────────────────
SQLite database initialisation using SQLAlchemy Core.
Creates all required tables if they do not exist.
"""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    event,
    text,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config.settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# ── Engine ───────────────────────────────────────────────────────────────────
_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            echo=False,
        )
        # Enable WAL mode for better concurrency
        @event.listens_for(_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal


def get_db() -> Session:
    """Dependency injection helper for getting a DB session."""
    SessionLocal = get_session_factory()
    db = SessionLocal()
    try:
        return db
    except Exception:
        db.close()
        raise


# ── ORM Base ─────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Table Definitions ────────────────────────────────────────────────────────
class InvoiceRecord(Base):
    """Persisted invoice snapshot for tracking and dashboard."""
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    invoice_id = Column(String(100), unique=True, nullable=False, index=True)
    client_name = Column(String(200), nullable=False)
    client_email = Column(String(200), nullable=False)
    amount_due = Column(Float, nullable=False)
    currency = Column(String(10), default="USD")
    due_date = Column(String(20), nullable=False)
    invoice_date = Column(String(20), nullable=False)
    days_overdue = Column(Integer, default=0)
    escalation_stage = Column(Integer, nullable=True)
    status = Column(String(30), default="PENDING")
    risk_score = Column(Float, nullable=True)
    payment_terms = Column(String(50), default="Net 30")
    contact_phone = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    """Full audit trail of every agent action."""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    invoice_id = Column(String(100), nullable=False, index=True)
    client_name = Column(String(200), nullable=False)
    client_email = Column(String(200), nullable=True)   # May be masked
    escalation_stage = Column(Integer, nullable=True)
    days_overdue = Column(Integer, nullable=True)
    email_subject = Column(Text, nullable=True)
    email_body = Column(Text, nullable=True)
    send_status = Column(String(20), nullable=False)    # SENT|MOCK_SENT|FAILED|SKIPPED
    error_message = Column(Text, nullable=True)
    escalation_status = Column(String(30), default="NORMAL")
    risk_score = Column(Float, nullable=True)
    dry_run = Column(Boolean, default=True)


class EscalationRecord(Base):
    """Records of invoices escalated to legal review (stage 5)."""
    __tablename__ = "escalations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    invoice_id = Column(String(100), nullable=False, index=True)
    client_name = Column(String(200), nullable=False)
    client_email = Column(String(200), nullable=True)
    amount_due = Column(Float, nullable=False)
    days_overdue = Column(Integer, nullable=False)
    risk_score = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(String(100), nullable=True)


class EmailHistory(Base):
    """Detailed history of every email sent (or mock-sent)."""
    __tablename__ = "email_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String(64), nullable=True, index=True)
    sent_at = Column(DateTime, default=datetime.utcnow, index=True)
    invoice_id = Column(String(100), nullable=False, index=True)
    client_name = Column(String(200), nullable=False)
    recipient_email = Column(String(200), nullable=False)
    subject = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    escalation_stage = Column(Integer, nullable=True)
    tone = Column(String(50), nullable=True)
    amount_due = Column(Float, nullable=True)
    days_overdue = Column(Integer, nullable=True)
    dry_run = Column(Boolean, default=True)
    send_status = Column(String(20), nullable=False)
    error_message = Column(Text, nullable=True)


def init_db() -> None:
    """Create all tables in the database (idempotent)."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database initialised — all tables ready.")


def reset_db() -> None:
    """Drop and recreate all tables. USE WITH CAUTION."""
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.warning("Database reset — all tables dropped and recreated.")
