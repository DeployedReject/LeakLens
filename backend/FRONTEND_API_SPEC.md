# LeakLens frontend API contract

Default local base URL: `http://localhost:8000`

## Core read endpoints

- `GET /health` — service state, training timestamp, dataset fingerprint.
- `GET /overview` — headline business/data-quality KPIs.
- `GET /transactions/summary` — live transaction counts, values and discount-margin bands.
- `GET /products/risk` — manager queue. Defaults to `sort_by=priority`.
- `GET /products/{product_id}` — full product drilldown including ML and priority signals.
- `GET /categories` — category-level failure/margin metrics.
- `GET /quality/campaigns` — live campaign quality summary + invalid rows.
- `GET /quality/inventory` — live inventory quality summary + inconsistent rows.
- `GET /metadata` — model, row counts, dataset hash and score semantics.
- `GET /diagnostics/model` — unsupervised stability diagnostics.
- `GET /validation` — validation warnings/errors for the currently loaded dataset.

## Product semantics

A product now exposes two distinct scores:

- `anomaly_score` / `is_anomaly`: Isolation Forest output. Statistical unusualness only.
- `priority_score` / `priority_level`: decision-support ranking that combines anomaly strength with business impact.

Do not call either score a probability of financial loss.

`risk_score` and `risk_level` remain compatibility aliases for the priority score/level.

## GET /products/risk parameters

- `limit` — 1..250
- `category` — exact category name
- `risk_level` — High, Medium or Low business priority
- `anomaly_only=true` — only Isolation Forest anomalies
- `sort_by=priority|anomaly`

## Upload validation

`POST /validate` accepts the same five multipart CSV fields as `/analyze` and returns blocking `errors` plus non-blocking `warnings`.

## Re-analyze

`POST /analyze` fields:

- `customers`
- `products`
- `transactions`
- `inventory`
- `campaigns`

On success the backend atomically replaces the active analysis. On validation or analysis failure, the previous valid state stays active.
