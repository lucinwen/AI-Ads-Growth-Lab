# AI Ads Growth Lab

AI-powered creative production and growth analytics workspace for the US beauty and skincare market.

> **Evidence boundary:** V1 demo metrics are synthetic. They are not actual TikTok/Meta delivery data and must not be represented as real CTR, CVR, ROAS, ROI, or GMV outcomes.

## V1 scope

- Product and approved-claims registry
- Creative brief and creative variant management
- Asset lineage and human review gates
- Deterministic paid-media metric calculations
- CSV import with SIMULATED / REAL data-mode separation
- Experiment analysis and next-test recommendations
- Agent orchestration with auditable tool traces

## Initial implementation

The first vertical slice will provide a deterministic metric engine, validated CSV import, sample synthetic dataset, and tests. Agent orchestration and the UI are staged after this foundation.

## Principles

1. Never mix SIMULATED and REAL data in one experiment or metric snapshot.
2. Calculate metrics in deterministic code; LLMs may explain, not invent, metrics.
3. ROAS is not ROI. ROI requires incremental profit and total investment.
4. Objective product claims require evidence; high-risk claims require human review.
5. No autonomous ad publishing or budget changes in V1.

## Planned stack

- Frontend: Next.js + TypeScript
- Backend: Python + FastAPI
- Database: PostgreSQL
- Analytics: Pandas / NumPy / SciPy
- Tests: Pytest + Playwright
- Local development: Docker Compose

## Repository map

- `docs/` — PRD, experiment design, data dictionary, portfolio criteria
- `backend/` — API and deterministic metric engine
- `data/` — explicitly synthetic demo data
- `skills/` — specialist Agent instructions
- `schemas/` — PostgreSQL schema

See `docs/BUILD_PLAN.md` for staged implementation.