from __future__ import annotations

from datetime import datetime
from typing import Any

from app.services.ai_runtime import (
    get_ai_semantic_rollout_history,
    get_ai_semantic_rollout_settings,
    save_ai_semantic_rollout_history,
    save_ai_semantic_rollout_settings,
)
from app.services.audit import log_audit_event
from app.services.reviewer_outcome_calibration import build_reviewer_outcome_calibration_report

_SEMANTIC_ROLLOUT_ENTITY_TYPE = "ai_semantic_rollout_config"
_APPLY_SCOPES = {"same_assignment", "cross_assignment", "both"}
_PROMOTION_STATES = {"blocked", "candidate", "approved_manual", "active_assist_only"}
_MULTILINGUAL_BLOCKER_TEXT = "multilingual coverage"


def _serialize_datetime(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.isoformat()
    return None


def _normalize_apply_scope(value: Any) -> str:
    normalized = str(value or "both").strip().lower()
    return normalized if normalized in _APPLY_SCOPES else "both"


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


def _normalize_justification(value: Any, *, required: bool) -> str:
    normalized = str(value or "").strip()
    if required and not normalized:
        raise ValueError("A justification is required for this semantic rollout action.")
    return normalized[:400]


def _diff_settings(old_value: dict[str, Any], new_value: dict[str, Any]) -> dict[str, dict[str, Any]]:
    keys = sorted(set(old_value.keys()) | set(new_value.keys()))
    changes: dict[str, dict[str, Any]] = {}
    for key in keys:
        old_item = old_value.get(key)
        new_item = new_value.get(key)
        if old_item == new_item:
            continue
        changes[key] = {"old": old_item, "new": new_item}
    return changes


def _scope_is_ready(readiness: dict[str, Any], scope: str) -> bool:
    if scope == "same_assignment":
        return bool((readiness.get("same_assignment") or {}).get("promotion_ready"))
    if scope == "cross_assignment":
        return bool((readiness.get("cross_assignment") or {}).get("promotion_ready"))
    return False


def _scope_blockers(readiness: dict[str, Any], scope: str) -> list[str]:
    if scope == "same_assignment":
        return list((readiness.get("same_assignment") or {}).get("blocker_reasons") or [])
    if scope == "cross_assignment":
        return list((readiness.get("cross_assignment") or {}).get("blocker_reasons") or [])
    return []


def _global_blockers(readiness: dict[str, Any]) -> list[str]:
    return list(readiness.get("blocker_reasons") or [])


def _to_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    return None


def _requested_scopes(scope: str) -> list[str]:
    return ["same_assignment", "cross_assignment"] if scope == "both" else [scope]


def _same_scope_threshold_keys() -> list[str]:
    return [
        "semantic_same_assignment_drift_threshold",
        "semantic_same_assignment_min_score",
        "semantic_same_assignment_min_sample_size",
    ]


def _cross_scope_threshold_keys() -> list[str]:
    return [
        "semantic_cross_assignment_drift_threshold",
        "semantic_cross_assignment_min_score",
        "semantic_cross_assignment_min_sample_size",
    ]


def _scope_pointer_keys(scope: str) -> list[str]:
    if scope == "same_assignment":
        return [
            "approved_snapshot_version_same_assignment",
            "active_snapshot_version_same_assignment",
            "semantic_same_assignment_promotion_state",
        ]
    if scope == "cross_assignment":
        return [
            "approved_snapshot_version_cross_assignment",
            "active_snapshot_version_cross_assignment",
            "semantic_cross_assignment_promotion_state",
        ]
    return []


def _scope_settings_keys(scope: str, *, include_pointers: bool = False, include_global: bool = False) -> list[str]:
    keys: list[str] = []
    if scope in {"same_assignment", "both"}:
        keys.extend(_same_scope_threshold_keys())
        if include_pointers:
            keys.extend(_scope_pointer_keys("same_assignment"))
    if scope in {"cross_assignment", "both"}:
        keys.extend(_cross_scope_threshold_keys())
        if include_pointers:
            keys.extend(_scope_pointer_keys("cross_assignment"))
    if include_global and scope == "both":
        keys.append("semantic_multilingual_min_sample_size")
    return keys


def _approved_versions_from_settings(settings_map: dict[str, Any]) -> dict[str, int | None]:
    return {
        "same_assignment": _to_int(settings_map.get("approved_snapshot_version_same_assignment")),
        "cross_assignment": _to_int(settings_map.get("approved_snapshot_version_cross_assignment")),
    }


def _active_versions_from_settings(settings_map: dict[str, Any]) -> dict[str, int | None]:
    return {
        "same_assignment": _to_int(settings_map.get("active_snapshot_version_same_assignment")),
        "cross_assignment": _to_int(settings_map.get("active_snapshot_version_cross_assignment")),
    }


def _scope_state(scope: str, settings_map: dict[str, Any], readiness: dict[str, Any]) -> str:
    blockers = _scope_blockers(readiness, scope)
    approved_versions = _approved_versions_from_settings(settings_map)
    active_versions = _active_versions_from_settings(settings_map)
    approved_version = approved_versions.get(scope)
    active_version = active_versions.get(scope)
    if blockers or not _scope_is_ready(readiness, scope):
        return "blocked"
    if active_version is not None and (approved_version is None or approved_version == active_version):
        return "active_assist_only"
    if approved_version is not None:
        return "approved_manual"
    return "candidate"


def _build_scope_states(settings_map: dict[str, Any], readiness: dict[str, Any]) -> dict[str, str]:
    states = {
        "same_assignment": _scope_state("same_assignment", settings_map, readiness),
        "cross_assignment": _scope_state("cross_assignment", settings_map, readiness),
    }
    return {key: value if value in _PROMOTION_STATES else "blocked" for key, value in states.items()}


def _settings_with_scope_states(settings_map: dict[str, Any], readiness: dict[str, Any]) -> dict[str, Any]:
    states = _build_scope_states(settings_map, readiness)
    updated = dict(settings_map)
    updated["semantic_same_assignment_promotion_state"] = states["same_assignment"]
    updated["semantic_cross_assignment_promotion_state"] = states["cross_assignment"]
    return updated


def _build_response(
    *,
    effective: dict[str, Any],
    calibration: dict[str, Any],
    changes: dict[str, dict[str, Any]] | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    readiness = calibration.get("semantic_rollout_readiness") or {}
    effective_with_states = _settings_with_scope_states(effective, readiness)
    return {
        "effective": effective_with_states,
        "recommendations": calibration.get("recommendations") or {},
        "semantic_rollout_readiness": readiness,
        "scope_states": _build_scope_states(effective_with_states, readiness),
        "current_version": _to_int(effective_with_states.get("config_version")) or 0,
        "approved_versions": _approved_versions_from_settings(effective_with_states),
        "active_versions": _active_versions_from_settings(effective_with_states),
        "gates": calibration.get("gates") or {},
        "changes": changes or {},
        **(extra or {}),
    }


def _recommended_snapshot_settings(
    current: dict[str, Any],
    recommendations: dict[str, Any],
    *,
    requested_scopes: list[str],
    include_sample_sizes: bool,
) -> dict[str, Any]:
    snapshot = dict(current)
    if "same_assignment" in requested_scopes:
        recommended_same_drift = recommendations.get("recommended_same_assignment_drift_threshold")
        recommended_min_semantic = recommendations.get("recommended_min_semantic_score")
        if isinstance(recommended_same_drift, (int, float)):
            snapshot["semantic_same_assignment_drift_threshold"] = float(recommended_same_drift)
        if isinstance(recommended_min_semantic, (int, float)):
            snapshot["semantic_same_assignment_min_score"] = float(recommended_min_semantic)
        if include_sample_sizes:
            sample_sizes = recommendations.get("recommended_min_sample_size") or {}
            same_sample_size = _to_int(sample_sizes.get("same_assignment"))
            if same_sample_size is not None:
                snapshot["semantic_same_assignment_min_sample_size"] = same_sample_size

    if "cross_assignment" in requested_scopes:
        recommended_cross_drift = recommendations.get("recommended_cross_assignment_drift_threshold")
        recommended_min_semantic = recommendations.get("recommended_min_semantic_score")
        if isinstance(recommended_cross_drift, (int, float)):
            snapshot["semantic_cross_assignment_drift_threshold"] = float(recommended_cross_drift)
        if isinstance(recommended_min_semantic, (int, float)):
            snapshot["semantic_cross_assignment_min_score"] = max(
                float(snapshot.get("semantic_cross_assignment_min_score") or 0.0),
                float(recommended_min_semantic),
            )
        if include_sample_sizes:
            sample_sizes = recommendations.get("recommended_min_sample_size") or {}
            cross_sample_size = _to_int(sample_sizes.get("cross_assignment"))
            if cross_sample_size is not None:
                snapshot["semantic_cross_assignment_min_sample_size"] = cross_sample_size
    return snapshot


def _merge_scope_values(
    destination: dict[str, Any],
    source: dict[str, Any],
    *,
    scope: str,
    include_pointers: bool = False,
    include_global: bool = False,
) -> dict[str, Any]:
    merged = dict(destination)
    for key in _scope_settings_keys(scope, include_pointers=include_pointers, include_global=include_global):
        if key in source:
            merged[key] = source.get(key)
    return merged


def _scope_matches_target(selected_scope: str, target_scope: str) -> bool:
    if selected_scope == "both":
        return target_scope == "both"
    return target_scope in {selected_scope, "both"}


def _has_multilingual_blocker(readiness: dict[str, Any], scope: str) -> bool:
    blockers = _scope_blockers(readiness, scope)
    if scope == "cross_assignment":
        blockers = blockers + _global_blockers(readiness)
    return any(_MULTILINGUAL_BLOCKER_TEXT in str(item).strip().lower() for item in blockers)


def _history_store_item(history_store: dict[str, Any], version: int) -> dict[str, Any] | None:
    for item in history_store.get("items") or []:
        if _to_int(item.get("version")) == version:
            return item
    return None


def _serialize_history_item(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id") or item.get("version") or ""),
        "version": _to_int(item.get("version")),
        "scope": item.get("scope"),
        "action": item.get("action"),
        "actor_user_id": item.get("actor_user_id"),
        "detail": item.get("detail"),
        "justification": item.get("justification"),
        "severity": item.get("severity"),
        "created_at": _serialize_datetime(item.get("created_at")),
        "effective_settings": item.get("effective_settings"),
        "snapshot_settings": item.get("snapshot_settings"),
        "resulting_scope_states": item.get("resulting_scope_states") or {},
        "restored_from_version": _to_int(item.get("restored_from_version")),
        "approved_versions": item.get("approved_versions") or {},
        "active_versions": item.get("active_versions") or {},
        "force": bool(item.get("force")) if item.get("force") is not None else False,
        "target_version": _to_int(item.get("target_version")),
    }


async def _append_history_item(
    *,
    database: Any,
    actor_user_id: str,
    action: str,
    scope: str,
    justification: str,
    detail: str,
    severity: str,
    effective_settings: dict[str, Any],
    snapshot_settings: dict[str, Any],
    resulting_scope_states: dict[str, str],
    restored_from_version: int | None = None,
    force: bool | None = None,
    target_version: int | None = None,
) -> dict[str, Any]:
    history_store = await get_ai_semantic_rollout_history(database=database)
    version = int(history_store.get("last_version") or 0) + 1
    item = {
        "id": f"semantic-rollout-{version}",
        "version": version,
        "scope": scope,
        "action": action,
        "actor_user_id": actor_user_id,
        "detail": detail,
        "justification": justification,
        "severity": severity,
        "created_at": datetime.utcnow(),
        "effective_settings": effective_settings,
        "snapshot_settings": snapshot_settings,
        "resulting_scope_states": resulting_scope_states,
        "approved_versions": _approved_versions_from_settings(effective_settings),
        "active_versions": _active_versions_from_settings(effective_settings),
        "restored_from_version": restored_from_version,
        "force": force,
        "target_version": target_version,
    }
    items = list(history_store.get("items") or [])
    items.append(item)
    await save_ai_semantic_rollout_history(
        {"last_version": version, "items": items},
        actor_user_id=actor_user_id,
        database=database,
    )
    return item


async def _preview_calibration(database: Any, settings_map: dict[str, Any]) -> dict[str, Any]:
    return await build_reviewer_outcome_calibration_report(
        database=database,
        semantic_rollout_settings_override=settings_map,
    )


async def _persist_settings_with_preview(
    *,
    database: Any,
    actor_user_id: str,
    next_payload: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    calibration = await _preview_calibration(database=database, settings_map=next_payload)
    effective = _settings_with_scope_states(next_payload, calibration.get("semantic_rollout_readiness") or {})
    updated = await save_ai_semantic_rollout_settings(effective, actor_user_id=actor_user_id, database=database)
    return updated, calibration


async def get_semantic_rollout_config_response(*, database: Any) -> dict[str, Any]:
    effective = await get_ai_semantic_rollout_settings(database=database)
    calibration = await build_reviewer_outcome_calibration_report(database=database)
    return _build_response(effective=effective, calibration=calibration)


async def update_semantic_rollout_config_response(
    payload: dict[str, Any] | None,
    *,
    actor_user_id: str,
    database: Any,
) -> dict[str, Any]:
    current = await get_ai_semantic_rollout_settings(database=database)
    history_store = await get_ai_semantic_rollout_history(database=database)
    next_version = int(history_store.get("last_version") or 0) + 1
    justification = _normalize_justification((payload or {}).get("justification") or "Updated semantic rollout thresholds manually.", required=False)
    next_payload = {
        **current,
        **(payload or {}),
        "config_version": next_version,
        "last_change_reason": justification,
        "last_change_actor_user_id": actor_user_id,
        "last_change_at": datetime.utcnow(),
    }
    updated, calibration = await _persist_settings_with_preview(
        database=database,
        actor_user_id=actor_user_id,
        next_payload=next_payload,
    )
    scope_states = _build_scope_states(updated, calibration.get("semantic_rollout_readiness") or {})
    history_item = await _append_history_item(
        database=database,
        actor_user_id=actor_user_id,
        action="update_semantic_rollout_config",
        scope="both",
        justification=justification,
        detail="Updated semantic rollout thresholds/sample settings manually.",
        severity="medium",
        effective_settings=updated,
        snapshot_settings=updated,
        resulting_scope_states=scope_states,
    )
    await log_audit_event(
        actor_user_id=actor_user_id,
        action="update_semantic_rollout_config",
        entity_type=_SEMANTIC_ROLLOUT_ENTITY_TYPE,
        detail="Updated semantic rollout thresholds/sample settings manually.",
        old_value=current,
        new_value=updated,
        severity="medium",
    )
    return _build_response(
        effective=updated,
        calibration=calibration,
        changes=_diff_settings(current, updated),
        extra={"history_item": _serialize_history_item(history_item)},
    )


async def approve_semantic_rollout_recommendations_response(
    payload: dict[str, Any] | None,
    *,
    actor_user_id: str,
    database: Any,
) -> dict[str, Any]:
    payload = payload or {}
    apply_scope = _normalize_apply_scope(payload.get("scope"))
    force = _normalize_bool(payload.get("force"), False)
    include_sample_sizes = _normalize_bool(payload.get("include_sample_sizes"), True)
    justification = _normalize_justification(payload.get("justification"), required=True)

    calibration = await build_reviewer_outcome_calibration_report(database=database)
    readiness = calibration.get("semantic_rollout_readiness") or {}
    recommendations = calibration.get("recommendations") or {}
    current = await get_ai_semantic_rollout_settings(database=database)
    history_store = await get_ai_semantic_rollout_history(database=database)
    next_version = int(history_store.get("last_version") or 0) + 1

    requested_scopes = _requested_scopes(apply_scope)
    scope_blockers: dict[str, list[str]] = {}
    for scope in requested_scopes:
        blockers = _scope_blockers(readiness, scope)
        scope_blockers[scope] = blockers
        if not force and not _scope_is_ready(readiness, scope):
            blocker_text = blockers[0] if blockers else f"{scope} readiness is not promotion-ready yet."
            raise ValueError(f"Cannot approve semantic recommendations for {scope}: {blocker_text}")

    snapshot_settings = _recommended_snapshot_settings(
        current,
        recommendations,
        requested_scopes=requested_scopes,
        include_sample_sizes=include_sample_sizes,
    )
    next_payload = {
        **current,
        "config_version": next_version,
        "last_change_reason": justification,
        "last_change_actor_user_id": actor_user_id,
        "last_change_at": datetime.utcnow(),
    }
    if "same_assignment" in requested_scopes:
        next_payload["approved_snapshot_version_same_assignment"] = next_version
    if "cross_assignment" in requested_scopes:
        next_payload["approved_snapshot_version_cross_assignment"] = next_version

    updated, refreshed_calibration = await _persist_settings_with_preview(
        database=database,
        actor_user_id=actor_user_id,
        next_payload=next_payload,
    )
    scope_states = _build_scope_states(updated, refreshed_calibration.get("semantic_rollout_readiness") or {})
    history_item = await _append_history_item(
        database=database,
        actor_user_id=actor_user_id,
        action="approve_semantic_rollout_recommendations",
        scope=apply_scope,
        justification=justification,
        detail=f"Approved semantic rollout recommendations for scope={apply_scope}.",
        severity="high" if force else "medium",
        effective_settings=updated,
        snapshot_settings=snapshot_settings,
        resulting_scope_states=scope_states,
        force=force,
    )
    await log_audit_event(
        actor_user_id=actor_user_id,
        action="approve_semantic_rollout_recommendations",
        entity_type=_SEMANTIC_ROLLOUT_ENTITY_TYPE,
        detail=f"Approved semantic rollout recommendations for scope={apply_scope}, force={force}.",
        old_value=current,
        new_value=updated,
        severity="high" if force else "medium",
    )
    return _build_response(
        effective=updated,
        calibration=refreshed_calibration,
        changes=_diff_settings(current, updated),
        extra={
            "approved_scope": apply_scope,
            "force": force,
            "include_sample_sizes": include_sample_sizes,
            "scope_blockers": scope_blockers,
            "approved_snapshot_version": next_version,
            "history_item": _serialize_history_item(history_item),
        },
    )


async def activate_semantic_rollout_snapshot_response(
    payload: dict[str, Any] | None,
    *,
    actor_user_id: str,
    database: Any,
) -> dict[str, Any]:
    payload = payload or {}
    apply_scope = _normalize_apply_scope(payload.get("scope"))
    force = _normalize_bool(payload.get("force"), False)
    justification = _normalize_justification(payload.get("justification"), required=True)
    target_version = _to_int(payload.get("target_version"))
    if target_version is None:
        raise ValueError("A target_version is required to activate a semantic rollout snapshot.")

    current = await get_ai_semantic_rollout_settings(database=database)
    history_store = await get_ai_semantic_rollout_history(database=database)
    target = _history_store_item(history_store, target_version)
    if not target:
        raise ValueError(f"Semantic rollout snapshot version {target_version} was not found.")
    if not _scope_matches_target(apply_scope, str(target.get("scope") or "both")):
        raise ValueError(f"Semantic rollout snapshot version {target_version} does not match scope={apply_scope}.")

    calibration = await build_reviewer_outcome_calibration_report(database=database)
    readiness = calibration.get("semantic_rollout_readiness") or {}
    requested_scopes = _requested_scopes(apply_scope)
    for scope in requested_scopes:
        blockers = _scope_blockers(readiness, scope)
        if _has_multilingual_blocker(readiness, scope):
            blocker_text = blockers[0] if blockers else "Multilingual coverage is below minimum sample targets."
            raise ValueError(f"Cannot activate semantic snapshot for {scope}: {blocker_text}")
        if not force and not _scope_is_ready(readiness, scope):
            blocker_text = blockers[0] if blockers else f"{scope} readiness is not promotion-ready yet."
            raise ValueError(f"Cannot activate semantic snapshot for {scope}: {blocker_text}")
        approved_versions = _approved_versions_from_settings(current)
        if approved_versions.get(scope) != target_version:
            raise ValueError(f"Semantic rollout snapshot version {target_version} is not the approved snapshot for {scope}.")

    history_last_version = int(history_store.get("last_version") or 0) + 1
    snapshot_settings = dict(target.get("snapshot_settings") or {})
    next_payload = {
        **current,
        "config_version": history_last_version,
        "last_change_reason": justification,
        "last_change_actor_user_id": actor_user_id,
        "last_change_at": datetime.utcnow(),
    }
    for scope in requested_scopes:
        next_payload = _merge_scope_values(next_payload, snapshot_settings, scope=scope, include_pointers=False, include_global=False)
        if scope == "same_assignment":
            next_payload["approved_snapshot_version_same_assignment"] = target_version
            next_payload["active_snapshot_version_same_assignment"] = target_version
        if scope == "cross_assignment":
            next_payload["approved_snapshot_version_cross_assignment"] = target_version
            next_payload["active_snapshot_version_cross_assignment"] = target_version

    updated, refreshed_calibration = await _persist_settings_with_preview(
        database=database,
        actor_user_id=actor_user_id,
        next_payload=next_payload,
    )
    scope_states = _build_scope_states(updated, refreshed_calibration.get("semantic_rollout_readiness") or {})
    history_item = await _append_history_item(
        database=database,
        actor_user_id=actor_user_id,
        action="activate_semantic_rollout_snapshot",
        scope=apply_scope,
        justification=justification,
        detail=f"Activated approved semantic rollout snapshot version {target_version} for scope={apply_scope}.",
        severity="high" if force else "medium",
        effective_settings=updated,
        snapshot_settings=updated,
        resulting_scope_states=scope_states,
        force=force,
        target_version=target_version,
    )
    await log_audit_event(
        actor_user_id=actor_user_id,
        action="activate_semantic_rollout_snapshot",
        entity_type=_SEMANTIC_ROLLOUT_ENTITY_TYPE,
        detail=f"Activated semantic rollout snapshot version {target_version} for scope={apply_scope}, force={force}.",
        old_value=current,
        new_value=updated,
        severity="high" if force else "medium",
    )
    return _build_response(
        effective=updated,
        calibration=refreshed_calibration,
        changes=_diff_settings(current, updated),
        extra={
            "activated_scope": apply_scope,
            "force": force,
            "target_version": target_version,
            "history_item": _serialize_history_item(history_item),
        },
    )


async def rollback_semantic_rollout_snapshot_response(
    payload: dict[str, Any] | None,
    *,
    actor_user_id: str,
    database: Any,
) -> dict[str, Any]:
    payload = payload or {}
    apply_scope = _normalize_apply_scope(payload.get("scope"))
    justification = _normalize_justification(payload.get("justification"), required=True)
    target_version = _to_int(payload.get("target_version"))
    if target_version is None:
        raise ValueError("A target_version is required to roll back a semantic rollout snapshot.")

    current = await get_ai_semantic_rollout_settings(database=database)
    history_store = await get_ai_semantic_rollout_history(database=database)
    target = _history_store_item(history_store, target_version)
    if not target:
        raise ValueError(f"Semantic rollout snapshot version {target_version} was not found.")
    if not _scope_matches_target(apply_scope, str(target.get("scope") or "both")):
        raise ValueError(f"Semantic rollout snapshot version {target_version} does not match scope={apply_scope}.")

    target_effective = dict(target.get("effective_settings") or {})
    history_last_version = int(history_store.get("last_version") or 0) + 1
    next_payload = {
        **current,
        "config_version": history_last_version,
        "last_change_reason": justification,
        "last_change_actor_user_id": actor_user_id,
        "last_change_at": datetime.utcnow(),
    }
    next_payload = _merge_scope_values(
        next_payload,
        target_effective,
        scope=apply_scope,
        include_pointers=True,
        include_global=True,
    )

    updated, refreshed_calibration = await _persist_settings_with_preview(
        database=database,
        actor_user_id=actor_user_id,
        next_payload=next_payload,
    )
    scope_states = _build_scope_states(updated, refreshed_calibration.get("semantic_rollout_readiness") or {})
    history_item = await _append_history_item(
        database=database,
        actor_user_id=actor_user_id,
        action="rollback_semantic_rollout_snapshot",
        scope=apply_scope,
        justification=justification,
        detail=f"Rolled back semantic rollout governance to snapshot version {target_version} for scope={apply_scope}.",
        severity="medium",
        effective_settings=updated,
        snapshot_settings=updated,
        resulting_scope_states=scope_states,
        restored_from_version=target_version,
        target_version=target_version,
    )
    await log_audit_event(
        actor_user_id=actor_user_id,
        action="rollback_semantic_rollout_snapshot",
        entity_type=_SEMANTIC_ROLLOUT_ENTITY_TYPE,
        detail=f"Rolled back semantic rollout snapshot version {target_version} for scope={apply_scope}.",
        old_value=current,
        new_value=updated,
        severity="medium",
    )
    return _build_response(
        effective=updated,
        calibration=refreshed_calibration,
        changes=_diff_settings(current, updated),
        extra={
            "rolled_back_scope": apply_scope,
            "restored_from_version": target_version,
            "history_item": _serialize_history_item(history_item),
        },
    )


async def apply_semantic_rollout_recommendations_response(
    payload: dict[str, Any] | None,
    *,
    actor_user_id: str,
    database: Any,
) -> dict[str, Any]:
    payload = payload or {}
    apply_scope = _normalize_apply_scope(payload.get("scope"))
    force = _normalize_bool(payload.get("force"), False)
    include_sample_sizes = _normalize_bool(payload.get("include_sample_sizes"), True)
    justification = _normalize_justification(
        payload.get("justification") or "Compatibility apply of approved semantic rollout recommendations.",
        required=False,
    )

    calibration = await build_reviewer_outcome_calibration_report(database=database)
    readiness = calibration.get("semantic_rollout_readiness") or {}
    recommendations = calibration.get("recommendations") or {}
    current = await get_ai_semantic_rollout_settings(database=database)
    history_store = await get_ai_semantic_rollout_history(database=database)
    next_version = int(history_store.get("last_version") or 0) + 1

    requested_scopes = _requested_scopes(apply_scope)
    scope_blockers: dict[str, list[str]] = {}
    for scope in requested_scopes:
        blockers = _scope_blockers(readiness, scope)
        scope_blockers[scope] = blockers
        if not force and not _scope_is_ready(readiness, scope):
            blocker_text = blockers[0] if blockers else f"{scope} readiness is not promotion-ready yet."
            raise ValueError(f"Cannot apply semantic recommendations for {scope}: {blocker_text}")
        if _has_multilingual_blocker(readiness, scope):
            blocker_text = blockers[0] if blockers else "Multilingual coverage is below minimum sample targets."
            raise ValueError(f"Cannot apply semantic recommendations for {scope}: {blocker_text}")

    next_payload = _recommended_snapshot_settings(
        current,
        recommendations,
        requested_scopes=requested_scopes,
        include_sample_sizes=include_sample_sizes,
    )
    next_payload.update(
        {
            "config_version": next_version,
            "last_change_reason": justification,
            "last_change_actor_user_id": actor_user_id,
            "last_change_at": datetime.utcnow(),
        }
    )
    if "same_assignment" in requested_scopes:
        next_payload["approved_snapshot_version_same_assignment"] = next_version
        next_payload["active_snapshot_version_same_assignment"] = next_version
    if "cross_assignment" in requested_scopes:
        next_payload["approved_snapshot_version_cross_assignment"] = next_version
        next_payload["active_snapshot_version_cross_assignment"] = next_version

    updated, refreshed_calibration = await _persist_settings_with_preview(
        database=database,
        actor_user_id=actor_user_id,
        next_payload=next_payload,
    )
    scope_states = _build_scope_states(updated, refreshed_calibration.get("semantic_rollout_readiness") or {})
    history_item = await _append_history_item(
        database=database,
        actor_user_id=actor_user_id,
        action="apply_semantic_rollout_recommendations",
        scope=apply_scope,
        justification=justification,
        detail=f"Applied semantic rollout recommendation workflow for scope={apply_scope}, force={force}.",
        severity="high" if force else "medium",
        effective_settings=updated,
        snapshot_settings=updated,
        resulting_scope_states=scope_states,
        force=force,
    )
    await log_audit_event(
        actor_user_id=actor_user_id,
        action="apply_semantic_rollout_recommendations",
        entity_type=_SEMANTIC_ROLLOUT_ENTITY_TYPE,
        detail=f"Applied semantic rollout recommendation workflow for scope={apply_scope}, force={force}.",
        old_value=current,
        new_value=updated,
        severity="high" if force else "medium",
    )
    return _build_response(
        effective=updated,
        calibration=refreshed_calibration,
        changes=_diff_settings(current, updated),
        extra={
            "applied_scope": apply_scope,
            "force": force,
            "include_sample_sizes": include_sample_sizes,
            "scope_blockers": scope_blockers,
            "history_item": _serialize_history_item(history_item),
        },
    )


async def list_semantic_rollout_config_history_response(*, database: Any, limit: int = 20) -> dict[str, Any]:
    history_store = await get_ai_semantic_rollout_history(database=database)
    items = sorted(
        list(history_store.get("items") or []),
        key=lambda item: int(item.get("version") or 0),
        reverse=True,
    )[:limit]
    return {
        "count": len(items),
        "items": [_serialize_history_item(item) for item in items],
    }
