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
- [x] GitHub Actions backend tests, frontend production build and Docker Compose config validation
- [ ] Browser-level visual QA and responsive screenshots

## P2 — Persistent product data
- [x] SQLite local persistence layer and idempotent demo seed
- [x] Workspace / Product / Claim / Creative CRUD APIs
- [x] AssetVersion / Experiment / Variant CRUD APIs
- [x] Verified claim requires evidence reference
- [x] Workspace ownership checks for products, creatives and experiment variants
- [x] Audit log for create, variant and review operations
- [x] Separate asset review endpoint; new versions always start PENDING
- [ ] PostgreSQL connection and migrations (SQLite is current local runtime)
- [x] Claim review records with reviewer, decision, evidence references, reason and timestamp
- [ ] Claim review UI and reviewer identity/access control
- [ ] Asset rights manifest and immutable approval transitions
- [ ] Import batch persistence, deduplication and validation report history
- [x] Persisted AgentRun trace model

## P3 — Functional creative workspace
- [x] Persisted creative hypotheses and Creative Studio draft creation
- [x] Product Claim Registry UI; new claims default to UNVERIFIED
- [x] Claim evidence rule: VERIFIED requires evidence references
- [x] Experiment builder persists experiment definitions and assigns creative variants
- [x] Asset version records start PENDING and require a separate human review action
- [ ] Full creative brief editor with product facts and audience hypothesis
- [x] Creative Production Agent generates structured scripts, storyboards, camera directions and asset prompts
- [x] Production brief versions persist per creative and are visible in Creative Studio
- [ ] Editable script / storyboard / prompt editor with version history
- [ ] Asset upload, storage, preview, and version comparison
- [ ] Compliance precheck linked to Claim Registry; block high-risk creative before READY_TO_TEST

## P4 — Agent workflow
- [x] First executable Creative Strategy Agent via configurable OpenAI-compatible endpoint
- [x] Structured JSON output validation and verified-claim ID enforcement
- [x] Persisted AgentRun status, input/output references, model, latency and errors
- [x] Creative Studio invokes Strategy Agent and saves returned concepts as drafts
- [x] Agent Activity view displays persisted run history
- [ ] Orchestrator and dependency-aware multi-agent task graph
- [ ] Creative Production, Compliance, Asset QA, Analytics and Growth Advisor agents
- [ ] Prompt/model cost tracking, retries, idempotency and structured tool traces
- [ ] Human review workflow integrated into Agent task transitions

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
