# tests/test_graph.py
from __future__ import annotations
import pytest
from datetime import date, timedelta
from unittest.mock import patch


def test_graph_builds():
    from app.graph.graph_builder import build_graph
    graph = build_graph()
    assert graph is not None


def test_stage_determination():
    from app.nodes.stage_node import _determine_stage
    assert _determine_stage(3) == 1
    assert _determine_stage(10) == 2
    assert _determine_stage(18) == 3
    assert _determine_stage(25) == 4
    assert _determine_stage(35) == 5
    assert _determine_stage(0) == 1


def test_overdue_node():
    from app.nodes.overdue_node import overdue_node
    from app.models.invoice import Invoice, InvoiceStatus
    from app.models.invoice import InvoiceBatch

    inv = Invoice(
        invoice_id="INV-OV-001",
        client_name="Overdue Client",
        client_email="test@example.org",
        amount_due=1000.0,
        due_date=date.today() - timedelta(days=5),
        invoice_date=date.today() - timedelta(days=35),
    )
    batch = InvoiceBatch(invoices=[inv])
    state = {"invoice_batch": batch}
    result = overdue_node(state)
    assert len(result["overdue_invoices"]) == 1
    assert result["overdue_invoices"][0].days_overdue == 5


def test_fallback_email_generation(sample_invoice):
    from app.prompts.output_parser import build_fallback_email
    sample_invoice.escalation_stage = 2
    sample_invoice.days_overdue = 10
    email = build_fallback_email(sample_invoice, 2, "test")
    assert sample_invoice.invoice_id in email.body
    assert sample_invoice.client_name in email.body
    assert email.escalation_stage == 2
    assert email.requires_legal_review is False
