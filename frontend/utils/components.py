"""
Reusable enterprise UI components for LeakLens.
"""

import re
import textwrap

import streamlit as st

from utils.formatting import get_risk_badge, format_inr, format_int


def render_html(markup: str) -> None:
    """
    Render an HTML fragment in the page without leaking raw tags into the UI.

    Streamlit renders markdown client-side via CommonMark, which treats any
    line indented by 4+ spaces as an indented code block and shows the markup
    as literal text. Fragments are dedented before rendering, and whitespace-
    only lines are collapsed because blank lines terminate an HTML block.
    """
    cleaned = re.sub(r"(?:\n[ \t]*){2,}", "\n", textwrap.dedent(markup))
    st.markdown(cleaned, unsafe_allow_html=True)

def render_header():
    """Render the master product header and datathon track metadata."""
    render_html("""
    <div class="leaklens-header-container">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 15px;">
            <div>
                <h1 class="leaklens-title">LeakLens</h1>
                <div class="leaklens-subtitle">Explainable Revenue & Operational Risk Monitor</div>
            </div>
            <div class="leaklens-badge-strip">
                <span class="leaklens-badge badge-track">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                    DATATHON 2026: The Money Leak
                </span>
                <span class="leaklens-badge badge-live">
                    <span style="display:inline-block; width:6px; height:6px; background:#10B981; border-radius:50%; margin-right:2px;"></span>
                    Diagnostic Engine Active
                </span>
            </div>
        </div>
    </div>
    """)

def render_kpi_card(title, value, subtext=None, risk_style="neutral"):
    """
    Render a styled enterprise KPI card.
    risk_style: 'high', 'warning', 'good', 'info', or 'neutral'
    """
    border_class = ""
    if risk_style == "high":
        border_class = "kpi-risk-high"
    elif risk_style == "warning":
        border_class = "kpi-risk-warning"
    elif risk_style == "good":
        border_class = "kpi-risk-good"
    elif risk_style == "info":
        border_class = "kpi-risk-info"

    subtext_html = f'<div class="kpi-subtext">{subtext}</div>' if subtext else ""

    render_html(f"""
    <div class="kpi-card {border_class}">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value">{value}</div>
        {subtext_html}
    </div>
    """)

def render_quality_warning_banner(title, evidence_text, caveat_text=None):
    """Render a high-visibility data quality callout banner."""
    caveat_html = f'<div style="margin-top: 6px; font-size: 0.84rem; color: #FDE68A;"><strong>Caution:</strong> {caveat_text}</div>' if caveat_text else ""
    render_html(f"""
    <div class="quality-warning-banner">
        <div class="quality-warning-title">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0zM12 9v4M12 17h.01"/></svg>
            DATA QUALITY ALERT: {title}
        </div>
        <div style="font-size: 0.92rem; line-height: 1.45; color: #F5F5F5;">
            {evidence_text}
        </div>
        {caveat_html}
    </div>
    """)

def render_ml_explainer():
    """Render the standard Isolation Forest explanation box with calibrated wording."""
    render_html("""
    <div class="ml-explain-card">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:8px;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#A3A3A3" stroke-width="2"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
            <span style="font-weight:600; font-size:1.05rem; color:#F5F5F5;">How does the ML work?</span>
            <span style="background:rgba(148, 163, 184, 0.12); border:1px solid #3A3A3A; color:#D4D4D4; font-size:0.72rem; padding:2px 8px; border-radius:4px; font-weight:600; text-transform:uppercase; letter-spacing:0.03em;">Isolation Forest Engine</span>
        </div>
        <p style="font-size:0.92rem; color:#D4D4D4; line-height:1.55; margin-bottom:6px;">
            <strong>LeakLens</strong> learns the typical behaviour of products across several operational and financial indicators. 
            Products with unusually different combinations of values receive a higher anomaly score and are prioritized for investigation.
        </p>
        <div style="font-size:0.82rem; color:#A3A3A3; font-style:italic;">
            Note: The anomaly score isolates statistical deviations from catalog baselines. It does not forecast future losses or claim verified commercial unprofitability.
        </div>
    </div>
    """)
