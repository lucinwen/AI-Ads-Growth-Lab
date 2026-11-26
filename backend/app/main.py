from __future__ import annotations

import csv
import io
from typing import Literal

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
