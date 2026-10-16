"""Inventory quality screen driven entirely by FastAPI results."""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.formatting import format_int, COLOR_HIGH_RISK, COLOR_MED_RISK, COLOR_LOW_RISK, COLOR_INFO, PLOT_BG_COLOR, PAPER_BG_COLOR
from utils.components import render_kpi_card, render_quality_warning_banner
import api_client


def render_inventory_page():
    st.markdown('<div class="section-heading">Inventory Telemetry Consistency & Supplier Health</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subheading">Auditing warehouse logging integrity, stockout contradictions, and supplier timing from the current backend analysis.</div>',
        unsafe_allow_html=True,
    )

    inv_data = api_client.fetch_inventory_quality()
    summary = inv_data.get("summary", {})
    sample_records = inv_data.get("rows", [])

    total_records = int(summary.get("total_records", 0))
    total_flags = int(summary.get("total_stockout_flags", 0))
    above_thresh = int(summary.get("stockout_above_threshold", 0))
    zero_stock = int(summary.get("zero_stock_not_flagged", 0))
    other_records = int(summary.get("other_records", max(total_records - above_thresh - zero_stock, 0)))

    render_quality_warning_banner(
        title="Inventory Flag Logic Inconsistencies Detected",
        evidence_text=(
            f"<strong>Telemetry audit:</strong> {total_flags} stockout flags were recorded. "
            f"{above_thresh} occur while stock is above the reorder threshold, and {zero_stock} zero-stock records are not flagged."
        ),
        caveat_text="These are consistency warnings requiring verification, not confirmed physical warehouse failures.",
    )

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card("Inventory Records", format_int(total_records), "Current uploaded dataset", "neutral")
    with c2:
        render_kpi_card("Total Stockout Flags", format_int(total_flags), "Database flags", "warning")
    with c3:
        render_kpi_card("Stockout Above Threshold", format_int(above_thresh), "Contradictory entries", "high")
    with c4:
        render_kpi_card("Zero Stock Not Flagged", format_int(zero_stock), "Silent zero-stock entries", "high")

    st.markdown("<br>", unsafe_allow_html=True)
    col_v1, col_v2 = st.columns(2)

    with col_v1:
        labels = ["Stockout above threshold", "Zero stock not flagged", "Other records"]
        values = [above_thresh, zero_stock, other_records]
        colors = [COLOR_HIGH_RISK, COLOR_MED_RISK, COLOR_LOW_RISK]
        fig_inv = go.Figure(data=[go.Pie(
            labels=labels,
            values=values,
            hole=0.55,
            marker=dict(colors=colors, line=dict(color="#0A0A0A", width=2)),
            textinfo="label+percent",
            hoverinfo="label+value+percent",
        )])
        fig_inv.update_layout(
            title=f"Inventory Consistency Breakdown ({total_records:,} Records)",
            paper_bgcolor=PAPER_BG_COLOR,
            plot_bgcolor=PLOT_BG_COLOR,
            font=dict(color="#D4D4D4", family="Inter"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.35, xanchor="center", x=0.5),
            margin=dict(l=20, r=20, t=40, b=60),
            height=370,
        )
        st.plotly_chart(fig_inv, use_container_width=True)

    with col_v2:
        supplier = pd.DataFrame(summary.get("supplier_by_category", []))
        fig_lead = go.Figure()
        if not supplier.empty:
            fig_lead.add_trace(go.Bar(
                name="Avg Product Lead Time",
                x=supplier["category"],
                y=supplier["avg_supplier_lead_days"],
                marker_color=COLOR_INFO,
            ))
            fig_lead.add_trace(go.Bar(
                name="Avg Observed Supplier Delay",
                x=supplier["category"],
                y=supplier["avg_supplier_delay"],
                marker_color=COLOR_MED_RISK,
            ))
        fig_lead.update_layout(
            title="Supplier Lead Time & Observed Delay by Category",
            barmode="group",
            paper_bgcolor=PAPER_BG_COLOR,
            plot_bgcolor=PLOT_BG_COLOR,
            font=dict(color="#D4D4D4", family="Inter"),
            yaxis=dict(title="Days", gridcolor="#262626"),
            xaxis=dict(gridcolor="#262626"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            margin=dict(l=20, r=20, t=40, b=40),
            height=370,
        )
        st.plotly_chart(fig_lead, use_container_width=True)

    st.markdown('<div class="section-heading">Sample Contradictory Inventory Records</div>', unsafe_allow_html=True)
    if sample_records:
        st.dataframe(pd.DataFrame(sample_records), use_container_width=True, height=260)
