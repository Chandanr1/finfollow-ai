"""
app/services/email_service.py
──────────────────────────────
Email sending service supporting:
- Real SMTP delivery
- Dry-run / mock-send mode (mandatory)
- Retry with exponential backoff
- Output saved to outputs/ directory
"""

from __future__ import annotations

import json
import logging
import smtplib
import time
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional, Tuple

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.config.settings import get_settings
from app.models.email_output import EmailOutput

logger = logging.getLogger(__name__)
settings = get_settings()

OUTPUTS_DIR = Path("outputs")
OUTPUTS_DIR.mkdir(exist_ok=True)


class EmailSendError(Exception):
    """Raised when email delivery fails."""


def send_email(email_out: EmailOutput, dry_run: Optional[bool] = None) -> Tuple[bool, str]:
    """
    Send or mock-send a generated email.

    Args:
        email_out: The generated email to send.
        dry_run: Override the global dry_run setting if provided.

    Returns:
        (success: bool, status_message: str)
    """
    use_dry_run = dry_run if dry_run is not None else settings.email_dry_run

    if use_dry_run:
        return mock_send_email(email_out)
    else:
        return _real_send_email(email_out)


def mock_send_email(email_out: EmailOutput) -> Tuple[bool, str]:
    """
    Simulate email sending in dry-run mode.
    - Logs the email to outputs/ as JSON
    - Does NOT make any SMTP connections
    """
    output_path = OUTPUTS_DIR / f"email_{email_out.invoice_id}_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"

    payload = {
        "mode": "DRY_RUN",
        "timestamp": datetime.utcnow().isoformat(),
        "from": f"{settings.email_from_name} <{settings.email_from_address}>",
        "to": email_out.client_email,
        "subject": email_out.subject,
        "body": email_out.body,
        "invoice_id": email_out.invoice_id,
        "client_name": email_out.client_name,
        "amount_due": email_out.amount_due,
        "days_overdue": email_out.days_overdue,
        "escalation_stage": email_out.escalation_stage,
        "tone": email_out.tone,
        "payment_link": email_out.payment_link,
        "risk_score": email_out.risk_score,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)

    logger.info(
        f"[MOCK_SENT] Invoice={email_out.invoice_id} | "
        f"To={email_out.client_email} | Stage={email_out.escalation_stage} | "
        f"Output={output_path}"
    )
    return True, f"MOCK_SENT — saved to {output_path}"


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((smtplib.SMTPException, ConnectionError, TimeoutError)),
    before_sleep=before_sleep_log(logger, logging.WARNING),
    reraise=True,
)
def _real_send_email(email_out: EmailOutput) -> Tuple[bool, str]:
    """
    Send email via SMTP with retry logic.
    Raises EmailSendError on final failure.
    """
    if not settings.smtp_username or not settings.smtp_password:
        raise EmailSendError("SMTP credentials not configured. Set SMTP_USERNAME and SMTP_PASSWORD.")

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{settings.email_from_name} <{settings.email_from_address}>"
    msg["To"] = email_out.client_email
    msg["Subject"] = email_out.subject
    msg["Reply-To"] = settings.company_contact_email
    msg["X-Mailer"] = "Finance-Credit-Agent/1.0"

    # Plain text part
    text_part = MIMEText(email_out.body, "plain", "utf-8")
    msg.attach(text_part)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(
                settings.email_from_address,
                [email_out.client_email],
                msg.as_string(),
            )

        logger.info(
            f"[SENT] Invoice={email_out.invoice_id} | To={email_out.client_email}"
        )
        return True, "SENT"

    except smtplib.SMTPAuthenticationError as e:
        raise EmailSendError(f"SMTP authentication failed: {e}") from e
    except smtplib.SMTPRecipientsRefused as e:
        raise EmailSendError(f"Recipient refused: {email_out.client_email} — {e}") from e
    except Exception as e:
        raise EmailSendError(f"SMTP error: {e}") from e
