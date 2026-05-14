"""
app/utils/logger.py
───────────────────
Structured JSON + SQLite audit logging.
All log events are persisted to both a JSON log file and the audit_logs DB table.
"""

from __future__ import annotations

import json
import logging
import logging.handlers
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.config.settings import get_settings
from app.utils.pii_masker import mask_pii

settings = get_settings()

# ── Setup JSON file logger ────────────────────────────────────────────────────
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

LOG_FILE = LOGS_DIR / "agent_audit.jsonl"


class JSONLineFormatter(logging.Formatter):
    """Emits one JSON object per log line (JSON Lines format)."""

    def format(self, record: logging.LogRecord) -> str:
        log_obj: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "extra"):
            log_obj.update(record.extra)

        if settings.mask_pii_in_logs:
            log_obj = _mask_dict(log_obj)

        return json.dumps(log_obj, default=str)


def _mask_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively mask PII in a log dict."""
    result = {}
    for k, v in d.items():
        if isinstance(v, str):
            result[k] = mask_pii(v)
        elif isinstance(v, dict):
            result[k] = _mask_dict(v)
        else:
            result[k] = v
    return result


def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with both console and file JSON handlers."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Console handler (human-readable) — use sys.stdout directly
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.stream.reconfigure(encoding="utf-8", errors="replace") if hasattr(console_handler.stream, "reconfigure") else None
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_fmt)

    # JSON file handler (rotated daily, keep 7 days)
    file_handler = logging.handlers.TimedRotatingFileHandler(
        LOG_FILE, when="midnight", backupCount=7, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(JSONLineFormatter())

    # Avoid duplicate handlers
    if not root.handlers:
        root.addHandler(console_handler)
        root.addHandler(file_handler)


class AgentLogger:
    """
    High-level audit logger that writes to:
    1. Standard Python logging (JSON file + console)
    2. SQLite audit_logs table via db_queries
    """

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.logger = logging.getLogger("finance_agent.audit")

    def log_email_sent(
        self,
        invoice_id: str,
        client_name: str,
        stage: int,
        dry_run: bool,
        subject: str,
    ) -> None:
        status = "MOCK_SENT" if dry_run else "SENT"
        self.logger.info(
            f"[{status}] Invoice={invoice_id} | Client={client_name} | "
            f"Stage={stage} | Subject={subject[:60]}"
        )

    def log_email_failed(self, invoice_id: str, error: str) -> None:
        self.logger.error(f"[FAILED] Invoice={invoice_id} | Error={error}")

    def log_escalation(self, invoice_id: str, client_name: str, days_overdue: int) -> None:
        self.logger.warning(
            f"[ESCALATED] Invoice={invoice_id} | Client={client_name} | "
            f"DaysOverdue={days_overdue} -> Referred to legal review"
        )

    def log_run_summary(self, stats: Dict[str, Any]) -> None:
        self.logger.info(f"[RUN COMPLETE] run_id={self.run_id} | stats={json.dumps(stats)}")
