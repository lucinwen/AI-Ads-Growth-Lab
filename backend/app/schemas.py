from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkspaceCreate(StrictModel):
    name: str = Field(min_length=2, max_length=100)
    market: str = Field(default="US", min_length=2, max_length=2)
    vertical: str = Field(default="beauty_skincare", max_length=60)
    data_mode: Literal["SIMULATED", "REAL"] = "SIMULATED"


class ProductCreate(StrictModel):
    workspace_id: str
    name: str = Field(min_length=2, max_length=160)
    category: str = Field(min_length=2, max_length=80)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    price_cents: int | None = Field(default=None, ge=0)
    facts: dict = Field(default_factory=dict)
    landing_page_url: str | None = None


class ClaimCreate(StrictModel):
    product_id: str
    claim_text: str = Field(min_length=3, max_length=500)
    claim_type: str = Field(min_length=2, max_length=80)
    status: Literal["VERIFIED", "UNVERIFIED", "PROHIBITED", "NEEDS_REVIEW"] = "UNVERIFIED"
    evidence_refs: list[str] = Field(default_factory=list)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "MEDIUM"
    notes: str | None = None


class CreativeCreate(StrictModel):
    workspace_id: str
    product_id: str
    concept_name: str = Field(min_length=2, max_length=120)
    angle: str | None = None
    hook: str | None = None
    narrative: str | None = None
    cta: str | None = None
    language: str = "en-US"
    format: str | None = None
    hypothesis: str | None = None


class AssetVersionCreate(StrictModel):
    creative_id: str
    asset_type: Literal["IMAGE", "VIDEO", "AUDIO", "SCRIPT", "STORYBOARD", "OTHER"]
    asset_uri: str | None = None
    prompt_text: str | None = None
    model_name: str | None = None
    file_hash: str | None = None
    approval_status: Literal["PENDING", "APPROVED", "REJECTED", "NEEDS_CHANGES", "BLOCKED"] = "PENDING"


class ExperimentCreate(StrictModel):
    workspace_id: str
    name: str = Field(min_length=2, max_length=160)
    hypothesis: str = Field(min_length=10, max_length=1000)
    channel: str = Field(min_length=2, max_length=60)
    data_mode: Literal["SIMULATED", "REAL"]
    attribution_window: str | None = None
    timezone: str = "America/Los_Angeles"
    budget_cap_cents: int | None = Field(default=None, ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)


class VariantCreate(StrictModel):
    creative_id: str
    allocation_pct: float = Field(gt=0, le=100)
    role: Literal["CONTROL", "TREATMENT"] = "TREATMENT"
