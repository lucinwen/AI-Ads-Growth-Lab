from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DEFAULT_DB = Path(__file__).resolve().parents[1] / "growthlab.sqlite3"
DB_PATH = Path(os.getenv("AI_ADS_DB_PATH", str(DEFAULT_DB)))


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS workspace (
          id TEXT PRIMARY KEY, name TEXT NOT NULL, market TEXT NOT NULL DEFAULT 'US',
          vertical TEXT NOT NULL DEFAULT 'beauty_skincare',
          data_mode TEXT NOT NULL CHECK(data_mode IN ('SIMULATED','REAL')),
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS product (
          id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
          name TEXT NOT NULL, category TEXT NOT NULL, currency TEXT NOT NULL DEFAULT 'USD',
          price_cents INTEGER, facts_json TEXT NOT NULL DEFAULT '{}', landing_page_url TEXT,
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS claim (
          id TEXT PRIMARY KEY, product_id TEXT NOT NULL REFERENCES product(id) ON DELETE CASCADE,
          claim_text TEXT NOT NULL, claim_type TEXT NOT NULL,
          status TEXT NOT NULL CHECK(status IN ('VERIFIED','UNVERIFIED','PROHIBITED','NEEDS_REVIEW')),
          evidence_refs_json TEXT NOT NULL DEFAULT '[]', risk_level TEXT NOT NULL DEFAULT 'MEDIUM',
          notes TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS creative (
          id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
          product_id TEXT NOT NULL REFERENCES product(id) ON DELETE CASCADE,
          concept_name TEXT NOT NULL, angle TEXT, hook TEXT, narrative TEXT, cta TEXT,
          language TEXT NOT NULL DEFAULT 'en-US', format TEXT, hypothesis TEXT,
          claims_used_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS asset_version (
          id TEXT PRIMARY KEY, creative_id TEXT NOT NULL REFERENCES creative(id) ON DELETE CASCADE,
          version_no INTEGER NOT NULL, asset_type TEXT NOT NULL, asset_uri TEXT,
          prompt_text TEXT, model_name TEXT, file_hash TEXT,
          approval_status TEXT NOT NULL DEFAULT 'PENDING'
            CHECK(approval_status IN ('PENDING','APPROVED','REJECTED','NEEDS_CHANGES','BLOCKED')),
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
          UNIQUE(creative_id, version_no)
        );
        CREATE TABLE IF NOT EXISTS experiment (
          id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
          name TEXT NOT NULL, hypothesis TEXT NOT NULL, channel TEXT NOT NULL,
          data_mode TEXT NOT NULL CHECK(data_mode IN ('SIMULATED','REAL')),
          status TEXT NOT NULL DEFAULT 'DRAFT',
          attribution_window TEXT, timezone TEXT NOT NULL DEFAULT 'America/Los_Angeles',
          budget_cap_cents INTEGER, currency TEXT NOT NULL DEFAULT 'USD',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS experiment_variant (
          id TEXT PRIMARY KEY, experiment_id TEXT NOT NULL REFERENCES experiment(id) ON DELETE CASCADE,
          creative_id TEXT NOT NULL REFERENCES creative(id) ON DELETE CASCADE,
          allocation_pct REAL NOT NULL CHECK(allocation_pct > 0 AND allocation_pct <= 100),
          role TEXT NOT NULL DEFAULT 'TREATMENT',
          UNIQUE(experiment_id, creative_id)
        );
        CREATE TABLE IF NOT EXISTS review_record (
          id TEXT PRIMARY KEY, asset_version_id TEXT NOT NULL REFERENCES asset_version(id) ON DELETE CASCADE,
          reviewer_id TEXT NOT NULL, decision TEXT NOT NULL
            CHECK(decision IN ('APPROVED','REJECTED','NEEDS_CHANGES','BLOCKED')),
          reason TEXT, findings_json TEXT NOT NULL DEFAULT '[]',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS agent_run (
          id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
          agent_name TEXT NOT NULL, status TEXT NOT NULL, model_name TEXT,
          input_refs_json TEXT NOT NULL DEFAULT '{}', output_refs_json TEXT NOT NULL DEFAULT '{}',
          error TEXT, latency_ms INTEGER, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS audit_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT, workspace_id TEXT NOT NULL REFERENCES workspace(id) ON DELETE CASCADE,
          actor_type TEXT NOT NULL, actor_id TEXT, action TEXT NOT NULL,
          entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
          details_json TEXT NOT NULL DEFAULT '{}',
          created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_product_workspace ON product(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_creative_workspace ON creative(workspace_id);
        CREATE INDEX IF NOT EXISTS idx_experiment_workspace ON experiment(workspace_id);
        """)
        creative_columns = {row["name"] for row in db.execute("PRAGMA table_info(creative)")}
        if "claims_used_json" not in creative_columns:
            db.execute("ALTER TABLE creative ADD COLUMN claims_used_json TEXT NOT NULL DEFAULT '[]'")


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for key in ("facts_json", "evidence_refs_json", "details_json", "claims_used_json"):
        if key in result and result[key] is not None:
            result[key.removesuffix("_json")] = json.loads(result.pop(key))
    return result


def audit(db: sqlite3.Connection, workspace_id: str, action: str, entity_type: str, entity_id: str, details: dict | None = None) -> None:
    db.execute(
        "INSERT INTO audit_log(workspace_id,actor_type,actor_id,action,entity_type,entity_id,details_json) VALUES(?,?,?,?,?,?,?)",
        (workspace_id, "USER", "local-owner", action, entity_type, entity_id, json.dumps(details or {}, ensure_ascii=False)),
    )


def seed_demo_workspace() -> tuple[str, str]:
    """Create an idempotent fictional demo workspace and its starter creative hypotheses."""
    workspace_id = "demo-us-beauty-workspace"
    product_id = "demo-luma-dew-moisturizer"
    with connect() as db:
        db.execute(
            "INSERT OR IGNORE INTO workspace(id,name,market,vertical,data_mode) VALUES(?,?,?,?,?)",
            (workspace_id, "Luma Dew / US Beauty Demo", "US", "beauty_skincare", "SIMULATED"),
        )
        db.execute(
            "INSERT OR IGNORE INTO product(id,workspace_id,name,category,currency,price_cents,facts_json,landing_page_url) VALUES(?,?,?,?,?,?,?,?)",
            (product_id, workspace_id, "Daily Barrier Moisturizer", "moisturizer", "USD", 2800,
             json.dumps({"brand":"Luma Dew","fictional":True,"approved_claims":[]}, ensure_ascii=False), None),
        )
        starter = [
            ("demo-creative-routine", "Everyday ritual", "Routine / everyday", "A simple step in my morning routine.", "Routine framing may make the product feel relevant to daily use.", "UGC vertical video · 20s"),
            ("demo-creative-texture", "Texture study", "Texture / sensory", "A closer look at the texture.", "A close-up product demonstration may increase qualified curiosity.", "Product demo · 15s"),
            ("demo-creative-education", "Ingredient education", "Product education", "What is in my daily moisturizer?", "Fact-based education may improve product understanding.", "Explainer · 25s"),
            ("demo-creative-creator", "Creator walkthrough", "Creator-style", "Here is how the product fits into my routine.", "Creator-style delivery may improve attention and comprehension.", "Creator-style · 20s"),
        ]
        for creative_id, name, angle, hook, hypothesis, fmt in starter:
            db.execute(
                "INSERT OR IGNORE INTO creative(id,workspace_id,product_id,concept_name,angle,hook,hypothesis,format,language) VALUES(?,?,?,?,?,?,?,?,?)",
                (creative_id, workspace_id, product_id, name, angle, hook, hypothesis, fmt, "en-US"),
            )
        return workspace_id, product_id
