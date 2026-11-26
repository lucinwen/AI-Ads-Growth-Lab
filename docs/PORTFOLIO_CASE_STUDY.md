# Portfolio Case Study — AI Ads Growth Lab

## One-line summary
Designed and implemented an AI-assisted creative strategy and advertising measurement workspace for a fictional US skincare brand, connecting persistent product/claim data, creative hypotheses, human review, experiment configuration, deterministic metric analysis, and configurable Strategy and Production Agents.

## Problem framing
AIGC can increase the supply of advertising creatives, but production volume alone does not prove business value. Teams need a traceable way to connect:
1. Product facts and approved claims.
2. Audience and campaign hypotheses.
3. Differentiated creative concepts and asset versions.
4. Claim evidence and human review.
5. Experiment configuration and performance data.
6. Funnel analysis and the next test decision.

The product is designed around that workflow rather than presenting a prompt box as the whole solution.

## Target user and scenario
- Market: United States.
- Vertical: Beauty & skincare.
- Demo brand: Luma Dew (fictional).
- Demo product: Daily Barrier Moisturizer (fictional).
- Channel framing: TikTok-style short-video creative; no live ad account connection.
- Data mode: SIMULATED.

## Product decisions
### 1. Keep strategy, production, measurement and approval separate
The system has dedicated surfaces for Overview, Creative Studio, Experiments, Growth Insights and Agent Activity. A creative concept is not automatically treated as a final asset or an approved ad.

### 2. Make claims evidence-aware
Objective product claims are stored in a Claim Registry. New claims default to UNVERIFIED. A VERIFIED claim requires at least one evidence reference. Asset versions start as PENDING and require a separate review action.

### 3. Keep metrics deterministic
The backend calculates CTR, CPC, LPV rate, ATC rate, click-to-purchase CVR, CPA, AOV, ROAS and refund rate from aggregated counts. Zero denominators return null. ROAS is explicitly not treated as ROI.

### 4. Make data provenance visible
SIMULATED and REAL data modes are isolated. The bundled dataset is synthetic and labeled as such throughout the dashboard and documentation. No simulated CTR, CVR, ROAS or GMV is presented as real campaign performance.

### 5. Keep humans in control
No automatic ad publishing, budget changes or campaign operations are implemented. Agent-generated concepts are drafts and require human creative/compliance review.

## Implemented product
- Responsive React + TypeScript dashboard.
- FastAPI backend.
- SQLite local persistence for workspace, product, claim, creative, asset version, experiment, variant, review, AgentRun and audit records.
- Seeded fictional demo workspace and four starter creative hypotheses.
- Creative Studio can save custom creative hypotheses to persistent storage.
- Claim Registry can add unverified product claims.
- Experiment Builder can save an experiment and attach the four creative hypotheses as variants.
- Asset versions default to PENDING and have a separate human-review endpoint.
- Configurable Creative Strategy Agent uses an OpenAI-compatible chat-completions endpoint, validates structured output and persists returned concepts as drafts.
- Configurable Creative Production Agent generates versioned scripts, storyboards, camera directions and asset prompts from a saved creative concept.
- AgentRun records retain status, model, input/output references, latency and error information.
- Dashboard aggregates the bundled synthetic dataset by date, creative and funnel stage.
- CSV validation endpoint rejects data-mode mismatch.
- Docker Compose runs frontend and backend together.
- GitHub Actions runs backend tests and frontend production build.

## Current verification
- Backend test suite: 23 tests passed in GitHub Actions at the last recorded full run.
- Frontend TypeScript/Vite production build: passed in GitHub Actions at the last recorded full run.
- Test coverage includes metric calculations, zero denominators, SIMULATED/REAL isolation, CSV validation, workspace/product/claim/creative/experiment persistence, asset review, Strategy and Production Agent provider paths using mocked providers, asset/claim review evidence gates, and statistical comparison/sample sufficiency tests.

## Demo flow
1. Open Overview and inspect the clearly labeled synthetic dataset.
2. Open Creative Studio and review the four seeded hypotheses.
3. Add a new creative hypothesis and confirm it persists after refresh.
4. Add a product claim and observe that it remains UNVERIFIED.
5. Configure an OpenAI-compatible provider and run Creative Strategy; inspect the generated drafts and AgentRun trace.
6. Open Experiments and create an experiment with four creative variants.
7. Inspect the persisted experiment and variant assignments.
8. Open Agent Activity and inspect run history.
9. Review the API docs and audit endpoints.

## Architecture
- Frontend: React, TypeScript, Vite, Recharts, Lucide.
- Backend: FastAPI, Pydantic, SQLite local persistence.
- Agent provider: configurable OpenAI-compatible chat-completions API.
- Deterministic analytics: Python metric engine.
- Data: synthetic CSV seed; real data import and platform connectors are future work.
- Deployment: Docker Compose.
- CI: GitHub Actions.

## Evidence and limitations
### Implemented
The UI, local CRUD APIs, SQLite persistence, deterministic metric calculations, CSV validation, configurable Strategy and Production Agent endpoints, AgentRun persistence, and CI tests are implemented.

### Simulated
All 84 daily media records, impressions, clicks, purchases, spend, attributed revenue, and the displayed ROAS/CTR/CVR values are synthetic. They do not represent actual TikTok or Meta delivery.

### Not yet implemented
- PostgreSQL runtime and migrations (SQLite is the current local adapter).
- Full multi-agent orchestrator and specialist execution beyond Strategy and Production.
- Image/video generation pipeline and asset storage.
- Full claim-review evidence UI and regulatory workflow.
- Read-only TikTok/Meta account connectors.
- Real randomized A/B tests, robust power analysis against actual traffic, sequential-testing controls, multiple-comparison correction, incrementality measurement, and actual campaign results.

## Interview narrative (90 seconds)
“I noticed that AIGC creative tools usually focus on producing more assets, but a commercial creative team also needs to know which claims are supported, which assets are ready for testing, how a test is configured, and what the data actually says. I built AI Ads Growth Lab around that workflow. It has a persistent product and claim registry, a Creative Studio for testable concepts, an experiment builder, deterministic funnel metrics, auditable Strategy and Production Agents that produce structured creative and storyboard drafts, and an experiment comparison workflow with statistical guardrails. I deliberately separated simulated and real data, made new claims unverified by default, and kept publishing and budget changes behind human control. The current demo proves the product workflow and engineering foundations; actual media lift remains unvalidated until an authorized live experiment is run.”

## Links
- Repository: https://github.com/lucinwen/AI-Ads-Growth-Lab
- PRD: docs/PRD.md
- Experiment plan: docs/EXPERIMENT_PLAN.md
- API reference: docs/API.md
- Build plan: docs/BUILD_PLAN.md
- Portfolio evidence standards: docs/PORTFOLIO_ACCEPTANCE.md
