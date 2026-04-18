from __future__ import annotations

from copy import deepcopy
from datetime import datetime
from typing import Any

from app.core.config import settings
from app.core.database import db
from app.core.schema_versions import SETTINGS_SCHEMA_VERSION

AI_RUNTIME_SETTINGS_KEY = "ai_runtime_config"
AI_SEMANTIC_ROLLOUT_SETTINGS_KEY = "ai_semantic_rollout_config"
AI_SEMANTIC_ROLLOUT_HISTORY_KEY = "ai_semantic_rollout_config_history"
AI_EVALUATION_PROMPT_VERSION = "submission-eval-v1"
AI_CHAT_PROMPT_VERSION = "teacher-chat-v1"
AI_SIMILARITY_ENGINE_VERSION = "tfidf-cosine-v1"
_SEMANTIC_PROMOTION_STATES = {"blocked", "candidate", "approved_manual", "active_assist_only"}


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


def _default_semantic_rollout_settings() -> dict[str, Any]:
    return {
        "semantic_same_assignment_drift_threshold": float(settings.semantic_same_assignment_drift_threshold),
        "semantic_cross_assignment_drift_threshold": float(settings.semantic_cross_assignment_drift_threshold),
        "semantic_same_assignment_min_score": float(settings.semantic_same_assignment_min_score),
        "semantic_cross_assignment_min_score": float(settings.semantic_cross_assignment_min_score),
        "semantic_same_assignment_min_sample_size": int(settings.semantic_same_assignment_min_sample_size),
        "semantic_cross_assignment_min_sample_size": int(settings.semantic_cross_assignment_min_sample_size),
        "semantic_multilingual_min_sample_size": int(settings.semantic_multilingual_min_sample_size),
        "config_version": 0,
        "approved_snapshot_version_same_assignment": None,
        "approved_snapshot_version_cross_assignment": None,
        "active_snapshot_version_same_assignment": None,
        "active_snapshot_version_cross_assignment": None,
        "semantic_same_assignment_promotion_state": "blocked",
        "semantic_cross_assignment_promotion_state": "blocked",
        "last_change_reason": None,
        "last_change_actor_user_id": None,
        "last_change_at": None,
        "manual_promotion_guidance_only": True,
    }


def _default_semantic_rollout_history() -> dict[str, Any]:
    return {
        "last_version": 0,
        "items": [],
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


def _normalize_float(value: Any, fallback: float, *, minimum: float, maximum: float) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return max(minimum, min(numeric, maximum))


def _normalize_int(value: Any, fallback: int, *, minimum: int, maximum: int) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        numeric = fallback
    return max(minimum, min(numeric, maximum))


def _normalize_optional_int(value: Any, fallback: int | None = None) -> int | None:
    if value in {None, ""}:
        return fallback
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        return fallback
    return numeric if numeric >= 0 else fallback


def _normalize_short_text(value: Any, fallback: str | None = None, *, limit: int = 240) -> str | None:
    if value is None:
        return fallback
    normalized = str(value).strip()
    if not normalized:
        return fallback
    return normalized[:limit]


def _normalize_datetime(value: Any, fallback: Any = None) -> Any:
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return fallback
    if value is None:
        return fallback
    return value


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


def normalize_semantic_rollout_overrides(payload: dict[str, Any] | None, *, base: dict[str, Any] | None = None) -> dict[str, Any]:
    defaults = {**_default_semantic_rollout_settings(), **(base or {})}
    payload = payload or {}
    return {
        "semantic_same_assignment_drift_threshold": _normalize_float(
            payload.get("semantic_same_assignment_drift_threshold"),
            float(defaults["semantic_same_assignment_drift_threshold"]),
            minimum=0.0,
            maximum=1.0,
        ),
        "semantic_cross_assignment_drift_threshold": _normalize_float(
            payload.get("semantic_cross_assignment_drift_threshold"),
            float(defaults["semantic_cross_assignment_drift_threshold"]),
            minimum=0.0,
            maximum=1.0,
        ),
        "semantic_same_assignment_min_score": _normalize_float(
            payload.get("semantic_same_assignment_min_score"),
            float(defaults["semantic_same_assignment_min_score"]),
            minimum=0.0,
            maximum=1.0,
        ),
        "semantic_cross_assignment_min_score": _normalize_float(
            payload.get("semantic_cross_assignment_min_score"),
            float(defaults["semantic_cross_assignment_min_score"]),
            minimum=0.0,
            maximum=1.0,
        ),
        "semantic_same_assignment_min_sample_size": _normalize_int(
            payload.get("semantic_same_assignment_min_sample_size"),
            int(defaults["semantic_same_assignment_min_sample_size"]),
            minimum=1,
            maximum=5000,
        ),
        "semantic_cross_assignment_min_sample_size": _normalize_int(
            payload.get("semantic_cross_assignment_min_sample_size"),
            int(defaults["semantic_cross_assignment_min_sample_size"]),
            minimum=1,
            maximum=5000,
        ),
        "semantic_multilingual_min_sample_size": _normalize_int(
            payload.get("semantic_multilingual_min_sample_size"),
            int(defaults["semantic_multilingual_min_sample_size"]),
            minimum=1,
            maximum=5000,
        ),
        "config_version": _normalize_int(payload.get("config_version"), int(defaults.get("config_version") or 0), minimum=0, maximum=1_000_000),
        "approved_snapshot_version_same_assignment": _normalize_optional_int(
            payload["approved_snapshot_version_same_assignment"] if "approved_snapshot_version_same_assignment" in payload else defaults.get("approved_snapshot_version_same_assignment"),
            None,
        ),
        "approved_snapshot_version_cross_assignment": _normalize_optional_int(
            payload["approved_snapshot_version_cross_assignment"] if "approved_snapshot_version_cross_assignment" in payload else defaults.get("approved_snapshot_version_cross_assignment"),
            None,
        ),
        "active_snapshot_version_same_assignment": _normalize_optional_int(
            payload["active_snapshot_version_same_assignment"] if "active_snapshot_version_same_assignment" in payload else defaults.get("active_snapshot_version_same_assignment"),
            None,
        ),
        "active_snapshot_version_cross_assignment": _normalize_optional_int(
            payload["active_snapshot_version_cross_assignment"] if "active_snapshot_version_cross_assignment" in payload else defaults.get("active_snapshot_version_cross_assignment"),
            None,
        ),
        "semantic_same_assignment_promotion_state": (
            str(payload.get("semantic_same_assignment_promotion_state") or defaults.get("semantic_same_assignment_promotion_state") or "blocked").strip().lower()
            if str(payload.get("semantic_same_assignment_promotion_state") or defaults.get("semantic_same_assignment_promotion_state") or "blocked").strip().lower() in _SEMANTIC_PROMOTION_STATES
            else "blocked"
        ),
        "semantic_cross_assignment_promotion_state": (
            str(payload.get("semantic_cross_assignment_promotion_state") or defaults.get("semantic_cross_assignment_promotion_state") or "blocked").strip().lower()
            if str(payload.get("semantic_cross_assignment_promotion_state") or defaults.get("semantic_cross_assignment_promotion_state") or "blocked").strip().lower() in _SEMANTIC_PROMOTION_STATES
            else "blocked"
        ),
        "last_change_reason": _normalize_short_text(payload.get("last_change_reason"), defaults.get("last_change_reason"), limit=400),
        "last_change_actor_user_id": _normalize_short_text(
            payload.get("last_change_actor_user_id"),
            defaults.get("last_change_actor_user_id"),
            limit=120,
        ),
        "last_change_at": _normalize_datetime(payload.get("last_change_at"), defaults.get("last_change_at")),
        "manual_promotion_guidance_only": True,
    }


async def get_ai_runtime_settings() -> dict[str, Any]:
    defaults = _default_runtime_settings()
    record = await db.settings.find_one({"key": AI_RUNTIME_SETTINGS_KEY})
    overrides = normalize_runtime_overrides(record.get("value") if record else {})
    merged = {**defaults, **overrides}
    merged["openai_configured"] = defaults["openai_configured"]
    merged["effective_provider_enabled"] = bool(merged["provider_enabled"] and defaults["openai_configured"])
    return merged


async def get_ai_semantic_rollout_settings(*, database: Any | None = None) -> dict[str, Any]:
    active_db = database if database is not None else db
    defaults = _default_semantic_rollout_settings()
    record = await active_db.settings.find_one({"key": AI_SEMANTIC_ROLLOUT_SETTINGS_KEY})
    overrides = normalize_semantic_rollout_overrides(record.get("value") if record else {}, base=defaults)
    return {**defaults, **overrides, "manual_promotion_guidance_only": True}


async def get_ai_semantic_rollout_history(*, database: Any | None = None) -> dict[str, Any]:
    active_db = database if database is not None else db
    defaults = _default_semantic_rollout_history()
    record = await active_db.settings.find_one({"key": AI_SEMANTIC_ROLLOUT_HISTORY_KEY})
    value = record.get("value") if record else {}
    items = list((value or {}).get("items") or [])
    last_version = _normalize_int((value or {}).get("last_version"), 0, minimum=0, maximum=1_000_000)
    return {
        **defaults,
        "last_version": last_version,
        "items": items,
    }


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


async def save_ai_semantic_rollout_settings(
    payload: dict[str, Any],
    *,
    actor_user_id: str | None = None,
    database: Any | None = None,
) -> dict[str, Any]:
    active_db = database if database is not None else db
    current = await get_ai_semantic_rollout_settings(database=active_db)
    merged = {**current, **(payload or {})}
    normalized = normalize_semantic_rollout_overrides(merged, base=current)
    await active_db.settings.update_one(
        {"key": AI_SEMANTIC_ROLLOUT_SETTINGS_KEY},
        {
            "$set": {
                "key": AI_SEMANTIC_ROLLOUT_SETTINGS_KEY,
                "value": normalized,
                "updated_by_user_id": actor_user_id,
                "schema_version": SETTINGS_SCHEMA_VERSION,
            }
        },
        upsert=True,
    )
    return await get_ai_semantic_rollout_settings(database=active_db)


async def save_ai_semantic_rollout_history(
    payload: dict[str, Any],
    *,
    actor_user_id: str | None = None,
    database: Any | None = None,
) -> dict[str, Any]:
    active_db = database if database is not None else db
    history = _default_semantic_rollout_history()
    history["last_version"] = _normalize_int(payload.get("last_version"), 0, minimum=0, maximum=1_000_000)
    history["items"] = list(payload.get("items") or [])
    await active_db.settings.update_one(
        {"key": AI_SEMANTIC_ROLLOUT_HISTORY_KEY},
        {
            "$set": {
                "key": AI_SEMANTIC_ROLLOUT_HISTORY_KEY,
                "value": history,
                "updated_by_user_id": actor_user_id,
                "schema_version": SETTINGS_SCHEMA_VERSION,
            }
        },
        upsert=True,
    )
    return await get_ai_semantic_rollout_history(database=active_db)


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
