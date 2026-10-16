"""
Data Upload & Re-analyze Screen for LeakLens.
Enables uploading 5 CSVs (customers, products, transactions, inventory, campaigns),
triggers POST /analyze on the FastAPI backend, retrains Isolation Forest,
and refreshes dashboard components.
"""

import io
from pathlib import Path
import streamlit as st
import pandas as pd
from utils.formatting import format_inr, format_pct
from utils.components import render_html
import api_client

def render_upload_page():
    st.markdown('<div class="section-heading">󰓦 Ingestion & ML Model Retraining (POST /analyze)</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-subheading">Upload updated business datasets. The FastAPI backend will join records, calculate operational friction, engineer feature profiles, and retrain the Isolation Forest model.</div>',
        unsafe_allow_html=True
    )

    render_html("""
    <div style="background:#141414; border:1px solid #262626; border-radius:6px; padding:18px; margin-bottom:20px;">
        <div style="font-weight:600; color:#F5F5F5; font-size:1.05rem; margin-bottom:6px;">Required Dataset Suite (5 CSV Files)</div>
        <div style="color:#D4D4D4; font-size:0.88rem; line-height:1.5;">
            To perform an end-to-end catalog recalculation and Isolation Forest retrain, provide all five operational tables:
            <code>customers.csv</code>, <code>products.csv</code>, <code>transactions.csv</code>, <code>inventory.csv</code>, and <code>campaigns.csv</code>.
        </div>
    </div>
    """)

    col1, col2 = st.columns(2)
    with col1:
        f_cust = st.file_uploader("1. customers.csv", type=["csv"], key="up_cust")
        f_prod = st.file_uploader("2. products.csv", type=["csv"], key="up_prod")
        f_txns = st.file_uploader("3. transactions.csv", type=["csv"], key="up_txns")

    with col2:
        f_inv = st.file_uploader("4. inventory.csv", type=["csv"], key="up_inv")
        f_camp = st.file_uploader("5. campaigns.csv", type=["csv"], key="up_camp")
        
        st.markdown("<br>", unsafe_allow_html=True)
        use_sample = st.checkbox("Generate & Use Calibrated Datathon Sample Files", value=False, help="Automatically synthesize standard Datathon 2026 CSV files for quick demo testing.")

    st.markdown("<hr style='border-color:#262626; margin:20px 0;'>", unsafe_allow_html=True)

    all_uploaded = all([f_cust, f_prod, f_txns, f_inv, f_camp]) or use_sample

    btn_label = "󱓞 Run End-to-End Pipeline & Retrain Isolation Forest"
    if st.button(btn_label, type="primary", disabled=not all_uploaded, use_container_width=True):
        with st.spinner("Uploading datasets to FastAPI backend, auditing telemetry, joining tables, and retraining Isolation Forest..."):
            try:
                # If using synthetic sample generator for demo
                if use_sample and not all([f_cust, f_prod, f_txns, f_inv, f_camp]):
                    sample_dir = Path(__file__).resolve().parent.parent.parent / "backend" / "data"
                    if not (sample_dir / "customers.csv").exists():
                        st.error("Sample CSV files not found in backend/data. Please upload the 5 files.")
                        return
                    
                    with open(sample_dir / "customers.csv", "rb") as fc:
                        b_c = io.BytesIO(fc.read())
                    with open(sample_dir / "products.csv", "rb") as fp:
                        b_p = io.BytesIO(fp.read())
                    with open(sample_dir / "transactions.csv", "rb") as ft:
                        b_t = io.BytesIO(ft.read())
                    with open(sample_dir / "inventory.csv", "rb") as fi:
                        b_i = io.BytesIO(fi.read())
                    with open(sample_dir / "campaigns.csv", "rb") as fcm:
                        b_cm = io.BytesIO(fcm.read())

                    res = api_client.post_analyze_datasets(b_c, b_p, b_t, b_i, b_cm)
                else:
                    res = api_client.post_analyze_datasets(f_cust, f_prod, f_txns, f_inv, f_camp)

                # Exactly required confirmation message:
                st.success(
                    "󰗠 **Analysis refreshed. ML risk rankings have been recalculated using the latest dataset.**"
                )

                # Show updated pipeline metrics
                ov = res.get("overview", {})
                st.markdown("#### Post-Analysis Telemetry & Model Summary")
                res_col1, res_col2, res_col3, res_col4 = st.columns(4)
                with res_col1:
                    st.metric("Total Order Value", format_inr(ov.get("total_transaction_value", 0), in_lakhs=True))
                with res_col2:
                    st.metric("Combined Exposure", format_inr(ov.get("combined_exposure", 0), in_lakhs=True))
                with res_col3:
                    st.metric("Negative Margin Rate", format_pct(ov.get("negative_margin_rate", 0)))
                with res_col4:
                    st.metric("SKUs Scored (Isolation Forest)", f"{res.get('product_count', 250)} SKUs")

                st.markdown("<br>", unsafe_allow_html=True)
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button("󰄨 View Refreshed Executive Overview →", use_container_width=True, type="primary"):
                        st.session_state["current_page"] = "Executive Overview"
                        st.rerun()
                with col_btn2:
                    if st.button("󰏓 Inspect Recalculated Product Risk Rankings →", use_container_width=True):
                        st.session_state["current_page"] = "Product Risk"
                        st.rerun()

            except Exception as e:
                st.error(f"Error during backend analysis execution: {str(e)}")
