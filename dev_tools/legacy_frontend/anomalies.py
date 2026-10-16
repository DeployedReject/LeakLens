import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from utils.formatting import format_inr, format_pct, get_risk_badge, COLOR_HIGH_RISK, COLOR_MED_RISK, COLOR_LOW_RISK, COLOR_INFO, PLOT_BG_COLOR, PAPER_BG_COLOR
from utils.components import render_kpi_card, render_ml_explainer, render_html

def render_anomalies_page(df_products):
    st.markdown('<div class="section-heading">\U000f09d1 Multivariate Anomaly Explorer (Isolation Forest)</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subheading">Prioritizing products whose operational and financial signatures deviate significantly from catalog norms.</div>', unsafe_allow_html=True)
    render_ml_explainer()
    ranked_products = df_products.sort_values(by='anomaly_score', ascending=False).reset_index(drop=True)
    ranked_products['rank'] = ranked_products.index + 1
    high_outliers = (ranked_products['anomaly_score'] >= 0.8).sum()
    median_score = ranked_products['anomaly_score'].median()
    total_exposure = ranked_products[ranked_products['risk_score'] == 'High']['estimated_impact'].sum()
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        render_kpi_card('Severe Outliers (Score ≥ 0.80)', str(high_outliers), 'Immediate investigation', 'high')
    with k2:
        render_kpi_card('Catalog Median Score', f'{median_score:.2f}', 'Typical baseline behavior', 'neutral')
    with k3:
        render_kpi_card('Exposed Value in Outliers', format_inr(total_exposure, True), 'Combined transaction exposure', 'high')
    with k4:
        render_kpi_card('ML Model', 'Isolation Forest', 'Multi-dimensional density', 'info')
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown('#### Ranked Outlier Priority Queue')
    st.dataframe(ranked_products[['rank', 'product_name', 'category', 'risk_score', 'anomaly_score', 'why_flagged', 'estimated_impact']].rename(columns={'rank': 'Rank', 'product_name': 'Product', 'category': 'Category', 'risk_score': 'Risk', 'anomaly_score': 'Anomaly Score', 'why_flagged': 'Main Reason', 'estimated_impact': 'Transaction Exposure'}).style.format({'Anomaly Score': '{:.2f}', 'Transaction Exposure': '₹{:,.0f}'}), use_container_width=True, height=270)
    st.markdown('<br>', unsafe_allow_html=True)
    st.markdown('<div class="section-heading">\U000f0654 Anomaly Profile & Metric Deviation Inspector</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-subheading">Compare a flagged product against catalog normal operating envelopes across 5 operational dimensions.</div>', unsafe_allow_html=True)
    options = [f"#{row['rank']} | {row['product_id']} — {row['product_name']}" for _, row in ranked_products.iterrows()]
    selected_option = st.selectbox('Select Flagged Product to Explain', options, index=0)
    selected_idx = int(selected_option.split(' | ')[0].replace('#', '')) - 1
    prod = ranked_products.iloc[selected_idx]
    c_chart, c_details = st.columns([1, 1])
    with c_chart:
        categories_radar = ['Failure Rate', 'Return Rate', 'Negative Margin %', 'Average Discount', 'Supplier Delay']
        prod_values = [prod['failure_rate'], prod['return_rate'], prod['negative_margin_rate'], prod['avg_discount'], prod['supplier_delay'] * 10]
        normal_benchmarks = [7.5, 4.0, 15.0, 15.0, 15.0]
        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(r=normal_benchmarks, theta=categories_radar, fill='toself', name='Catalog Normal Envelope', line=dict(color=COLOR_INFO, dash='dash'), fillcolor='rgba(56, 189, 248, 0.15)'))
        fig_radar.add_trace(go.Scatterpolar(r=prod_values, theta=categories_radar, fill='toself', name=f"{prod['product_name'][:25]}...", line=dict(color=COLOR_HIGH_RISK, width=2.5), fillcolor='rgba(239, 68, 68, 0.25)'))
        fig_radar.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, max(max(prod_values) + 10, 75)], gridcolor='#262626'), angularaxis=dict(gridcolor='#262626')), paper_bgcolor=PAPER_BG_COLOR, plot_bgcolor=PLOT_BG_COLOR, font=dict(color='#D4D4D4', family='Inter'), title=f"Multivariate Deviation Signature: #{prod['rank']} {prod['product_name'][:24]}", title_font=dict(size=13, color='#F5F5F5'), legend=dict(orientation='h', yanchor='bottom', y=-0.25, xanchor='center', x=0.5), margin=dict(l=40, r=40, t=40, b=40), height=370)
        st.plotly_chart(fig_radar, use_container_width=True)
    with c_details:
        render_html(f"""\n        <div style="background:#141414; border:1px solid #262626; border-radius:10px; padding:20px; height:100%;">\n            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">\n                <span style="font-size:0.85rem; color:#A3A3A3; text-transform:uppercase; font-weight:600;">Rank #{prod['rank']} | {prod['category']}</span>\n                {get_risk_badge(prod['risk_score'])}\n            </div>\n            \n            <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px;">\n                <div style="background:#0A0A0A; padding:10px; border-radius:6px; border:1px solid #262626;">\n                    <div style="font-size:0.75rem; color:#A3A3A3;">Anomaly Score</div>\n                    <div style="font-size:1.4rem; font-weight:700; color:#EF4444;">{prod['anomaly_score']:.2f}</div>\n                    <div style="font-size:0.75rem; color:#6E6E6E;">Isolation Forest Metric</div>\n                </div>\n                <div style="background:#0A0A0A; padding:10px; border-radius:6px; border:1px solid #262626;">\n                    <div style="font-size:0.75rem; color:#A3A3A3;">Potential Exposure</div>\n                    <div style="font-size:1.4rem; font-weight:700; color:#F59E0B;">{format_inr(prod['estimated_impact'])}</div>\n                    <div style="font-size:0.75rem; color:#6E6E6E;">Transaction Value</div>\n                </div>\n            </div>\n\n            <div style="font-size:0.85rem; color:#EF4444; font-weight:700; text-transform:uppercase; margin-bottom:4px;">\n                \U000f0241 Highlighted Abnormal Values:\n            </div>\n            <div class="issue-evidence-box" style="margin-top:4px; margin-bottom:12px;">\n                {prod['why_flagged']}\n                <div style="margin-top:4px; font-size:0.85rem; color:#A3A3A3;">\n                    • Negative Margin Rate: <strong>{prod['negative_margin_rate']}%</strong> (Peer Baseline: ~15%)<br>\n                    • Failure Rate: <strong>{prod['failure_rate']}%</strong> (Peer Baseline: ~7.5%)\n                </div>\n            </div>\n\n            <div style="font-size:0.85rem; color:#F59E0B; font-weight:700; text-transform:uppercase; margin-bottom:4px;">\n                \U000f05d1 Data Confidence:\n            </div>\n            <div style="font-size:0.86rem; color:#FDE68A; background:rgba(245, 158, 11, 0.1); border-left:3px solid #F59E0B; padding:8px 12px; border-radius:4px; margin-bottom:12px;">\n                Cost fields in the source dataset were independently generated. Apparent negative margins should be verified against supplier wholesale invoices.\n            </div>\n\n            <div style="font-size:0.85rem; color:#10B981; font-weight:700; text-transform:uppercase; margin-bottom:4px;">\n                \U000f04fe Suggested Next Investigation:\n            </div>\n            <div class="issue-action-box" style="margin-top:4px; margin-bottom:0;">\n                {prod['recommended_action']}\n            </div>\n        </div>\n        """)
