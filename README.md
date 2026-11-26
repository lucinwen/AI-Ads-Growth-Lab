# AI Ads Growth Lab

AI-powered creative production and growth analytics workspace for the US beauty and skincare market.

> **Evidence boundary:** The bundled demo dataset is synthetic. It is not actual TikTok/Meta delivery data and must not be represented as real CTR, CVR, ROAS, ROI, or GMV outcomes.

## Current implementation status

### Implemented
- Responsive React + TypeScript dashboard with Overview, Creative Studio, Experiments, Growth Insights, and Agent Activity views.
- FastAPI health, deterministic metric aggregation, CSV validation, and demo overview endpoints.
- Demo overview aggregation by creative, date, and funnel stage.
- Explicit SIMULATED / REAL data-mode isolation in aggregation and CSV validation.
- 84 synthetic daily records covering 12 creative variants across 7 dates.
- Agent role specifications, product requirements, experiment plan, data dictionary, PostgreSQL schema draft, and portfolio evidence standards.
- GitHub Actions checks for backend tests and frontend production build.

### Not implemented yet
- Persistent PostgreSQL integration and migrations.
- Persistent CRUD for workspaces, products, claims, creative assets, and experiments.
- Actual LLM-backed Agent execution, tool routing, and persisted AgentRun traces.
- Real asset generation, upload, and storage pipeline.
- Real ad account connectors or live campaign operations.
- Real campaign results or causal growth evidence.

## Quick start

Requires Docker Compose, or Python 3.11+ and Node.js 20+.

### Docker Compose (recommended)

```bash
docker compose up --build
```

Open:
- Frontend: http://localhost:5173
- API docs: http://localhost:8000/docs
- Health: http://localhost:8000/health

### Run separately

Start the backend:

```bash
cd backend
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows PowerShell:
# .venv\\Scripts\\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

In a second terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## API endpoints

- `GET /health`
- `GET /v1/demo/overview` — aggregated demo data for dashboard views
- `POST /v1/metrics/aggregate` — aggregate validated metric rows
- `POST /v1/import/csv/validate?data_mode=SIMULATED` — validate a CSV upload and return aggregate metrics

## Product principles

1. Never mix SIMULATED and REAL data in one experiment or metric snapshot.
2. Calculate metrics in deterministic code; LLMs may explain, not invent, metrics.
3. ROAS is not ROI. ROI requires incremental profit and total investment.
4. Objective product claims require evidence; high-risk claims require human review.
5. No autonomous ad publishing or budget changes in V1.
6. Synthetic demo results are not evidence of real campaign lift.
7. Draft concepts and Agent specifications must not be represented as generated assets or executed Agent runs.

## Planned stack

- Frontend: React + TypeScript + Vite
- Backend: Python + FastAPI
- Database: PostgreSQL
- Analytics: deterministic Python metric engine; statistical modules to follow
- Tests: Pytest + frontend production build
- Local development: Docker Compose

## Repository map

- `docs/` — PRD, experiment design, data dictionary, build plan, portfolio acceptance
- `backend/` — API, deterministic metric engine, tests
- `frontend/` — responsive workspace dashboard
- `data/` — explicitly synthetic demo data
- `skills/` — specialist Agent instructions
- `schemas/` — PostgreSQL schema draft

See `docs/BUILD_PLAN.md` for staged implementation.
