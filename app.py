"""StrategyPilot AI Streamlit application."""

from __future__ import annotations

import os
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from src.audit import build_evidence_payload, generate_audit
from src.charts import category_performance, drawdown_curve, equity_curve, pnl_distribution
from src.metrics import calculate_metrics
from src.parser import ValidationError, parse_csv
from src.utils import audit_to_markdown, format_currency, format_percent, format_ratio

ROOT = Path(__file__).resolve().parent
SAMPLE_PATH = ROOT / "sample_data" / "trades.csv"

st.set_page_config(
    page_title="StrategyPilot AI",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --mint:#63e6be; --ink:#07111f; --panel:rgba(15,23,42,.78); --line:rgba(148,163,184,.16); }
    .stApp { background:
        radial-gradient(circle at 84% 8%, rgba(45,212,191,.10), transparent 25rem),
        radial-gradient(circle at 7% 24%, rgba(59,130,246,.09), transparent 28rem), #070d18; }
    [data-testid="stSidebar"] { background:rgba(8,15,28,.94); border-right:1px solid var(--line); }
    [data-testid="stHeader"] { background:rgba(7,13,24,.72); }
    [data-testid="stAppViewContainer"] { color:#e5edf8; }
    .block-container { max-width:1440px; padding-top:calc(2.2rem + 12px); }
    .eyebrow { color:var(--mint); font-size:.75rem; font-weight:800; letter-spacing:.16em; text-transform:uppercase;
        line-height:1.5; padding:.18rem 0 .22rem; margin:0; height:auto; transform:none; overflow:visible; }
    .hero h1 { color:#f8fafc !important; font-size:clamp(2.4rem,5vw,4.3rem); line-height:1; margin:.45rem 0 .8rem; letter-spacing:-.045em; }
    .hero p { color:#c3d1e3; max-width:760px; font-size:1.08rem; line-height:1.65; }
    .status-pill { display:inline-block; padding:.38rem .68rem; border-radius:999px; color:#a7f3d0;
        border:1px solid rgba(99,230,190,.35); background:rgba(16,185,129,.09); font-size:.78rem; font-weight:700; }
    [data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4 { color:#f8fafc !important; }
    [data-testid="stSidebar"] label, [data-testid="stSidebar"] label p,
    [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color:#e2e8f0 !important; }
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
    [data-testid="stSidebar"] .stMarkdown p { color:#b8c7da !important; }
    [data-testid="stSidebar"] [data-testid="stTextInput"] input { color:#eaf2fb !important; }
    [data-testid="stSidebar"] [data-testid="stTextInput"] input:disabled { -webkit-text-fill-color:#cbd5e1; opacity:1; }
    [data-testid="stRadio"] label p { color:#e2e8f0 !important; }
    [data-testid="stAlert"] p { color:#e5edf8 !important; }
    [data-testid="stMetric"] { background:linear-gradient(145deg,rgba(20,31,50,.9),rgba(11,20,35,.86));
        border:1px solid var(--line); border-radius:16px; padding:1rem 1.05rem; min-height:112px; }
    [data-testid="stMetricLabel"], [data-testid="stMetricLabel"] p { color:#b9c7da !important; }
    [data-testid="stMetricValue"] { color:#f8fafc !important; }
    .section-label { color:#f8fafc; margin:2rem 0 .3rem; font-size:1.4rem; font-weight:750; letter-spacing:-.02em; }
    .section-note { color:#b2c2d6; margin-bottom:1rem; }
    button[data-baseweb="tab"][aria-selected="false"],
    button[data-baseweb="tab"][aria-selected="false"] * {
        color:#e2e8f0 !important; -webkit-text-fill-color:#e2e8f0 !important; opacity:1 !important;
    }
    .audit-card { border:1px solid var(--line); border-radius:16px; padding:1.15rem 1.25rem;
        margin:.8rem 0; background:linear-gradient(145deg,rgba(19,30,48,.88),rgba(10,18,32,.84)); }
    .audit-card h3 { color:#f8fafc !important; margin:.3rem 0 .8rem; font-size:1.05rem; }
    .audit-card p { color:#c3d1e3; line-height:1.55; margin:.5rem 0; }
    .priority-high,.priority-medium,.priority-low { display:inline-block; border-radius:999px; padding:.22rem .55rem;
        font-size:.7rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
    .priority-high { color:#fecaca; background:rgba(239,68,68,.15); }
    .priority-medium { color:#fde68a; background:rgba(245,158,11,.15); }
    .priority-low { color:#bfdbfe; background:rgba(59,130,246,.15); }
    .det-banner { border-left:3px solid var(--mint); background:rgba(99,230,190,.07); padding:.8rem 1rem;
        border-radius:0 10px 10px 0; color:#bfdbd5; margin:.6rem 0 1rem; }
    .footer-note { color:#a8b7ca; font-size:.79rem; border-top:1px solid var(--line); margin-top:2.4rem; padding-top:1.1rem; }
    div[data-testid="stDataFrame"] { border:1px solid var(--line); border-radius:12px; overflow:hidden; }
    .stButton > button, .stDownloadButton > button { border-radius:10px; font-weight:700; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _secret(name: str) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    try:
        secret_value = st.secrets.get(name)
        return str(secret_value) if secret_value else None
    except (FileNotFoundError, KeyError):
        return None


def _metric_cards(metrics: dict[str, Any]) -> None:
    first = st.columns(5)
    first[0].metric("Complete setups", f"{metrics['complete_setups']:,}", help="Rows sharing setup_id are counted once.")
    first[1].metric("Setup win rate", format_percent(metrics["setup_win_rate"]))
    first[2].metric("Net profit", format_currency(metrics["net_profit"]))
    first[3].metric("Profit factor", format_ratio(metrics["profit_factor"]))
    first[4].metric("Max drawdown magnitude", format_currency(metrics["maximum_drawdown"]))
    second = st.columns(6)
    second[0].metric("Expectancy", format_currency(metrics["expectancy"]))
    second[1].metric("Gross profit", format_currency(metrics["gross_profit"]))
    second[2].metric("Gross loss magnitude", format_currency(metrics["gross_loss"]))
    second[3].metric("Avg winner", format_currency(metrics["average_winner"]))
    second[4].metric("Avg loser", format_currency(metrics["average_loser"]))
    second[5].metric("Win/loss ratio", format_ratio(metrics["win_loss_ratio"]))


def _evidence_frame(metrics: dict[str, Any]) -> pd.DataFrame:
    direction = pd.DataFrame(metrics["direction_performance"]).rename(columns={"direction": "Segment"})
    direction.insert(0, "Dimension", "Direction")
    session = pd.DataFrame(metrics["session_performance"]).rename(columns={"session": "Segment"})
    session.insert(0, "Dimension", "Session")
    frame = pd.concat([direction, session], ignore_index=True)
    frame = frame.rename(columns={"setups": "Setups", "wins": "Wins", "win_rate": "Win rate", "net_profit": "Net profit", "expectancy": "Expectancy"})
    frame["Win rate"] = frame["Win rate"] * 100
    frame["Net profit"] = frame["Net profit"].map(format_currency)
    frame["Expectancy"] = frame["Expectancy"].map(format_currency)
    return frame[["Dimension", "Segment", "Setups", "Wins", "Win rate", "Net profit", "Expectancy"]]


st.markdown(
    """<div class="hero"><div class="eyebrow">OpenAI Build Week 2026</div>
    <h1>StrategyPilot <span style="color:#63e6be">AI</span></h1>
    <p>Turn raw trading-result CSVs into deterministic performance evidence, prioritized engineering work, and repeatable regression checks.</p>
    <span class="status-pill">Engineering audit · Not trade prediction</span></div>""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### Data control")
    source_mode = st.radio("Choose a source", ["Included sample", "Upload CSV"], label_visibility="collapsed")
    uploaded = None
    if source_mode == "Upload CSV":
        uploaded = st.file_uploader("Upload trading results", type=["csv"], help="Required: entry_time, direction, pnl")
    else:
        st.caption("A judge-ready fixture with multi-leg setups is included.")
        st.button("Load sample data", type="primary", width="stretch")
    st.divider()
    st.markdown("### Audit configuration")
    model = _secret("OPENAI_MODEL") or "gpt-5.6-sol"
    api_key = _secret("OPENAI_API_KEY")
    st.text_input("OpenAI model", value=model, disabled=True)
    st.caption("API key detected" if api_key else "Offline mode · Demo Audit enabled")
    st.divider()
    st.caption("Canonical minimum")
    st.code("entry_time, direction, pnl", language=None)
    st.caption("Rows sharing `setup_id` are reconstructed before metrics are calculated.")

if source_mode == "Upload CSV" and uploaded is None:
    st.info("Upload a CSV in the sidebar, or switch to the included sample to explore the complete workflow.")
    st.stop()

source = uploaded.getvalue() if uploaded is not None else SAMPLE_PATH.read_bytes()
source_label = uploaded.name if uploaded is not None else "Included sample · sample_data/trades.csv"

try:
    parsed = parse_csv(source)
    metrics, setups = calculate_metrics(parsed.data)
except (ValidationError, ValueError) as exc:
    st.error(f"Validation failed: {exc}")
    st.stop()

st.success(f"Validated {len(parsed.data):,} trade leg(s) and reconstructed {len(setups):,} complete setup(s).")
for warning in parsed.warnings:
    st.warning(warning)

st.markdown('<div class="section-label">Deterministic evidence</div>', unsafe_allow_html=True)
st.markdown('<div class="section-note">Calculated in Python from complete reconstructed setups. AI is not involved in these values.</div>', unsafe_allow_html=True)
st.markdown('<div class="det-banner">Every trade leg sharing a <code>setup_id</code> is combined first. Win rate, counts, expectancy, and all downstream evidence operate on those completed setups.</div>', unsafe_allow_html=True)
_metric_cards(metrics)

tab_overview, tab_segments, tab_evidence = st.tabs(["Equity & risk", "Direction & session", "Evidence table"])
with tab_overview:
    left, right = st.columns(2)
    left.plotly_chart(equity_curve(setups), width="stretch", theme=None)
    right.plotly_chart(drawdown_curve(setups), width="stretch", theme=None)
    st.plotly_chart(pnl_distribution(setups), width="stretch", theme=None)
with tab_segments:
    left, right = st.columns(2)
    left.plotly_chart(category_performance(metrics["direction_performance"], "direction", "Direction performance"), width="stretch", theme=None)
    right.plotly_chart(category_performance(metrics["session_performance"], "session", "Session performance"), width="stretch", theme=None)
with tab_evidence:
    st.dataframe(
        _evidence_frame(metrics), hide_index=True, width="stretch",
        column_config={
            "Win rate": st.column_config.NumberColumn(format="%.1f%%"),
            "Net profit": st.column_config.TextColumn(),
            "Expectancy": st.column_config.TextColumn(),
        },
    )
    with st.expander("Reconstructed setup ledger"):
        setup_display = setups[["setup_id", "entry_time", "direction", "session", "symbol", "trade_legs", "pnl", "outcome"]].copy()
        setup_display["pnl"] = setup_display["pnl"].map(format_currency)
        st.dataframe(
            setup_display,
            hide_index=True, width="stretch",
            column_config={"pnl": st.column_config.TextColumn("Setup P&L")},
        )

st.markdown('<div class="section-label">Engineering audit</div>', unsafe_allow_html=True)
st.markdown('<div class="section-note">Interpretation is separated from the verified evidence above. GPT receives aggregate JSON only—never raw trade rows.</div>', unsafe_allow_html=True)
payload = build_evidence_payload(metrics)
audit_cache_key = f"{source_label}:{hash(source)}:{model}:{bool(api_key)}"
if st.session_state.get("audit_cache_key") != audit_cache_key:
    with st.spinner("Building evidence-grounded audit…"):
        st.session_state.audit_result = generate_audit(payload, api_key, model)
        st.session_state.audit_cache_key = audit_cache_key
audit = st.session_state.audit_result

if audit.mode.startswith("Deterministic"):
    st.info(f"{audit.mode}: {audit.notice}")
else:
    st.success(f"{audit.mode}: {audit.notice}")

for finding in audit.findings:
    priority_class = f"priority-{finding['priority'].lower()}"
    st.markdown(
        f"""<div class="audit-card"><span class="{priority_class}">{finding['priority']} priority</span>
        <h3>{escape(finding['finding'])}</h3><p><strong>Evidence</strong><br>{escape(finding['evidence'])}</p>
        <p><strong>Engineering task</strong><br>{escape(finding['engineering_task'])}</p>
        <p><strong>Regression check</strong><br>{escape(finding['regression_check'])}</p></div>""",
        unsafe_allow_html=True,
    )

report = audit_to_markdown(metrics, audit.findings, source_label, audit.mode)
st.download_button(
    "Download audit as Markdown", data=report, file_name="strategypilot_audit.md",
    mime="text/markdown", type="primary", width="stretch",
)
st.markdown(
    '<div class="footer-note"><strong>Financial-information disclaimer:</strong> StrategyPilot AI is an engineering audit tool for analyzing historical test outputs. It does not provide financial advice, recommend trades, predict results, or connect to brokers. Historical results do not guarantee future performance.</div>',
    unsafe_allow_html=True,
)
