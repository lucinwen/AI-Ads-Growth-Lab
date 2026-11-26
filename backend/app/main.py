from __future__ import annotations

import csv
import io
import os
import json
import re
from math import isfinite
import sqlite3
import zipfile
from io import BytesIO
import uuid
from time import perf_counter
from typing import Literal
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field, ConfigDict

from .metrics import MetricRow, aggregate_metrics, compare_proportions
from . import storage
from .schemas import (WorkspaceCreate, ProductCreate, ClaimCreate, ClaimReviewCreate, CreativeCreate, AssetVersionCreate, AssetReviewCreate, ExperimentCreate, VariantCreate, StrategyRunRequest, ProductionRunRequest)
from .agents import generate_creative_strategy, generate_production_brief
from . import media
from .schemas import ImageGenerationRequest, VideoGenerationRequest, AssetMetadataUpdate

app = FastAPI(title="AI Ads Growth Lab API", version="0.5.0")
storage.init_db()
storage.seed_demo_workspace()
media.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(media.MEDIA_ROOT)), name="media")

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
        if payload.status != "UNVERIFIED":
            raise HTTPException(status_code=422, detail="Claims must be created UNVERIFIED; use the claim review endpoint to change status.")
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
        return [dict(row) for row in db.execute(
            "SELECT e.*, (SELECT COUNT(*) FROM experiment_variant v WHERE v.experiment_id=e.id) AS variant_count "
            "FROM experiment e WHERE e.workspace_id=? ORDER BY e.created_at DESC",
            (workspace_id,),
        )]


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


@app.post("/v1/agents/creative-strategy/run", status_code=201)
async def run_creative_strategy_agent(payload: StrategyRunRequest):
    run_id = str(uuid.uuid4())
    with storage.connect() as db:
        workspace = db.execute("SELECT * FROM workspace WHERE id=?", (payload.workspace_id,)).fetchone()
        product = db.execute("SELECT * FROM product WHERE id=?", (payload.product_id,)).fetchone()
        if not workspace:
            raise HTTPException(status_code=404, detail="Workspace not found")
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        if product["workspace_id"] != payload.workspace_id:
            raise HTTPException(status_code=422, detail="Product does not belong to the supplied workspace")
        verified_claim_rows = db.execute(
            "SELECT id,claim_text,claim_type,evidence_refs_json FROM claim WHERE product_id=? AND status='VERIFIED'",
            (payload.product_id,),
        ).fetchall()
        verified_claims = [{
            "id": row["id"], "claim_text": row["claim_text"], "claim_type": row["claim_type"],
            "evidence_refs": json.loads(row["evidence_refs_json"])
        } for row in verified_claim_rows]
        product_data = {
            "id": product["id"], "name": product["name"], "category": product["category"],
            "currency": product["currency"], "price_cents": product["price_cents"],
            "facts": json.loads(product["facts_json"]),
        }
        input_refs = {
            "workspace_id": payload.workspace_id, "product_id": payload.product_id,
            "audience_hypothesis": payload.audience_hypothesis,
            "campaign_objective": payload.campaign_objective,
            "concept_count": payload.concept_count, "verified_claim_ids": [item["id"] for item in verified_claims]
        }
        db.execute(
            "INSERT INTO agent_run(id,workspace_id,agent_name,status,input_refs_json) VALUES(?,?,?,?,?)",
            (run_id, payload.workspace_id, "creative_strategy", "RUNNING", json.dumps(input_refs, ensure_ascii=False)),
        )
        storage.audit(db, payload.workspace_id, "RUN", "AGENT", run_id, {"agent_name":"creative_strategy"})

    started = perf_counter()
    try:
        output, model_name = await generate_creative_strategy(
            product=product_data, verified_claims=verified_claims,
            audience_hypothesis=payload.audience_hypothesis,
            campaign_objective=payload.campaign_objective,
            concept_count=payload.concept_count, language=payload.language,
        )
    except RuntimeError as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        with storage.connect() as db:
            db.execute("UPDATE agent_run SET status='FAILED',error=?,latency_ms=? WHERE id=?",
                       (str(exc), latency_ms, run_id))
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        with storage.connect() as db:
            db.execute("UPDATE agent_run SET status='FAILED',error=?,latency_ms=? WHERE id=?",
                       (str(exc), latency_ms, run_id))
        raise HTTPException(status_code=502, detail=f"Creative strategy provider failed: {exc}") from exc

    saved = []
    with storage.connect() as db:
        for concept in output.concepts:
            creative_id = str(uuid.uuid4())
            db.execute(
                "INSERT INTO creative(id,workspace_id,product_id,concept_name,angle,hook,narrative,cta,language,format,hypothesis,claims_used_json) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                (creative_id, payload.workspace_id, payload.product_id, concept.concept_name, concept.angle,
                 concept.hook, concept.narrative, concept.cta, payload.language, concept.format,
                 concept.hypothesis, json.dumps(concept.claims_used)),
            )
            saved.append({
                "id": creative_id, **concept.model_dump(),
                "language": payload.language, "status": "DRAFT_REQUIRES_REVIEW"
            })
        latency_ms = int((perf_counter() - started) * 1000)
        output_refs = {"creative_ids": [item["id"] for item in saved], "concept_count": len(saved)}
        db.execute(
            "UPDATE agent_run SET status='SUCCEEDED',model_name=?,output_refs_json=?,latency_ms=? WHERE id=?",
            (model_name, json.dumps(output_refs, ensure_ascii=False), latency_ms, run_id),
        )
        storage.audit(db, payload.workspace_id, "COMPLETE", "AGENT", run_id, output_refs)

    return {
        "run_id": run_id, "agent_name": "creative_strategy", "status": "SUCCEEDED",
        "model": model_name, "latency_ms": latency_ms, "data_mode": workspace["data_mode"],
        "verified_claims_available": len(verified_claims), "concepts": saved,
        "limitations": [
            "Generated concepts are drafts and require human creative and compliance review.",
            "No ad assets are generated by this strategy endpoint.",
            "No campaign is published and no budget is spent."
        ]
    }


@app.get("/v1/workspaces/{workspace_id}/agent-runs")
def list_agent_runs(workspace_id: str):
    with storage.connect() as db:
        if not db.execute("SELECT 1 FROM workspace WHERE id=?", (workspace_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Workspace not found")
        rows = db.execute("SELECT * FROM agent_run WHERE workspace_id=? ORDER BY created_at DESC LIMIT 100", (workspace_id,))
        results = []
        for row in rows:
            result = dict(row)
            result["input_refs"] = json.loads(result.pop("input_refs_json"))
            result["output_refs"] = json.loads(result.pop("output_refs_json"))
            results.append(result)
        return results


@app.post("/v1/claims/{claim_id}/review", status_code=201)
def review_claim(claim_id: str, payload: ClaimReviewCreate):
    review_id = str(uuid.uuid4())
    if payload.decision == "VERIFIED" and not payload.evidence_refs:
        raise HTTPException(status_code=422, detail="VERIFIED claims require at least one evidence reference")
    with storage.connect() as db:
        claim = db.execute(
            "SELECT cl.id, cl.product_id, p.workspace_id FROM claim cl JOIN product p ON p.id=cl.product_id WHERE cl.id=?",
            (claim_id,),
        ).fetchone()
        if not claim:
            raise HTTPException(status_code=404, detail="Claim not found")
        db.execute(
            "INSERT INTO claim_review(id,claim_id,reviewer_id,decision,evidence_refs_json,reason) VALUES(?,?,?,?,?,?)",
            (review_id, claim_id, payload.reviewer_id, payload.decision,
             json.dumps(payload.evidence_refs, ensure_ascii=False), payload.reason),
        )
        db.execute(
            "UPDATE claim SET status=?,evidence_refs_json=? WHERE id=?",
            (payload.decision, json.dumps(payload.evidence_refs, ensure_ascii=False), claim_id),
        )
        storage.audit(db, claim["workspace_id"], "REVIEW", "CLAIM", claim_id,
                      {"reviewer_id": payload.reviewer_id, "decision": payload.decision})
        row = db.execute("SELECT * FROM claim_review WHERE id=?", (review_id,)).fetchone()
        result = dict(row)
        result["evidence_refs"] = json.loads(result.pop("evidence_refs_json"))
        return result


@app.get("/v1/claims/{claim_id}/reviews")
def list_claim_reviews(claim_id: str):
    with storage.connect() as db:
        if not db.execute("SELECT 1 FROM claim WHERE id=?", (claim_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Claim not found")
        rows = db.execute("SELECT * FROM claim_review WHERE claim_id=? ORDER BY created_at DESC", (claim_id,))
        results = []
        for row in rows:
            result = dict(row)
            result["evidence_refs"] = json.loads(result.pop("evidence_refs_json"))
            results.append(result)
        return results


@app.post("/v1/agents/creative-production/run", status_code=201)
async def run_creative_production_agent(payload: ProductionRunRequest):
    run_id = str(uuid.uuid4())
    with storage.connect() as db:
        creative = db.execute("SELECT * FROM creative WHERE id=?", (payload.creative_id,)).fetchone()
        if not creative:
            raise HTTPException(status_code=404, detail="Creative not found")
        product = db.execute("SELECT * FROM product WHERE id=?", (creative["product_id"],)).fetchone()
        verified_rows = db.execute(
            "SELECT id,claim_text,claim_type,evidence_refs_json FROM claim WHERE product_id=? AND status='VERIFIED'",
            (creative["product_id"],),
        ).fetchall()
        verified_claims = [{
            "id": row["id"], "claim_text": row["claim_text"], "claim_type": row["claim_type"],
            "evidence_refs": json.loads(row["evidence_refs_json"])
        } for row in verified_rows]
        creative_data = {
            "id": creative["id"], "concept_name": creative["concept_name"],
            "angle": creative["angle"], "hook": creative["hook"],
            "narrative": creative["narrative"], "cta": creative["cta"],
            "hypothesis": creative["hypothesis"], "format": creative["format"],
        }
        product_data = {
            "id": product["id"], "name": product["name"], "category": product["category"],
            "currency": product["currency"], "price_cents": product["price_cents"],
            "facts": json.loads(product["facts_json"]),
        }
        input_refs = {
            "creative_id": payload.creative_id, "product_id": product["id"],
            "duration_sec": payload.duration_sec, "placement": payload.placement,
            "language": payload.language, "verified_claim_ids": [item["id"] for item in verified_claims],
        }
        db.execute(
            "INSERT INTO agent_run(id,workspace_id,agent_name,status,input_refs_json) VALUES(?,?,?,?,?)",
            (run_id, creative["workspace_id"], "creative_production", "RUNNING", json.dumps(input_refs, ensure_ascii=False)),
        )
        storage.audit(db, creative["workspace_id"], "RUN", "AGENT", run_id, {"agent_name":"creative_production"})

    started = perf_counter()
    try:
        output, model_name = await generate_production_brief(
            creative=creative_data, product=product_data, verified_claims=verified_claims,
            duration_sec=payload.duration_sec, placement=payload.placement, language=payload.language,
        )
    except RuntimeError as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        with storage.connect() as db:
            db.execute("UPDATE agent_run SET status='FAILED',error=?,latency_ms=? WHERE id=?",
                       (str(exc), latency_ms, run_id))
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        latency_ms = int((perf_counter() - started) * 1000)
        with storage.connect() as db:
            db.execute("UPDATE agent_run SET status='FAILED',error=?,latency_ms=? WHERE id=?",
                       (str(exc), latency_ms, run_id))
        raise HTTPException(status_code=502, detail=f"Creative production provider failed: {exc}") from exc

    with storage.connect() as db:
        current = db.execute(
            "SELECT COALESCE(MAX(version_no),0) AS version_no FROM production_draft WHERE creative_id=?",
            (payload.creative_id,),
        ).fetchone()["version_no"]
        version_no = current + 1
        production_id = str(uuid.uuid4())
        production_json = output.model_dump()
        db.execute(
            "INSERT INTO production_draft(id,creative_id,version_no,model_name,production_json,status) VALUES(?,?,?,?,?,?)",
            (production_id, payload.creative_id, version_no, model_name,
             json.dumps(production_json, ensure_ascii=False), "DRAFT_REQUIRES_REVIEW"),
        )
        latency_ms = int((perf_counter() - started) * 1000)
        output_refs = {"production_draft_id": production_id, "creative_id": payload.creative_id, "version_no": version_no}
        db.execute(
            "UPDATE agent_run SET status='SUCCEEDED',model_name=?,output_refs_json=?,latency_ms=? WHERE id=?",
            (model_name, json.dumps(output_refs), latency_ms, run_id),
        )
        storage.audit(db, creative["workspace_id"], "COMPLETE", "AGENT", run_id, output_refs)

    return {
        "run_id": run_id, "production_draft_id": production_id, "version_no": version_no,
        "agent_name": "creative_production", "status": "SUCCEEDED", "model": model_name,
        "latency_ms": latency_ms, "production": production_json,
        "limitations": [
            "This output is a script/storyboard/prompt brief, not a rendered image or video.",
            "All objective product claims must be supported and human-reviewed.",
            "No ad is published and no budget is spent."
        ]
    }


@app.get("/v1/creatives/{creative_id}/production-drafts")
def list_production_drafts(creative_id: str):
    with storage.connect() as db:
        if not db.execute("SELECT 1 FROM creative WHERE id=?", (creative_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Creative not found")
        rows = db.execute("SELECT * FROM production_draft WHERE creative_id=? ORDER BY version_no DESC", (creative_id,))
        results = []
        for row in rows:
            result = dict(row)
            result["production"] = json.loads(result.pop("production_json"))
            results.append(result)
        return results


@app.get("/v1/demo/experiment/compare")
def compare_demo_creative_families(
    control_family: str = "C-A",
    treatment_family: str = "C-B",
    metric: Literal["CTR", "CVR"] = "CTR",
    mde_absolute: float | None = None,
):
    """Compare two synthetic creative families using a two-proportion test."""
    if control_family == treatment_family:
        raise HTTPException(status_code=422, detail="Control and treatment families must differ")
    if not control_family.startswith("C-") or not treatment_family.startswith("C-"):
        raise HTTPException(status_code=422, detail="Creative family IDs must use the C-X format")
    dataset = Path(os.getenv("AI_ADS_DEMO_DATA_PATH", str(Path(__file__).resolve().parents[2] / "data" / "synthetic_daily_metrics.csv")))
    if not dataset.exists():
        raise HTTPException(status_code=503, detail="Demo dataset is not available")
    totals = {
        control_family: {"successes": 0, "trials": 0, "rows": 0},
        treatment_family: {"successes": 0, "trials": 0, "rows": 0},
    }
    try:
        with dataset.open("r", encoding="utf-8-sig", newline="") as handle:
            for row in csv.DictReader(handle):
                creative_id = row.get("creative_id", "")
                family = "-".join(creative_id.split("-")[:2])
                if family not in totals:
                    continue
                if row.get("data_mode", "").upper() != "SIMULATED":
                    raise ValueError("Demo comparison only accepts SIMULATED records")
                if metric == "CTR":
                    successes, trials = int(row["clicks"]), int(row["impressions"])
                else:
                    successes, trials = int(row["purchases"]), int(row["clicks"])
                totals[family]["successes"] += successes
                totals[family]["trials"] += trials
                totals[family]["rows"] += 1
        if not totals[control_family]["rows"] or not totals[treatment_family]["rows"]:
            raise ValueError("No matching creative family rows found")
        result = compare_proportions(
            control_successes=totals[control_family]["successes"],
            control_trials=totals[control_family]["trials"],
            treatment_successes=totals[treatment_family]["successes"],
            treatment_trials=totals[treatment_family]["trials"],
            mde_absolute=mde_absolute,
        )
        return {
            "data_mode": "SIMULATED",
            "experiment_id": "EXP-US-BEAUTY-001",
            "metric": metric,
            "control_family": control_family,
            "treatment_family": treatment_family,
            "control_rows": totals[control_family]["rows"],
            "treatment_rows": totals[treatment_family]["rows"],
            "analysis": result,
            "decision_note": "This is a statistical workflow demonstration on synthetic aggregate records, not a valid real-world randomized experiment or evidence of causal lift.",
        }
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/v1/demo/data-quality")
def demo_data_quality():
    """Run deterministic row-level and event-funnel checks over the bundled demo CSV."""
    dataset = Path(os.getenv("AI_ADS_DEMO_DATA_PATH", str(Path(__file__).resolve().parents[2] / "data" / "synthetic_daily_metrics.csv")))
    if not dataset.exists():
        raise HTTPException(status_code=503, detail="Demo dataset is not available")
    required = [
        "date", "experiment_id", "creative_id", "data_mode", "impressions",
        "video_2s_views", "video_6s_views", "clicks", "landing_page_views",
        "add_to_cart", "checkout_starts", "purchases", "orders_refunded",
        "spend_usd", "attributed_revenue_usd",
    ]
    checks = {
        "duplicate_grain": 0, "clicks_exceed_impressions": 0,
        "landing_views_exceed_clicks": 0, "add_to_cart_exceed_landing_views": 0,
        "checkout_exceed_add_to_cart": 0, "purchases_exceed_checkouts": 0,
        "refunds_exceed_purchases": 0, "two_second_views_exceed_impressions": 0,
        "six_second_views_exceed_two_second_views": 0, "invalid_numeric_rows": 0,
        "non_simulated_rows": 0, "missing_required_fields": 0,
    }
    seen = set()
    row_count = 0
    modes: dict[str, int] = {}
    try:
        with dataset.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            headers = set(reader.fieldnames or [])
            missing_headers = sorted(set(required) - headers)
            if missing_headers:
                raise ValueError(f"Missing required columns: {missing_headers}")
            for row in reader:
                row_count += 1
                if any(row.get(field) in (None, "") for field in required):
                    checks["missing_required_fields"] += 1
                    continue
                mode = row["data_mode"].upper()
                modes[mode] = modes.get(mode, 0) + 1
                if mode != "SIMULATED":
                    checks["non_simulated_rows"] += 1
                key = (row["date"], row["experiment_id"], row["creative_id"])
                if key in seen:
                    checks["duplicate_grain"] += 1
                seen.add(key)
                try:
                    v = {field: float(row[field]) for field in required[4:]}
                    if any(value < 0 for value in v.values()) or not all(isfinite(value) for value in v.values()):
                        raise ValueError("Negative or non-finite metric")
                    comparisons = [
                        ("clicks", "impressions", "clicks_exceed_impressions"),
                        ("landing_page_views", "clicks", "landing_views_exceed_clicks"),
                        ("add_to_cart", "landing_page_views", "add_to_cart_exceed_landing_views"),
                        ("checkout_starts", "add_to_cart", "checkout_exceed_add_to_cart"),
                        ("purchases", "checkout_starts", "purchases_exceed_checkouts"),
                        ("orders_refunded", "purchases", "refunds_exceed_purchases"),
                        ("video_2s_views", "impressions", "two_second_views_exceed_impressions"),
                        ("video_6s_views", "video_2s_views", "six_second_views_exceed_two_second_views"),
                    ]
                    for left, right, check_name in comparisons:
                        if v[left] > v[right]:
                            checks[check_name] += 1
                except (ValueError, TypeError):
                    checks["invalid_numeric_rows"] += 1
        total_issues = sum(checks.values())
        return {
            "data_mode": "SIMULATED",
            "source": "bundled_synthetic_dataset",
            "row_count": row_count,
            "unique_grain_count": len(seen),
            "data_mode_counts": modes,
            "checks": checks,
            "issue_count": total_issues,
            "status": "PASS" if total_issues == 0 else "REVIEW_REQUIRED",
            "grain": "date × experiment_id × creative_id",
            "limitations": [
                "Passing deterministic schema and funnel checks does not prove the source data is authentic.",
                "The dataset is synthetic and does not represent an actual ad platform export.",
                "Attribution, deduplication across devices, timezone and event quality require source-specific validation for REAL data.",
            ],
        }
    except (OSError, csv.Error, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


# Creative Production Studio — generated media library
def _media_asset_dict(row):
    result = dict(row)
    try:
        result["metadata"] = json.loads(result.pop("metadata_json") or "{}")
    except (TypeError, json.JSONDecodeError):
        result["metadata"] = {}
    return result


@app.get("/v1/creatives/{creative_id}/media-assets")
def list_media_assets(creative_id: str):
    with storage.connect() as db:
        if not db.execute("SELECT 1 FROM creative WHERE id=?", (creative_id,)).fetchone():
            raise HTTPException(status_code=404, detail="Creative not found")
        rows = db.execute("SELECT * FROM media_asset WHERE creative_id=? ORDER BY created_at DESC", (creative_id,))
        return [_media_asset_dict(row) for row in rows]


@app.get("/v1/media-assets/{asset_id}")
def get_media_asset(asset_id: str):
    with storage.connect() as db:
        row = db.execute("SELECT * FROM media_asset WHERE id=?", (asset_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Media asset not found")
        return _media_asset_dict(row)


@app.post("/v1/media-assets/generate-image", status_code=201)
async def create_generated_image(payload: ImageGenerationRequest):
    with storage.connect() as db:
        creative = db.execute("SELECT workspace_id FROM creative WHERE id=?", (payload.creative_id,)).fetchone()
        if not creative:
            raise HTTPException(status_code=404, detail="Creative not found")
        workspace_id = creative["workspace_id"]
    try:
        generated = await media.generate_image(payload.prompt, payload.size, payload.quality)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Image provider failed: {exc}") from exc

    asset_id = str(uuid.uuid4())
    filename = generated["asset_uri"].rsplit("/", 1)[-1]
    with storage.connect() as db:
        db.execute(
            """INSERT INTO media_asset
            (id,workspace_id,creative_id,asset_type,provider,model_name,prompt_text,asset_uri,
             local_filename,content_type,byte_size,status,variation_group,metadata_json)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (asset_id, workspace_id, payload.creative_id, "IMAGE", generated["provider"],
             generated["model"], payload.prompt, generated["asset_uri"], filename,
             generated["content_type"], generated["bytes"], "GENERATED",
             payload.variation_group, json.dumps({"size":payload.size,"quality":payload.quality})),
        )
        storage.audit(db, workspace_id, "GENERATE_IMAGE", "MEDIA_ASSET", asset_id,
                      {"provider":generated["provider"],"model":generated["model"]})
        row = db.execute("SELECT * FROM media_asset WHERE id=?", (asset_id,)).fetchone()
        return _media_asset_dict(row)


@app.post("/v1/media-assets/generate-video", status_code=202)
async def create_generated_video(payload: VideoGenerationRequest):
    with storage.connect() as db:
        creative = db.execute("SELECT workspace_id FROM creative WHERE id=?", (payload.creative_id,)).fetchone()
        if not creative:
            raise HTTPException(status_code=404, detail="Creative not found")
        workspace_id = creative["workspace_id"]
    try:
        job = await media.start_video(payload.prompt, payload.aspect_ratio, payload.duration_sec)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Video provider failed: {exc}") from exc
    asset_id = str(uuid.uuid4())
    with storage.connect() as db:
        db.execute(
            """INSERT INTO media_asset
            (id,workspace_id,creative_id,asset_type,provider,model_name,prompt_text,status,metadata_json)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (asset_id, workspace_id, payload.creative_id, "VIDEO", job["provider"], job["model"],
             payload.prompt, "GENERATING", json.dumps({"prediction_id":job["prediction_id"],"aspect_ratio":payload.aspect_ratio,"duration_sec":payload.duration_sec})),
        )
        storage.audit(db, workspace_id, "START_VIDEO_GENERATION", "MEDIA_ASSET", asset_id,
                      {"prediction_id":job["prediction_id"],"model":job["model"]})
        row = db.execute("SELECT * FROM media_asset WHERE id=?", (asset_id,)).fetchone()
        return {**_media_asset_dict(row), "provider_status":job["status"]}


@app.post("/v1/media-assets/{asset_id}/refresh")
async def refresh_video_asset(asset_id: str):
    with storage.connect() as db:
        row = db.execute("SELECT * FROM media_asset WHERE id=?", (asset_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Media asset not found")
        asset = _media_asset_dict(row)
        if asset["asset_type"] != "VIDEO":
            raise HTTPException(status_code=422, detail="Only video generation jobs can be refreshed")
        prediction_id = asset["metadata"].get("prediction_id")
    if not prediction_id:
        raise HTTPException(status_code=422, detail="Video prediction ID is missing")
    try:
        result = await media.poll_video(prediction_id)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Video status check failed: {exc}") from exc
    with storage.connect() as db:
        if result["status"] == "succeeded" and result.get("asset_uri"):
            filename = result["asset_uri"].rsplit("/", 1)[-1]
            db.execute(
                "UPDATE media_asset SET asset_uri=?,local_filename=?,content_type='video/mp4',status='GENERATED' WHERE id=?",
                (result["asset_uri"], filename, asset_id),
            )
        elif result["status"] in {"failed", "canceled"}:
            db.execute("UPDATE media_asset SET status='FAILED' WHERE id=?", (asset_id,))
        current = db.execute("SELECT * FROM media_asset WHERE id=?", (asset_id,)).fetchone()
        return {**_media_asset_dict(current), "provider_status":result["status"], "provider_error":result.get("error")}


@app.post("/v1/media-assets/upload", status_code=201)
async def upload_media_asset(
    creative_id: str = Form(...),
    file: UploadFile = File(...),
    label: str = Form(""),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="A filename is required")
    content_type = (file.content_type or "").lower()
    if content_type not in {"image/png","image/jpeg","image/webp","video/mp4","video/webm"}:
        raise HTTPException(status_code=415, detail="Only PNG, JPEG, WebP, MP4 and WebM files are supported")
    raw = await file.read()
    if len(raw) > 100 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Maximum upload size is 100 MB")
    with storage.connect() as db:
        creative = db.execute("SELECT workspace_id FROM creative WHERE id=?", (creative_id,)).fetchone()
        if not creative:
            raise HTTPException(status_code=404, detail="Creative not found")
        workspace_id = creative["workspace_id"]
    ext = media._safe_ext(content_type)
    filename = f"upload-{uuid.uuid4()}{ext}"
    media.MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    (media.MEDIA_ROOT / filename).write_bytes(raw)
    asset_id = str(uuid.uuid4())
    asset_type = "IMAGE" if content_type.startswith("image/") else "VIDEO"
    uri = f"{media.PUBLIC_BASE}/media/{filename}"
    with storage.connect() as db:
        db.execute(
            """INSERT INTO media_asset
            (id,workspace_id,creative_id,asset_type,provider,model_name,prompt_text,asset_uri,
             local_filename,content_type,byte_size,status,label)
            VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (asset_id,workspace_id,creative_id,asset_type,"USER_UPLOAD",None,"User uploaded asset",
             uri,filename,content_type,len(raw),"UPLOADED",label or file.filename),
        )
        storage.audit(db,workspace_id,"UPLOAD_MEDIA","MEDIA_ASSET",asset_id,{"filename":file.filename,"bytes":len(raw)})
        return _media_asset_dict(db.execute("SELECT * FROM media_asset WHERE id=?",(asset_id,)).fetchone())


@app.patch("/v1/media-assets/{asset_id}")
def update_media_asset(asset_id: str, payload: AssetMetadataUpdate):
    with storage.connect() as db:
        row = db.execute("SELECT * FROM media_asset WHERE id=?", (asset_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Media asset not found")
        db.execute("UPDATE media_asset SET label=COALESCE(?,label), notes=COALESCE(?,notes) WHERE id=?",
                   (payload.label,payload.notes,asset_id))
        return _media_asset_dict(db.execute("SELECT * FROM media_asset WHERE id=?",(asset_id,)).fetchone())


@app.post("/v1/media-assets/{asset_id}/review", status_code=201)
def review_generated_media(asset_id: str, payload: AssetReviewCreate):
    review_id = str(uuid.uuid4())
    with storage.connect() as db:
        asset = db.execute("SELECT * FROM media_asset WHERE id=?",(asset_id,)).fetchone()
        if not asset:
            raise HTTPException(status_code=404,detail="Media asset not found")
        if asset["status"] in {"GENERATING","FAILED"}:
            raise HTTPException(status_code=422,detail="Only completed media assets can be reviewed")
        db.execute("INSERT INTO media_review(id,media_asset_id,reviewer_id,decision,reason) VALUES(?,?,?,?,?)",
                   (review_id,asset_id,payload.reviewer_id,payload.decision,payload.reason))
        db.execute("UPDATE media_asset SET status=? WHERE id=?",(payload.decision,asset_id))
        storage.audit(db,asset["workspace_id"],"REVIEW_MEDIA","MEDIA_ASSET",asset_id,
                      {"reviewer_id":payload.reviewer_id,"decision":payload.decision})
        return dict(db.execute("SELECT * FROM media_review WHERE id=?",(review_id,)).fetchone())


@app.get("/v1/media-assets/{asset_id}/reviews")
def list_media_reviews(asset_id: str):
    with storage.connect() as db:
        if not db.execute("SELECT 1 FROM media_asset WHERE id=?",(asset_id,)).fetchone():
            raise HTTPException(status_code=404,detail="Media asset not found")
        return [dict(row) for row in db.execute("SELECT * FROM media_review WHERE media_asset_id=? ORDER BY created_at DESC",(asset_id,))]


@app.post("/v1/media-assets/export")
def export_media_assets(asset_ids: list[str]):
    if not asset_ids or len(asset_ids) > 100:
        raise HTTPException(status_code=422,detail="Select between 1 and 100 assets to export")
    buffer = BytesIO()
    missing = []
    with storage.connect() as db:
        placeholders = ",".join("?" for _ in asset_ids)
        rows = db.execute(f"SELECT * FROM media_asset WHERE id IN ({placeholders})",asset_ids).fetchall()
    if len(rows) != len(set(asset_ids)):
        raise HTTPException(status_code=404,detail="One or more selected assets do not exist")
    with zipfile.ZipFile(buffer,"w",zipfile.ZIP_DEFLATED) as archive:
        manifest=[]
        for row in rows:
            asset=dict(row)
            filename=asset.get("local_filename")
            path=media.MEDIA_ROOT / filename if filename else None
            if not path or not path.is_file():
                missing.append(asset["id"])
                continue
            safe_name=re.sub(r"[^A-Za-z0-9._-]+","_",asset.get("label") or path.name)
            if "." not in safe_name:
                safe_name=path.stem+path.suffix
            archive.write(path,f"assets/{safe_name}")
            manifest.append({
                "asset_id":asset["id"],"creative_id":asset["creative_id"],"asset_type":asset["asset_type"],
                "provider":asset["provider"],"model":asset["model_name"],"prompt":asset["prompt_text"],
                "asset_uri":asset["asset_uri"],"status":asset["status"],"content_type":asset["content_type"],
                "byte_size":asset["byte_size"],"created_at":asset["created_at"]
            })
        if not manifest:
            raise HTTPException(status_code=404,detail="No selected asset files are available on this server")
        archive.writestr("manifest.json",json.dumps({"assets":manifest,"missing_asset_ids":missing},ensure_ascii=False,indent=2))
    buffer.seek(0)
    return StreamingResponse(buffer,media_type="application/zip",headers={"Content-Disposition":"attachment; filename=creative-assets-export.zip"})
