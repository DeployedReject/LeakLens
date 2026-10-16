# LeakLens 🔍
### *Explainable Revenue & Operational Risk Monitor*
**Datathon 2026** | **Track:** Business — *“The Money Leak”*

---

## 🏛️ System Architecture

LeakLens strictly enforces decoupling between analytical computing and user interface delivery:

```
┌────────────────────────────────────────┐
│           Streamlit Frontend           │
│         (Pure Presentation Layer)      │
│          http://localhost:8501         │
└───────────────────▲────────────────────┘
                    │ HTTP / JSON
┌───────────────────▼────────────────────┐
│            FastAPI Backend             │
│        (Data Engine & ML Core)         │
│          http://localhost:8000         │
└────────────────────────────────────────┘
```

- **FastAPI Backend (`http://localhost:8000`):** Performs all Pandas aggregation, multi-table joins, telemetry quality auditing, feature engineering, Isolation Forest unsupervised outlier scoring, and explainable recommendation synthesis.
- **Streamlit Frontend (`http://localhost:8501`):** Pure presentation interface consuming JSON payloads from the backend. Contains zero embedded business logic or ML training algorithms.

---

## 📡 Backend API Endpoints Reference

| Endpoint | Method | Purpose | Key Payload Fields |
| :--- | :--- | :--- | :--- |
| `/health` | `GET` | Health check & model status | `status`, `model`, `product_count` |
| `/overview` | `GET` | Headline exposure KPIs | `total_transaction_value`, `combined_exposure`, `exposure_pct`, `negative_margin_rate`, `invalid_campaign_rows`, `stockout_above_threshold` |
| `/products/risk` | `GET` | Sorted catalog risk rankings | `product_id`, `category`, `risk_score`, `risk_level`, `why_flagged`, `recommended_action` |
| `/products/{id}` | `GET` | SKU deep-dive drilldown | `risk_score`, `transaction_volume`, operational rates, benchmark comparisons, caveats |
| `/categories` | `GET` | Category risk comparison | `category`, `failure_rate`, `negative_margin_rate`, `failed_transaction_value` |
| `/quality/campaigns` | `GET` | Funnel telemetry anomalies | 171 invalid rows (84 clicks > imp, 88 conv > clicks) |
| `/quality/inventory` | `GET` | Warehouse contradiction flags | 760 stockout flags (648 with stock > reorder threshold, 10 unflagged zero-stock) |
| `/transactions/summary` | `GET` | Order distribution & discount tiers | Status volume & discount margin leak bands |
| `/analyze` | `POST` | Ingests 5 CSVs & retrains ML | `customers.csv`, `products.csv`, `transactions.csv`, `inventory.csv`, `campaigns.csv` |

---

## 🚀 Running LeakLens

You can run both services concurrently with a single command:

```bash
# Unified Launcher (starts FastAPI on port 8000 and Streamlit on port 8501)
python run_services.py
```

*Or launch each service in separate terminals:*

```bash
# Terminal 1 - Backend:
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2 - Frontend:
streamlit run app.py
```

---

## ⏱️ 20-Second Judge Pitch Walkthrough

1. **Executive Overview:** Land on the dashboard. Point to **₹16.22 Lakh combined transaction exposure** (18.18% of gross volume). Review Issue **#1 Pricing & Margin Anomalies** (37.94% apparent negative margin rate).
2. **Category Diagnostic:** Highlight the observed signal: **Beauty category margin risk sits at 55.21%**, far exceeding peer departments despite similar transaction failure rates (~16.85%).
3. **Product Risk:** Jump to **Product Risk**, sort by risk score, and select SKU `PR0001`. Review the dual-panel explanation:
   - **Why This Needs Attention:** Identifies specific evidence triggers (high supplier delay, unusual inventory behavior).
   - **Suggested Investigation:** Practical non-causal management audit steps.
4. **Data Quality Audits:** Demonstrate the **Inventory** and **Campaigns** screens where **171 impossible funnel rows** and **648 contradictory stockout records** are isolated from business decisions.
5. **Data Upload & Retrain (POST /analyze):** Open the **Data Upload / Re-analyze** screen. Submit updated tables and watch the backend retrain the Isolation Forest and refresh all catalog rankings with:
   > *"Analysis refreshed. ML risk rankings have been recalculated using the latest dataset."*

---

## 🛡️ Executive Communication & Linguistic Standards

LeakLens strictly adheres to statistical honesty and executive credibility:

| ❌ What We Never Claim | ✅ What LeakLens Uses |
| :--- | :--- |
| *“₹16.22 lakh was definitely lost.”* | **“₹16.22 lakh of transaction value is exposed to cancellations and returns.”** |
| *“These products are definitely unprofitable.”* | **“These products show apparent margin anomalies under the supplied cost data.”** |
| *“The model predicts which products will fail.”* | **“The model identifies products whose combined behaviour is unusually different and prioritizes them for investigation.”** |
| *“760 items failed to be stocked.”* | **“760 telemetry records exhibit flag contradictions (Stockout=1 with positive inventory) requiring verification.”** |
