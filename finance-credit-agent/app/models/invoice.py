"""
app/models/invoice.py
─────────────────────
Pydantic models for invoice data validation and type safety.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


class Currency(str, Enum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    INR = "INR"
    CAD = "CAD"
    AUD = "AUD"


class InvoiceStatus(str, Enum):
    PENDING = "PENDING"
    OVERDUE = "OVERDUE"
    PAID = "PAID"
    DISPUTED = "DISPUTED"
    ESCALATED = "ESCALATED"
    WRITTEN_OFF = "WRITTEN_OFF"


class Invoice(BaseModel):
    """Validated invoice record from CSV/Excel ingestion."""

    invoice_id: str = Field(..., min_length=1, max_length=100, description="Unique invoice identifier")
    client_name: str = Field(..., min_length=1, max_length=200, description="Full legal name of the client")
    client_email: str = Field(..., description="Client's billing contact email")
    amount_due: float = Field(..., gt=0, description="Outstanding amount in base currency")
    due_date: date = Field(..., description="Payment due date")
    invoice_date: date = Field(..., description="Date invoice was issued")
    currency: Currency = Field(default=Currency.USD, description="Invoice currency")
    payment_terms: str = Field(default="Net 30", description="Payment terms label")
    contact_phone: Optional[str] = Field(default=None, description="Client phone (optional)")
    notes: Optional[str] = Field(default=None, max_length=500, description="Internal notes")
    status: InvoiceStatus = Field(default=InvoiceStatus.PENDING)

    # ── Computed at runtime ──────────────────────────────────
    days_overdue: Optional[int] = Field(default=None, description="Days past due (set by overdue_node)")
    escalation_stage: Optional[int] = Field(default=None, description="1–5 escalation stage")
    risk_score: Optional[float] = Field(default=None, ge=0, le=100, description="AI-generated risk score")

    @field_validator("client_email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError(f"Invalid email format: {v}")
        return v

    @field_validator("client_name")
    @classmethod
    def sanitize_client_name(cls, v: str) -> str:
        """Strip dangerous characters to prevent prompt injection via names."""
        stripped = v.strip()
        # Remove characters that could break prompt templates
        for ch in ["{", "}", "<", ">", "\\", "|"]:
            stripped = stripped.replace(ch, "")
        return stripped

    @field_validator("invoice_id")
    @classmethod
    def sanitize_invoice_id(cls, v: str) -> str:
        import re
        if not re.match(r"^[A-Za-z0-9\-_#.]+$", v.strip()):
            raise ValueError(f"Invoice ID contains invalid characters: {v}")
        return v.strip()

    @field_validator("notes")
    @classmethod
    def sanitize_notes(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        # Truncate and sanitize
        return v.strip()[:500]

    @model_validator(mode="after")
    def validate_date_order(self) -> "Invoice":
        if self.invoice_date > self.due_date:
            raise ValueError("invoice_date cannot be after due_date")
        return self

    class Config:
        use_enum_values = True


class InvoiceBatch(BaseModel):
    """A batch of validated invoices."""
    invoices: list[Invoice] = Field(default_factory=list)
    source_file: str = Field(default="")
    loaded_at: datetime = Field(default_factory=datetime.utcnow)
    total_count: int = Field(default=0)
    error_count: int = Field(default=0)
    errors: list[str] = Field(default_factory=list)
