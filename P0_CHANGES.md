# LeakLens P0 cleanup

Changes made:

1. Replaced runtime backend CSVs with the original supplied Datathon files.
2. Moved the calibrated synthetic generator to `dev_tools/generate_data.py`; it is no longer exposed in the normal upload/demo flow.
3. Removed silent hardcoded KPI/category/campaign/inventory fallbacks from the frontend HTTP client.
4. When FastAPI is offline, the Streamlit app now clearly stops instead of showing apparently live mock values.
5. Added `GET /transactions/summary` so transaction counts, values and discount/margin curves are generated from the current analysis batch.
6. Updated the Transactions page to use only current API data.
7. `POST /analyze` now returns `product_count` explicitly.
8. Unified launcher now polls `/health` instead of sleeping for a fixed 2.5 seconds.

Smoke-tested against the supplied dataset:
- customers: 3,000
- products: 250
- transactions: 18,000
- inventory: 5,000
- campaigns: 1,200
- cancelled + returned exposure: ~₹16.22L
- apparent negative-margin rate: ~37.94%
- invalid campaign rows: 171
- stockout-above-threshold rows: 648
- Isolation Forest anomalies: 25
