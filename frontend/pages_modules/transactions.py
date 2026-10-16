"""
Transactions Screen for LeakLens.
Consumes transaction status summaries, category failed values, and discount margin tiers from the FastAPI backend.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from utils.formatting import (
    format_inr, format_pct, format_int,
    COLOR_HIGH_RISK, COLOR_MED_RISK, COLOR_LOW_RISK, COLOR_INFO,
    PLOT_BG_COLOR, PAPER_BG_COLOR
)
from utils.components import render_kpi_card
import api_client

def render_transactions_page():
    st.markdown('<div class="section-heading">󰿯 Transaction Status & Margin Compression</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subheading">Evaluating transaction-value exposure, failure distributions, and discount-level margin risk.</div>',
        unsafe_allow_html=True
    )

    # 1. Fetch Data from API
    overview = api_client.fetch_overview()
    tx_summary = api_client.fetch_transactions_summary()
    categories_data = api_client.fetch_categories()

    status_dist = tx_summary["status_distribution"]
    total_transactions = tx_summary.get("total_transactions", sum(v["count"] for v in status_dist.values()))

    # KPI Strip: Completed, Cancelled, Returned, Pending
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card(
            title="Completed Orders",
            value=format_int(status_dist["Completed"]["count"]),
            subtext=f"{status_dist['Completed']['pct']}% | {format_inr(status_dist['Completed']['value'], True)}",
            risk_style="good"
        )
    with c2:
        render_kpi_card(
            title="Cancelled Orders",
            value=format_int(status_dist["Cancelled"]["count"]),
            subtext=f"{status_dist['Cancelled']['pct']}% | {format_inr(status_dist['Cancelled']['value'], True)}",
            risk_style="high"
        )
    with c3:
        render_kpi_card(
            title="Returned Orders",
            value=format_int(status_dist["Returned"]["count"]),
            subtext=f"{status_dist['Returned']['pct']}% | {format_inr(status_dist['Returned']['value'], True)}",
            risk_style="warning"
        )
    with c4:
        render_kpi_card(
            title="Pending Settlement",
            value=format_int(status_dist["Pending"]["count"]),
            subtext=f"{status_dist['Pending']['pct']}% | {format_inr(status_dist['Pending']['value'], True)}",
            risk_style="info"
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Visual Row 1: Status Breakdown vs Category Failure
    col_v1, col_v2 = st.columns(2)

    with col_v1:
        # Donut Chart: Status Distribution
        labels = list(status_dist.keys())
        counts = [status_dist[k]["count"] for k in labels]
        colors = [COLOR_LOW_RISK, COLOR_HIGH_RISK, COLOR_MED_RISK, COLOR_INFO]

        fig_status = go.Figure(data=[go.Pie(
            labels=labels,
            values=counts,
            hole=0.55,
            marker=dict(colors=colors, line=dict(color='#0A0A0A', width=2)),
            textinfo='label+percent',
            hoverinfo='label+value+percent'
        )])
        fig_status.update_layout(
            title=f"Transaction Status Distribution ({total_transactions:,} Volume)",
            title_font=dict(size=14, color="#F5F5F5"),
            paper_bgcolor=PAPER_BG_COLOR,
            plot_bgcolor=PLOT_BG_COLOR,
            font=dict(color="#D4D4D4", family="Inter"),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            margin=dict(l=20, r=20, t=40, b=40),
            height=340
        )
        st.plotly_chart(fig_status, use_container_width=True)

    with col_v2:
        # Failed Value by Category
        df_cat = pd.DataFrame(categories_data)
        fig_failed_val = px.bar(
            df_cat,
            x="category",
            y="failed_transaction_value",
            color="category",
            color_discrete_sequence=["#F6821F", "#F59E0B", "#EF4444", "#4C9AFF", "#10B981", "#6E6E6E"],
            title="Failed Transaction Value Exposure by Category (₹)",
            text_auto=True
        )
        fig_failed_val.update_layout(
            paper_bgcolor=PAPER_BG_COLOR,
            plot_bgcolor=PLOT_BG_COLOR,
            font=dict(color="#D4D4D4", family="Inter"),
            yaxis=dict(title="Exposed Value (₹)", gridcolor="#262626"),
            xaxis=dict(title="Category", gridcolor="#262626"),
            showlegend=False,
            margin=dict(l=20, r=20, t=40, b=40),
            height=340
        )
        st.plotly_chart(fig_failed_val, use_container_width=True)

    # Visual Row 2: Failure Rate by Category vs Margin Risk by Discount
    col_v3, col_v4 = st.columns(2)

    with col_v3:
        # Failure Rate by Category
        fig_fail_rate = px.bar(
            df_cat,
            x="category",
            y="failure_rate",
            title="Failure Rate by Category (%)",
            color_discrete_sequence=[COLOR_MED_RISK],
            text_auto='.1f'
        )
        fig_fail_rate.update_layout(
            paper_bgcolor=PAPER_BG_COLOR,
            plot_bgcolor=PLOT_BG_COLOR,
            font=dict(color="#D4D4D4", family="Inter"),
            yaxis=dict(title="Failure Rate (%)", gridcolor="#262626"),
            xaxis=dict(title="Category", gridcolor="#262626"),
            margin=dict(l=20, r=20, t=40, b=40),
            height=340
        )
        st.plotly_chart(fig_fail_rate, use_container_width=True)

    with col_v4:
        # Margin Risk by Discount Tier
        discount_bands = tx_summary["discount_margin_bands"]

        df_bands = pd.DataFrame(discount_bands)
        fig_disc = go.Figure()
        fig_disc.add_trace(go.Bar(
            x=df_bands["band"],
            y=df_bands["orders"],
            name="Order Count",
            marker_color="#3A3A3A",
            yaxis="y"
        ))
        fig_disc.add_trace(go.Scatter(
            x=df_bands["band"],
            y=df_bands["negative_margin_rate"],
            name="Apparent Negative Margin %",
            mode="lines+markers",
            line=dict(color=COLOR_HIGH_RISK, width=3),
            marker=dict(size=8, color=COLOR_HIGH_RISK),
            yaxis="y2"
        ))
        fig_disc.update_layout(
            title="Margin Risk by Discount Band",
            title_font=dict(size=14, color="#F5F5F5"),
            paper_bgcolor=PAPER_BG_COLOR,
            plot_bgcolor=PLOT_BG_COLOR,
            font=dict(color="#D4D4D4", family="Inter"),
            xaxis=dict(title="Discount Band", gridcolor="#262626"),
            yaxis=dict(title="Order Count", gridcolor="#262626"),
            yaxis2=dict(
                title="Negative Margin %",
                overlaying="y",
                side="right",
                range=[0, 100],
                showgrid=False
            ),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5),
            margin=dict(l=20, r=20, t=40, b=40),
            height=340
        )
        st.plotly_chart(fig_disc, use_container_width=True)
