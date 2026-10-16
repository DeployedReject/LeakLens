from __future__ import annotations

from pathlib import Path
from threading import Lock

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from analysis import AnalysisResult, analyze_business_data


app = FastAPI(title="LeakLens API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path("data")
_state_lock = Lock()
_current: AnalysisResult | None = None


def records(df: pd.DataFrame):
    return df.where(pd.notnull(df), None).to_dict(orient="records")


def read_csv_upload(upload: UploadFile):
    try:
        upload.file.seek(0)
        return pd.read_csv(upload.file)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read {upload.filename}: {exc}")


def load_local():
    files = {
        "customers": DATA_DIR / "customers.csv",
        "products": DATA_DIR / "products.csv",
        "transactions": DATA_DIR / "transactions.csv",
        "inventory": DATA_DIR / "inventory.csv",
        "campaigns": DATA_DIR / "campaigns.csv",
    }
    if not all(p.exists() for p in files.values()):
        return None
    return analyze_business_data(
        pd.read_csv(files["customers"]),
        pd.read_csv(files["products"]),
        pd.read_csv(files["transactions"]),
        pd.read_csv(files["inventory"]),
        pd.read_csv(files["campaigns"]),
    )


@app.on_event("startup")
def startup():
    global _current
    result = load_local()
    if result is not None:
        with _state_lock:
            _current = result


def current():
    with _state_lock:
        result = _current
    if result is None:
        raise HTTPException(status_code=503, detail="No analysis loaded. Upload the five CSVs to POST /analyze.")
    return result


@app.get("/health")
def health():
    with _state_lock:
        result = _current
    return {
        "status": "ok",
        "analysis_loaded": result is not None,
        "model": "IsolationForest",
        "training_mode": "retrain_on_each_analysis",
        "product_count": 0 if result is None else len(result.product_risk),
    }


@app.get("/overview")
def overview():
    return current().overview


@app.get("/metadata")
def metadata():
    return current().metadata


@app.get("/products/risk")
def products_risk(limit: int = 250, category: str | None = None, risk_level: str | None = None):
    df = current().product_risk.copy()
    if category:
        df = df[df["category"].str.lower() == category.lower()]
    if risk_level:
        df = df[df["risk_level"].str.lower() == risk_level.lower()]
    return records(df.head(max(1, min(limit, 250))))


@app.get("/products/{product_id}")
def product_detail(product_id: str):
    df = current().product_risk
    rows = df[df["product_id"] == product_id]
    if rows.empty:
        raise HTTPException(status_code=404, detail="Product not found")
    return records(rows)[0]


@app.get("/categories")
def categories():
    return records(current().categories.sort_values("negative_margin_rate", ascending=False))


@app.get("/quality/campaigns")
def campaign_quality(limit: int = 500):
    result = current()
    return {
        "summary": {"invalid_rows": len(result.campaign_issues)},
        "rows": records(result.campaign_issues.head(limit)),
    }


@app.get("/quality/inventory")
def inventory_quality(limit: int = 500):
    result = current()
    return {
        "summary": {"issue_rows": len(result.inventory_issues)},
        "rows": records(result.inventory_issues.head(limit)),
    }


@app.post("/analyze")
def analyze(
    customers: UploadFile = File(...),
    products: UploadFile = File(...),
    transactions: UploadFile = File(...),
    inventory: UploadFile = File(...),
    campaigns: UploadFile = File(...),
):
    global _current
    try:
        result = analyze_business_data(
            read_csv_upload(customers),
            read_csv_upload(products),
            read_csv_upload(transactions),
            read_csv_upload(inventory),
            read_csv_upload(campaigns),
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}")

    with _state_lock:
        _current = result

    return {
        "status": "success",
        "message": "Analysis refreshed; Isolation Forest retrained on latest data.",
        "overview": result.overview,
        "metadata": result.metadata,
        "top_risky_products": records(
            result.product_risk[
                ["product_id", "category", "risk_score", "risk_level", "why_flagged", "recommended_action"]
            ].head(10)
        ),
    }
