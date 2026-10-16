# LeakLens hardening and model improvements

## Correctness and provenance
- Runtime uses the supplied competition CSVs, not calibrated/generated substitutes.
- Silent frontend mock fallbacks were removed.
- Stale mock-oriented frontend modules were archived under `dev_tools/legacy_frontend/`.
- Upload failures do not replace the last valid backend analysis state.

## Data validation
`POST /validate` and the analysis pipeline now check:
- required columns and unique primary IDs;
- foreign-key integrity;
- discounts in `[0, 1]`;
- positive quantities and non-negative prices/costs/stock/campaign counts;
- supported transaction statuses.

Logical campaign/inventory contradictions remain non-blocking warnings because surfacing them is part of LeakLens' product value.

## ML semantics
- Isolation Forest uses 14 non-redundant product features.
- `failure_rate` remains visible to managers but is excluded from the model because it is exactly `cancel_rate + return_rate`.
- StandardScaler was removed because Isolation Forest does not require scaling.
- `anomaly_score` and `is_anomaly` are strictly ML outputs.

## Business-priority layer
`priority_score` is separate from the ML anomaly score:
- 30% ML anomaly strength
- 20% transaction value
- 25% apparent negative-margin exposure
- 15% cancelled/returned transaction-value exposure
- 10% operational signal (stockouts, supplier delay, inventory inconsistency)

This answers a different question: *which item should a manager investigate first?*

## Explainability
Each product now returns `top_deviations`: the strongest differences from catalog medians measured in IQR units. These are explicitly described as interpretable context, not causal model-feature attribution.

## Diagnostics
`GET /diagnostics/model` reports:
- number of Isolation Forest anomalies;
- seed-to-seed top-10 overlap;
- anomaly-set Jaccard stability;
- sensitivity to 5%, 10%, and 15% contamination settings.

These are robustness diagnostics, not supervised accuracy metrics.

## Metadata
`GET /metadata` and `/health` expose:
- training timestamp;
- dataset fingerprint/hash;
- row counts;
- features and score semantics.

## Automated tests
Run:

```bash
pip install -r requirements-dev.txt
pytest -q
```
