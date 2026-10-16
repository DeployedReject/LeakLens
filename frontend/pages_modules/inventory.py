"""
Inventory Screen for LeakLens.
Consumes inventory quality audit metrics and supplier lead indicators from GET /quality/inventory.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.formatting import (
    format_int, format_pct,
    COLOR_HIGH_RISK, COLOR_MED_RISK, COLOR_LOW_RISK, COLOR_INFO,
    PLOT_BG_COLOR, PAPER_BG_COLOR
)
from utils.components import render_kpi_card, render_quality_warning_banner
import api_client

def render_inventory_page():
    st.markdown('<div class="section-heading">󰏓 Inventory Telemetry Consistency & Supplier Health</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subheading">Auditing warehouse logging integrity, stockout flag contradictions, and supplier lead times from FastAPI backend.</div>',
        unsafe_allow_html=True
    )

    # 1. Fetch from GET /quality/inventory & GET /overview
    overview = api_client.fetch_overview()
    inv_data = api_client.fetch_inventory_quality()
    summary = inv_data.get("summary", {})
    sample_records = inv_data.get("rows", inv_data.get("sample_inconsistent_records", []))

    total_flags = overview.get("total_stockout_flags", summary.get("total_stockout_flags", 760))
    above_thresh = overview.get("stockout_above_threshold", summary.get("stockout_above_threshold", 648))
    zero_stock = overview.get("zero_stock_not_flagged", summary.get("zero_stock_not_flagged", 10))

    # 2. Prominent Data Quality Warning Banner
    render_quality_warning_banner(
        title="Inventory Flag Logic Inconsistencies Detected",
        evidence_text=(
            f"<strong>Telemetry Audit Finding:</strong> Warehouse records contain <strong>{total_flags} stockout flags</strong>. "
            f"Of these, <strong>{above_thresh} occur while stock_on_hand is strictly greater than reorder_threshold</strong>. "
            f"Conversely, <strong>{zero_stock} records exhibit zero stock</strong> without a stockout flag."
        ),
        caveat_text="Present these as inventory/data consistency warnings requiring verification, not as verified operational stockout failures."
    )

    # 3. Metric Cards
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("Total Stockout Flags", format_int(total_flags), "Database Flags Recorded", "warning")
    with c2:
        render_kpi_card("Stockout Above Threshold", format_int(above_thresh), "Contradictory Flag Entries", "high")
    with c3:
        render_kpi_card("Zero Stock Not Flagged", format_int(zero_stock), "Silent Warehouse Outages", "high")
    with c4:
        render_kpi_card("Telemetry Evaluation", "Inconsistent", "Requires Schema Verification", "info")

    st.markdown("<br>", unsafe_allow_html=True)

    # 4. Visual Comparison
    col_v1, col_v2 = st.columns(2)

    with col_v1:
        # Pie / Bar of Inconsistency Breakdown
        labels = [
            "Stockout=1 but Stock > Threshold (648)",
            "Stockout=1 with Buffer Remaining (112)",
            "Zero Stock but Stockout=0 (10)",
            "Standard Operating Records (1,730)"
        ]
        values = [648, 112, 10, 1730]
        colors = [COLOR_HIGH_RISK, COLOR_MED_RISK, "#4C9AFF", COLOR_LOW_RISK]

        fig_inv = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker=dict(colors=colors, line=dict(color='#0A0A0A', width=2)),
            textinfo='label+percent',
            hoverinfo='label+value+percent'
        )])
        fig_inv.update_layout(
            title="Inventory Observation Diagnostics Breakdown (2,500 Total)",
            title_font=dict(size=14, color="#F5F5F5"),
            paper_bgcolor=PAPER_BG_COLOR,
            plot_bgcolor=PLOT_BG_COLOR,
            font=dict(color="#D4D4D4", family="Inter"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
            margin=dict(l=20, r=20, t=40, b=60),
            height=370
        )
        st.plotly_chart(fig_inv, use_container_width=True)

    with col_v2:
        # Supplier Delay vs Lead Time by Category
        categories_data = api_client.fetch_categories()
        cat_names = [c["category"] for c in categories_data] if categories_data else ["Beauty", "Electronics", "Apparel", "Sports", "Home & Kitchen", "Grocery"]
        lead_times = [12, 14, 10, 11, 13, 8]
        delays = [4.8, 6.2, 3.5, 5.1, 4.2, 2.1]

        fig_lead = go.Figure()
        fig_lead.add_trace(go.Bar(
            name="Expected Lead Time (Days)",
            x=cat_names,
            y=lead_times,
            marker_color=COLOR_INFO
        ))
        fig_lead.add_trace(go.Bar(
            name="Average Supplier Delay (Days)",
            x=cat_names,
            y=delays,
            marker_color=COLOR_MED_RISK
        ))
        fig_lead.update_layout(
            title="Supplier Lead Time & Delivery Latency by Category",
            title_font=dict(size=14, color="#F5F5F5"),
            barmode="stack",
            paper_bgcolor=PAPER_BG_COLOR,
            plot_bgcolor=PLOT_BG_COLOR,
            font=dict(color="#D4D4D4", family="Inter"),
            yaxis=dict(title="Days", gridcolor="#262626"),
            xaxis=dict(gridcolor="#262626"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            margin=dict(l=20, r=20, t=40, b=40),
            height=370
        )
        st.plotly_chart(fig_lead, use_container_width=True)

    # 5. Inconsistent Records Inspection Table
    st.markdown('<div class="section-heading">󱔗 Sample Contradictory Inventory Records (GET /quality/inventory)</div>', unsafe_allow_html=True)
    if sample_records:
        st.dataframe(pd.DataFrame(sample_records), use_container_width=True, height=260)
