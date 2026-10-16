from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


ML_FEATURES = [
    "transaction_count",
    "avg_order_value",
    "avg_discount",
    "cancel_rate",
    "return_rate",
    "failure_rate",
    "negative_margin_rate",
    "avg_margin",
    "avg_stock_on_hand",
    "avg_reorder_threshold",
    "stockout_rate",
    "avg_supplier_delay",
    "stockout_inconsistency_rate",
    "supplier_lead_days",
    "base_margin_pct",
]


@dataclass
class AnalysisResult:
    overview: dict[str, Any]
    product_risk: pd.DataFrame
    categories: pd.DataFrame
    campaign_issues: pd.DataFrame
    inventory_issues: pd.DataFrame
    metadata: dict[str, Any]


def validate_columns(customers, products, transactions, inventory, campaigns):
    required = {
        "customers": {"customer_id", "region", "customer_segment", "signup_date", "preferred_channel"},
        "products": {"product_id", "category", "unit_cost", "list_price", "supplier_lead_days"},
        "transactions": {"transaction_id", "customer_id", "product_id", "timestamp", "quantity", "unit_price", "discount_pct", "status", "channel", "payment_method"},
        "inventory": {"inventory_record_id", "product_id", "date", "stock_on_hand", "reorder_threshold", "stockout_flag", "supplier_delay_days"},
        "campaigns": {"campaign_id", "date", "channel", "category", "spend", "impressions", "clicks", "conversions"},
    }
    frames = {
        "customers": customers,
        "products": products,
        "transactions": transactions,
        "inventory": inventory,
        "campaigns": campaigns,
    }
    errors = []
    for name, cols in required.items():
        missing = sorted(cols - set(frames[name].columns))
        if missing:
            errors.append(f"{name}: missing columns {missing}")
    if errors:
        raise ValueError("; ".join(errors))


def analyze_business_data(customers, products, transactions, inventory, campaigns):
    validate_columns(customers, products, transactions, inventory, campaigns)

    customers = customers.copy()
    products = products.copy()
    transactions = transactions.copy()
    inventory = inventory.copy()
    campaigns = campaigns.copy()

    products["price_below_cost"] = products["list_price"] < products["unit_cost"]

    tx = (
        transactions
        .merge(customers, on="customer_id", how="left", validate="many_to_one")
        .merge(products, on="product_id", how="left", validate="many_to_one")
    )

    if len(tx) != len(transactions):
        raise ValueError("Transaction row count changed after joins.")

    if tx[["region", "customer_segment", "category", "unit_cost"]].isna().any().any():
        raise ValueError("Unmatched customer or product foreign keys detected.")

    tx["revenue"] = tx["quantity"] * tx["unit_price"] * (1 - tx["discount_pct"])
    tx["estimated_cost"] = tx["quantity"] * tx["unit_cost"]
    tx["estimated_margin"] = tx["revenue"] - tx["estimated_cost"]
    tx["negative_margin"] = (tx["estimated_margin"] < 0).astype(int)
    tx["failed_transaction"] = tx["status"].isin(["Cancelled", "Returned"]).astype(int)

    cancelled_value = tx.loc[tx["status"] == "Cancelled", "revenue"].sum()
    returned_value = tx.loc[tx["status"] == "Returned", "revenue"].sum()
    combined_exposure = cancelled_value + returned_value
    non_pending_value = tx.loc[tx["status"] != "Pending", "revenue"].sum()
    exposure_pct = combined_exposure / non_pending_value * 100 if non_pending_value else 0.0

    campaigns["invalid_clicks"] = campaigns["clicks"] > campaigns["impressions"]
    campaigns["invalid_conversions"] = campaigns["conversions"] > campaigns["clicks"]
    campaigns["campaign_invalid"] = campaigns["invalid_clicks"] | campaigns["invalid_conversions"]

    inventory["stockout_above_threshold"] = (
        (inventory["stockout_flag"] == 1)
        & (inventory["stock_on_hand"] > inventory["reorder_threshold"])
    )
    inventory["zero_stock_not_flagged"] = (
        (inventory["stock_on_hand"] == 0)
        & (inventory["stockout_flag"] == 0)
    )

    product_tx = (
        tx.groupby("product_id")
        .agg(
            transaction_count=("transaction_id", "count"),
            avg_order_value=("revenue", "mean"),
            total_transaction_value=("revenue", "sum"),
            avg_discount=("discount_pct", "mean"),
            cancel_rate=("status", lambda x: (x == "Cancelled").mean()),
            return_rate=("status", lambda x: (x == "Returned").mean()),
            failure_rate=("failed_transaction", "mean"),
            negative_margin_rate=("negative_margin", "mean"),
            avg_margin=("estimated_margin", "mean"),
        )
        .reset_index()
    )

    product_inventory = (
        inventory.groupby("product_id")
        .agg(
            avg_stock_on_hand=("stock_on_hand", "mean"),
            avg_reorder_threshold=("reorder_threshold", "mean"),
            stockout_rate=("stockout_flag", "mean"),
            avg_supplier_delay=("supplier_delay_days", "mean"),
            stockout_inconsistency_rate=("stockout_above_threshold", "mean"),
        )
        .reset_index()
    )

    product_risk = (
        products
        .merge(product_tx, on="product_id", how="left", validate="one_to_one")
        .merge(product_inventory, on="product_id", how="left", validate="one_to_one")
    )

    product_risk["base_price_margin"] = product_risk["list_price"] - product_risk["unit_cost"]
    product_risk["base_margin_pct"] = np.where(
        product_risk["unit_cost"] != 0,
        product_risk["base_price_margin"] / product_risk["unit_cost"],
        np.nan,
    )

    X = product_risk[ML_FEATURES].replace([np.inf, -np.inf], np.nan).copy()
    for col in X.columns:
        med = X[col].median()
        X[col] = X[col].fillna(0.0 if pd.isna(med) else med)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = IsolationForest(n_estimators=300, contamination=0.10, random_state=42)
    product_risk["anomaly_label"] = model.fit_predict(X_scaled)
    product_risk["raw_anomaly_score"] = model.decision_function(X_scaled)
    product_risk["anomaly_score"] = -product_risk["raw_anomaly_score"]

    smin = product_risk["anomaly_score"].min()
    smax = product_risk["anomaly_score"].max()
    product_risk["risk_score"] = 0.0 if smax == smin else (
        (product_risk["anomaly_score"] - smin) / (smax - smin) * 100
    )

    product_risk["risk_level"] = pd.cut(
        product_risk["risk_score"],
        bins=[-1, 40, 70, 101],
        labels=["Low", "Medium", "High"],
        include_lowest=True,
    ).astype(str)

    q75_neg = product_risk["negative_margin_rate"].quantile(0.75)
    q75_fail = product_risk["failure_rate"].quantile(0.75)
    q75_disc = product_risk["avg_discount"].quantile(0.75)
    q75_stock = product_risk["stockout_rate"].quantile(0.75)
    q75_delay = product_risk["avg_supplier_delay"].quantile(0.75)
    q25_margin = product_risk["base_margin_pct"].quantile(0.25)

    def explain(row):
        reasons = []
        if row["negative_margin_rate"] > q75_neg:
            reasons.append("high apparent negative-margin rate")
        if row["failure_rate"] > q75_fail:
            reasons.append("high cancelled/returned rate")
        if row["avg_discount"] > q75_disc:
            reasons.append("high average discount")
        if row["stockout_rate"] > q75_stock:
            reasons.append("high stockout flag rate")
        if row["avg_supplier_delay"] > q75_delay:
            reasons.append("high supplier delay")
        if row["base_margin_pct"] < q25_margin:
            reasons.append("weak supplied price-cost margin")
        return "; ".join(reasons) if reasons else "unusual combination of business metrics"

    def action(row):
        actions = []
        if row["negative_margin_rate"] > 0.50:
            actions.append("review pricing and discount rules")
        if row["failure_rate"] > 0.20:
            actions.append("investigate cancellations and returns")
        if row["stockout_rate"] > 0.25:
            actions.append("review inventory policy")
        if row["avg_supplier_delay"] > q75_delay:
            actions.append("review supplier reliability")
        if row["base_margin_pct"] < 0:
            actions.append("verify product cost and list price")
        return "; ".join(actions) if actions else "investigate unusual product behaviour"

    product_risk["why_flagged"] = product_risk.apply(explain, axis=1)
    product_risk["recommended_action"] = product_risk.apply(action, axis=1)
    product_risk = product_risk.sort_values("risk_score", ascending=False).reset_index(drop=True)

    category_summary = (
        tx.groupby("category")
        .agg(
            transaction_count=("transaction_id", "count"),
            failure_rate=("failed_transaction", "mean"),
            negative_margin_rate=("negative_margin", "mean"),
            avg_margin=("estimated_margin", "mean"),
        )
        .reset_index()
    )

    failed_values = (
        tx.loc[tx["failed_transaction"] == 1]
        .groupby("category")["revenue"]
        .sum()
        .rename("failed_transaction_value")
        .reset_index()
    )

    categories = category_summary.merge(failed_values, on="category", how="left")
    categories["failed_transaction_value"] = categories["failed_transaction_value"].fillna(0.0)
    categories["failure_rate"] *= 100
    categories["negative_margin_rate"] *= 100

    campaign_issues = campaigns.loc[campaigns["campaign_invalid"]].copy()
    inventory_issues = inventory.loc[
        inventory["stockout_above_threshold"] | inventory["zero_stock_not_flagged"]
    ].copy()

    overview = {
        "total_transaction_value": float(tx["revenue"].sum()),
        "cancelled_value": float(cancelled_value),
        "returned_value": float(returned_value),
        "combined_exposure": float(combined_exposure),
        "exposure_pct": float(exposure_pct),
        "negative_margin_rate": float(tx["negative_margin"].mean() * 100),
        "cancelled_returned_rate": float(tx["failed_transaction"].mean() * 100),
        "invalid_campaign_rows": int(campaigns["campaign_invalid"].sum()),
        "invalid_click_rows": int(campaigns["invalid_clicks"].sum()),
        "invalid_conversion_rows": int(campaigns["invalid_conversions"].sum()),
        "total_stockout_flags": int(inventory["stockout_flag"].sum()),
        "stockout_above_threshold": int(inventory["stockout_above_threshold"].sum()),
        "zero_stock_not_flagged": int(inventory["zero_stock_not_flagged"].sum()),
        "high_risk_product_count": int((product_risk["risk_level"] == "High").sum()),
        "anomaly_count": int((product_risk["anomaly_label"] == -1).sum()),
    }

    metadata = {
        "model": "IsolationForest",
        "training_mode": "retrain_on_each_analysis",
        "n_estimators": 300,
        "contamination": 0.10,
        "product_count": int(len(product_risk)),
        "ml_feature_count": len(ML_FEATURES),
        "ml_features": ML_FEATURES,
    }

    return AnalysisResult(
        overview=overview,
        product_risk=product_risk,
        categories=categories,
        campaign_issues=campaign_issues,
        inventory_issues=inventory_issues,
        metadata=metadata,
    )
