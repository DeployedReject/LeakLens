"""
Product Risk Screen for LeakLens.
Consumes sorted product risk list from GET /products/risk and
single SKU drilldown from GET /products/{product_id}.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.formatting import (
    format_inr, format_pct, get_risk_badge,
    COLOR_HIGH_RISK, COLOR_MED_RISK, COLOR_LOW_RISK, COLOR_INFO,
    PLOT_BG_COLOR, PAPER_BG_COLOR
)
from utils.components import render_kpi_card, render_html
import api_client

def render_products_page():
    st.markdown('<div class="section-heading">󰏓 Product Risk & Anomaly Triage</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subheading">Ranked product catalog evaluated by FastAPI Isolation Forest backend across multi-dimensional operational metrics.</div>',
        unsafe_allow_html=True
    )

    # 1. Filters
    categories_data = api_client.fetch_categories()
    cat_list = ["All"] + sorted([c["category"] for c in categories_data])

    col_f1, col_f2, col_f3 = st.columns([2, 2, 3])
    with col_f1:
        selected_cat = st.selectbox("Category Filter", cat_list, index=0)
    with col_f2:
        selected_risk = st.selectbox("Risk Level Filter", ["All", "High", "Medium", "Low"], index=0)
    with col_f3:
        search_kw = st.text_input("Search Product ID", placeholder="e.g. PR0001")

    # Fetch from API
    products = api_client.fetch_products_risk(category=selected_cat, risk_level=selected_risk)
    
    if search_kw:
        products = [p for p in products if search_kw.lower() in p.get("product_id", "").lower()]

    # Metric Cards
    high_count = sum(1 for p in products if p.get("risk_level") == "High")
    med_count = sum(1 for p in products if p.get("risk_level") == "Medium")
    low_count = sum(1 for p in products if p.get("risk_level") == "Low")

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        render_kpi_card("Filtered Products", str(len(products)), "Matching Active Criteria", "neutral")
    with m2:
        render_kpi_card("High Risk Level", str(high_count), "Urgent Priority Triage", "high")
    with m3:
        render_kpi_card("Medium Risk Level", str(med_count), "Watchlist Monitoring", "warning")
    with m4:
        render_kpi_card("Low Risk Level", str(low_count), "Stable Operational Norms", "good")

    st.markdown("<br>", unsafe_allow_html=True)

    # 2. Sortable Table
    st.markdown("#### Ranked Product Risk Matrix (GET /products/risk)")
    if not products:
        st.warning("No products found for the selected filter.")
        return

    df_display = pd.DataFrame(products)

    # Reorder columns for optimal readability
    col_order = [
        "product_id", "category", "risk_score", "risk_level",
        "failure_rate", "cancel_rate", "return_rate", "negative_margin_rate",
        "avg_discount", "avg_margin", "stockout_rate", "avg_supplier_delay",
        "why_flagged", "recommended_action"
    ]
    avail_cols = [c for c in col_order if c in df_display.columns]

    st.dataframe(
        df_display[avail_cols].style.format({
            "risk_score": "{:.1f}",
            "failure_rate": "{:.2%}",
            "cancel_rate": "{:.2%}",
            "return_rate": "{:.2%}",
            "negative_margin_rate": "{:.2%}",
            "avg_discount": "{:.2%}",
            "stockout_rate": "{:.2%}",
            "avg_margin": "₹{:.2f}",
            "avg_supplier_delay": "{:.1f}d"
        }),
        use_container_width=True,
        height=280
    )

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. Product Drilldown (GET /products/{product_id})
    st.markdown('<div class="section-heading">󰍉 Product Detailed Drilldown (GET /products/{product_id})</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subheading">Select any product to inspect explainable evidence, operational signals, and distinct ML anomaly scores.</div>',
        unsafe_allow_html=True
    )

    id_options = [p["product_id"] + " (" + p["category"] + " — Risk: " + str(p["risk_score"]) + ")" for p in products]
    selected_option = st.selectbox("Choose Product for Deep Dive", id_options, index=0)
    selected_pid = selected_option.split(" ")[0]

    # Call drilldown API
    detail = api_client.fetch_product_detail(selected_pid)
    if not detail:
        st.error(f"Could not load details for product {selected_pid}.")
        return

    # Two-Column Detailed Layout
    col_left, col_right = st.columns([1, 1])

    with col_left:
        render_html(f"""
        <div style="background:#141414; border:1px solid #262626; border-radius:12px; padding:22px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <span style="font-size:0.85rem; color:#A3A3A3; text-transform:uppercase; font-weight:600;">{detail.get('category')} SKU</span>
                {get_risk_badge(detail.get('risk_level', 'Medium'))}
            </div>
            <h2 style="margin:0; color:#F5F5F5; font-size:1.6rem;">{detail.get('product_id')}</h2>
            <div style="font-size:0.82rem; color:#A3A3A3; margin-top:2px; margin-bottom:16px;">
                Volume: <strong>{detail.get('transaction_count', detail.get('transaction_volume', 69))} Transactions</strong>
            </div>

            <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-bottom:18px;">
                <div style="background:#0A0A0A; padding:12px; border-radius:8px; border:1px solid #262626;">
                    <div style="font-size:0.75rem; color:#A3A3A3; text-transform:uppercase; font-weight:600;">ML Anomaly Score</div>
                    <div style="font-size:1.6rem; font-weight:700; color:#EF4444; margin-top:4px;">{detail.get('risk_score', 0):.1f} / 100</div>
                    <div style="font-size:0.72rem; color:#6E6E6E;">Unsupervised Isolation Forest</div>
                </div>
                <div style="background:#0A0A0A; padding:12px; border-radius:8px; border:1px solid #262626;">
                    <div style="font-size:0.75rem; color:#A3A3A3; text-transform:uppercase; font-weight:600;">Average Margin</div>
                    <div style="font-size:1.6rem; font-weight:700; color:{'#10B981' if detail.get('avg_margin', 0) > 0 else '#EF4444'}; margin-top:4px;">₹{detail.get('avg_margin', 0):.2f}</div>
                    <div style="font-size:0.72rem; color:#6E6E6E;">Per Unit Realized Margin</div>
                </div>
            </div>

            <div style="font-weight:700; color:#F5F5F5; margin-bottom:8px; font-size:0.92rem;">Deterministic Operational Indicators:</div>
            <ul style="color:#D4D4D4; font-size:0.88rem; line-height:1.65; margin-bottom:0; padding-left:20px;">
                <li>Cancellation Rate: <strong>{detail.get('cancel_rate', 0):.2%}</strong></li>
                <li>Return Rate: <strong>{detail.get('return_rate', 0):.2%}</strong></li>
                <li>Combined Failure Rate: <strong>{detail.get('failure_rate', 0):.2%}</strong></li>
                <li>Apparent Negative-Margin Rate: <strong>{detail.get('negative_margin_rate', 0):.2%}</strong></li>
                <li>Average Promo Discount: <strong>{detail.get('avg_discount', 0):.2%}</strong></li>
                <li>Stockout Frequency: <strong>{detail.get('stockout_rate', 0):.2%}</strong></li>
                <li>Supplier Lead Delay: <strong>{detail.get('avg_supplier_delay', 0):.1f} days</strong> (Lead: {detail.get('supplier_lead_days', 10)}d)</li>
            </ul>
        </div>
        """)

    with col_right:
        render_html(f"""
        <div style="background:#141414; border:1px solid #262626; border-radius:12px; padding:22px; height:100%;">
            <div style="font-size:0.85rem; color:#EF4444; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">
                󰉁 Why This Needs Attention
            </div>
            <div class="issue-evidence-box" style="margin-top:8px; margin-bottom:16px;">
                <strong>Trigger Signals:</strong> {detail.get('why_flagged', 'Identified as behavioral outlier by multi-feature density model.')}
                <div style="font-size:0.82rem; color:#A3A3A3; margin-top:6px;">
                    This product's operational metrics deviate significantly from the baseline behavior observed in peer catalog items.
                </div>
            </div>

            <div style="font-size:0.85rem; color:#10B981; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">
                󰓾 Suggested Investigation
            </div>
            <div class="issue-action-box" style="margin-top:8px; margin-bottom:16px;">
                <strong>Management Action:</strong> {detail.get('recommended_action', 'Audit supplier procurement contract and promo discount rules.')}
                <ul style="margin-top:8px; margin-bottom:0; padding-left:18px; font-size:0.88rem;">
                    <li>Audit selling price formula against supplier procurement costs</li>
                    <li>Inspect promotional discount eligibility to prevent negative net contribution</li>
                    <li>Verify return reasons (quality/defects vs customer sizing)</li>
                    <li>Review supplier shipment lead time SLAs</li>
                </ul>
            </div>

            <div style="font-size:0.85rem; color:#F59E0B; font-weight:700; text-transform:uppercase; letter-spacing:0.04em;">
                󰗑 Data Confidence / Caveats
            </div>
            <div class="issue-confidence-box" style="margin-top:8px; margin-bottom:0;">
                {detail.get('caveats', 'Cost fields in source dataset were independently generated. Apparent negative margins require supplier invoice verification.')}
            </div>
        </div>
        """)

    st.markdown("<br>", unsafe_allow_html=True)

    # Deviation Radar Visualizer for Selected Product
    st.markdown("#### Multivariate Metric vs Catalog Benchmark Normal Envelope")
    norms = detail.get("benchmark_norms", {
        "catalog_avg_failure_rate": 0.1685,
        "catalog_avg_cancel_rate": 0.0938,
        "catalog_avg_return_rate": 0.0795,
        "catalog_avg_discount": 0.1450,
        "catalog_avg_negative_margin_rate": 0.3794,
        "catalog_avg_stockout_rate": 0.0820,
        "catalog_avg_supplier_delay": 3.20
    })

    categories_radar = [
        "Failure Rate",
        "Return Rate",
        "Apparent Neg Margin",
        "Avg Discount",
        "Stockout Rate",
        "Supplier Delay (Scaled)"
    ]

    prod_radar = [
        detail.get("failure_rate", 0) * 100,
        detail.get("return_rate", 0) * 100,
        detail.get("negative_margin_rate", 0) * 100,
        detail.get("avg_discount", 0) * 100,
        detail.get("stockout_rate", 0) * 100,
        detail.get("avg_supplier_delay", 0) * 5 # scaled for display
    ]

    benchmark_radar = [
        norms.get("catalog_avg_failure_rate", 0.1685) * 100,
        norms.get("catalog_avg_return_rate", 0.0795) * 100,
        norms.get("catalog_avg_negative_margin_rate", 0.3794) * 100,
        norms.get("catalog_avg_discount", 0.1450) * 100,
        norms.get("catalog_avg_stockout_rate", 0.0820) * 100,
        norms.get("catalog_avg_supplier_delay", 3.20) * 5
    ]

    fig_rad = go.Figure()
    fig_rad.add_trace(go.Scatterpolar(
        r=benchmark_radar,
        theta=categories_radar,
        fill='toself',
        name='Catalog Benchmark Envelope',
        line=dict(color=COLOR_INFO, dash='dash'),
        fillcolor='rgba(56, 189, 248, 0.12)'
    ))
    fig_rad.add_trace(go.Scatterpolar(
        r=prod_radar,
        theta=categories_radar,
        fill='toself',
        name=f"SKU: {detail.get('product_id')}",
        line=dict(color=COLOR_HIGH_RISK if detail.get('risk_level') == 'High' else COLOR_MED_RISK, width=2.5),
        fillcolor='rgba(239, 68, 68, 0.22)'
    ))
    fig_rad.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, max(max(prod_radar) + 15, 80)], gridcolor="#262626"),
            angularaxis=dict(gridcolor="#262626")
        ),
        paper_bgcolor=PAPER_BG_COLOR,
        plot_bgcolor=PLOT_BG_COLOR,
        font=dict(color="#D4D4D4", family="Inter"),
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
        margin=dict(l=40, r=40, t=40, b=40),
        height=360
    )
    st.plotly_chart(fig_rad, use_container_width=True)
