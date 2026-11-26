# Frontend

React + TypeScript + Vite dashboard for AI Ads Growth Lab.

## Run locally

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173. The FastAPI backend must be running at the URL configured by `VITE_API_BASE_URL` (default `http://localhost:8000`).

## Build

```bash
npm run build
```

The current UI includes Overview, Creative Studio, Experiments, Growth Insights, and Agent Activity. The strategy cards and agent registry are explicitly labeled as drafts/specifications until model execution and persistence are implemented.
