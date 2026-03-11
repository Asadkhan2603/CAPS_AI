from typing import Any

from app.services.ai_runtime import get_ai_runtime_settings, save_ai_runtime_settings


def build_provider_mode_payload(runtime_settings: dict[str, Any]) -> dict[str, Any]:
    openai_configured = bool(runtime_settings.get("openai_configured"))
    effective_provider_enabled = bool(runtime_settings.get("effective_provider_enabled"))
    return {
        "openai_configured": openai_configured,
        "provider_enabled": bool(runtime_settings.get("provider_enabled")),
        "mode": "openai+fallback" if effective_provider_enabled else "fallback-only",
        "model": runtime_settings.get("openai_model") if openai_configured else None,
        "timeout_seconds": runtime_settings.get("openai_timeout_seconds"),
        "max_output_tokens": runtime_settings.get("openai_max_output_tokens"),
        "similarity_threshold": runtime_settings.get("similarity_threshold"),
    }


def build_runtime_config_response(runtime_settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "effective": runtime_settings,
        "provider": build_provider_mode_payload(runtime_settings),
    }


async def get_runtime_config_response() -> dict[str, Any]:
    runtime_settings = await get_ai_runtime_settings()
    return build_runtime_config_response(runtime_settings)


async def update_runtime_config_response(
    payload: dict[str, Any],
    *,
    actor_user_id: str,
) -> dict[str, Any]:
    runtime_settings = await save_ai_runtime_settings(payload, actor_user_id=actor_user_id)
    return build_runtime_config_response(runtime_settings)
