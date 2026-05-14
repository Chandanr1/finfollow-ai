# Finance Credit Follow-Up Email Agent

> **Production-grade AI Finance Automation System**  
> Built with LangGraph · LangChain · GPT-4o-mini · Streamlit · SQLite

---

## Project Overview

The **Finance Credit Follow-Up Email Agent** is an autonomous AI system that reads overdue invoice records, determines the appropriate escalation stage, generates personalised professional follow-up emails using GPT-4o-mini, sends or mock-sends them, and logs every action in a tamper-proof audit trail. A real-time Streamlit dashboard provides full operational visibility.

This project is designed to simulate a real SaaS-grade finance automation product with production-quality code, security controls, and observability.

---

## Features

| Feature | Status |
|---|---|
| CSV / Excel invoice ingestion | ✅ |
| Automatic overdue detection | ✅ |
| 5-stage escalation engine | ✅ |
| AI email generation (GPT-4o-mini) | ✅ |
| Email personalisation (per-invoice data) | ✅ |
| SMTP send + dry-run mock mode | ✅ |
| SQLite audit logging | ✅ |
| JSON structured logs (JSONL) | ✅ |
| Stage 5 legal escalation | ✅ |
| AI payment risk scoring (0–100) | ✅ |
| Streamlit dashboard | ✅ |
| LangGraph workflow | ✅ |
| Pydantic structured outputs | ✅ |
| Prompt injection protection | ✅ |
| PII masking in logs | ✅ |
| Retry with exponential backoff | ✅ |
| APScheduler automation | ✅ |
| LangSmith tracing (optional) | ✅ |
| Docker support | ✅ |
| Unit tests | ✅ |

---

## Architecture

```
                        ┌──────────────────────────────────────────┐
                        │         LangGraph StateGraph             │
                        │                                          │
  CSV/Excel ──────►  load_node ──► validate_node ──► overdue_node │
                        │                                  │       │
                        │                            stage_node    │
                        │                                  │       │
                        │                         email_gen_node   │
                        │                     (GPT-4o-mini + LLM) │
                        │                                  │       │
                        │                    email_validate_node   │
                        │                                  │       │
                        │               send_node (SMTP/mock)      │
                        │                                  │       │
                        │                          audit_node      │
                        │                                  │       │
                        │                        escalate_node     │
                        │                                  │       │
                        │                         finalize_node    │
                        └──────────────────────────────────────────┘
                                           │
                    ┌──────────────────────┴────────────────────────┐
                    │                                               │
               SQLite DB                                    Streamlit UI
          (invoices, audit_logs,                         (KPIs, charts,
           escalations,                                   email preview,
           email_history)                                 audit log)
```

---

## Escalation Matrix

| Stage | Days Overdue | Tone | Action |
|---|---|---|---|
| 1 | 1–7 days | Warm & Friendly | Send reminder email |
| 2 | 8–14 days | Polite but Firm | Second notice with late fee warning |
| 3 | 15–21 days | Formal & Serious | Formal demand with consequence notice |
| 4 | 22–30 days | Stern & Urgent | Final notice before collections |
| 5 | >30 days | N/A | **NO EMAIL** — Flag for legal review |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| AI Agent Framework | LangGraph, LangChain |
| LLM | OpenAI GPT-4o-mini |
| Structured Output | Pydantic v2 |
| Dashboard | Streamlit |
| Database | SQLite via SQLAlchemy |
| Data Processing | pandas |
| Email | smtplib (SMTP) + dry-run mode |
| Scheduling | APScheduler |
| Observability | LangSmith (optional) |
| Resilience | tenacity (retry + backoff) |
| Security | dotenv, input sanitization, PII masking |

---

## LLM Choice Justification

**GPT-4o-mini** was chosen because:
- Best cost/quality ratio for high-volume batch email generation
- Excellent instruction-following for structured JSON output
- Fast response times (< 2s per email)
- Native JSON mode compatible with Pydantic output parsers
- Sufficient context window for invoice data + tone instructions

---

## LangGraph Architecture

The workflow is implemented as a **StateGraph** with:
- **Typed shared state** (`AgentState` TypedDict) passed between all nodes
- **Conditional routing** — fatal errors short-circuit to abort node; no-overdue path skips email generation
- **10 nodes**: load → validate → overdue → stage → email_gen → email_validate → send → audit → escalate → finalize
- **Compiled graph** (singleton) for performance
- **Idempotent** — safe to re-run; upserts invoices rather than duplicating

---

## Prompt Engineering Strategy

1. **System prompt** defines the AI's role, company context, and strict data-usage rules
2. **Stage-specific tone prompts** injected dynamically per escalation stage
3. **Structured JSON output requirement** in every prompt — forces parseable output
4. **Anti-hallucination guardrails** — LLM instructed to use only provided data
5. **Output validation** post-generation — checks invoice ID, client name, amount in body
6. **Fallback templates** — if LLM fails/times out, a rule-based template is used

---

## Security Mitigations

| Risk | Mitigation |
|---|---|
| Prompt injection via invoice data | Pattern detection in `sanitizer.py`; data values escaped before prompt injection |
| Hallucinated invoice data | Post-generation validation checks real data appears in email body |
| API key exposure | `.env` file; never hardcoded; `python-dotenv` |
| PII in logs | `pii_masker.py` masks emails and phone numbers before writing to log |
| SMTP spoofing | From address validated; Reply-To set to accounts contact |
| Input validation | Pydantic v2 validators on all Invoice fields |
| Rate limiting | Configured via `RATE_LIMIT_PER_MINUTE` env var |
| Malformed CSV | Row-level error handling with error accumulation (does not crash) |

---

## Setup Instructions

### 1. Clone / navigate to project

```bash
cd finance-credit-agent
```

### 2. Create virtual environment

```bash
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate  # Linux/Mac
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env — set OPENAI_API_KEY at minimum
```

### 5. Run the agent

```bash
# Windows (fixes Unicode in terminal)
set PYTHONUTF8=1
python run.py

# Linux/Mac
python run.py
```

### 6. Launch dashboard

```bash
streamlit run app/ui/dashboard.py
# Open http://localhost:8501
```

---

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | **Required** for AI email generation |
| `OPENAI_MODEL` | `gpt-4o-mini` | LLM model to use |
| `EMAIL_DRY_RUN` | `true` | Set `false` to send real emails |
| `SMTP_HOST` | `smtp.gmail.com` | SMTP server |
| `SMTP_USERNAME` | — | SMTP login |
| `SMTP_PASSWORD` | — | SMTP app password |
| `COMPANY_NAME` | `Acme Finance Ltd` | Your company name |
| `COMPANY_PAYMENT_URL` | — | Payment portal base URL |
| `LANGCHAIN_TRACING_V2` | `false` | Enable LangSmith |
| `LANGCHAIN_API_KEY` | — | LangSmith API key |
| `MASK_PII_IN_LOGS` | `true` | Mask emails/phones in logs |
| `DATABASE_URL` | `sqlite:///./finance_agent.db` | DB connection string |

---

## Running the Project

```bash
# Dry-run (default) — no real emails sent
python run.py

# Live mode — real SMTP emails
python run.py --live

# Custom invoice file
python run.py --file data/my_invoices.xlsx

# Generate sample Excel from CSV
python run.py --generate-samples

# Start scheduler daemon
python run.py --scheduler

# Run tests
pytest tests/ -v

# Dashboard
streamlit run app/ui/dashboard.py
```

---

## Database Schema

```sql
-- invoices: persisted snapshot of all loaded invoices
CREATE TABLE invoices (
    id INTEGER PRIMARY KEY,
    invoice_id TEXT UNIQUE NOT NULL,
    client_name TEXT, client_email TEXT,
    amount_due REAL, currency TEXT,
    due_date TEXT, invoice_date TEXT,
    days_overdue INTEGER, escalation_stage INTEGER,
    status TEXT, risk_score REAL,
    payment_terms TEXT, contact_phone TEXT, notes TEXT,
    created_at DATETIME, updated_at DATETIME
);

-- audit_logs: complete action trail
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY,
    run_id TEXT, timestamp DATETIME,
    invoice_id TEXT, client_name TEXT, client_email TEXT,
    escalation_stage INTEGER, days_overdue INTEGER,
    email_subject TEXT, email_body TEXT,
    send_status TEXT, error_message TEXT,
    escalation_status TEXT, risk_score REAL, dry_run BOOLEAN
);

-- escalations: legal escalation records
CREATE TABLE escalations (
    id INTEGER PRIMARY KEY,
    run_id TEXT, timestamp DATETIME,
    invoice_id TEXT, client_name TEXT, client_email TEXT,
    amount_due REAL, days_overdue INTEGER, risk_score REAL,
    notes TEXT, resolved BOOLEAN, resolved_at DATETIME, resolved_by TEXT
);

-- email_history: per-email send record
CREATE TABLE email_history (
    id INTEGER PRIMARY KEY,
    run_id TEXT, sent_at DATETIME,
    invoice_id TEXT, client_name TEXT, recipient_email TEXT,
    subject TEXT, body TEXT,
    escalation_stage INTEGER, tone TEXT,
    amount_due REAL, days_overdue INTEGER,
    dry_run BOOLEAN, send_status TEXT, error_message TEXT
);
```

---

## Sample Output (Mock Email)

```json
{
  "mode": "DRY_RUN",
  "from": "Finance Collections Team <collections@acmefinance.com>",
  "to": "billing@apextech.com",
  "subject": "Payment Reminder: Invoice INV-2024-001 — USD 15,750.00 Overdue",
  "invoice_id": "INV-2024-001",
  "client_name": "Apex Technologies Ltd",
  "amount_due": 15750.0,
  "days_overdue": 8,
  "escalation_stage": 2,
  "tone": "polite_firm"
}
```

---

## Future Improvements

- [ ] Multi-tenant support (per-company configurations)
- [ ] REST API (FastAPI) for external integrations
- [ ] PDF invoice attachment generation
- [ ] Email open/click tracking
- [ ] Human approval workflow for Stage 4 emails
- [ ] ML-based payment prediction (beyond heuristic risk scoring)
- [ ] Slack/Teams notification for escalations
- [ ] OAuth2 email authentication
- [ ] Multi-language email support

---

## Why This Project Stands Out

1. **Production architecture** — not a tutorial script. Real separation of concerns, proper dependency injection, singleton patterns.
2. **LangGraph correctness** — proper `TypedDict` state, conditional routing, compiled graph.
3. **Security-first** — prompt injection protection, PII masking, input sanitization, structured validation.
4. **Zero hallucinations** — post-generation validation ensures every email contains real invoice data.
5. **Operational resilience** — tenacity retries, fallback email templates, non-crashing error handling.
6. **Complete observability** — JSON audit logs, SQLite audit trail, Streamlit dashboard, optional LangSmith.
7. **Works without an API key** — dry-run + fallback mode means the entire system runs demonstrably without spending money.
