# API Reference — AI Ads Growth Lab

Base URL: `http://localhost:8000`

## Health and demo
- `GET /health` — service health.
- `GET /v1/demo/overview` — bundled synthetic experiment aggregated by date, creative, and funnel stage. Includes seeded demo workspace/product IDs.\n- `GET /v1/demo/experiment/compare?control_family=C-A&treatment_family=C-B&metric=CTR&mde_absolute=0.005` — synthetic creative-family comparison with two-proportion z-test, Wilson intervals, sample sufficiency and approximate sample planning.\n- `GET /v1/demo/data-quality` — row-grain, missing-field, numeric, data-mode and funnel-monotonicity audit for the bundled dataset.

## Persistent workspace APIs

The current local runtime uses SQLite for persistence. The PostgreSQL schema is a deployment/migration target and is not yet wired into the application.

- `POST /v1/workspaces` / `GET /v1/workspaces`
- `POST /v1/products` / `GET /v1/workspaces/{workspace_id}/products`
- `POST /v1/claims` / `GET /v1/products/{product_id}/claims`
- `POST /v1/claims/{claim_id}/review` / `GET /v1/claims/{claim_id}/reviews`
- `POST /v1/creatives` / `GET /v1/workspaces/{workspace_id}/creatives`
- `POST /v1/assets/versions` / `GET /v1/creatives/{creative_id}/assets`
- `POST /v1/assets/versions/{asset_version_id}/review` / `GET /v1/assets/versions/{asset_version_id}/reviews`
- `POST /v1/experiments` / `GET /v1/workspaces/{workspace_id}/experiments`
- `POST /v1/experiments/{experiment_id}/variants` / `GET /v1/experiments/{experiment_id}/variants`
- `GET /v1/workspaces/{workspace_id}/audit`
- `POST /v1/agents/creative-strategy/run` — calls the configured OpenAI-compatible model, validates structured concepts, persists drafts and an AgentRun trace.
- `POST /v1/agents/creative-production/run` — generates a script/storyboard/shot and prompt brief for a saved creative; persists versioned production drafts.
- `GET /v1/creatives/{creative_id}/production-drafts` — lists saved production brief versions.
- `GET /v1/workspaces/{workspace_id}/agent-runs` — lists persisted Agent execution records.

### Guardrails
- New claims are created as UNVERIFIED; verification requires a separate reviewer record and at least one evidence reference.
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

Zero denominator returns null. ROAS is not ROI.\n\n## Experiment statistics\n\nThe comparison endpoint supports CTR (clicks / impressions) and click-to-purchase CVR (purchases / clicks). It returns arm-level Wilson 95% intervals, an absolute difference interval, relative lift, z-score, two-sided p-value, a minimum-sample decision label, and an approximate equal-allocation sample estimate for 80% power at 5% alpha when an MDE is supplied.\n\nThe implementation is a two-proportion z-test over aggregate counts. It assumes independent binary outcomes and is only a statistical workflow demonstration on the bundled synthetic dataset. It does not correct for multiple comparisons, repeated peeking, cluster effects, or platform delivery bias. Do not use it to declare real campaign winners without randomized assignment and a pre-registered analysis plan.

## Creative Strategy Agent configuration

Copy the root `.env.example` to `.env` and set `OPENAI_API_KEY`. Optional settings:
- `OPENAI_BASE_URL` (default: `https://api.openai.com/v1`)
- `OPENAI_MODEL` (default: `gpt-4.1-mini`)

The provider key is read from the process environment and is never written to SQLite. Strategy and Production Agents receive only product facts and VERIFIED claims. If no verified claims exist, the prompt explicitly forbids inventing product efficacy, clinical outcomes, testimonials or endorsements. Generated concepts are saved as drafts and require human review. The endpoint does not generate final image/video assets, publish ads or spend budget.
