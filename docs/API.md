# API Reference — AI Ads Growth Lab

Base URL: `http://localhost:8000`

## Health and demo
- `GET /health` — service health.
- `GET /v1/demo/overview` — bundled synthetic experiment aggregated by date, creative, and funnel stage. Includes seeded demo workspace/product IDs.

## Persistent workspace APIs

The current local runtime uses SQLite for persistence. The PostgreSQL schema is a deployment/migration target and is not yet wired into the application.

- `POST /v1/workspaces` / `GET /v1/workspaces`
- `POST /v1/products` / `GET /v1/workspaces/{workspace_id}/products`
- `POST /v1/claims` / `GET /v1/products/{product_id}/claims`
- `POST /v1/creatives` / `GET /v1/workspaces/{workspace_id}/creatives`
- `POST /v1/assets/versions` / `GET /v1/creatives/{creative_id}/assets`
- `POST /v1/assets/versions/{asset_version_id}/review` / `GET /v1/assets/versions/{asset_version_id}/reviews`
- `POST /v1/experiments` / `GET /v1/workspaces/{workspace_id}/experiments`
- `POST /v1/experiments/{experiment_id}/variants` / `GET /v1/experiments/{experiment_id}/variants`
- `GET /v1/workspaces/{workspace_id}/audit`

### Guardrails
- A VERIFIED claim requires at least one evidence reference.
- Experiment `data_mode` must match its workspace.
- Creative and product must belong to the same workspace.
- Experiment variants can only reference creatives from the same workspace.
- Every create operation writes an audit record.
- Asset versions increment per creative and are not overwritten.
- New asset versions always start as PENDING; a separate review endpoint records reviewer, decision, reason and findings.

## Metrics
- `POST /v1/metrics/aggregate` — deterministic metric aggregation.
- `POST /v1/import/csv/validate?data_mode=SIMULATED` — validate and aggregate uploaded CSV.

Metric semantics:
- CTR = clicks / impressions
- CPC = spend / clicks
- LPV rate = landing page views / clicks
- ATC rate = add to cart / landing page views
- CVR = purchases / clicks (click-to-purchase)
- CPA = spend / purchases
- AOV = attributed revenue / purchases
- ROAS = attributed revenue / spend

Zero denominator returns null. ROAS is not ROI.
