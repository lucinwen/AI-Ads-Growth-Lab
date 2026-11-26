# AI Ads Growth Lab

AI-powered creative production and growth analytics workspace for the US beauty and skincare market.

> **Evidence boundary:** V1 demo metrics are synthetic. They are not actual TikTok/Meta delivery data and must not be represented as real CTR, CVR, ROAS, ROI, or GMV outcomes.

## V1 scope

- Product facts and approved-claims registry
- Creative brief and creative variant management
- Asset lineage and human review gates
- Deterministic paid-media metric calculations
- CSV import with SIMULATED / REAL data-mode separation
- Experiment analysis and next-test recommendations
- Agent orchestration with auditable tool traces

## Current implementation status

**Implemented in the first backend slice**
- FastAPI health endpoint\n- Demo overview endpoint aggregating the bundled dataset by date, creative and funnel stage\n- CORS configured for the local Vite frontend
- Deterministic metric aggregation endpoint
- CSV validation endpoint with data-mode isolation
- Metric engine and API smoke tests
- Synthetic 84-row daily dataset (12 creative variants × 7 days)
- Initial PRD, experiment plan, data dictionary, build plan, Agent Skills, and PostgreSQL schema

**Not implemented yet**
- Persistent database integration/migrations
- Persistent database integration/migrations
- LLM-backed Agent execution
- Asset upload/storage UI
- Persistent experiment management and LLM-backed Agent execution\n- TikTok/Meta read-only connectors
- TikTok/Meta read-only connectors

## Quick start — full local application\n\nRequires Docker Compose, or Python 3.11+ and Node.js 20+.\n\n### Docker Compose (recommended)\n\n\\`\\`\\`bash\ndocker compose up --build\n\\`\\`\\`\n\nOpen the frontend at http://localhost:5173 and API docs at http://localhost:8000/docs.\n\n### Run frontend and API separately\n\nStart the API using the steps below, then in another terminal:\n\n\\`\\`\\`bash\ncd frontend\nnpm install\nnpm run dev\n\\`\\`\\`\n\n## Quick start — API only

Requires Python 3.11+.

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

Open:
- API health: http://localhost:8000/health
- Interactive API docs: http://localhost:8000/docs

Run tests:

```bash
cd backend
pytest -q
```

Or use Docker from the repository root:

```bash
docker compose up --build
```

## API endpoints

- `GET /health`
- `POST /v1/metrics/aggregate` — aggregate validated metric rows
- `POST /v1/import/csv/validate?data_mode=SIMULATED` — validate a CSV upload and return aggregate metrics\n- `GET /v1/demo/overview` — aggregated demo data for dashboard views

Example aggregate request:

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

## Principles

1. Never mix SIMULATED and REAL data in one experiment or metric snapshot.
2. Calculate metrics in deterministic code; LLMs may explain, not invent, metrics.
3. ROAS is not ROI. ROI requires incremental profit and total investment.
4. Objective product claims require evidence; high-risk claims require human review.
5. No autonomous ad publishing or budget changes in V1.
6. Synthetic demo results are not evidence of real campaign lift.

## Planned stack

- Frontend: Next.js + TypeScript
- Backend: Python + FastAPI
- Database: PostgreSQL
- Analytics: Pandas / NumPy / SciPy
- Tests: Pytest + Playwright
- Local development: Docker Compose

## Repository map

- `docs/` — PRD, experiment design, data dictionary, portfolio criteria
- `backend/` — API, deterministic metric engine, tests\n- `frontend/` — responsive React + TypeScript workspace dashboard
- `data/` — explicitly synthetic demo data
- `skills/` — specialist Agent instructions
- `schemas/` — PostgreSQL schema

See `docs/BUILD_PLAN.md` for staged implementation.
