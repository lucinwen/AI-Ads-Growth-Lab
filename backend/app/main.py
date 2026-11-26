from __future__ import annotations

import csv
import io
from typing import Literal
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel, Field, ConfigDict

from .metrics import MetricRow, aggregate_metrics

app = FastAPI(title="AI Ads Growth Lab API", version="0.1.0")


class MetricInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data_mode: Literal["SIMULATED", "REAL"]
    impressions: int = Field(ge=0)
    clicks: int = Field(ge=0)
    landing_page_views: int = Field(ge=0)
    add_to_cart: int = Field(ge=0)
    purchases: int = Field(ge=0)
    refunded_orders: int = Field(ge=0)
    spend_usd: float = Field(ge=0)
    attributed_revenue_usd: float = Field(ge=0)


class AggregateRequest(BaseModel):
    rows: list[MetricInput] = Field(min_length=1)


@app.get("/health")
def health():
    return {"status": "ok", "service": "ai-ads-growth-lab-api", "version": "0.1.0"}


@app.post("/v1/metrics/aggregate")
def metrics_aggregate(payload: AggregateRequest):
    rows = [MetricRow(**row.model_dump()) for row in payload.rows]
    try:
        return aggregate_metrics(rows)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/v1/import/csv/validate")
async def validate_csv(file: UploadFile = File(...), data_mode: Literal["SIMULATED", "REAL"] = "SIMULATED"):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file")
    raw = await file.read()
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        required = {
            "data_mode", "impressions", "clicks", "landing_page_views",
            "add_to_cart", "purchases", "refunded_orders", "spend_usd",
            "attributed_revenue_usd"
        }
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ValueError(f"Missing required columns: {missing}")
        rows = list(reader)
        if not rows:
            raise ValueError("CSV contains no data rows")
        modes = {row.get("data_mode", "").strip().upper() for row in rows}
        if modes != {data_mode}:
            raise ValueError(f"CSV data_mode {sorted(modes)} does not match requested mode {data_mode}")
        parsed = []
        for index, row in enumerate(rows, start=2):
            try:
                parsed.append(MetricRow(
                    data_mode=data_mode,
                    impressions=int(row["impressions"]),
                    clicks=int(row["clicks"]),
                    landing_page_views=int(row["landing_page_views"]),
                    add_to_cart=int(row["add_to_cart"]),
                    purchases=int(row["purchases"]),
                    refunded_orders=int(row["refunded_orders"]),
                    spend_usd=float(row["spend_usd"]),
                    attributed_revenue_usd=float(row["attributed_revenue_usd"]),
                ))
            except Exception as exc:
                raise ValueError(f"Invalid row {index}: {exc}") from exc
        result = aggregate_metrics(parsed)
        return {"filename": file.filename, "data_mode": data_mode, "validated_rows": len(parsed), "aggregate": result}
    except (UnicodeDecodeError, csv.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v1/demo/overview")
def demo_overview():
    """Return the bundled synthetic experiment for the interactive portfolio demo."""
    dataset = Path(__file__).resolve().parents[2] / "data" / "synthetic_daily_metrics.csv"
    if not dataset.exists():
        raise HTTPException(status_code=503, detail="Demo dataset is not available")

    try:
        with dataset.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            raw_rows = list(reader)
        if not raw_rows:
            raise ValueError("Demo dataset is empty")

        parsed = []
        for index, row in enumerate(raw_rows, start=2):
            mode = row.get("data_mode", "").strip().upper()
            if mode != "SIMULATED":
                raise ValueError(f"Demo dataset row {index} must be SIMULATED")
            parsed.append({
                "date": row["date"],
                "creative_id": row["creative_id"],
                "variant": row["variant"],
                "metric": MetricRow(
                    data_mode=mode,
                    impressions=int(row["impressions"]),
                    clicks=int(row["clicks"]),
                    landing_page_views=int(row["landing_page_views"]),
                    add_to_cart=int(row["add_to_cart"]),
                    purchases=int(row["purchases"]),
                    refunded_orders=int(row["orders_refunded"]),
                    spend_usd=float(row["spend_usd"]),
                    attributed_revenue_usd=float(row["attributed_revenue_usd"]),
                )
            })

        overall = aggregate_metrics([item["metric"] for item in parsed])
        creative_groups = {}
        daily_groups = {}
        for item in parsed:
            creative_groups.setdefault(item["creative_id"], []).append(item["metric"])
            daily_groups.setdefault(item["date"], []).append(item["metric"])

        creative_rows = []
        for creative_id, group in sorted(creative_groups.items()):
            result = aggregate_metrics(group)
            creative_rows.append({
                "creative_id": creative_id,
                "concept": creative_id.rsplit("-", 1)[0],
                "variant": creative_id.rsplit("-", 1)[1],
                "totals": result["totals"],
                "metrics": result["metrics"],
            })

        daily_rows = []
        for event_date, group in sorted(daily_groups.items()):
            result = aggregate_metrics(group)
            daily_rows.append({
                "date": event_date,
                "spend_usd": result["totals"]["spend_usd"],
                "revenue_usd": result["totals"]["attributed_revenue_usd"],
                "impressions": result["totals"]["impressions"],
                "clicks": result["totals"]["clicks"],
                "purchases": result["totals"]["purchases"],
                "roas": result["metrics"]["roas"],
                "ctr": result["metrics"]["ctr"],
            })

        funnel = [
            {"stage": "Impressions", "value": overall["totals"]["impressions"]},
            {"stage": "Clicks", "value": overall["totals"]["clicks"]},
            {"stage": "Landing page views", "value": overall["totals"]["landing_page_views"]},
            {"stage": "Add to cart", "value": overall["totals"]["add_to_cart"]},
            {"stage": "Purchases", "value": overall["totals"]["purchases"]},
        ]
        return {
            "experiment_id": "EXP-US-BEAUTY-001",
            "workspace": "Luma Dew / US Beauty Demo",
            "data_mode": "SIMULATED",
            "source": "bundled_synthetic_dataset",
            "date_range": {"start": min(daily_groups), "end": max(daily_groups)},
            "row_count": len(parsed),
            "creative_count": len(creative_rows),
            "summary": overall,
            "daily": daily_rows,
            "creatives": creative_rows,
            "funnel": funnel,
            "limitations": [
                "All records are synthetic and do not represent actual TikTok or Meta delivery.",
                "Descriptive differences are not causal evidence or proof of market lift.",
                "ROAS is attributed revenue divided by spend; it is not profit or ROI."
            ]
        }
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=500, detail=f"Demo dataset validation failed: {exc}") from exc
