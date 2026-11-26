# Backend API — first vertical slice

Base URL: `http://localhost:8000`

## GET /health
Returns service health and version.

## POST /v1/metrics/aggregate
Accepts JSON with one or more rows. Every row must include:
`data_mode, impressions, clicks, landing_page_views, add_to_cart, purchases, refunded_orders, spend_usd, attributed_revenue_usd`.

All rows must use the same mode: SIMULATED or REAL. Mixed modes return HTTP 422. Negative counts or costs are rejected. Zero denominators return JSON null.

Example:
```json
{
  "rows": [{
    "data_mode": "SIMULATED",
    "impressions": 1000,
    "clicks": 20,
    "landing_page_views": 18,
    "add_to_cart": 5,
    "purchases": 2,
    "refunded_orders": 0,
    "spend_usd": 20,
    "attributed_revenue_usd": 60
  }]
}
```

## POST /v1/import/csv/validate?data_mode=SIMULATED
Multipart form upload with field name `file`. Requires a CSV with the metric fields plus a `data_mode` column. Every row must match the requested mode. This endpoint validates and aggregates; it does not persist data yet.

## Metric semantics
- CTR = clicks / impressions
- CPC = spend / clicks
- LPV rate = landing page views / clicks
- ATC rate = add to cart / landing page views
- CVR = purchases / clicks (click-to-purchase)
- CPA = spend / purchases
- AOV = attributed revenue / purchases
- ROAS = attributed revenue / spend

ROAS is not ROI. This API does not calculate ROI because incremental profit and full investment costs are not yet modeled.
