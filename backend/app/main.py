from __future__ import annotations

import csv
import io
import os
import json
import sqlite3
import uuid
from typing import Literal
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, ConfigDict

from .metrics import MetricRow, aggregate_metrics
from . import storage
from .schemas import (WorkspaceCreate, ProductCreate, ClaimCreate, CreativeCreate, AssetVersionCreate, AssetReviewCreate, ExperimentCreate, VariantCreate)

app = FastAPI(title="AI Ads Growth Lab API", version="0.4.0")
storage.init_db()
storage.seed_demo_workspace()

@app.on_event("startup")
def initialize_storage():
    storage.init_db()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


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
    dataset = Path(os.getenv("AI_ADS_DEMO_DATA_PATH", str(Path(__file__).resolve().parents[2] / "data" / "synthetic_daily_metrics.csv")) )
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
            "workspace_id": "demo-us-beauty-workspace",
            "product_id": "demo-luma-dew-moisturizer",
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


# Persistent workspace API. The local V1 runtime uses SQLite; the PostgreSQL schema
# remains the deployment target for a later migration.
@app.post("/v1/workspaces", status_code=201)
def create_workspace(payload: WorkspaceCreate):
    workspace_id = str(uuid.uuid4())
    with storage.connect() as db:
        db.execute(
            "INSERT INTO workspace(id,name,market,vertical,data_mode) VALUES(?,?,?,?,?)",
            (workspace_id, payload.name, payload.market.upper(), payload.vertical, payload.data_mode),
        )
        storage.audit(db, workspace_id, "CREATE", "WORKSPACE", workspace_id, payload.model_dump())
        row = db.execute("SELECT * FROM workspace WHERE id=?", (workspace_id,)).fetchone()
        return storage.row_dict(row)


@app.get("/v1/workspaces")
def list_workspaces():
    with storage.connect() as db:
        return [storage.row_dict(row) for row in db.execute("SELECT * FROM workspace ORDER BY created_at DESC")]


@app.post("/v1/products", status_code=201)
def create_product(payload: ProductCreate):
    product_id = str(uuid.uuid4())
    with storage.connect() as db:
        workspace = db.execute("SELECT id FROM workspace WHERE id=?", (payload.workspace_id,)).fetchone()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        db.execute(
            "INSERT INTO product(id,workspace_id,name,category,currency,price_cents,facts_json,landing_page_url) VALUES(?,?,?,?,?,?,?,?)",
            (product_id, payload.workspace_id, payload.name, payload.category, payload.currency.upper(),
             payload.price_cents, json.dumps(payload.facts, ensure_ascii=False), payload.landing_page_url),
        )
        storage.audit(db, payload.workspace_id, "CREATE", "PRODUCT", product_id, {"name": payload.name})
        return storage.row_dict(db.execute("SELECT * FROM product WHERE id=?", (product_id,)).fetchone())


@app.get("/v1/workspaces/{workspace_id}/products")
def list_products(workspace_id: str):
    with storage.connect() as db:
        if not db.execute("SELECT 1 FROM workspace WHERE id=?", (workspace_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Workspace not found")
        return [storage.row_dict(row) for row in db.execute("SELECT * FROM product WHERE workspace_id=? ORDER BY created_at DESC", (workspace_id,))]


@app.post("/v1/claims", status_code=201)
def create_claim(payload: ClaimCreate):
    claim_id = str(uuid.uuid4())
    with storage.connect() as db:
        product = db.execute("SELECT id FROM product WHERE id=?", (payload.product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if payload.status == "VERIFIED" and not payload.evidence_refs:
            raise HTTPException(status_code=422, detail="VERIFIED claims require at least one evidence reference")
        db.execute(
            "INSERT INTO claim(id,product_id,claim_text,claim_type,status,evidence_refs_json,risk_level,notes) VALUES(?,?,?,?,?,?,?,?)",
            (claim_id, payload.product_id, payload.claim_text, payload.claim_type, payload.status,
             json.dumps(payload.evidence_refs, ensure_ascii=False), payload.risk_level, payload.notes),
        )
        workspace_id = db.execute("SELECT workspace_id FROM product WHERE id=?", (payload.product_id,)).fetchone()["workspace_id"]
        storage.audit(db, workspace_id, "CREATE", "CLAIM", claim_id, {"status": payload.status})
        return storage.row_dict(db.execute("SELECT * FROM claim WHERE id=?", (claim_id,)).fetchone())


@app.get("/v1/products/{product_id}/claims")
def list_claims(product_id: str):
    with storage.connect() as db:
        if not db.execute("SELECT 1 FROM product WHERE id=?", (product_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Product not found")
        return [storage.row_dict(row) for row in db.execute("SELECT * FROM claim WHERE product_id=? ORDER BY created_at DESC", (product_id,))]


@app.post("/v1/creatives", status_code=201)
def create_creative(payload: CreativeCreate):
    creative_id = str(uuid.uuid4())
    with storage.connect() as db:
        product = db.execute("SELECT workspace_id FROM product WHERE id=?", (payload.product_id,)).fetchone()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if product["workspace_id"] != payload.workspace_id:
            raise HTTPException(status_code=422, detail="Product does not belong to the supplied workspace")
        db.execute(
            "INSERT INTO creative(id,workspace_id,product_id,concept_name,angle,hook,narrative,cta,language,format,hypothesis) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (creative_id, payload.workspace_id, payload.product_id, payload.concept_name, payload.angle,
             payload.hook, payload.narrative, payload.cta, payload.language, payload.format, payload.hypothesis),
        )
        storage.audit(db, payload.workspace_id, "CREATE", "CREATIVE", creative_id, {"concept_name": payload.concept_name})
        return dict(db.execute("SELECT * FROM creative WHERE id=?", (creative_id,)).fetchone())


@app.get("/v1/workspaces/{workspace_id}/creatives")
def list_creatives(workspace_id: str):
    with storage.connect() as db:
        if not db.execute("SELECT 1 FROM workspace WHERE id=?", (workspace_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Workspace not found")
        return [dict(row) for row in db.execute("SELECT * FROM creative WHERE workspace_id=? ORDER BY created_at DESC", (workspace_id,))]


@app.post("/v1/assets/versions", status_code=201)
def create_asset_version(payload: AssetVersionCreate):
    asset_id = str(uuid.uuid4())
    with storage.connect() as db:
        creative = db.execute("SELECT workspace_id FROM creative WHERE id=?", (payload.creative_id,)).fetchone()
        if not creative:
            raise HTTPException(status_code=404, detail="Creative not found")
        current = db.execute("SELECT COALESCE(MAX(version_no),0) AS version_no FROM asset_version WHERE creative_id=?", (payload.creative_id,)).fetchone()["version_no"]
        version_no = current + 1
        db.execute(
            "INSERT INTO asset_version(id,creative_id,version_no,asset_type,asset_uri,prompt_text,model_name,file_hash,approval_status) VALUES(?,?,?,?,?,?,?,?,?)",
            (asset_id, payload.creative_id, version_no, payload.asset_type, payload.asset_uri, payload.prompt_text,
             payload.model_name, payload.file_hash, "PENDING"),
        )
        storage.audit(db, creative["workspace_id"], "CREATE_VERSION", "ASSET_VERSION", asset_id, {"version_no": version_no})
        return dict(db.execute("SELECT * FROM asset_version WHERE id=?", (asset_id,)).fetchone())


@app.get("/v1/creatives/{creative_id}/assets")
def list_asset_versions(creative_id: str):
    with storage.connect() as db:
        if not db.execute("SELECT 1 FROM creative WHERE id=?", (creative_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Creative not found")
        return [dict(row) for row in db.execute("SELECT * FROM asset_version WHERE creative_id=? ORDER BY version_no DESC", (creative_id,))]


@app.post("/v1/experiments", status_code=201)
def create_experiment(payload: ExperimentCreate):
    experiment_id = str(uuid.uuid4())
    with storage.connect() as db:
        workspace = db.execute("SELECT data_mode FROM workspace WHERE id=?", (payload.workspace_id,)).fetchone()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if workspace["data_mode"] != payload.data_mode:
            raise HTTPException(status_code=422, detail="Experiment data_mode must match its workspace data_mode")
        db.execute(
            "INSERT INTO experiment(id,workspace_id,name,hypothesis,channel,data_mode,attribution_window,timezone,budget_cap_cents,currency) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (experiment_id, payload.workspace_id, payload.name, payload.hypothesis, payload.channel,
             payload.data_mode, payload.attribution_window, payload.timezone, payload.budget_cap_cents, payload.currency.upper()),
        )
        storage.audit(db, payload.workspace_id, "CREATE", "EXPERIMENT", experiment_id, {"data_mode": payload.data_mode})
        return dict(db.execute("SELECT * FROM experiment WHERE id=?", (experiment_id,)).fetchone())


@app.get("/v1/workspaces/{workspace_id}/experiments")
def list_experiments(workspace_id: str):
    with storage.connect() as db:
        if not db.execute("SELECT 1 FROM workspace WHERE id=?", (workspace_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Workspace not found")
        return [dict(row) for row in db.execute("SELECT * FROM experiment WHERE workspace_id=? ORDER BY created_at DESC", (workspace_id,))]


@app.post("/v1/experiments/{experiment_id}/variants", status_code=201)
def add_experiment_variant(experiment_id: str, payload: VariantCreate):
    variant_id = str(uuid.uuid4())
    with storage.connect() as db:
        experiment = db.execute("SELECT workspace_id FROM experiment WHERE id=?", (experiment_id,)).fetchone()
        creative = db.execute("SELECT workspace_id FROM creative WHERE id=?", (payload.creative_id,)).fetchone()
        if not experiment:
            raise HTTPException(status_code=404, detail="Experiment not found")
        if not creative:
            raise HTTPException(status_code=404, detail="Creative not found")
        if experiment["workspace_id"] != creative["workspace_id"]:
            raise HTTPException(status_code=422, detail="Creative and experiment must belong to the same workspace")
        db.execute(
            "INSERT INTO experiment_variant(id,experiment_id,creative_id,allocation_pct,role) VALUES(?,?,?,?,?)",
            (variant_id, experiment_id, payload.creative_id, payload.allocation_pct, payload.role),
        )
        storage.audit(db, experiment["workspace_id"], "ADD_VARIANT", "EXPERIMENT_VARIANT", variant_id, payload.model_dump())
        return dict(db.execute("SELECT * FROM experiment_variant WHERE id=?", (variant_id,)).fetchone())


@app.get("/v1/experiments/{experiment_id}/variants")
def list_experiment_variants(experiment_id: str):
    with storage.connect() as db:
        if not db.execute("SELECT 1 FROM experiment WHERE id=?", (experiment_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Experiment not found")
        return [dict(row) for row in db.execute("SELECT * FROM experiment_variant WHERE experiment_id=? ORDER BY rowid", (experiment_id,))]


@app.get("/v1/workspaces/{workspace_id}/audit")
def list_audit_log(workspace_id: str):
    with storage.connect() as db:
        if not db.execute("SELECT 1 FROM workspace WHERE id=?", (workspace_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Workspace not found")
        return [storage.row_dict(row) for row in db.execute("SELECT * FROM audit_log WHERE workspace_id=? ORDER BY id DESC LIMIT 200", (workspace_id,))]


@app.post("/v1/assets/versions/{asset_version_id}/review", status_code=201)
def review_asset_version(asset_version_id: str, payload: AssetReviewCreate):
    review_id = str(uuid.uuid4())
    with storage.connect() as db:
        asset = db.execute(
            "SELECT av.id, c.workspace_id FROM asset_version av JOIN creative c ON c.id=av.creative_id WHERE av.id=?",
            (asset_version_id,),
        ).fetchone()
        if not asset:
            raise HTTPException(status_code=404, detail="Asset version not found")
        db.execute(
            "INSERT INTO review_record(id,asset_version_id,reviewer_id,decision,reason,findings_json) VALUES(?,?,?,?,?,?)",
            (review_id, asset_version_id, payload.reviewer_id, payload.decision, payload.reason,
             json.dumps(payload.findings, ensure_ascii=False)),
        )
        db.execute("UPDATE asset_version SET approval_status=? WHERE id=?", (payload.decision, asset_version_id))
        storage.audit(db, asset["workspace_id"], "REVIEW", "ASSET_VERSION", asset_version_id,
                      {"reviewer_id": payload.reviewer_id, "decision": payload.decision})
        row = db.execute("SELECT * FROM review_record WHERE id=?", (review_id,)).fetchone()
        result = dict(row)
        result["findings"] = json.loads(result.pop("findings_json"))
        return result


@app.get("/v1/assets/versions/{asset_version_id}/reviews")
def list_asset_reviews(asset_version_id: str):
    with storage.connect() as db:
        if not db.execute("SELECT 1 FROM asset_version WHERE id=?", (asset_version_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Asset version not found")
        rows = db.execute("SELECT * FROM review_record WHERE asset_version_id=? ORDER BY created_at DESC", (asset_version_id,))
        results = []
        for row in rows:
            result = dict(row)
            result["findings"] = json.loads(result.pop("findings_json"))
            results.append(result)
        return results
