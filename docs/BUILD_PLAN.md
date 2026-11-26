# Build Plan

## P0 — Analytics foundation
- [x] Initialize repository and project documentation
- [x] Deterministic metric engine (aggregation API + zero-denominator handling)
- [x] CSV schema validation and SIMULATED/REAL isolation
- [x] Synthetic seed CSV (84 daily rows / 12 variants / 7 days)
- [x] Pytest unit/API smoke tests passing in GitHub Actions
- [x] FastAPI health, aggregation, CSV validation, and demo overview endpoints
- [x] Demo overview aggregates metrics by creative, date, and funnel stage

## P1 — Portfolio demo interface
- [x] Responsive React + TypeScript + Vite application shell
- [x] Overview dashboard with KPI cards, spend/revenue trend, funnel, and creative table
- [x] CSV validation interaction wired to backend API
- [x] Creative Studio draft concepts and local hypothesis drafting
- [x] Experiment design view with hypothesis and guardrail framing
- [x] Growth Insights view with descriptive signals and explicit limitations
- [x] Agent Activity registry that distinguishes specifications from executed runs
- [x] Docker Compose frontend + backend services
- [x] GitHub Actions backend tests and frontend production build
- [ ] Browser-level visual QA and responsive screenshots

## P2 — Persistent product data
- [ ] PostgreSQL connection, migrations, and seed process
- [ ] Workspace / Brand / Product / Claim models and CRUD APIs
- [ ] Creative / AssetVersion / Experiment / Variant models and CRUD APIs
- [ ] Claim evidence registry and reviewer workflow
- [ ] Asset manifests, version lineage, and rights metadata
- [ ] Audit log and persisted AgentRun trace model
- [ ] Import batch persistence, deduplication, and validation report history

## P3 — Functional creative workspace
- [ ] Creative brief editor with product facts and audience hypothesis
- [ ] Strategy Agent generates structured concept matrix
- [ ] Script / storyboard / prompt editor with version history
- [ ] Asset upload, storage, preview, and version comparison
- [ ] Compliance precheck linked to Claim Registry
- [ ] Human approval queue blocks non-compliant assets

## P4 — Agent workflow
- [ ] Orchestrator and dependency-aware task graph
- [ ] Strategy, Production, Compliance, Asset QA, Analytics, Growth Advisor agents
- [ ] Structured tool schemas, timeouts, retries, idempotency, and error states
- [ ] Prompt/model/version trace and cost/latency capture
- [ ] Human approval gates for claims, assets, and any campaign action

## P5 — Experiment analytics
- [ ] Experiment Builder with pre-registration, MDE, power, and stopping rules
- [ ] CSV import UI with field mapping and data-quality diagnostics
- [ ] Creative breakdowns, funnel analysis, and confidence intervals
- [ ] Analytics Agent cites metric snapshots and data limitations
- [ ] Exportable experiment report and portfolio case study

## P6 — Real data readiness
- [ ] Read-only TikTok/Meta export adapters
- [ ] Explicit account/data authorization and secure secret handling
- [ ] Attribution, timezone, currency, refund, and deduplication checks
- [ ] No publishing or spend mutation without separate human approval

## Definition of Done
- Clean-machine startup via README and Docker Compose.
- Synthetic/real data separation enforced server-side.
- Metric formulas covered by tests.
- Every asset traces to brief, source facts, prompt/model, version, rights, and review.
- Compliance blockers prevent READY_TO_TEST.
- Every analytics insight cites a metric snapshot and limitations.
- No autonomous budget change or ad publishing in V1.
- Portfolio claims distinguish IMPLEMENTED, TESTED, SIMULATED, REAL DATA, and CONCEPT.
