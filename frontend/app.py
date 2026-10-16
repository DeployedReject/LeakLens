"""
LeakLens - Explainable Revenue & Operational Risk Monitor
Track: Business - "The Money Leak" (Datathon 2026)
Presentation Layer communicating with FastAPI Backend over HTTP/JSON.
"""

from pathlib import Path
import streamlit as st

# Configure wide layout and page identity
st.set_page_config(
    page_title="LeakLens | Revenue & Operational Risk Monitor",
    page_icon="󰍉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load Custom CSS Theme
css_path = Path(__file__).parent / "style.css"
if css_path.exists():
    with open(css_path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Import Frontend API Client & Screens
import api_client
from utils.components import render_html
from pages_modules.overview import render_overview_page
from pages_modules.products import render_products_page
from pages_modules.transactions import render_transactions_page
from pages_modules.inventory import render_inventory_page
from pages_modules.campaigns import render_campaigns_page
from pages_modules.upload import render_upload_page

# 6 Navigation Screens
PAGES = [
    "Executive Overview",
    "Product Risk",
    "Transactions",
    "Inventory",
    "Campaigns",
    "Data Upload / Re-analyze"
]

if "current_page" not in st.session_state:
    st.session_state["current_page"] = "Executive Overview"

# ==========================================
# SIDEBAR NAVIGATION & FASTAPI STATUS
# ==========================================
with st.sidebar:
    # Sidebar Header
    render_html("""
    <div style="padding: 10px 0 16px 0; border-bottom: 1px solid #262626;">
        <div style="display:flex; align-items:center; gap:10px;">
            <div style="background:#F6821F; width:38px; height:38px; border-radius:6px; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:1.25rem; color:#0A0A0A;">
                L
            </div>
            <div>
                <div style="font-size:1.3rem; font-weight:700; color:#F5F5F5; letter-spacing:-0.01em; line-height:1.1;">LeakLens</div>
                <div style="font-size:0.75rem; color:#A3A3A3; font-weight:400;">Revenue & Risk Monitor</div>
            </div>
        </div>
        <div style="margin-top:12px; font-size:0.75rem; color:#F6821F; font-weight:600; text-transform:uppercase; letter-spacing:0.03em;">
            Datathon 2026 • Business Track
        </div>
    </div>
    """)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div style='font-size:0.8rem; text-transform:uppercase; color:#A3A3A3; font-weight:600; margin-bottom:8px;'>Navigation</div>", unsafe_allow_html=True)

    # Page Selection Radio
    current_idx = PAGES.index(st.session_state["current_page"]) if st.session_state["current_page"] in PAGES else 0
    selected_page = st.radio(
        label="Select View",
        options=PAGES,
        index=current_idx,
        label_visibility="collapsed"
    )

    if selected_page != st.session_state["current_page"]:
        st.session_state["current_page"] = selected_page
        st.rerun()

    st.markdown("<hr style='border-color:#262626; margin:20px 0;'>", unsafe_allow_html=True)

    # Backend Connection Indicator
    health = api_client.check_backend_health()
    is_online = health.get("status") == "ok"

    status_color = "#10B981" if is_online else "#EF4444"
    status_label = "FastAPI Backend Online" if is_online else "FastAPI Backend Offline"
    model_name = health.get("model", "IsolationForest") if is_online else "Unavailable"
    p_count = health.get("product_count", 0) if is_online else 0
    dataset_hash = health.get("dataset_hash", "-") if is_online else "-"
    trained_at = health.get("trained_at_utc", "-") if is_online else "-"

    render_html(f"""
    <div style="background:#141414; border:1px solid #262626; border-radius:6px; padding:12px; margin-bottom:16px;">
        <div style="display:flex; align-items:center; gap:8px;">
            <span style="display:inline-block; width:8px; height:8px; background:{status_color}; border-radius:50%;"></span>
            <span style="font-size:0.8rem; font-weight:700; color:{status_color};">{status_label}</span>
        </div>
        <div style="font-size:0.75rem; color:#A3A3A3; margin-top:6px;">
            Service: <code>http://localhost:8000</code><br>
            ML Model: <strong>{model_name}</strong><br>
            Catalog Scored: <strong>{p_count} SKUs</strong><br>
            Dataset: <code>{dataset_hash}</code><br>
            Trained: <strong>{trained_at[:19] if trained_at and trained_at != '-' else '-'}</strong> UTC
        </div>
    </div>
    """)

    render_html("""
    <div style="margin-top:24px; padding-top:12px; border-top:1px solid #141414; font-size:0.72rem; color:#6E6E6E;">
        LeakLens Architecture v2.1<br>
        FastAPI Backend + Streamlit Frontend
    </div>
    """)

# ==========================================
# PAGE ROUTING
# ==========================================
active_page = st.session_state["current_page"]

if not is_online:
    st.error(
        "LeakLens backend is offline. Dashboard values are intentionally not replaced "
        "with mock or hardcoded data. Start FastAPI on port 8000, then refresh this page."
    )
    st.code("python -m uvicorn app:app --host 0.0.0.0 --port 8000", language="bash")
    st.stop()

if active_page == "Executive Overview":
    render_overview_page()

elif active_page == "Product Risk":
    render_products_page()

elif active_page == "Transactions":
    render_transactions_page()

elif active_page == "Inventory":
    render_inventory_page()

elif active_page == "Campaigns":
    render_campaigns_page()

elif active_page == "Data Upload / Re-analyze":
    render_upload_page()
