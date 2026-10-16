from __future__ import annotations

from pathlib import Path
from threading import Lock
from contextlib import asynccontextmanager

import numpy as np
import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from analysis import AnalysisResult, analyze_business_data, validate_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _current
    result = load_local()
    if result is not None:
        with _state_lock:
            _current = result
    yield


app = FastAPI(title="LeakLens API", version="2.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = Path(__file__).resolve().parent / "data"
_state_lock = Lock()
_current: AnalysisResult | None = None


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, np.generic):
        return value.item()
    if pd.isna(value) if not isinstance(value, (str, bytes, list, dict, tuple)) else False:
        return None
    return value


def records(df: pd.DataFrame):
    return [_json_safe(row) for row in df.to_dict(orient="records")]


def read_csv_upload(upload: UploadFile):
    try:
        upload.file.seek(0)
        return pd.read_csv(upload.file)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not read {upload.filename}: {exc}") from exc


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
        "dataset_hash": None if result is None else result.metadata.get("dataset_hash"),
        "trained_at_utc": None if result is None else result.metadata.get("trained_at_utc"),
    }


@app.get("/overview")
def overview():
    return current().overview


@app.get("/transactions/summary")
def transactions_summary():
    return current().transactions_summary


@app.get("/metadata")
def metadata():
    return current().metadata


@app.get("/diagnostics/model")
def model_diagnostics():
    return current().diagnostics


@app.get("/validation")
def validation_report():
    return current().validation


@app.get("/products/risk")
def products_risk(
    limit: int = 250,
    category: str | None = None,
    risk_level: str | None = None,
    anomaly_only: bool = False,
    sort_by: str = "priority",
):
    df = current().product_risk.copy()
    if category:
        df = df[df["category"].str.lower() == category.lower()]
    if risk_level:
        df = df[df["priority_level"].str.lower() == risk_level.lower()]
    if anomaly_only:
        df = df[df["is_anomaly"]]

    if sort_by == "anomaly":
        df = df.sort_values("anomaly_score", ascending=False)
    elif sort_by == "priority":
        df = df.sort_values("priority_score", ascending=False)
    else:
        raise HTTPException(status_code=400, detail="sort_by must be 'priority' or 'anomaly'")

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
    summary = dict(result.campaign_summary)
    summary["warnings"] = [w for w in result.validation["warnings"] if "campaign" in w.lower()]
    return {
        "summary": summary,
        "rows": records(result.campaign_issues.head(max(1, min(limit, 2000)))),
    }


@app.get("/quality/inventory")
def inventory_quality(limit: int = 500):
    result = current()
    summary = dict(result.inventory_summary)
    summary["issue_rows"] = len(result.inventory_issues)
    summary["warnings"] = [w for w in result.validation["warnings"] if "inventory" in w.lower()]
    return {
        "summary": summary,
        "rows": records(result.inventory_issues.head(max(1, min(limit, 5000)))),
    }


@app.post("/validate")
def validate_uploads(
    customers: UploadFile = File(...),
    products: UploadFile = File(...),
    transactions: UploadFile = File(...),
    inventory: UploadFile = File(...),
    campaigns: UploadFile = File(...),
):
    frames = [
        read_csv_upload(customers),
        read_csv_upload(products),
        read_csv_upload(transactions),
        read_csv_upload(inventory),
        read_csv_upload(campaigns),
    ]
    return validate_data(*frames)


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
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc

    # Atomic state replacement: failed uploads never corrupt the current good analysis.
    with _state_lock:
        _current = result

    return {
        "status": "success",
        "message": "Analysis refreshed; Isolation Forest retrained and business priority scores recalculated.",
        "overview": result.overview,
        "metadata": result.metadata,
        "validation": result.validation,
        "diagnostics": result.diagnostics,
        "product_count": int(len(result.product_risk)),
        "top_priority_products": records(
            result.product_risk[
                [
                    "product_id", "category", "priority_score", "priority_level",
                    "anomaly_score", "is_anomaly", "why_flagged", "recommended_action",
                ]
            ].head(10)
        ),
    }
