import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.formatting import format_int, COLOR_HIGH_RISK, COLOR_MED_RISK, COLOR_LOW_RISK, COLOR_INFO, PLOT_BG_COLOR, PAPER_BG_COLOR
from utils.components import render_kpi_card, render_quality_warning_banner
import api_client

def render_campaigns_page():
    st.markdown('<div class="section-heading">Campaign Spend & Funnel Quality Audit</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subheading">Auditing marketing telemetry integrity and separating trusted funnel metrics from logically inconsistent rows.</div>', unsafe_allow_html=True)
    camp_data = api_client.fetch_campaign_quality()
    summary = camp_data.get('summary', {})
    sample_records = camp_data.get('rows', [])
    total = int(summary.get('total_campaigns', 0))
    invalid_total = int(summary.get('invalid_rows', 0))
    clean = int(summary.get('clean_rows', max(total - invalid_total, 0)))
    clicks_only = int(summary.get('clicks_only_rows', 0))
    conv_only = int(summary.get('conversions_only_rows', 0))
    overlap = int(summary.get('overlap_rows', 0))
    df_bad = pd.DataFrame(sample_records)
    invalid_clicks = int(df_bad.get('invalid_clicks', pd.Series(dtype=bool)).sum()) if not df_bad.empty else clicks_only + overlap
    invalid_convs = int(df_bad.get('invalid_conversions', pd.Series(dtype=bool)).sum()) if not df_bad.empty else conv_only + overlap
    render_quality_warning_banner(title=f'Impossible Funnel Telemetry Detected ({invalid_total} Rows)', evidence_text=f'<strong>Attribution integrity warning:</strong> {invalid_clicks} rows have clicks greater than impressions and {invalid_convs} rows have conversions greater than clicks. Affected rows are excluded from trusted CTR/CVR summaries.', caveat_text='These are data-quality warnings, not business-performance claims.')
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_kpi_card('Campaigns Evaluated', format_int(total), 'Current uploaded dataset', 'neutral')
    with c2:
        render_kpi_card('Clicks > Impressions', format_int(invalid_clicks), 'Impossible CTR relationship', 'high')
    with c3:
        render_kpi_card('Conversions > Clicks', format_int(invalid_convs), 'Impossible CVR relationship', 'high')
    with c4:
        render_kpi_card('Trusted Clean Rows', format_int(clean), 'Used for trusted funnel KPIs', 'good')
    st.markdown('<br>', unsafe_allow_html=True)
    col_v1, col_v2 = st.columns(2)
    with col_v1:
        trusted_ctr = float(summary.get('trusted_ctr_pct', 0))
        trusted_cvr = float(summary.get('trusted_cvr_pct', 0))
        raw_ctr = float(summary.get('raw_ctr_pct', 0))
        raw_cvr = float(summary.get('raw_cvr_pct', 0))
        fig = go.Figure()
        fig.add_trace(go.Bar(name='Trusted clean rows', x=['CTR (%)', 'CVR (%)'], y=[trusted_ctr, trusted_cvr], marker_color=COLOR_LOW_RISK))
        fig.add_trace(go.Bar(name='Raw all rows', x=['CTR (%)', 'CVR (%)'], y=[raw_ctr, raw_cvr], marker_color=COLOR_HIGH_RISK))
        fig.update_layout(title='Trusted vs Raw Funnel Metrics', barmode='group', paper_bgcolor=PAPER_BG_COLOR, plot_bgcolor=PLOT_BG_COLOR, font=dict(color='#D4D4D4', family='Inter'), yaxis=dict(title='Percentage (%)', gridcolor='#262626'), legend=dict(orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5), margin=dict(l=20, r=20, t=40, b=40), height=340)
        st.plotly_chart(fig, use_container_width=True)
    with col_v2:
        labels = ['Trusted clean', 'Clicks-only issue', 'Conversions-only issue', 'Both issues']
        values = [clean, clicks_only, conv_only, overlap]
        colors = [COLOR_LOW_RISK, COLOR_HIGH_RISK, COLOR_MED_RISK, '#DC2626']
        fig_pie = go.Figure(data=[go.Pie(labels=labels, values=values, hole=0.55, marker=dict(colors=colors, line=dict(color='#0A0A0A', width=2)), textinfo='label+percent', hoverinfo='label+value+percent')])
        fig_pie.update_layout(title=f'Campaign Telemetry Reliability ({total:,} Rows)', paper_bgcolor=PAPER_BG_COLOR, plot_bgcolor=PLOT_BG_COLOR, font=dict(color='#D4D4D4', family='Inter'), legend=dict(orientation='h', yanchor='bottom', y=-0.35, xanchor='center', x=0.5), margin=dict(l=20, r=20, t=40, b=60), height=340)
        st.plotly_chart(fig_pie, use_container_width=True)
    st.markdown('<div class="section-heading">Sample Impossible Funnel Rows</div>', unsafe_allow_html=True)
    if sample_records:
        st.dataframe(pd.DataFrame(sample_records), use_container_width=True, height=260)
