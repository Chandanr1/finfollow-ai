"""
app/config/settings.py
─────────────────────
Centralised settings loaded from .env via pydantic-settings.
All configuration is validated at startup.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional

from pydantic import EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings validated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── OpenAI ──────────────────────────────────────────────
    openai_api_key: str = "sk-placeholder"
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 1500
    openai_temperature: float = 0.3

    # ── LangSmith ───────────────────────────────────────────
    langchain_tracing_v2: bool = False
    langchain_api_key: Optional[str] = None
    langchain_project: str = "finance-credit-agent"

    # ── Email / SMTP ─────────────────────────────────────────
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    email_from_name: str = "Finance Collections Team"
    email_from_address: str = "collections@yourcompany.com"
    email_dry_run: bool = True

    # ── Company ──────────────────────────────────────────────
    company_name: str = "Acme Finance Ltd"
    company_payment_url: str = "https://pay.acmefinance.com/invoice"
    company_contact_email: str = "accounts@acmefinance.com"
    company_contact_phone: str = "+1-800-555-0100"
    company_legal_department: str = "legal@acmefinance.com"

    # ── Database ─────────────────────────────────────────────
    database_url: str = "sqlite:///./finance_agent.db"

    # ── Scheduler ────────────────────────────────────────────
    scheduler_enabled: bool = False
    scheduler_interval_hours: int = 24
    scheduler_start_hour: int = 9
    scheduler_timezone: str = "UTC"

    # ── Security / Resilience ────────────────────────────────
    max_retries: int = 3
    rate_limit_per_minute: int = 60
    log_level: str = "INFO"
    mask_pii_in_logs: bool = True

    # ── FastAPI ──────────────────────────────────────────────
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True

    @field_validator("openai_temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v

    @field_validator("smtp_port")
    @classmethod
    def validate_smtp_port(cls, v: int) -> int:
        if v not in (25, 465, 587, 2525):
            raise ValueError(f"Unexpected SMTP port: {v}")
        return v

    @property
    def langsmith_enabled(self) -> bool:
        return self.langchain_tracing_v2 and bool(self.langchain_api_key)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance (singleton)."""
    return Settings()
