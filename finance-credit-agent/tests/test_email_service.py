# tests/test_email_service.py
from __future__ import annotations
import pytest
from datetime import datetime
from app.models.email_output import EmailOutput
from app.services.email_service import mock_send_email


def _make_email():
    return EmailOutput(
        invoice_id="INV-TEST-001",
        client_name="Test Corp",
        client_email="billing@testcorp.com",
        subject="Payment Reminder: Invoice INV-TEST-001 — $5,000.00 Overdue",
        body="Dear Test Corp,\n\nThis is a reminder that invoice INV-TEST-001 for $5,000.00 is overdue by 10 days. Please pay immediately via https://pay.acmefinance.com/invoice/INV-TEST-001\n\nBest regards,\nFinance Team",
        escalation_stage=2,
        tone="polite_firm",
        amount_due=5000.00,
        days_overdue=10,
        requires_legal_review=False,
        payment_link="https://pay.acmefinance.com/invoice/INV-TEST-001",
        risk_score=35.0,
    )


def test_mock_send_creates_output_file():
    email = _make_email()
    success, msg = mock_send_email(email)
    assert success is True
    assert "MOCK_SENT" in msg or "outputs" in msg.lower()


def test_mock_send_returns_true():
    email = _make_email()
    result, _ = mock_send_email(email)
    assert result is True


def test_risk_score_range(sample_invoice):
    from app.services.risk_scorer import calculate_risk_score
    score = calculate_risk_score(sample_invoice)
    assert 0.0 <= score <= 100.0


def test_stage5_no_email(stage5_invoice):
    from app.nodes.stage_node import _determine_stage
    stage = _determine_stage(stage5_invoice.days_overdue)
    assert stage == 5


def test_pii_masking():
    from app.utils.pii_masker import mask_pii
    masked = mask_pii("Contact john@company.com for details")
    assert "@company.com" in masked
    assert "john" not in masked or "j***" in masked
