"""
app/services/risk_scorer.py
────────────────────────────
AI-generated payment risk scoring.

Generates a 0-100 risk score for each invoice based on:
- Days overdue
- Amount due
- Escalation stage
- Historical patterns (heuristic)

Can be extended to call LLM for advanced scoring.
"""

from __future__ import annotations

import logging
from typing import Optional

from app.config.constants import RISK_SCORE_THRESHOLDS
from app.models.invoice import Invoice

logger = logging.getLogger(__name__)


def calculate_risk_score(invoice: Invoice) -> float:
    """
    Calculate a payment risk score (0-100) using heuristic rules.

    Scoring factors:
    - Days overdue (max 40 points)
    - Amount due magnitude (max 20 points)
    - Escalation stage (max 30 points)
    - Missing contact info penalty (max 10 points)

    Returns: float between 0.0 and 100.0
    """
    score = 0.0
    days = invoice.days_overdue or 0
    stage = invoice.escalation_stage or 1

    # Days overdue component (0–40 points)
    if days <= 7:
        score += (days / 7) * 15
    elif days <= 14:
        score += 15 + ((days - 7) / 7) * 10
    elif days <= 21:
        score += 25 + ((days - 14) / 7) * 8
    elif days <= 30:
        score += 33 + ((days - 21) / 9) * 7
    else:
        score += 40  # Max days component

    # Amount due component (0–20 points)
    amount = invoice.amount_due
    if amount < 1_000:
        score += 2
    elif amount < 10_000:
        score += 8
    elif amount < 50_000:
        score += 14
    elif amount < 100_000:
        score += 18
    else:
        score += 20

    # Escalation stage component (0–30 points)
    stage_scores = {1: 5, 2: 12, 3: 20, 4: 27, 5: 30}
    score += stage_scores.get(stage, 5)

    # Missing contact info penalty (0–10 points)
    if not invoice.contact_phone:
        score += 5
    if not invoice.notes:
        score += 2
    if invoice.client_email.endswith(("gmail.com", "yahoo.com", "hotmail.com")):
        # Personal email for corporate invoice = higher risk
        score += 3

    # Cap at 100
    final_score = min(score, 100.0)
    logger.debug(f"Risk score for {invoice.invoice_id}: {final_score:.1f}")
    return round(final_score, 1)


def get_risk_label(score: float) -> str:
    """Return a human-readable risk label for a score."""
    for label, (low, high) in RISK_SCORE_THRESHOLDS.items():
        if low <= score <= high:
            return label.upper()
    return "UNKNOWN"


def score_invoice_batch(invoices: list[Invoice]) -> list[Invoice]:
    """Apply risk scoring to a list of invoices in-place."""
    for invoice in invoices:
        invoice.risk_score = calculate_risk_score(invoice)
    return invoices
