"""
app/services/invoice_loader.py
───────────────────────────────
CSV and Excel invoice ingestion with pandas.
Handles malformed data, missing columns, and type coercion.
"""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.config.constants import OPTIONAL_INVOICE_COLUMNS, REQUIRED_INVOICE_COLUMNS
from app.models.invoice import Invoice, InvoiceBatch
from app.utils.sanitizer import sanitize_invoice_row
from app.utils.validators import validate_invoice_row

logger = logging.getLogger(__name__)


def load_invoices_from_file(file_path: str) -> InvoiceBatch:
    """
    Load invoices from CSV or Excel file.
    Returns an InvoiceBatch with validated invoices and any errors.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Invoice file not found: {file_path}")

    logger.info(f"Loading invoices from: {file_path}")

    ext = path.suffix.lower()
    try:
        if ext == ".csv":
            df = pd.read_csv(file_path, dtype=str, keep_default_na=False)
        elif ext in (".xlsx", ".xls"):
            df = pd.read_excel(file_path, dtype=str, keep_default_na=False)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Use .csv or .xlsx")
    except Exception as e:
        raise IOError(f"Failed to read file {file_path}: {e}") from e

    # Normalize column names
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

    # Check for required columns
    missing_cols = [c for c in REQUIRED_INVOICE_COLUMNS if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}. Found: {list(df.columns)}")

    batch = InvoiceBatch(source_file=file_path, total_count=len(df))
    invoices = []
    errors = []

    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        row_num = idx + 2  # 1-indexed + header row

        try:
            # Validate raw row
            is_valid, row_errors = validate_invoice_row(row_dict)
            if not is_valid:
                for err in row_errors:
                    errors.append(f"Row {row_num}: {err}")
                continue

            # Sanitize and check for injection
            sanitized = sanitize_invoice_row(row_dict)

            # Parse dates
            sanitized["due_date"] = _parse_date(sanitized.get("due_date", ""))
            sanitized["invoice_date"] = _parse_date(sanitized.get("invoice_date", ""))

            if not sanitized["due_date"] or not sanitized["invoice_date"]:
                errors.append(f"Row {row_num}: Invalid date format in due_date or invoice_date")
                continue

            # Parse amount
            sanitized["amount_due"] = float(str(sanitized["amount_due"]).replace(",", "").replace("$", "").strip())

            # Fill optional fields with defaults
            sanitized.setdefault("currency", "USD")
            sanitized.setdefault("payment_terms", "Net 30")

            # Build Pydantic model
            invoice = Invoice(**sanitized)
            invoices.append(invoice)

        except Exception as e:
            errors.append(f"Row {row_num}: {str(e)}")
            logger.warning(f"Skipping row {row_num}: {e}")
            continue

    batch.invoices = invoices
    batch.error_count = len(errors)
    batch.errors = errors

    logger.info(
        f"Loaded {len(invoices)} valid invoices, {len(errors)} errors from {path.name}"
    )
    return batch


def _parse_date(value: Any) -> Optional[date]:
    """Try multiple date formats to parse a date value."""
    if isinstance(value, date):
        return value

    formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%m-%d-%Y", "%Y/%m/%d"]
    str_val = str(value).strip()

    for fmt in formats:
        try:
            return pd.to_datetime(str_val, format=fmt).date()
        except Exception:
            continue

    # Last resort: let pandas infer
    try:
        return pd.to_datetime(str_val, infer_datetime_format=True).date()
    except Exception:
        return None


def load_sample_data() -> InvoiceBatch:
    """Load the bundled sample CSV file."""
    sample_path = Path("data/sample_invoices.csv")
    if not sample_path.exists():
        raise FileNotFoundError("Sample data not found. Run: python run.py --generate-samples")
    return load_invoices_from_file(str(sample_path))
