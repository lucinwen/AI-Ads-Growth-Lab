# Build Plan

## P0 — First vertical slice
- [x] Initialize repository and project documentation
- [x] Deterministic metric engine (aggregation API + zero-denominator handling)
- [x] CSV schema validation and SIMULATED/REAL isolation
- [x] Synthetic seed CSV (84 daily rows / 12 variants / 7 days)
- [x] Pytest unit/API smoke tests added (CI execution pending)
- [x] FastAPI health, aggregation, and CSV validation endpoints

## P1 — Core product data
- [ ] Workspace / Brand / Product / Claim models
- [ ] Creative / AssetVersion / Experiment / Variant models
- [ ] PostgreSQL migrations
- [ ] Audit log and agent-run trace model

## P2 — Creative workspace
- [ ] Creative brief editor
- [ ] Creative matrix and asset registry
- [ ] Prompt/script/storyboard generation
- [ ] Asset version comparison and review UI

## P3 — Agent workflow
- [ ] Orchestrator and task graph
- [ ] Strategy, Production, Compliance, Asset QA agents
- [ ] Human approval gates
- [ ] Retry, timeout, idempotency and structured tool logs

## P4 — Experiment analytics
- [ ] CSV upload UI and validation report
- [ ] Metric dashboard and funnel breakdown
- [ ] Experiment analysis and next-test recommendation
- [ ] Exportable case-study report

## P5 — Real data readiness
- [ ] Read-only platform export adapters
- [ ] Explicit account/data authorization
- [ ] Attribution, timezone, currency, refund and deduplication checks
- [ ] No publishing or spend mutation without separate human approval

## Definition of Done
- Clean-machine startup via README.
- Synthetic/real data separation enforced server-side.
- Metric formulas covered by tests.
- Every asset traces to brief, source facts, prompt/model, version and review.
- Compliance blockers prevent READY_TO_TEST.
- Every analytics insight cites a metric snapshot and limitations.
- No autonomous budget change or ad publishing in V1.
