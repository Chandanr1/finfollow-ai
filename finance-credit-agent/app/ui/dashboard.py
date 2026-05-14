"""
app/ui/dashboard.py
────────────────────
Professional Streamlit dashboard for the Finance Credit Follow-Up Email Agent.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

# ── Path setup ────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from app.config.constants import ESCALATION_MATRIX
from app.database.db_setup import init_db
from app.database.db_queries import (
    get_all_invoices,
    get_audit_logs,
    get_dashboard_stats,
    get_email_history,
    get_escalations,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Finance Credit Agent — Dashboard",
    page_icon="💳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.main { background: #0d1117; }

.kpi-card {
    background: linear-gradient(135deg, #1a1f2e 0%, #16213e 100%);
    border: 1px solid #2d3748;
    border-radius: 16px;
    padding: 24px 20px;
    text-align: center;
    transition: transform 0.2s, box-shadow 0.2s;
}
.kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 8px 32px rgba(99,102,241,0.2);
}
.kpi-number {
    font-size: 2.8rem;
    font-weight: 700;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    line-height: 1.1;
}
.kpi-label {
    font-size: 0.85rem;
    color: #94a3b8;
    margin-top: 6px;
    font-weight: 500;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}
.kpi-delta {
    font-size: 0.75rem;
    margin-top: 8px;
    padding: 2px 8px;
    border-radius: 20px;
    display: inline-block;
}

.stage-badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-weight: 600;
    color: white;
}

.section-header {
    font-size: 1.1rem;
    font-weight: 600;
    color: #e2e8f0;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid #2d3748;
}

[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d1117 0%, #1a1f2e 100%);
    border-right: 1px solid #2d3748;
}

.stButton > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.5rem !important;
    transition: all 0.2s !important;
}
.stButton > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 15px rgba(99,102,241,0.4) !important;
}

div[data-testid="metric-container"] {
    background: #1a1f2e;
    border: 1px solid #2d3748;
    border-radius: 12px;
    padding: 12px;
}
</style>
""", unsafe_allow_html=True)

# ── Init DB ───────────────────────────────────────────────────────────────────
init_db()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 💳 Finance Agent")
    st.markdown("**AI-Powered Credit Collections**")
    st.markdown("---")

    # Dry-run toggle
    dry_run = st.toggle("🔒 Dry-Run Mode", value=True, help="When ON, emails are simulated — not actually sent.")
    if dry_run:
        st.success("✅ Dry-run active — emails won't be sent")
    else:
        st.warning("⚠️ Live mode — real emails will be sent!")

    st.markdown("---")

    # File upload
    st.markdown("### 📂 Invoice File")
    uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx"])

    source_file = "data/sample_invoices.csv"
    if uploaded:
        save_path = Path("data") / uploaded.name
        save_path.parent.mkdir(exist_ok=True)
        with open(save_path, "wb") as f:
            f.write(uploaded.getbuffer())
        source_file = str(save_path)
        st.success(f"Uploaded: {uploaded.name}")

    st.markdown("---")

    # Manual trigger
    st.markdown("### ▶ Run Agent")
    run_btn = st.button("🚀 Run Agent Now", use_container_width=True)
    st.caption(f"Source: `{Path(source_file).name}`")

    st.markdown("---")
    st.markdown("### ℹ️ System")
    st.caption("Model: GPT-4o-mini")
    st.caption("Framework: LangGraph + LangChain")
    st.caption("DB: SQLite")

# ── Run agent if triggered ────────────────────────────────────────────────────
if run_btn:
    with st.spinner("🤖 Agent running — processing invoices..."):
        try:
            from app.agents.email_agent import run_agent
            from app.utils.logger import setup_logging
            setup_logging("INFO")
            result = run_agent(source_file=source_file, dry_run=dry_run)
            stats = result.get("run_stats", {})
            if stats.get("status") == "ABORTED":
                st.error(f"❌ Agent aborted: {stats.get('error', 'Unknown error')}")
            else:
                st.success(
                    f"✅ Run complete! "
                    f"Emails sent: **{stats.get('emails_sent', 0)}** | "
                    f"Escalated: **{stats.get('escalated_cases', 0)}**"
                )
                st.rerun()
        except Exception as e:
            st.error(f"❌ Agent error: {e}")

# ── Main dashboard ────────────────────────────────────────────────────────────
st.markdown("# 💳 Finance Credit Follow-Up Agent")
st.markdown("*Autonomous AI-powered invoice collection and escalation management*")
st.markdown("---")

# Load data
stats = get_dashboard_stats()
invoices = get_all_invoices()
audit_logs = get_audit_logs(limit=200)
email_hist = get_email_history(limit=100)
escalations = get_escalations()

# ── KPI Cards ─────────────────────────────────────────────────────────────────
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-number">{stats['total_invoices']}</div>
        <div class="kpi-label">📄 Total Invoices</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-number">{stats['overdue_invoices']}</div>
        <div class="kpi-label">⏰ Overdue Invoices</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-number">{stats['emails_sent']}</div>
        <div class="kpi-label">✉️ Emails Sent</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="kpi-card">
        <div class="kpi-number">{stats['escalated_cases']}</div>
        <div class="kpi-label">🚨 Escalated Cases</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ── Charts ────────────────────────────────────────────────────────────────────
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.markdown('<div class="section-header">📊 Overdue by Escalation Stage</div>', unsafe_allow_html=True)
    stage_dist = stats.get("stage_distribution", {})
    stage_labels = [f"Stage {i}" for i in range(1, 6)]
    stage_values = [stage_dist.get(f"stage_{i}", 0) for i in range(1, 6)]
    stage_colors = ["#4CAF50", "#FF9800", "#F44336", "#9C27B0", "#212121"]

    fig_stage = go.Figure(data=[
        go.Bar(
            x=stage_labels,
            y=stage_values,
            marker_color=stage_colors,
            text=stage_values,
            textposition="outside",
            textfont=dict(color="#e2e8f0", size=13),
        )
    ])
    fig_stage.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(26,31,46,0.8)",
        font=dict(color="#94a3b8", family="Inter"),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(gridcolor="#2d3748", title=""),
        yaxis=dict(gridcolor="#2d3748", title="Count"),
        showlegend=False,
        height=280,
    )
    st.plotly_chart(fig_stage, use_container_width=True)

with chart_col2:
    st.markdown('<div class="section-header">💰 Payment Aging Distribution</div>', unsafe_allow_html=True)
    if invoices:
        df_inv = pd.DataFrame(invoices)
        bins = [0, 7, 14, 21, 30, float("inf")]
        labels = ["1-7d", "8-14d", "15-21d", "22-30d", ">30d"]
        df_inv["aging_bucket"] = pd.cut(
            df_inv["days_overdue"].fillna(0).clip(lower=0),
            bins=bins,
            labels=labels,
            right=True,
        )
        aging_counts = df_inv[df_inv["days_overdue"] > 0]["aging_bucket"].value_counts().reindex(labels, fill_value=0)

        fig_aging = go.Figure(data=[
            go.Pie(
                labels=aging_counts.index.tolist(),
                values=aging_counts.values.tolist(),
                hole=0.55,
                marker_colors=stage_colors,
                textfont=dict(size=12, color="white"),
            )
        ])
        fig_aging.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8", family="Inter"),
            margin=dict(l=10, r=10, t=10, b=10),
            showlegend=True,
            legend=dict(font=dict(color="#94a3b8")),
            height=280,
        )
        st.plotly_chart(fig_aging, use_container_width=True)
    else:
        st.info("No invoice data yet. Run the agent to populate.")

# ── Email Activity Chart ───────────────────────────────────────────────────────
if email_hist:
    st.markdown('<div class="section-header">📈 Daily Email Activity</div>', unsafe_allow_html=True)
    df_email = pd.DataFrame(email_hist)
    df_email["date"] = pd.to_datetime(df_email["sent_at"]).dt.date
    daily = df_email.groupby("date").size().reset_index(name="count")

    fig_daily = px.area(
        daily,
        x="date",
        y="count",
        labels={"date": "Date", "count": "Emails Sent"},
        color_discrete_sequence=["#6366f1"],
    )
    fig_daily.update_traces(fill="tozeroy", fillcolor="rgba(99,102,241,0.15)", line_color="#6366f1")
    fig_daily.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(26,31,46,0.8)",
        font=dict(color="#94a3b8", family="Inter"),
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis=dict(gridcolor="#2d3748"),
        yaxis=dict(gridcolor="#2d3748"),
        height=220,
    )
    st.plotly_chart(fig_daily, use_container_width=True)

st.markdown("---")

# ── Invoice Table ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📋 Invoice Register</div>', unsafe_allow_html=True)

if invoices:
    df_table = pd.DataFrame(invoices)[[
        "invoice_id", "client_name", "amount_due", "currency",
        "due_date", "days_overdue", "escalation_stage", "status", "risk_score"
    ]].copy()
    df_table.columns = [
        "Invoice ID", "Client", "Amount Due", "Currency",
        "Due Date", "Days Overdue", "Stage", "Status", "Risk Score"
    ]
    df_table["Amount Due"] = df_table["Amount Due"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
    df_table["Risk Score"] = df_table["Risk Score"].apply(lambda x: f"{x:.1f}" if pd.notna(x) else "—")
    df_table["Days Overdue"] = df_table["Days Overdue"].apply(lambda x: int(x) if pd.notna(x) else 0)

    st.dataframe(
        df_table,
        use_container_width=True,
        height=320,
        column_config={
            "Stage": st.column_config.NumberColumn("Stage", format="%d"),
            "Days Overdue": st.column_config.NumberColumn("Days Overdue", format="%d"),
        },
    )
else:
    st.info("No invoices loaded yet. Upload a file and run the agent.")

st.markdown("---")

# ── Email Preview Panel ───────────────────────────────────────────────────────
st.markdown('<div class="section-header">✉️ Email Preview</div>', unsafe_allow_html=True)

if email_hist:
    df_eh = pd.DataFrame(email_hist)
    selected_inv = st.selectbox(
        "Select invoice to preview email:",
        options=df_eh["invoice_id"].tolist(),
        key="email_preview_select",
    )
    row = df_eh[df_eh["invoice_id"] == selected_inv].iloc[0]

    prev_col1, prev_col2 = st.columns([1, 2])
    with prev_col1:
        st.metric("Client", row.get("client_name", "—"))
        st.metric("Amount Due", f"${row.get('amount_due', 0):,.2f}")
        st.metric("Days Overdue", row.get("days_overdue", 0))
        stage = row.get("escalation_stage", 1)
        stage_cfg = ESCALATION_MATRIX.get(stage)
        st.metric("Stage", f"{stage} — {stage_cfg.tone if stage_cfg else 'N/A'}")
        st.metric("Send Status", row.get("send_status", "—"))
        dry = "Yes (Mock)" if row.get("dry_run") else "No (Live)"
        st.caption(f"Dry Run: {dry}")

    with prev_col2:
        st.text_input("Subject", value=row.get("subject", ""), key="preview_subject", disabled=True)
        # Retrieve body from audit_logs (email_hist doesn't store body)
        logs = get_audit_logs(limit=500)
        body = ""
        for log in logs:
            if log["invoice_id"] == selected_inv and log.get("email_body"):
                body = log["email_body"]
                break
        st.text_area("Email Body", value=body or "(Body stored in audit logs)", height=240, key="preview_body", disabled=True)
else:
    st.info("No emails generated yet. Run the agent to generate and preview emails.")

st.markdown("---")

# ── Escalations Table ─────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🚨 Legal Escalations</div>', unsafe_allow_html=True)
if escalations:
    df_esc = pd.DataFrame(escalations)
    df_esc["amount_due"] = df_esc["amount_due"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "—")
    st.dataframe(df_esc[["invoice_id", "client_name", "amount_due", "days_overdue", "risk_score", "notes", "resolved", "timestamp"]], use_container_width=True)
else:
    st.success("✅ No accounts currently flagged for legal review.")

st.markdown("---")

# ── Audit Log + Download ──────────────────────────────────────────────────────
st.markdown('<div class="section-header">📝 Audit Log</div>', unsafe_allow_html=True)

if audit_logs:
    df_audit = pd.DataFrame(audit_logs)
    st.dataframe(
        df_audit[["timestamp", "invoice_id", "client_name", "escalation_stage",
                  "days_overdue", "send_status", "escalation_status", "risk_score", "dry_run"]],
        use_container_width=True,
        height=280,
    )

    # Download button
    csv_buf = io.StringIO()
    df_audit.to_csv(csv_buf, index=False)
    st.download_button(
        label="⬇️ Download Audit Log (CSV)",
        data=csv_buf.getvalue().encode("utf-8"),
        file_name="finance_agent_audit_log.csv",
        mime="text/csv",
        use_container_width=False,
    )
else:
    st.info("No audit records yet. Run the agent to populate the audit log.")

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center;color:#475569;font-size:0.8rem;'>"
    "Finance Credit Follow-Up Agent &nbsp;|&nbsp; Powered by LangGraph + GPT-4o-mini &nbsp;|&nbsp; "
    "Built for AI Finance Automation"
    "</div>",
    unsafe_allow_html=True,
)
