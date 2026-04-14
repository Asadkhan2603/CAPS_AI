from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.core.database import db
from app.core.schema_versions import SETTINGS_SCHEMA_VERSION

MAX_SHARED_SIMILARITY_VIEWS = 20
SHARED_SIMILARITY_LIBRARY_KEY = "staff"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def _resolve_user_label(user_id: str | None, *, database: Any = db) -> str | None:
    database = db if database is None else database
    if not user_id or not ObjectId.is_valid(user_id):
        return None
    user = await database.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return None
    return user.get("full_name") or user.get("email")


def _normalize_filters(filters: dict[str, Any]) -> dict[str, Any]:
    return {
        "search": str(filters.get("search") or "").strip(),
        "review_status": str(filters.get("review_status") or "").strip(),
        "decision_mode": str(filters.get("decision_mode") or "").strip(),
        "awaiting_final_decision": bool(filters.get("awaiting_final_decision")),
        "stale_review": bool(filters.get("stale_review")),
        "counts_toward_calibration": bool(filters.get("counts_toward_calibration")),
        "calibration_eligible": bool(filters.get("calibration_eligible")),
        "semantic_review_candidate": bool(filters.get("semantic_review_candidate")),
        "semantic_drift_present": bool(filters.get("semantic_drift_present")),
        "match_scope": str(filters.get("match_scope") or "").strip().lower(),
        "language_bucket": str(filters.get("language_bucket") or "").strip().lower(),
        "cap_reached": bool(filters.get("cap_reached")),
        "low_extraction_quality": bool(filters.get("low_extraction_quality")),
        "min_score": (
            max(0.0, min(1.0, float(filters.get("min_score"))))
            if filters.get("min_score") not in {None, ""}
            else None
        ),
        "max_score": (
            max(0.0, min(1.0, float(filters.get("max_score"))))
            if filters.get("max_score") not in {None, ""}
            else None
        ),
    }


def similarity_view_public(document: dict[str, Any], *, created_by_label: str | None = None) -> dict[str, Any]:
    return {
        "id": str(document.get("_id") or ""),
        "library_key": str(document.get("library_key") or SHARED_SIMILARITY_LIBRARY_KEY),
        "name": document.get("name"),
        "filters": _normalize_filters(document.get("filters") or {}),
        "created_by_user_id": document.get("created_by_user_id"),
        "created_by_label": created_by_label,
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "schema_version": int(document.get("schema_version") or SETTINGS_SCHEMA_VERSION),
    }


async def list_shared_similarity_views(*, database: Any | None = None) -> list[dict[str, Any]]:
    database = db if database is None else database
    rows = await database.ai_similarity_views.find(
        {"library_key": SHARED_SIMILARITY_LIBRARY_KEY}
    ).sort([("updated_at", -1), ("created_at", -1)]).limit(MAX_SHARED_SIMILARITY_VIEWS).to_list(length=MAX_SHARED_SIMILARITY_VIEWS)
    output: list[dict[str, Any]] = []
    for row in rows:
        output.append(
            similarity_view_public(
                row,
                created_by_label=await _resolve_user_label(row.get("created_by_user_id"), database=database),
            )
        )
    return output


async def save_shared_similarity_view(
    *,
    name: str,
    filters: dict[str, Any],
    current_user_id: str,
    database: Any | None = None,
) -> dict[str, Any]:
    database = db if database is None else database
    now = _utc_now()
    document = {
        "library_key": SHARED_SIMILARITY_LIBRARY_KEY,
        "name": name.strip(),
        "filters": _normalize_filters(filters),
        "created_by_user_id": current_user_id,
        "created_at": now,
        "updated_at": now,
        "schema_version": SETTINGS_SCHEMA_VERSION,
    }
    result = await database.ai_similarity_views.insert_one(document)
    stored = await database.ai_similarity_views.find_one({"_id": result.inserted_id})
    await _prune_shared_similarity_views(database=database)
    return similarity_view_public(
        stored or {**document, "_id": result.inserted_id},
        created_by_label=await _resolve_user_label(current_user_id, database=database),
    )


async def delete_shared_similarity_view(
    *,
    view_id: str,
    current_user_id: str,
    is_admin: bool,
    database: Any | None = None,
) -> bool:
    database = db if database is None else database
    if not ObjectId.is_valid(view_id):
        return False
    query: dict[str, Any] = {
        "_id": ObjectId(view_id),
        "library_key": SHARED_SIMILARITY_LIBRARY_KEY,
    }
    if not is_admin:
        query["created_by_user_id"] = current_user_id
    result = await database.ai_similarity_views.delete_one(query)
    return bool(getattr(result, "deleted_count", 0))


async def _prune_shared_similarity_views(*, database: Any | None = None) -> None:
    database = db if database is None else database
    rows = await database.ai_similarity_views.find(
        {"library_key": SHARED_SIMILARITY_LIBRARY_KEY}
    ).sort([("updated_at", -1), ("created_at", -1)]).to_list(length=MAX_SHARED_SIMILARITY_VIEWS + 20)
    for row in rows[MAX_SHARED_SIMILARITY_VIEWS:]:
        await database.ai_similarity_views.delete_one({"_id": row.get("_id")})
