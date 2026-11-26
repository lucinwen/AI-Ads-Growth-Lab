from __future__ import annotations

import base64
import os
import re
import uuid
from pathlib import Path
from typing import Any

import httpx

MEDIA_ROOT = Path(os.getenv("AI_ADS_MEDIA_PATH", str(Path(__file__).resolve().parents[2] / "media")))
PUBLIC_BASE = os.getenv("AI_ADS_PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")


def _safe_ext(content_type: str, fallback: str = ".bin") -> str:
    return {
        "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
        "video/mp4": ".mp4", "video/webm": ".webm", "audio/mpeg": ".mp3",
    }.get(content_type.split(";")[0].lower(), fallback)


def _save_bytes(data: bytes, content_type: str, prefix: str) -> tuple[str, str]:
    MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
    asset_id = str(uuid.uuid4())
    ext = _safe_ext(content_type)
    filename = f"{prefix}-{asset_id}{ext}"
    path = MEDIA_ROOT / filename
    path.write_bytes(data)
    return asset_id, f"{PUBLIC_BASE}/media/{filename}"


async def generate_image(prompt: str, size: str = "1024x1536", quality: str = "high") -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for real image generation.")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-1")
    async with httpx.AsyncClient(timeout=180.0) as client:
        response = await client.post(
            f"{base_url}/images/generations",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"model": model, "prompt": prompt, "size": size, "quality": quality, "n": 1},
        )
        response.raise_for_status()
        payload = response.json()
    item = payload["data"][0]
    if item.get("b64_json"):
        raw = base64.b64decode(item["b64_json"])
        content_type = "image/png"
    elif item.get("url"):
        async with httpx.AsyncClient(timeout=90.0, follow_redirects=True) as client:
            download = await client.get(item["url"])
            download.raise_for_status()
            raw = download.content
            content_type = download.headers.get("content-type", "image/png")
    else:
        raise RuntimeError("Image provider returned no downloadable image payload.")
    asset_id, uri = _save_bytes(raw, content_type, "image")
    return {"provider": "openai-compatible-images", "model": model, "asset_id": asset_id,
            "asset_uri": uri, "content_type": content_type, "bytes": len(raw)}


async def start_video(prompt: str, aspect_ratio: str = "9:16", duration: int = 5) -> dict[str, Any]:
    token = os.getenv("REPLICATE_API_TOKEN")
    model = os.getenv("REPLICATE_MODEL")
    if not token or not model or "/" not in model:
        raise RuntimeError("Set REPLICATE_API_TOKEN and REPLICATE_MODEL=owner/model to enable video generation.")
    owner, name = model.split("/", 1)
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"https://api.replicate.com/v1/models/{owner}/{name}/predictions",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json", "Prefer": "wait=1"},
            json={"input": {"prompt": prompt, "aspect_ratio": aspect_ratio, "duration": duration}},
        )
        response.raise_for_status()
        result = response.json()
    return {"provider": "replicate", "model": model, "prediction_id": result["id"],
            "status": result.get("status", "starting"), "output": result.get("output"),
            "poll_url": result.get("urls", {}).get("get")}


async def poll_video(prediction_id: str) -> dict[str, Any]:
    token = os.getenv("REPLICATE_API_TOKEN")
    if not token:
        raise RuntimeError("REPLICATE_API_TOKEN is not configured.")
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.get(
            f"https://api.replicate.com/v1/predictions/{prediction_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        result = response.json()
    output = result.get("output")
    media_url = output[0] if isinstance(output, list) and output else output if isinstance(output, str) else None
    local_uri = None
    if result.get("status") == "succeeded" and media_url:
        async with httpx.AsyncClient(timeout=180.0, follow_redirects=True) as client:
            download = await client.get(media_url)
            download.raise_for_status()
        _, local_uri = _save_bytes(download.content, download.headers.get("content-type", "video/mp4"), "video")
    return {"prediction_id": prediction_id, "status": result.get("status"),
            "error": result.get("error"), "output_url": media_url, "asset_uri": local_uri}
