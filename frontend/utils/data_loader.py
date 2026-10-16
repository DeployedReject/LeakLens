"""
Data Loader module for LeakLens.
Centralizes data access and ensures seamless fallback to calibrated mock data
matching Datathon 2026 ground truth numbers if CSVs are missing.
"""

from pathlib import Path
import json
import pandas as pd
import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"

# Status registry for UI badges (indicates whether real CSV or fallback is in use)
DATA_SOURCE_STATUS = {
    "transactions": False,
    "products": False,
    "inventory": False,
    "campaigns": False,
    "overview": False,
}

# ==========================================
# 1. EXECUTIVE OVERVIEW METRICS
# ==========================================
def load_overview_metrics():
    """
    Load high-level KPI metrics.
    Uses overview_metrics.json if present, else calibrated datathon baseline.
    """
    json_path = DATA_DIR / "overview_metrics.json"
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                DATA_SOURCE_STATUS["overview"] = True
                return json.load(f)
        except Exception:
            pass

    DATA_SOURCE_STATUS["overview"] = False
    # Calibrated datathon metrics from problem statement
    return {
        "completed_count": 13962,
        "completed_pct": 77.57,
        "cancelled_count": 1689,
        "cancelled_pct": 9.38,
        "returned_count": 1431,
        "returned_pct": 7.95,
        "pending_count": 918,
        "pending_pct": 5.10,
        "total_transactions": 18000,
        "cancelled_value": 862000,       # ~₹8.62 lakh
        "returned_value": 760000,        # ~₹7.60 lakh
        "total_exposure_value": 1622000, # ~₹16.22 lakh
        "negative_margin_overall_rate": 37.9,
        "beauty_negative_margin_rate": 55.2,
        "campaign_invalid_rows": 172,
        "inventory_flag_inconsistencies": 760
    }

def load_top_issues():
    """
    Ranked issues to investigate with evidence, actions, confidence caveats,
    and target page routes for immediate investigation.
    """
    return [
        {
            "id": "pricing_margin",
            "rank": 1,
            "title": "Pricing & Margin Anomalies",
            "severity": "High",
            "target_page": "Product Risk",
            "category_focus": "All Categories",
            "evidence": "37.9% of transactions show an apparent negative estimated margin under the supplied cost fields.",
            "metrics": {"Metric": "Negative Margin Rate", "Value": "37.9%", "Benchmark": "< 8.0%"},
            "action": "Review price/cost assumptions, minimum price floors, and promo stacking rules across top volume SKUs.",
            "confidence_warning": "Supplied dataset documentation states costs and prices were independently generated. Treat as an anomaly requiring verification before altering live contracts.",
            "exposure_text": "High operational leakage risk across catalog"
        },
        {
            "id": "beauty_margin",
            "rank": 2,
            "title": "Beauty Category Margin Risk",
            "severity": "High",
            "target_page": "Transactions",
            "category_focus": "Beauty",
            "evidence": "Approximately 55.2% apparent negative-margin transaction rate in the Beauty category, far exceeding all other departments.",
            "metrics": {"Metric": "Beauty Negative Margin Rate", "Value": "55.2%", "Benchmark": "37.9% avg"},
            "action": "Conduct immediate SKU-level audit of Beauty product pricing formulas and check high-discount (>30%) transactions.",
            "confidence_warning": "Check for synthetic cost noise in beauty supplier entries prior to operational supplier renegotiations.",
            "exposure_text": "Disproportionate drag on overall catalog profitability"
        },
        {
            "id": "campaign_integrity",
            "rank": 3,
            "title": "Campaign Funnel Data Integrity",
            "severity": "Medium/High",
            "target_page": "Campaigns",
            "category_focus": "Marketing",
            "evidence": "84 campaign rows show clicks > impressions, and 88 campaign rows show conversions > clicks.",
            "metrics": {"Metric": "Impossible Funnel Records", "Value": "172 Rows", "Benchmark": "0 Rows"},
            "action": "Validate marketing-source ETL pipeline and telemetry trackers before trusting ROAS/CPA allocation algorithms.",
            "confidence_warning": "Attribution metrics in affected rows are fundamentally untrusted; exclude these rows from budget decisions.",
            "exposure_text": "Risk of misallocating ad spend on corrupted attribution signals"
        },
        {
            "id": "inventory_inconsistency",
            "rank": 4,
            "title": "Inventory Stockout Flag Inconsistency",
            "severity": "Medium/High",
            "target_page": "Inventory",
            "category_focus": "Supply Chain",
            "evidence": "648 stockout records occur despite stock_on_hand sitting above the reorder threshold. 10 records show zero stock without a stockout flag.",
            "metrics": {"Metric": "Inconsistent Stockout Records", "Value": "760 Records", "Benchmark": "0 Records"},
            "action": "Verify the true semantic meaning and trigger source of stockout_flag before automating supplier reorders.",
            "confidence_warning": "These reflect database logging contradictions rather than confirmed operational stockouts.",
            "exposure_text": "Premature reorder triggers could lead to capital lockup"
        }
    ]

# ==========================================
# 2. TRANSACTIONS DATA
# ==========================================
def load_transactions_data():
    """
    Load transaction level dataset or synthesize calibrated mock data.
    """
    csv_path = DATA_DIR / "processed_transactions.csv"
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            DATA_SOURCE_STATUS["transactions"] = True
            return df
        except Exception:
            pass

    DATA_SOURCE_STATUS["transactions"] = False
    
    # Synthesize realistic sample of 1,200 representative records matching the 18,000 exact proportions
    np.random.seed(42)
    n_samples = 1200
    
    # Target proportions: Completed ~77.57%, Cancelled ~9.38%, Returned ~7.95%, Pending ~5.10%
    statuses = np.random.choice(
        ["Completed", "Cancelled", "Returned", "Pending"],
        size=n_samples,
        p=[0.7757, 0.0938, 0.0795, 0.0510]
    )
    
    categories = np.random.choice(
        ["Beauty", "Electronics", "Apparel", "Home & Kitchen", "Grocery"],
        size=n_samples,
        p=[0.28, 0.24, 0.22, 0.16, 0.10]
    )
    
    channels = np.random.choice(
        ["Mobile App", "Website", "Social Store", "Partner API"],
        size=n_samples,
        p=[0.48, 0.32, 0.14, 0.06]
    )
    
    regions = np.random.choice(
        ["North", "South", "West", "East", "Central"],
        size=n_samples,
        p=[0.30, 0.25, 0.22, 0.13, 0.10]
    )

    base_prices = {
        "Beauty": (300, 1500),
        "Electronics": (800, 4500),
        "Apparel": (400, 2500),
        "Home & Kitchen": (500, 3000),
        "Grocery": (150, 900)
    }

    order_values = []
    cost_prices = []
    discounts = []

    for cat in categories:
        low, high = base_prices[cat]
        price = np.random.uniform(low, high)
        disc = np.random.choice([0, 5, 10, 15, 20, 30, 45, 60], p=[0.20, 0.15, 0.20, 0.15, 0.12, 0.10, 0.05, 0.03])
        net_price = price * (1 - disc / 100.0)
        
        # Beauty has 55.2% negative margin rate; others average ~31% to produce 37.9% overall
        if cat == "Beauty":
            neg_margin = np.random.rand() < 0.552
        else:
            neg_margin = np.random.rand() < 0.312
            
        if neg_margin:
            cost = net_price * np.random.uniform(1.05, 1.45)
        else:
            cost = net_price * np.random.uniform(0.55, 0.92)
            
        order_values.append(round(net_price, 2))
        cost_prices.append(round(cost, 2))
        discounts.append(disc)

    dates = pd.date_range(start="2026-01-01", periods=n_samples, freq="15min")
    
    df = pd.DataFrame({
        "transaction_id": [f"TXN-{100000 + i}" for i in range(n_samples)],
        "timestamp": dates,
        "category": categories,
        "status": statuses,
        "order_value": order_values,
        "cost_price": cost_prices,
        "discount_pct": discounts,
        "channel": channels,
        "region": regions
    })
    
    df["estimated_margin"] = df["order_value"] - df["cost_price"]
    df["margin_pct"] = (df["estimated_margin"] / df["order_value"]) * 100
    df["is_negative_margin"] = df["estimated_margin"] < 0
    return df

# ==========================================
# 3. PRODUCT RISK DATA
# ==========================================
def load_product_risk_data():
    """
    Load product-level risk table or synthesize realistic catalog data.
    """
    csv_path = DATA_DIR / "product_risk.csv"
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            DATA_SOURCE_STATUS["products"] = True
            return df
        except Exception:
            pass

    DATA_SOURCE_STATUS["products"] = False
    
    # 35 curated SKUs with realistic anomaly drivers
    products = [
        # High Risk Products (Beauty and Electronics with acute leaks)
        {"id": "PRD-B101", "name": "Velvet Matte Luxe Lipstick 12hr", "cat": "Beauty", "risk": "High", "anom": 0.94, "fail": 24.2, "ret": 14.8, "canc": 9.4, "disc": 42.0, "neg_marg": 68.5, "stockout": 22.0, "delay": 5.4, "impact": 184500, "flag": "Apparent negative margins (68.5%) & high promo discounting", "action": "Audit supplier procurement unit cost vs promotion discount threshold."},
        {"id": "PRD-B108", "name": "Bio-Retinol Night Repair Serum 50ml", "cat": "Beauty", "risk": "High", "anom": 0.91, "fail": 28.5, "ret": 18.2, "canc": 10.3, "disc": 35.0, "neg_marg": 62.0, "stockout": 19.5, "delay": 4.8, "impact": 152000, "flag": "High return rate (18.2%) and negative margin clustering", "action": "Investigate return reason codes (packaging/breakage vs allergic reaction)."},
        {"id": "PRD-E204", "name": "TrueWireless ANC Earbuds Pro X", "cat": "Electronics", "risk": "High", "anom": 0.89, "fail": 21.0, "ret": 15.6, "canc": 5.4, "disc": 28.0, "neg_marg": 48.0, "stockout": 31.0, "delay": 7.2, "impact": 168000, "flag": "Supplier delay (7.2d above peer avg) & elevated return rate", "action": "Review OEM defect batches and evaluate warranty turnaround SLAs."},
        {"id": "PRD-B114", "name": "Hydra-Glow Vitamin C Gel Crème", "cat": "Beauty", "risk": "High", "anom": 0.87, "fail": 22.4, "ret": 12.1, "canc": 10.3, "disc": 38.5, "neg_marg": 59.4, "stockout": 14.0, "delay": 3.1, "impact": 139000, "flag": "Persistent negative margin rate (59.4%) with high cancellation", "action": "Evaluate fulfillment speed and cross-check bundled promo pricing."},
        {"id": "PRD-A309", "name": "Seamless Thermal Athleisure Set", "cat": "Apparel", "risk": "High", "anom": 0.85, "fail": 26.8, "ret": 19.4, "canc": 7.4, "disc": 30.0, "neg_marg": 41.2, "stockout": 12.0, "delay": 4.0, "impact": 115000, "flag": "Sizing mismatch suspected: return rate 19.4% vs apparel avg 8%", "action": "Inspect size chart fit feedback and vendor batch tolerances."},
        {"id": "PRD-H402", "name": "Rapid Induction Cooktop 2100W", "cat": "Home & Kitchen", "risk": "High", "anom": 0.83, "fail": 19.5, "ret": 13.0, "canc": 6.5, "disc": 25.0, "neg_marg": 39.0, "stockout": 26.0, "delay": 6.8, "impact": 128000, "flag": "Frequent stockout logging with extended supplier replenishment lag", "action": "Verify safety stock buffer calculations and supplier lead time agreements."},
        {"id": "PRD-E219", "name": "UltraSlim Power Bank 20000mAh", "cat": "Electronics", "risk": "High", "anom": 0.82, "fail": 18.2, "ret": 11.0, "canc": 7.2, "disc": 32.0, "neg_marg": 44.5, "stockout": 18.0, "delay": 5.9, "impact": 98000, "flag": "High promo elasticity driving apparent negative unit contribution", "action": "Cap platform discount coupons to prevent negative net contribution."},
        
        # Medium Risk Products
        {"id": "PRD-B122", "name": "Organic Rosewater Facial Toner", "cat": "Beauty", "risk": "Medium", "anom": 0.69, "fail": 14.5, "ret": 7.5, "canc": 7.0, "disc": 22.0, "neg_marg": 46.0, "stockout": 8.0, "delay": 2.1, "impact": 74000, "flag": "Moderate negative margin clustering under current cost table", "action": "Verify baseline supplier wholesale cost list updates."},
        {"id": "PRD-A315", "name": "Classic Oxford Cotton Shirt", "cat": "Apparel", "risk": "Medium", "anom": 0.67, "fail": 16.0, "ret": 11.2, "canc": 4.8, "disc": 18.0, "neg_marg": 32.0, "stockout": 9.5, "delay": 3.0, "impact": 68000, "flag": "Returns elevated slightly above apparel benchmark", "action": "Review customer reviews for fit and collar fabric consistency."},
        {"id": "PRD-H411", "name": "Stainless Steel Multipurpose Knife Set", "cat": "Home & Kitchen", "risk": "Medium", "anom": 0.65, "fail": 13.2, "ret": 7.0, "canc": 6.2, "disc": 20.0, "neg_marg": 35.0, "stockout": 15.0, "delay": 4.5, "impact": 61000, "flag": "Stockout logging spikes during weekend promotion periods", "action": "Adjust weekend replenishment forecasts."},
        {"id": "PRD-G501", "name": "Cold-Pressed Virgin Coconut Oil 1L", "cat": "Grocery", "risk": "Medium", "anom": 0.63, "fail": 11.5, "ret": 5.2, "canc": 6.3, "disc": 12.0, "neg_marg": 31.0, "stockout": 14.0, "delay": 4.2, "impact": 52000, "flag": "Shipping leakage reports and container seal checks needed", "action": "Check transit packaging specifications to reduce courier cancellations."},
        {"id": "PRD-E230", "name": "Braided Fast Charge USB-C Cable 2m", "cat": "Electronics", "risk": "Medium", "anom": 0.61, "fail": 12.8, "ret": 8.0, "canc": 4.8, "disc": 15.0, "neg_marg": 28.0, "stockout": 11.0, "delay": 2.5, "impact": 49000, "flag": "Low value SKU with disproportionate cancellation rate", "action": "Assess minimum order quantity threshold for free logistics."},
        {"id": "PRD-A320", "name": "Denim Relaxed Fit Chore Jacket", "cat": "Apparel", "risk": "Medium", "anom": 0.58, "fail": 14.0, "ret": 9.8, "canc": 4.2, "disc": 25.0, "neg_marg": 29.5, "stockout": 7.0, "delay": 3.4, "impact": 58000, "flag": "Moderate returns with periodic holiday discount stacking", "action": "Ensure seasonal discount caps are enforced."},

        # Low Risk / Baseline Stable Products
        {"id": "PRD-G505", "name": "Roasted Almonds Himalayan Salt 250g", "cat": "Grocery", "risk": "Low", "anom": 0.28, "fail": 4.5, "ret": 1.2, "canc": 3.3, "disc": 8.0, "neg_marg": 8.5, "stockout": 4.0, "delay": 1.2, "impact": 14000, "flag": "Consistent performance, healthy fulfillment and margin", "action": "Maintain current operational inventory cadence."},
        {"id": "PRD-H420", "name": "Borosilicate Glass Water Bottle 1L", "cat": "Home & Kitchen", "risk": "Low", "anom": 0.25, "fail": 5.0, "ret": 2.1, "canc": 2.9, "disc": 10.0, "neg_marg": 12.0, "stockout": 3.5, "delay": 1.5, "impact": 18000, "flag": "Strong consumer satisfaction and stable vendor lead times", "action": "No immediate intervention required."},
        {"id": "PRD-E250", "name": "Ergonomic Optical Wireless Mouse", "cat": "Electronics", "risk": "Low", "anom": 0.22, "fail": 4.8, "ret": 2.4, "canc": 2.4, "disc": 12.0, "neg_marg": 9.2, "stockout": 5.0, "delay": 1.8, "impact": 22000, "flag": "Low anomaly metric profile across operational dimensions", "action": "Benchmark as healthy control for category peers."},
        {"id": "PRD-B140", "name": "Nourishing Shea Butter Lip Balm", "cat": "Beauty", "risk": "Low", "anom": 0.21, "fail": 3.9, "ret": 1.0, "canc": 2.9, "disc": 5.0, "neg_marg": 14.0, "stockout": 2.5, "delay": 1.0, "impact": 9500, "flag": "Healthy beauty SKU defying broad category margin anomalies", "action": "Examine pricing structure as model for struggling Beauty SKUs."},
        {"id": "PRD-A335", "name": "Bamboo Fiber Crew Socks (Pack of 3)", "cat": "Apparel", "risk": "Low", "anom": 0.18, "fail": 3.2, "ret": 0.8, "canc": 2.4, "disc": 8.0, "neg_marg": 7.0, "stockout": 2.0, "delay": 1.1, "impact": 8200, "flag": "Minimal operational friction and reliable customer retention", "action": "Consider scaling inventory levels safely."}
    ]

    df = pd.DataFrame(products)
    df.columns = [
        "product_id", "product_name", "category", "risk_score",
        "anomaly_score", "failure_rate", "return_rate", "cancel_rate",
        "avg_discount", "negative_margin_rate", "stockout_rate",
        "supplier_delay", "estimated_impact", "why_flagged", "recommended_action"
    ]
    return df

# ==========================================
# 4. INVENTORY DATA
# ==========================================
def load_inventory_data():
    """
    Load inventory summary data or synthesize dataset adhering to specific
    data quality findings (760 stockout=1 with stock>0, 648 > threshold, 10 stock=0 with stockout=0).
    """
    csv_path = DATA_DIR / "inventory_summary.csv"
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            DATA_SOURCE_STATUS["inventory"] = True
            return df
        except Exception:
            pass

    DATA_SOURCE_STATUS["inventory"] = False
    
    np.random.seed(101)
    n_records = 2500
    
    # Generate distribution where exactly 760 records have stockout_flag = 1
    # but stock_on_hand > 0, and 648 of them have stock_on_hand > reorder_threshold
    categories = np.random.choice(["Beauty", "Electronics", "Apparel", "Home & Kitchen", "Grocery"], size=n_records)
    reorder_thresholds = np.random.randint(15, 60, size=n_records)
    
    stock_on_hand = np.zeros(n_records, dtype=int)
    stockout_flags = np.zeros(n_records, dtype=int)
    supplier_delays = np.random.exponential(scale=2.5, size=n_records).round(1)
    lead_times = np.random.randint(2, 18, size=n_records) + supplier_delays.astype(int)

    # 1. First 760 rows: Stockout flag = 1, but stock > 0
    # 648 of these have stock > reorder_threshold
    for i in range(760):
        stockout_flags[i] = 1
        thresh = reorder_thresholds[i]
        if i < 648:
            stock_on_hand[i] = thresh + np.random.randint(5, 75)
        else:
            stock_on_hand[i] = np.random.randint(1, thresh)

    # 2. Next 10 rows: stock_on_hand = 0, but stockout_flag = 0 (inconsistency)
    for i in range(760, 770):
        stockout_flags[i] = 0
        stock_on_hand[i] = 0

    # 3. Remaining rows: standard regular operations
    for i in range(770, n_records):
        thresh = reorder_thresholds[i]
        if np.random.rand() < 0.15:
            # Normal stockout situation
            stockout_flags[i] = 1
            stock_on_hand[i] = 0
        else:
            stockout_flags[i] = 0
            stock_on_hand[i] = np.random.randint(thresh, thresh + 120)

    df = pd.DataFrame({
        "sku_id": [f"SKU-{1000 + i}" for i in range(n_records)],
        "category": categories,
        "stock_on_hand": stock_on_hand,
        "reorder_threshold": reorder_thresholds,
        "stockout_flag": stockout_flags,
        "supplier_delay_days": supplier_delays,
        "lead_time_days": lead_times
    })

    # Add diagnostic classification column
    conditions = [
        (df["stockout_flag"] == 1) & (df["stock_on_hand"] > df["reorder_threshold"]),
        (df["stockout_flag"] == 1) & (df["stock_on_hand"] > 0) & (df["stock_on_hand"] <= df["reorder_threshold"]),
        (df["stockout_flag"] == 0) & (df["stock_on_hand"] == 0),
        (df["stockout_flag"] == 1) & (df["stock_on_hand"] == 0),
        (df["stockout_flag"] == 0) & (df["stock_on_hand"] > 0)
    ]
    choices = [
        "Anomaly: Stockout=1 but Stock > Threshold",
        "Anomaly: Stockout=1 with Buffer Remaining",
        "Anomaly: Zero Stock but Stockout=0",
        "Valid Stockout (Zero Stock)",
        "Normal Stock Operating"
    ]
    df["inventory_quality_status"] = np.select(conditions, choices, default="Normal")
    return df

# ==========================================
# 5. CAMPAIGNS DATA
# ==========================================
def load_campaigns_data():
    """
    Load marketing campaign summary data.
    Accurately embeds known datathon quality issues:
    - 84 campaigns have clicks > impressions
    - 88 campaigns have conversions > clicks
    """
    csv_path = DATA_DIR / "campaign_summary.csv"
    if csv_path.exists():
        try:
            df = pd.read_csv(csv_path)
            DATA_SOURCE_STATUS["campaigns"] = True
            return df
        except Exception:
            pass

    DATA_SOURCE_STATUS["campaigns"] = False
    
    np.random.seed(303)
    n_campaigns = 500
    channels = np.random.choice(["Google Ads", "Meta Ads", "Influencer Promo", "Email Retargeting", "Affiliate"], size=n_campaigns)
    spend = np.random.uniform(5000, 95000, size=n_campaigns).round(2)
    impressions = np.random.randint(15000, 250000, size=n_campaigns)
    clicks = np.zeros(n_campaigns, dtype=int)
    conversions = np.zeros(n_campaigns, dtype=int)
    funnel_quality = ["Valid"] * n_campaigns

    # Set up normal realistic baseline: CTR ~ 1.5% - 4.5%, CVR ~ 2% - 8%
    for i in range(n_campaigns):
        clicks[i] = int(impressions[i] * np.random.uniform(0.015, 0.045))
        conversions[i] = max(1, int(clicks[i] * np.random.uniform(0.02, 0.08)))

    # Inject exact 84 rows with clicks > impressions
    for i in range(84):
        clicks[i] = impressions[i] + np.random.randint(150, 4200)
        funnel_quality[i] = "Invalid: Clicks > Impressions"

    # Inject exact 88 rows with conversions > clicks (distinct campaigns from index 84 to 171)
    for i in range(84, 84 + 88):
        conversions[i] = clicks[i] + np.random.randint(25, 650)
        funnel_quality[i] = "Invalid: Conversions > Clicks"

    df = pd.DataFrame({
        "campaign_id": [f"CMP-{2000 + i}" for i in range(n_campaigns)],
        "campaign_name": [f"Promo Campaign {i+1} ({channels[i]})" for i in range(n_campaigns)],
        "channel": channels,
        "spend": spend,
        "impressions": impressions,
        "clicks": clicks,
        "conversions": conversions,
        "funnel_quality": funnel_quality
    })

    # Compute raw metrics
    df["raw_ctr"] = (df["clicks"] / df["impressions"]) * 100
    df["raw_cvr"] = (df["conversions"] / df["clicks"]) * 100
    df["cpa"] = df["spend"] / df["conversions"].replace(0, 1)
    df["is_funnel_invalid"] = df["funnel_quality"] != "Valid"
    return df
