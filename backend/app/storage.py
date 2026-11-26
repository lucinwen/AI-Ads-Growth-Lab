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


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    result = dict(row)
    for key in ("facts_json", "evidence_refs_json", "details_json"):
        if key in result and result[key] is not None:
            result[key.removesuffix("_json")] = json.loads(result.pop(key))
    return result


def audit(db: sqlite3.Connection, workspace_id: str, action: str, entity_type: str, entity_id: str, details: dict | None = None) -> None:
    db.execute(
        "INSERT INTO audit_log(workspace_id,actor_type,actor_id,action,entity_type,entity_id,details_json) VALUES(?,?,?,?,?,?,?)",
        (workspace_id, "USER", "local-owner", action, entity_type, entity_id, json.dumps(details or {}, ensure_ascii=False)),
    )
