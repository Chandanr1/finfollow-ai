"""
app/config/constants.py
───────────────────────
Escalation matrix, stage metadata, and application-wide constants.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class EscalationStageConfig:
    stage: int
    label: str
    min_days: int
    max_days: int          # inclusive; -1 means unbounded
    tone: str
    send_email: bool
    description: str
    color: str             # for UI badge colour


ESCALATION_MATRIX: Dict[int, EscalationStageConfig] = {
    1: EscalationStageConfig(
        stage=1,
        label="Stage 1 — Warm & Friendly",
        min_days=1,
        max_days=7,
        tone="warm_friendly",
        send_email=True,
        description="Gentle reminder; assume the client may have overlooked the invoice.",
        color="#4CAF50",
    ),
    2: EscalationStageConfig(
        stage=2,
        label="Stage 2 — Polite but Firm",
        min_days=8,
        max_days=14,
        tone="polite_firm",
        send_email=True,
        description="Second notice; politely insist on payment and note potential late fees.",
        color="#FF9800",
    ),
    3: EscalationStageConfig(
        stage=3,
        label="Stage 3 — Formal & Serious",
        min_days=15,
        max_days=21,
        tone="formal_serious",
        send_email=True,
        description="Formal demand; reference contractual terms and mention consequences.",
        color="#F44336",
    ),
    4: EscalationStageConfig(
        stage=4,
        label="Stage 4 — Stern & Urgent",
        min_days=22,
        max_days=30,
        tone="stern_urgent",
        send_email=True,
        description="Final notice before legal/collections referral.",
        color="#9C27B0",
    ),
    5: EscalationStageConfig(
        stage=5,
        label="Stage 5 — Legal Review",
        min_days=31,
        max_days=-1,
        tone="none",
        send_email=False,
        description="Do NOT email. Flag for legal/manual finance review immediately.",
        color="#212121",
    ),
}

# Required columns in invoice CSV/Excel
REQUIRED_INVOICE_COLUMNS = [
    "invoice_id",
    "client_name",
    "client_email",
    "amount_due",
    "due_date",
    "invoice_date",
]

OPTIONAL_INVOICE_COLUMNS = [
    "currency",
    "payment_terms",
    "contact_phone",
    "notes",
]

# Prompt injection patterns to detect
PROMPT_INJECTION_PATTERNS = [
    "ignore previous instructions",
    "disregard all prior",
    "forget everything",
    "you are now",
    "act as",
    "roleplay as",
    "jailbreak",
    "system:",
    "user:",
    "assistant:",
    "<|im_start|>",
    "<|im_end|>",
    "<!-- inject",
]

# PII patterns for log masking
PII_PATTERNS = {
    "email": r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}",
    "phone": r"(\+?[\d\-\s\(\)]{7,15})",
    "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
}

# Risk score thresholds
RISK_SCORE_THRESHOLDS = {
    "low": (0, 30),
    "medium": (31, 60),
    "high": (61, 85),
    "critical": (86, 100),
}

# Audit log statuses
EMAIL_STATUS_SENT = "SENT"
EMAIL_STATUS_MOCK = "MOCK_SENT"
EMAIL_STATUS_FAILED = "FAILED"
EMAIL_STATUS_SKIPPED = "SKIPPED"

ESCALATION_STATUS_NORMAL = "NORMAL"
ESCALATION_STATUS_ESCALATED = "ESCALATED_LEGAL"
