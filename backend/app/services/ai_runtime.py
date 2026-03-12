from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.core.config import settings
from app.core.database import db
from app.core.schema_versions import SETTINGS_SCHEMA_VERSION

AI_RUNTIME_SETTINGS_KEY = "ai_runtime_config"
AI_EVALUATION_PROMPT_VERSION = "submission-eval-v1"
AI_CHAT_PROMPT_VERSION = "teacher-chat-v1"
AI_SIMILARITY_ENGINE_VERSION = "tfidf-cosine-v1"


def _default_runtime_settings() -> dict[str, Any]:
    provider_enabled = True
    openai_configured = bool(settings.openai_api_key)
    effective_provider_enabled = provider_enabled and openai_configured
    return {
        "provider_enabled": provider_enabled,
        "openai_model": settings.openai_model,
        "openai_timeout_seconds": settings.openai_timeout_seconds,
        "openai_max_output_tokens": settings.openai_max_output_tokens,
        "similarity_threshold": settings.similarity_threshold,
        "openai_configured": openai_configured,
        "effective_provider_enabled": effective_provider_enabled,
    }


def _normalize_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off"}:
            return False
    return fallback


def normalize_runtime_overrides(payload: dict[str, Any] | None) -> dict[str, Any]:
    defaults = _default_runtime_settings()
    payload = payload or {}
    return {
        "provider_enabled": _normalize_bool(payload.get("provider_enabled"), True),
        "openai_model": str(payload.get("openai_model") or defaults["openai_model"]).strip()[:120],
        "openai_timeout_seconds": max(5, min(int(payload.get("openai_timeout_seconds") or defaults["openai_timeout_seconds"]), 120)),
        "openai_max_output_tokens": max(50, min(int(payload.get("openai_max_output_tokens") or defaults["openai_max_output_tokens"]), 4000)),
        "similarity_threshold": max(0.0, min(float(payload.get("similarity_threshold") or defaults["similarity_threshold"]), 1.0)),
    }


async def get_ai_runtime_settings() -> dict[str, Any]:
    defaults = _default_runtime_settings()
    record = await db.settings.find_one({"key": AI_RUNTIME_SETTINGS_KEY})
    overrides = normalize_runtime_overrides(record.get("value") if record else {})
    merged = {**defaults, **overrides}
    merged["openai_configured"] = defaults["openai_configured"]
    merged["effective_provider_enabled"] = bool(merged["provider_enabled"] and defaults["openai_configured"])
    return merged


async def save_ai_runtime_settings(payload: dict[str, Any], *, actor_user_id: str | None = None) -> dict[str, Any]:
    normalized = normalize_runtime_overrides(payload)
    await db.settings.update_one(
        {"key": AI_RUNTIME_SETTINGS_KEY},
        {
            "$set": {
                "key": AI_RUNTIME_SETTINGS_KEY,
                "value": normalized,
                "updated_by_user_id": actor_user_id,
                "schema_version": SETTINGS_SCHEMA_VERSION,
            }
        },
        upsert=True,
    )
    return await get_ai_runtime_settings()


def build_runtime_snapshot(runtime_settings: dict[str, Any] | None) -> dict[str, Any]:
    settings_map = runtime_settings or _default_runtime_settings()
    return {
        "provider_enabled": bool(settings_map.get("provider_enabled")),
        "effective_provider_enabled": bool(settings_map.get("effective_provider_enabled")),
        "openai_model": settings_map.get("openai_model"),
        "openai_timeout_seconds": settings_map.get("openai_timeout_seconds"),
        "openai_max_output_tokens": settings_map.get("openai_max_output_tokens"),
        "similarity_threshold": settings_map.get("similarity_threshold"),
    }


def clone_runtime_snapshot(runtime_settings: dict[str, Any] | None) -> dict[str, Any]:
    return deepcopy(build_runtime_snapshot(runtime_settings))
