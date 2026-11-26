from __future__ import annotations

import json
import os
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError


class CreativeConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concept_name: str = Field(min_length=2, max_length=120)
    angle: str = Field(min_length=2, max_length=160)
    hook: str = Field(min_length=3, max_length=240)
    narrative: str = Field(min_length=10, max_length=1200)
    cta: str = Field(min_length=2, max_length=160)
    hypothesis: str = Field(min_length=10, max_length=600)
    format: str = Field(min_length=2, max_length=120)
    claims_used: list[str] = Field(default_factory=list)


class StrategyOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    concepts: list[CreativeConcept]


def _extract_json(content: str) -> dict[str, Any]:
    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    return json.loads(text)


async def generate_creative_strategy(
    *,
    product: dict[str, Any],
    verified_claims: list[dict[str, Any]],
    audience_hypothesis: str,
    campaign_objective: str,
    concept_count: int,
    language: str,
) -> tuple[StrategyOutput, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured. Add it to the repository-root .env file; the key is never stored in the database.")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

    system_prompt = (
        "You are a senior performance creative strategist for US beauty advertising. "
        "Return only a valid JSON object matching {concepts:[{concept_name,angle,hook,narrative,cta,hypothesis,format,claims_used}]}. "
        "Create genuinely differentiated, testable concepts. Use only the supplied VERIFIED claim IDs. "
        "If no verified claims exist, claims_used must be empty and do not invent product benefits, ingredients, clinical results, testimonials, dermatologist endorsements, guarantees, or before/after outcomes. "
        "Do not claim a synthetic actor is a real customer. Keep all creative concepts suitable for human review, not auto-publishing."
    )
    user_payload = {
        "product": product,
        "verified_claims": verified_claims,
        "audience_hypothesis": audience_hypothesis,
        "campaign_objective": campaign_objective,
        "concept_count": concept_count,
        "language": language,
        "market": "United States",
        "vertical": "beauty_skincare",
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0.7,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()

    try:
        message = payload["choices"][0]["message"]["content"]
        output = StrategyOutput.model_validate(_extract_json(message))
    except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
        raise RuntimeError(f"Strategy model returned invalid structured output: {exc}") from exc

    if len(output.concepts) != concept_count:
        raise RuntimeError(f"Strategy model returned {len(output.concepts)} concepts; expected {concept_count}.")
    verified_ids = {str(item["id"]) for item in verified_claims}
    for concept in output.concepts:
        unknown = set(concept.claims_used) - verified_ids
        if unknown:
            raise RuntimeError(f"Strategy model referenced non-verified claim IDs: {sorted(unknown)}")
    return output, model


class ProductionScene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    scene_number: int = Field(ge=1, le=12)
    duration_sec: int = Field(ge=1, le=20)
    visual_description: str = Field(min_length=8, max_length=500)
    camera_direction: str = Field(min_length=3, max_length=240)
    on_screen_text: str = Field(max_length=180)
    voiceover: str = Field(max_length=400)
    asset_prompt: str = Field(min_length=8, max_length=800)
    claims_used: list[str] = Field(default_factory=list)


class ProductionOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=2, max_length=120)
    hook: str = Field(min_length=3, max_length=240)
    scenes: list[ProductionScene] = Field(min_length=3, max_length=12)
    caption: str = Field(max_length=500)
    cta: str = Field(min_length=2, max_length=160)
    production_notes: list[str] = Field(default_factory=list)


async def generate_production_brief(
    *,
    creative: dict[str, Any],
    product: dict[str, Any],
    verified_claims: list[dict[str, Any]],
    duration_sec: int,
    placement: str,
    language: str,
) -> tuple[ProductionOutput, str]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured. Add it to the repository-root .env file.")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
    system_prompt = (
        "You are a performance-ad video producer for US beauty brands. "
        "Return only valid JSON matching {title,hook,scenes:[{scene_number,duration_sec,visual_description,camera_direction,on_screen_text,voiceover,asset_prompt,claims_used}],caption,cta,production_notes}. "
        "Create a shootable/AI-producible storyboard with a clear opening hook, product demonstration, message, and CTA. "
        "Use only supplied VERIFIED claim IDs. If no verified claims exist, claims_used must be empty and do not invent product benefits, ingredients, clinical results, testimonials, endorsements, guarantees, or before/after outcomes. "
        "Do not imply synthetic actors are real customers. Keep captions and on-screen text consistent with product facts. This is a production brief, not a generated media asset."
    )
    user_payload = {
        "creative": creative, "product": product, "verified_claims": verified_claims,
        "duration_sec": duration_sec, "placement": placement, "language": language,
        "market": "United States", "vertical": "beauty_skincare"
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{base_url}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model, "temperature": 0.65,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)}
                ]
            }
        )
        response.raise_for_status()
        payload = response.json()
    try:
        message = payload["choices"][0]["message"]["content"]
        output = ProductionOutput.model_validate(_extract_json(message))
    except (KeyError, IndexError, TypeError, ValueError, ValidationError) as exc:
        raise RuntimeError(f"Production model returned invalid structured output: {exc}") from exc
    verified_ids = {str(item["id"]) for item in verified_claims}
    for scene in output.scenes:
        unknown = set(scene.claims_used) - verified_ids
        if unknown:
            raise RuntimeError(f"Production model referenced non-verified claim IDs: {sorted(unknown)}")
    if sum(scene.duration_sec for scene in output.scenes) > duration_sec + 3:
        raise RuntimeError("Storyboard scene durations exceed the requested video duration.")
    return output, model
