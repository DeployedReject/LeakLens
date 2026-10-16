from pathlib import Path
import sys

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from analysis import analyze_business_data, validate_data


def load_frames():
    d = BACKEND / "data"
    return (
        pd.read_csv(d / "customers.csv"),
        pd.read_csv(d / "products.csv"),
        pd.read_csv(d / "transactions.csv"),
        pd.read_csv(d / "inventory.csv"),
        pd.read_csv(d / "campaigns.csv"),
    )


def test_real_dataset_analysis_shape_and_semantics():
    result = analyze_business_data(*load_frames())
    assert len(result.product_risk) == 250
    assert result.overview["anomaly_count"] == 25
    assert result.product_risk["anomaly_score"].between(0, 100).all()
    assert result.product_risk["priority_score"].between(0, 100).all()
    assert "failure_rate" not in result.metadata["ml_features"]
    assert result.metadata["ml_feature_count"] == 14
    assert result.validation["valid"] is True
    assert result.metadata["dataset_hash"]


def test_invalid_discount_is_rejected():
    c, p, t, i, m = load_frames()
    t.loc[0, "discount_pct"] = 1.5
    report = validate_data(c, p, t, i, m)
    assert report["valid"] is False
    assert any("discount_pct" in e for e in report["errors"])
    with pytest.raises(ValueError):
        analyze_business_data(c, p, t, i, m)


def test_missing_required_column_is_rejected():
    c, p, t, i, m = load_frames()
    t = t.drop(columns=["status"])
    report = validate_data(c, p, t, i, m)
    assert report["valid"] is False
    assert any("missing columns" in e for e in report["errors"])


def test_quality_warnings_are_non_blocking():
    result = analyze_business_data(*load_frames())
    assert result.validation["valid"] is True
    assert result.validation["warnings"]
    assert result.overview["invalid_campaign_rows"] == 171
    assert result.overview["stockout_above_threshold"] == 648


def test_top_deviation_payload_exists():
    result = analyze_business_data(*load_frames())
    payload = result.product_risk.iloc[0]["top_deviations"]
    assert isinstance(payload, list)
    assert 1 <= len(payload) <= 5
    assert {"feature", "label", "value", "catalog_median", "direction", "iqr_deviation"}.issubset(payload[0])
