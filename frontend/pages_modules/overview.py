"""
Executive Overview Page for LeakLens.
Consumes headline KPIs, category comparisons, and top issues from the FastAPI backend.
"""

import streamlit as st
import plotly.graph_objects as go
from utils.formatting import (
    format_inr, format_pct, format_int, get_risk_badge,
    COLOR_HIGH_RISK, COLOR_MED_RISK, COLOR_LOW_RISK, COLOR_INFO,
    PLOT_BG_COLOR, PAPER_BG_COLOR
)
from utils.components import render_header, render_kpi_card, render_html
import api_client

def render_overview_page():
    render_header()

    # 1. Fetch Headline KPIs from GET /overview
    overview = api_client.fetch_overview()
    products = api_client.fetch_products_risk()
    categories = api_client.fetch_categories()

    high_risk_count = sum(1 for p in products if p.get("risk_level") == "High")

    st.markdown('<div class="section-heading">Operational & Financial Baseline</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subheading">Headline exposure metrics computed by FastAPI backend from transaction profiles.</div>',
        unsafe_allow_html=True
    )

    # 5 KPI Headline Cards
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_kpi_card(
            title="Total Transaction Value",
            value=format_inr(overview.get("total_transaction_value", 9390803.10), in_lakhs=True),
            subtext="Catalog Gross Order Value",
            risk_style="neutral"
        )
    with c2:
        render_kpi_card(
            title="Cancelled + Returned Exposure",
            value=format_inr(overview.get("combined_exposure", 1622171.91), in_lakhs=True),
            subtext="Friction Exposure (NOT Loss)",
            risk_style="high"
        )
    with c3:
        render_kpi_card(
            title="Exposure Rate",
            value=format_pct(overview.get("exposure_pct", 18.18)),
            subtext="Of Gross Transaction Value",
            risk_style="warning"
        )
    with c4:
        render_kpi_card(
            title="Apparent Negative Margins",
            value=format_pct(overview.get("negative_margin_rate", 37.94)),
            subtext="Transactions Below Cost",
            risk_style="high"
        )
    with c5:
        render_kpi_card(
            title="High-Risk Products Flagged",
            value=f"{high_risk_count} SKUs",
            subtext="Prioritized by Isolation Forest",
            risk_style="high"
        )

    st.info(
        "󰋼 **Terminology Standard:** Value figure represents **transaction-value exposure** "
        "(~₹8.62L cancelled + ~₹7.60L returned) under operational friction, **NOT** guaranteed bottom-line loss. "
        "Apparent negative-margin rate reflects supplied cost fields requiring supplier invoice verification."
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. TOP ISSUES SECTION
    st.markdown('<div class="section-heading">󰀦 Top Issues to Investigate</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subheading">Ranked prioritized operational and margin risks generated from backend diagnostics.</div>',
        unsafe_allow_html=True
    )

    top_issues = [
        {
            "rank": 1,
            "title": "Pricing & Margin Anomalies",
            "severity": "High",
            "evidence": f"{overview.get('negative_margin_rate', 37.94)}% of transactions show an apparent negative estimated margin under supplied cost fields.",
            "action": "Review price/cost assumptions, minimum price floors, and promo stacking rules.",
            "caveat": "Supplied dataset documentation states costs and prices were independently generated; treat as an anomaly requiring verification.",
            "page": "Product Risk"
        },
        {
            "rank": 2,
            "title": "Campaign Funnel Data-Quality Anomaly",
            "severity": "Medium/High",
            "evidence": f"{overview.get('invalid_campaign_rows', 171)} campaign rows contain impossible funnel telemetry (84 clicks > impressions; 88 conversions > clicks).",
            "action": "Validate marketing-source ETL and ad network attribution webhooks before trusting CTR/CVR.",
            "caveat": "Attribution metrics in affected rows are fundamentally untrusted; exclude these rows from budget decisions.",
            "page": "Campaigns"
        },
        {
            "rank": 3,
            "title": "Inventory Telemetry Consistency Anomaly",
            "severity": "Medium/High",
            "evidence": f"{overview.get('stockout_above_threshold', 648)} stockout records occur despite stock_on_hand above reorder threshold; {overview.get('zero_stock_not_flagged', 10)} records show zero stock without a flag.",
            "action": "Verify the true semantic meaning and trigger source of stockout_flag before automating replenishment.",
            "caveat": "Reflects database logging contradictions rather than confirmed warehouse physical stockouts.",
            "page": "Inventory"
        },
        {
            "rank": 4,
            "title": "Highest-Risk Product Clustering",
            "severity": "High",
            "evidence": f"{high_risk_count} SKUs isolated by Isolation Forest with risk scores >= 70.0, exhibiting multi-dimensional margin compression and delivery latency.",
            "action": "Audit top 10 prioritized product cards in Product Risk for SKU-level renegotiation.",
            "caveat": "The model identifies products whose combined behaviour is unusually different; it does not predict future failure.",
            "page": "Product Risk"
        }
    ]

    for issue in top_issues:
        badge_html = get_risk_badge(issue["severity"])
        with st.expander(f"#{issue['rank']} — {issue['title']}  |  Severity: {issue['severity']}", expanded=(issue["rank"] <= 2)):
            render_html(f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
                <span style="font-size:1.15rem; font-weight:700; color:#F5F5F5;">{issue['title']}</span>
                <div>{badge_html}</div>
            </div>
            <div class="issue-evidence-box">
                <strong>Evidence Identified:</strong><br>{issue['evidence']}
            </div>
            <div class="issue-action-box">
                <strong>Recommended Next Action:</strong><br>{issue['action']}
            </div>
            <div class="issue-confidence-box">
                <strong>Data Confidence / Caveats:</strong><br>{issue['caveat']}
            </div>
            """)

            if st.button(f"󰍉 Investigate {issue['title']} in {issue['page']} →", key=f"btn_issue_{issue['rank']}", type="primary"):
                st.session_state["current_page"] = issue["page"]
                st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Category Comparison Visual (Signal: Beauty has highest apparent negative margin rate)
    st.markdown('<div class="section-heading">󰄨 Category Risk Breakdown (GET /categories)</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subheading">Observed signal: Beauty exhibits the highest apparent negative-margin rate (~55.2%), while failure rates are comparatively similar across departments (~16.8%).</div>',
        unsafe_allow_html=True
    )

    if categories:
        cat_names = [c["category"] for c in categories]
        neg_rates = [c["negative_margin_rate"] for c in categories]
        fail_rates = [c["failure_rate"] for c in categories]

        fig_cat = go.Figure()
        fig_cat.add_trace(go.Bar(
            name="Apparent Negative Margin %",
            x=cat_names,
            y=neg_rates,
            marker_color=[COLOR_HIGH_RISK if c == "Beauty" else "#DC2626" for c in cat_names],
            text=[f"{v:.1f}%" for v in neg_rates],
            textposition="auto"
        ))
        fig_cat.add_trace(go.Bar(
            name="Transaction Failure Rate %",
            x=cat_names,
            y=fail_rates,
            marker_color=COLOR_MED_RISK,
            text=[f"{v:.1f}%" for v in fail_rates],
            textposition="auto"
        ))
        fig_cat.update_layout(
            title="Apparent Negative Margin % vs Transaction Failure Rate by Category",
            title_font=dict(size=14, color="#F5F5F5"),
            barmode="group",
            paper_bgcolor=PAPER_BG_COLOR,
            plot_bgcolor=PLOT_BG_COLOR,
            font=dict(color="#D4D4D4", family="Inter"),
            yaxis=dict(title="Percentage (%)", gridcolor="#262626"),
            xaxis=dict(gridcolor="#262626"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            margin=dict(l=20, r=20, t=40, b=40),
            height=340
        )
        st.plotly_chart(fig_cat, use_container_width=True)
