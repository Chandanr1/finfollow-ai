# Finance Credit Follow-Up Email Agent
## Complete Project Report

---

## Dashboard — Live Preview

![Finance Agent Dashboard running at localhost:8501](C:\Users\umr81\.gemini\antigravity\brain\7657d91e-eee3-4b41-b42a-3cbb64021802\dashboard_screenshot.webp)

---

## 1. What Is This Project?

The **Finance Credit Follow-Up Email Agent** is a fully autonomous AI system built to automate one of the most manual, repetitive, and high-stakes tasks in any finance team: **chasing overdue invoices**.

In most companies, a finance analyst has to:
- Manually check which invoices are overdue
- Decide what tone to use based on how long they've been unpaid
- Write a personalised email for each client
- Send the email, log it, and escalate severe cases

This agent does **all of that automatically**, end-to-end, using:
- A LangGraph AI workflow that mirrors a real human decision process
- OpenAI GPT-4o-mini to write personalised professional emails
- A SQLite database that remembers every action
- A Streamlit dashboard so finance managers can monitor everything in real time

> **Think of it as hiring a tireless AI collections assistant who works 24/7, never sends the wrong tone, never forgets to log, and automatically escalates the worst accounts to your legal team.**

---

## 2. What Problem Does It Solve?

| Pain Point | How the Agent Solves It |
|---|---|
| Manual invoice checking | Automatically loads CSV/Excel and detects overdue invoices |
| Inconsistent tone in chasing emails | Escalation matrix enforces exact tone per days overdue |
| Generic copy-paste emails | GPT-4o-mini writes personalised emails per client with real invoice data |
| No audit trail | Every action logged to SQLite + JSONL audit file |
| Missing legal escalations | Stage 5 (>30 days) auto-flags accounts for legal review |
| Lack of visibility | Real-time Streamlit dashboard with KPI cards, charts, tables |
| Human error / hallucinated data | Post-generation validation checks real invoice data appears in email body |

---

## 3. How It Works — End-to-End Flow

```
┌─────────────────────────────────────────────────────────────┐
│                 AGENT WORKFLOW (LangGraph)                   │
│                                                             │
│  1. LOAD          Read CSV / Excel invoice file             │
│       │                                                     │
│  2. VALIDATE      Check all required fields, save to DB     │
│       │                                                     │
│  3. DETECT OVERDUE  Compare due_date vs today               │
│       │                                                     │
│  4. STAGE         Assign escalation stage 1–5               │
│       │           + Calculate AI risk score (0–100)         │
│       │                                                     │
│  5. GENERATE EMAIL  Call GPT-4o-mini with stage prompt      │
│       │           Fallback template if LLM unavailable      │
│       │                                                     │
│  6. VALIDATE EMAIL  Check invoice data in email body        │
│       │                                                     │
│  7. SEND          SMTP send OR mock-send (dry-run)          │
│       │           Save email JSON to outputs/               │
│       │                                                     │
│  8. AUDIT LOG     Write to SQLite + JSONL log file          │
│       │                                                     │
│  9. ESCALATE      Stage 5 → legal escalation DB record      │
│       │                                                     │
│ 10. FINALIZE      Compute run stats → dashboard refresh     │
└─────────────────────────────────────────────────────────────┘
```

### Escalation Matrix (The Core Logic)

| Stage | Days Overdue | Tone | Email Sent? |
|---|---|---|---|
| **Stage 1** | 1 – 7 days | Warm & Friendly | ✅ Yes |
| **Stage 2** | 8 – 14 days | Polite but Firm | ✅ Yes |
| **Stage 3** | 15 – 21 days | Formal & Serious | ✅ Yes |
| **Stage 4** | 22 – 30 days | Stern & Urgent | ✅ Yes |
| **Stage 5** | > 30 days | N/A | ❌ No — Legal Review |

---

## 4. Tech Stack (With Reasons)

| Layer | Technology | Why Chosen |
|---|---|---|
| **Language** | Python 3.11+ | Industry standard for AI/ML |
| **AI Framework** | LangChain + LangGraph | LangGraph enables multi-step stateful agent workflows — far superior to simple LLM calls |
| **LLM** | OpenAI GPT-4o-mini | Best cost/quality ratio; excellent JSON output mode; fast (< 2s/email) |
| **Structured Output** | Pydantic v2 | Validates every field in/out; prevents hallucinations reaching the database |
| **Dashboard** | Streamlit | Fastest way to build a professional Python data dashboard |
| **Database** | SQLite + SQLAlchemy | Zero-setup, file-based, production-ready for this scale |
| **Data** | pandas | Industry standard for CSV/Excel processing |
| **Email** | smtplib + dry-run | Built-in Python; dry-run means safe to demo without sending real emails |
| **Scheduling** | APScheduler | Pure Python scheduler; runs agent on a cron-like schedule |
| **Resilience** | tenacity | Automatic retry with exponential backoff for LLM and SMTP calls |
| **Security** | dotenv, PII masker, sanitizer | Environment variables never hardcoded; emails masked in logs |
| **Observability** | LangSmith (optional) | Traces every LLM call for debugging and cost tracking |

---

## 5. Project Folder Structure

```
finance-credit-agent/
│
├── app/                         ← All Python application code
│   ├── agents/
│   │   └── email_agent.py       ← Top-level orchestrator (entry point for graph)
│   │
│   ├── graph/
│   │   └── graph_builder.py     ← Assembles the LangGraph StateGraph
│   │
│   ├── nodes/                   ← One file per workflow step
│   │   ├── load_node.py         ← Step 1: Load invoices
│   │   ├── validate_node.py     ← Step 2: Validate & persist to DB
│   │   ├── overdue_node.py      ← Step 3: Detect overdue
│   │   ├── stage_node.py        ← Step 4: Assign escalation stage
│   │   ├── email_gen_node.py    ← Step 5: Call GPT-4o-mini
│   │   ├── email_validate_node.py ← Step 6: Validate generated email
│   │   ├── send_node.py         ← Step 7: Send / mock-send
│   │   ├── audit_node.py        ← Step 8: Write audit log
│   │   └── escalate_node.py     ← Step 9: Handle legal escalations
│   │
│   ├── prompts/
│   │   ├── system_prompt.py     ← Base LLM system prompt + ChatPromptTemplate
│   │   ├── stage_prompts.py     ← Per-stage tone instructions
│   │   └── output_parser.py     ← JSON parser + fallback email template
│   │
│   ├── services/
│   │   ├── invoice_loader.py    ← CSV/Excel ingestion with pandas
│   │   ├── email_service.py     ← SMTP + dry-run email sender
│   │   ├── risk_scorer.py       ← AI payment risk scoring (0-100)
│   │   └── scheduler.py         ← APScheduler daemon
│   │
│   ├── models/
│   │   ├── invoice.py           ← Invoice Pydantic model
│   │   ├── email_output.py      ← EmailOutput + AuditRecord Pydantic models
│   │   └── agent_state.py       ← LangGraph AgentState TypedDict
│   │
│   ├── database/
│   │   ├── db_setup.py          ← SQLAlchemy ORM + 4 table definitions
│   │   └── db_queries.py        ← CRUD operations for all tables
│   │
│   ├── utils/
│   │   ├── logger.py            ← JSON + console audit logger
│   │   ├── pii_masker.py        ← Email/phone masking in logs
│   │   ├── sanitizer.py         ← Prompt injection detection + input sanitization
│   │   └── validators.py        ← Email format + data validation helpers
│   │
│   ├── config/
│   │   ├── settings.py          ← Pydantic settings loaded from .env
│   │   └── constants.py         ← Escalation matrix + all app constants
│   │
│   └── ui/
│       └── dashboard.py         ← Streamlit dashboard (full UI)
│
├── data/
│   ├── sample_invoices.csv      ← 15 realistic sample invoices
│   └── sample_invoices.xlsx     ← Same data in Excel format
│
├── logs/
│   └── agent_audit.jsonl        ← JSON Lines audit log (auto-created)
│
├── outputs/
│   └── email_INV-*.json         ← Mock-sent emails (one file per email)
│
├── tests/
│   ├── conftest.py              ← Pytest fixtures
│   ├── test_invoice_loader.py   ← Tests for loading, validation, sanitization
│   ├── test_email_service.py    ← Tests for email service, risk scorer, PII
│   └── test_graph.py            ← Tests for graph build, stage logic, overdue
│
├── .env.example                 ← Environment variable template
├── requirements.txt             ← All Python dependencies
├── run.py                       ← CLI entry point
├── Dockerfile                   ← Docker container definition
├── docker-compose.yml           ← Multi-container Docker setup
└── README.md                    ← Full technical documentation
```

---

## 6. Step-by-Step: How to Run the Project

### Prerequisites

- Python 3.11 or 3.13 installed
- pip (comes with Python)
- Windows PowerShell or any terminal
- Internet connection (for pip install)
- Optional: OpenAI API key (project works without one in fallback mode)

---

### STEP 1 — Open the Project Folder

Open PowerShell or Command Prompt and navigate to the project:

```powershell
cd "C:\Users\umr81\Downloads\Finance  Email Agent\finance-credit-agent"
```

---

### STEP 2 — (Optional) Create a Virtual Environment

This keeps your system Python clean:

```powershell
python -m venv venv
venv\Scripts\activate
```

You should see `(venv)` at the start of your prompt.

---

### STEP 3 — Install All Dependencies

```powershell
pip install -r requirements.txt
pip install --upgrade pyarrow
```

Wait for installation to complete (2–5 minutes first time).

---

### STEP 4 — Configure Your Environment

```powershell
# Copy the template
copy .env.example .env
```

Open `.env` in Notepad and update at minimum:

```
OPENAI_API_KEY=sk-your-real-key-here     ← Get from platform.openai.com
EMAIL_DRY_RUN=true                        ← Keep true for safe demo mode
COMPANY_NAME=Your Company Name
COMPANY_PAYMENT_URL=https://pay.yourcompany.com/invoice
```

> **Without an API key?** The project still runs fully! It uses a professional fallback email template instead of GPT-4o-mini. All other features (DB, audit log, dashboard, escalations) work identically.

---

### STEP 5 — Run the Agent

```powershell
# Set UTF-8 encoding (required on Windows)
$env:PYTHONUTF8="1"

# Run with sample data (dry-run by default — no real emails sent)
python run.py
```

**Expected output:**
```
============================================================
  Finance Credit Follow-Up Email Agent
  Mode: DRY RUN (mock)
  File: data/sample_invoices.csv
============================================================

[INFO] Loading from: data/sample_invoices.csv
[INFO] Loaded 15 valid invoices, 0 errors
[INFO] 15 overdue invoices detected
[INFO] 9 invoices staged for email (Stages 1-4)
[INFO] 6 invoices escalated to legal review (Stage 5)
[INFO] Generated 9 emails
[INFO] 9 emails MOCK_SENT → saved to outputs/
[INFO] 15 audit records logged

============================================================
  RUN COMPLETE
============================================================
  total_invoices           : 15
  overdue_invoices         : 15
  emails_sent              : 9
  emails_failed            : 0
  escalated_cases          : 6
  dry_run                  : True
============================================================
```

---

### STEP 6 — Launch the Dashboard

In a **new** PowerShell window:

```powershell
cd "C:\Users\umr81\Downloads\Finance  Email Agent\finance-credit-agent"
$env:PYTHONUTF8="1"
streamlit run app/ui/dashboard.py
```

Then open your browser at: **http://localhost:8501**

The dashboard shows:
- **KPI Cards**: Total Invoices (15), Overdue (6), Emails Sent (27+), Escalated (18+)
- **Bar Chart**: Overdue count per escalation stage
- **Pie Chart**: Payment aging distribution (1-7d, 8-14d, 15-21d, >30d)
- **Area Chart**: Daily email activity over time
- **Invoice Table**: Full register with stage, risk score, status
- **Email Preview**: Click any invoice to preview the generated email
- **Escalations Table**: All Stage 5 legal escalation cases
- **Audit Log**: Every agent action with download button

---

### STEP 7 — Run the Tests

```powershell
$env:PYTHONUTF8="1"
python -m pytest tests/ -v
```

Expected: **14 passed, 0 failed**

---

### Additional Run Modes

```powershell
# Use your own invoice file (CSV or Excel)
python run.py --file data/my_invoices.csv

# Send real emails via SMTP (requires SMTP settings in .env)
python run.py --live

# Generate Excel sample from the CSV
python run.py --generate-samples

# Start the automated scheduler (runs agent daily at 9am)
python run.py --scheduler

# Reset database (WARNING: deletes all data)
python run.py --reset-db
```

---

### Using the Dashboard UI to Trigger the Agent

1. Open **http://localhost:8501**
2. In the left sidebar:
   - Toggle **Dry-Run Mode** ON/OFF
   - Upload a CSV or Excel invoice file (optional)
3. Click **"Run Agent Now"** button
4. Watch the KPI cards and charts update automatically

---

## 7. Sample Generated Email

When the agent runs in dry-run mode, each email is saved to `outputs/` as a JSON file:

**File:** `outputs/email_INV-2024-003_20260514_183256.json`

```json
{
  "mode": "DRY_RUN",
  "from": "Finance Collections Team <collections@yourcompany.com>",
  "to": "finance@bluehorizon.com",
  "subject": "Payment Reminder: Invoice INV-2024-003 — USD 45,000.00 Overdue (23 days)",
  "body": "Dear Blue Horizon Finance,\n\nWe are writing to draw your attention to Invoice INV-2024-003 which remains outstanding.\n\nInvoice Details:\n- Invoice Number: INV-2024-003\n- Amount Due: USD 45,000.00\n- Due Date: 2026-04-22\n- Days Overdue: 23\n\nPlease arrange payment immediately using the link below:\nhttps://pay.acmefinance.com/invoice/INV-2024-003\n\nFor queries, please contact our accounts team:\nEmail: accounts@acmefinance.com\nPhone: +1-800-555-0100\n\nBest regards,\nFinance Collections Team\nAcme Finance Ltd",
  "invoice_id": "INV-2024-003",
  "client_name": "Blue Horizon Finance",
  "amount_due": 45000.0,
  "days_overdue": 23,
  "escalation_stage": 4,
  "tone": "stern_urgent",
  "payment_link": "https://pay.acmefinance.com/invoice/INV-2024-003"
}
```

> **Stage 4 (23 days overdue)** = Stern & Urgent tone. The email is firm, professional, and contains the real invoice number, amount, and personalised payment link.

---

## 8. Database — What Gets Stored

The agent creates a file `finance_agent.db` (SQLite) in the project root. It contains 4 tables:

### `invoices` table
Stores every invoice processed — updated on every run.

| Column | Example |
|---|---|
| invoice_id | INV-2024-001 |
| client_name | Apex Technologies Ltd |
| amount_due | 15750.00 |
| days_overdue | 8 |
| escalation_stage | 2 |
| risk_score | 42.5 |
| status | OVERDUE |

### `audit_logs` table
One row per invoice per run — the complete action trail.

| Column | Example |
|---|---|
| run_id | run_20260514_183256_a83445b9 |
| invoice_id | INV-2024-001 |
| send_status | MOCK_SENT |
| escalation_status | NORMAL |
| email_subject | Payment Reminder: Invoice INV-2024-001... |

### `escalations` table
Only Stage 5 (>30 days) accounts appear here.

| Column | Example |
|---|---|
| invoice_id | INV-2024-011 |
| client_name | Sterling Capital Advisors |
| amount_due | 125000.00 |
| days_overdue | 62 |
| risk_score | 90.0 |

### `email_history` table
Full history of every email sent (including body text).

---

## 9. Security Features

| Feature | How It Works |
|---|---|
| **No hardcoded secrets** | All keys in `.env` file, never in code |
| **Prompt injection protection** | `sanitizer.py` scans all invoice field values for attack patterns before they reach the LLM prompt |
| **PII masking** | `pii_masker.py` replaces email addresses (`j***@company.com`) and phone numbers in all log output |
| **Input validation** | Pydantic v2 models validate every invoice field before processing |
| **Anti-hallucination** | After LLM generates email, code checks that the real invoice ID, client name, and amount appear in the body |
| **Structured output** | LLM is instructed to return only JSON — parsed and validated by Pydantic |
| **Rate limiting** | `RATE_LIMIT_PER_MINUTE` env var limits API call frequency |

---

## 10. AI Risk Scoring

Every overdue invoice gets an AI-generated risk score from **0 to 100**:

| Score Range | Label | Meaning |
|---|---|---|
| 0 – 30 | LOW | Low payment risk, likely just delayed |
| 31 – 60 | MEDIUM | Moderate risk, follow up promptly |
| 61 – 85 | HIGH | High risk, prioritise collections |
| 86 – 100 | CRITICAL | Critical — likely bad debt |

Scored by these factors:
- **Days overdue** (up to 40 points)
- **Amount due** (up to 20 points)
- **Escalation stage** (up to 30 points)
- **Missing contact info** (up to 10 points)

---

## 11. Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError: pyarrow` | Run: `pip install --upgrade pyarrow` |
| `UnicodeEncodeError` in terminal | Run: `$env:PYTHONUTF8="1"` before any command |
| Dashboard shows "No data" | Run `python run.py` first to populate the database |
| `FileNotFoundError: sample_invoices.csv` | Make sure you're in the `finance-credit-agent/` directory |
| `OpenAI API key` error | Set key in `.env` OR leave blank — fallback mode works without it |
| SMTP auth failure | Set `EMAIL_DRY_RUN=true` in `.env` to avoid SMTP entirely |
| Port 8501 already in use | Run: `streamlit run app/ui/dashboard.py --server.port=8502` |

---

## 12. Real-World Usage Scenario

**Your company has 200 overdue invoices each month. Here's what happens:**

1. Your finance team exports overdue invoices to CSV from your ERP system
2. They upload the CSV to the Streamlit dashboard (or drop it in `data/`)
3. They click **"Run Agent Now"**
4. In under 30 seconds:
   - Stages 1–4 invoices get personalised emails (mock-sent or real)
   - Stage 5 accounts are flagged in the escalations table for your legal team
   - Every action is logged with a timestamped audit trail
   - The dashboard updates with all KPIs and charts
5. Your finance manager downloads the audit log CSV for their records

**Time saved: ~4 hours of manual email writing per 200 invoices → 30 seconds.**

---

## 13. What's Next (Future Enhancements)

- **Live OpenAI Mode** — Add your API key and the LLM writes genuinely personalised emails
- **Real SMTP** — Set `EMAIL_DRY_RUN=false` and configure SMTP to send real emails
- **Scheduler** — Run `python run.py --scheduler` to run automatically every day at 9am
- **LangSmith Tracing** — Set `LANGCHAIN_TRACING_V2=true` to see every LLM call traced at langsmith.com
- **Docker** — Run `docker-compose up` to containerise the entire stack
- **Custom Invoice Format** — Any CSV/Excel with the required columns works out of the box

---

*Report generated: 2026-05-15 | Finance Credit Follow-Up Email Agent v1.0*
