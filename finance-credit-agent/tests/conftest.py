# tests/conftest.py
from __future__ import annotations
import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import date, timedelta
from app.models.invoice import Invoice, InvoiceStatus


@pytest.fixture
def sample_invoice():
    return Invoice(
        invoice_id="INV-TEST-001",
        client_name="Test Corp",
        client_email="billing@testcorp.com",
        amount_due=5000.00,
        due_date=date.today() - timedelta(days=10),
        invoice_date=date.today() - timedelta(days=40),
        currency="USD",
        payment_terms="Net 30",
        days_overdue=10,
        escalation_stage=2,
    )


@pytest.fixture
def stage5_invoice():
    return Invoice(
        invoice_id="INV-TEST-005",
        client_name="Deadbeat LLC",
        client_email="noone@deadbeat.com",
        amount_due=99000.00,
        due_date=date.today() - timedelta(days=45),
        invoice_date=date.today() - timedelta(days=75),
        currency="USD",
        payment_terms="Net 30",
        days_overdue=45,
        escalation_stage=5,
    )
