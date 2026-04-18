from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.core.database import db
from app.core.schema_versions import SETTINGS_SCHEMA_VERSION

MAX_SHARED_QUEUE_VIEWS = 12
MAX_SHARED_QUEUE_SNAPSHOTS = 24
PENDING_QUEUE_STATUSES = {"pending", "waitlisted"}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _queue_age_bucket(value: datetime | None) -> str:
    normalized = _normalize_datetime(value)
    if normalized is None:
        return "fresh"
    age_days = max(0, int((_utc_now() - normalized).total_seconds() // (60 * 60 * 24)))
    if age_days >= 7:
        return "stale"
    if age_days >= 3:
        return "aging"
    return "fresh"


async def _resolve_user_label(user_id: str | None, *, database: Any = db) -> str | None:
    database = database if database is not None else db
    if not user_id or not ObjectId.is_valid(user_id):
        return None
    user = await database.users.find_one({"_id": ObjectId(user_id)})
    if not user:
        return None
    return user.get("full_name") or user.get("email")


def _view_public(document: dict[str, Any], *, created_by_label: str | None = None) -> dict[str, Any]:
    return {
        "id": str(document.get("_id") or ""),
        "scope_type": document.get("scope_type"),
        "scope_id": document.get("scope_id"),
        "queue_type": document.get("queue_type"),
        "name": document.get("name"),
        "filters": document.get("filters") or {},
        "created_by_user_id": document.get("created_by_user_id"),
        "created_by_label": created_by_label,
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "schema_version": int(document.get("schema_version") or SETTINGS_SCHEMA_VERSION),
    }


def _snapshot_public(document: dict[str, Any], *, changed_by_label: str | None = None) -> dict[str, Any]:
    return {
        "id": str(document.get("_id") or ""),
        "scope_type": document.get("scope_type"),
        "scope_id": document.get("scope_id"),
        "queue_type": document.get("queue_type"),
        "total": int(document.get("total") or 0),
        "pending": int(document.get("pending") or 0),
        "waitlisted": int(document.get("waitlisted") or 0),
        "fresh": int(document.get("fresh") or 0),
        "aging": int(document.get("aging") or 0),
        "stale": int(document.get("stale") or 0),
        "signature": document.get("signature"),
        "captured_at": document.get("captured_at"),
        "source_action": document.get("source_action"),
        "changed_by_user_id": document.get("changed_by_user_id"),
        "changed_by_label": changed_by_label,
        "schema_version": int(document.get("schema_version") or SETTINGS_SCHEMA_VERSION),
    }


async def list_shared_queue_views(
    *,
    scope_type: str,
    scope_id: str,
    queue_type: str,
    database: Any | None = None,
) -> list[dict[str, Any]]:
    database = database if database is not None else db
    rows = await database.club_queue_views.find(
        {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "queue_type": queue_type,
        }
    ).sort([("updated_at", -1), ("created_at", -1)]).limit(MAX_SHARED_QUEUE_VIEWS).to_list(length=MAX_SHARED_QUEUE_VIEWS)
    output: list[dict[str, Any]] = []
    for row in rows:
        output.append(_view_public(row, created_by_label=await _resolve_user_label(row.get("created_by_user_id"), database=database)))
    return output


async def save_shared_queue_view(
    *,
    scope_type: str,
    scope_id: str,
    queue_type: str,
    name: str,
    filters: dict[str, Any],
    current_user_id: str,
    database: Any | None = None,
) -> dict[str, Any]:
    database = database if database is not None else db
    now = _utc_now()
    document = {
        "scope_type": scope_type,
        "scope_id": scope_id,
        "queue_type": queue_type,
        "name": name.strip(),
        "filters": {
            "search": str(filters.get("search") or "").strip(),
            "status": str(filters.get("status") or "all").strip() or "all",
            "page_size": max(1, min(100, int(filters.get("page_size") or 8))),
        },
        "created_by_user_id": current_user_id,
        "created_at": now,
        "updated_at": now,
        "schema_version": SETTINGS_SCHEMA_VERSION,
    }
    result = await database.club_queue_views.insert_one(document)
    stored = await database.club_queue_views.find_one({"_id": result.inserted_id})
    await _prune_shared_queue_views(scope_type=scope_type, scope_id=scope_id, queue_type=queue_type, database=database)
    return _view_public(
        stored or {**document, "_id": result.inserted_id},
        created_by_label=await _resolve_user_label(current_user_id, database=database),
    )


async def delete_shared_queue_view(
    *,
    view_id: str,
    scope_type: str,
    scope_id: str,
    queue_type: str,
    database: Any | None = None,
) -> bool:
    database = database if database is not None else db
    if not ObjectId.is_valid(view_id):
        return False
    result = await database.club_queue_views.delete_one(
        {
            "_id": ObjectId(view_id),
            "scope_type": scope_type,
            "scope_id": scope_id,
            "queue_type": queue_type,
        }
    )
    return bool(getattr(result, "deleted_count", 0))


async def _prune_shared_queue_views(
    *,
    scope_type: str,
    scope_id: str,
    queue_type: str,
    database: Any | None = None,
) -> None:
    database = database if database is not None else db
    rows = await database.club_queue_views.find(
        {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "queue_type": queue_type,
        }
    ).sort([("updated_at", -1), ("created_at", -1)]).to_list(length=MAX_SHARED_QUEUE_VIEWS + 20)
    for row in rows[MAX_SHARED_QUEUE_VIEWS:]:
        await database.club_queue_views.delete_one({"_id": row.get("_id")})


async def list_shared_queue_snapshots(
    *,
    scope_type: str,
    scope_id: str,
    queue_type: str,
    limit: int = 12,
    database: Any | None = None,
) -> list[dict[str, Any]]:
    database = database if database is not None else db
    scoped_limit = max(1, min(MAX_SHARED_QUEUE_SNAPSHOTS, int(limit)))
    rows = await database.club_queue_snapshots.find(
        {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "queue_type": queue_type,
        }
    ).sort("captured_at", -1).limit(scoped_limit).to_list(length=scoped_limit)
    output: list[dict[str, Any]] = []
    for row in rows:
        output.append(_snapshot_public(row, changed_by_label=await _resolve_user_label(row.get("changed_by_user_id"), database=database)))
    return output


async def _persist_shared_queue_snapshot(
    *,
    scope_type: str,
    scope_id: str,
    queue_type: str,
    snapshot: dict[str, Any],
    changed_by_user_id: str | None,
    source_action: str | None,
    database: Any | None = None,
) -> dict[str, Any]:
    database = database if database is not None else db
    latest = await database.club_queue_snapshots.find_one(
        {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "queue_type": queue_type,
        },
        sort=[("captured_at", -1)],
    )
    if latest and latest.get("signature") == snapshot.get("signature"):
        return _snapshot_public(latest, changed_by_label=await _resolve_user_label(latest.get("changed_by_user_id"), database=database))

    document = {
        "scope_type": scope_type,
        "scope_id": scope_id,
        "queue_type": queue_type,
        "total": int(snapshot.get("total") or 0),
        "pending": int(snapshot.get("pending") or 0),
        "waitlisted": int(snapshot.get("waitlisted") or 0),
        "fresh": int(snapshot.get("fresh") or 0),
        "aging": int(snapshot.get("aging") or 0),
        "stale": int(snapshot.get("stale") or 0),
        "signature": snapshot.get("signature"),
        "captured_at": snapshot.get("captured_at") or _utc_now(),
        "source_action": source_action,
        "changed_by_user_id": changed_by_user_id,
        "schema_version": SETTINGS_SCHEMA_VERSION,
    }
    result = await database.club_queue_snapshots.insert_one(document)
    stored = await database.club_queue_snapshots.find_one({"_id": result.inserted_id})
    await _prune_shared_queue_snapshots(scope_type=scope_type, scope_id=scope_id, queue_type=queue_type, database=database)
    return _snapshot_public(
        stored or {**document, "_id": result.inserted_id},
        changed_by_label=await _resolve_user_label(changed_by_user_id, database=database),
    )


async def _prune_shared_queue_snapshots(
    *,
    scope_type: str,
    scope_id: str,
    queue_type: str,
    database: Any | None = None,
) -> None:
    database = database if database is not None else db
    rows = await database.club_queue_snapshots.find(
        {
            "scope_type": scope_type,
            "scope_id": scope_id,
            "queue_type": queue_type,
        }
    ).sort("captured_at", -1).to_list(length=MAX_SHARED_QUEUE_SNAPSHOTS + 40)
    for row in rows[MAX_SHARED_QUEUE_SNAPSHOTS:]:
        await database.club_queue_snapshots.delete_one({"_id": row.get("_id")})


def _build_queue_snapshot(rows: list[dict[str, Any]], *, created_at_field: str, signature_prefix: str) -> dict[str, Any]:
    counts = {"fresh": 0, "aging": 0, "stale": 0}
    pending = 0
    waitlisted = 0
    for row in rows:
        status = str(row.get("status") or "")
        if status == "pending":
            pending += 1
        elif status == "waitlisted":
            waitlisted += 1
        bucket = _queue_age_bucket(row.get(created_at_field))
        counts[bucket] += 1
    total = len(rows)
    return {
        "total": total,
        "pending": pending,
        "waitlisted": waitlisted,
        "fresh": counts["fresh"],
        "aging": counts["aging"],
        "stale": counts["stale"],
        "signature": f"{signature_prefix}-{total}-{pending}-{waitlisted}-{counts['fresh']}-{counts['aging']}-{counts['stale']}",
        "captured_at": _utc_now(),
    }


async def record_membership_queue_snapshot(
    *,
    club_id: str,
    changed_by_user_id: str | None = None,
    source_action: str | None = None,
    database: Any | None = None,
) -> dict[str, Any]:
    database = database if database is not None else db
    rows = await database.club_applications.find(
        {
            "club_id": club_id,
            "status": {"$in": list(PENDING_QUEUE_STATUSES)},
        }
    ).to_list(length=2000)
    snapshot = _build_queue_snapshot(rows, created_at_field="applied_at", signature_prefix="membership")
    return await _persist_shared_queue_snapshot(
        scope_type="club",
        scope_id=club_id,
        queue_type="membership",
        snapshot=snapshot,
        changed_by_user_id=changed_by_user_id,
        source_action=source_action,
        database=database,
    )


async def record_event_queue_snapshot(
    *,
    event_id: str,
    changed_by_user_id: str | None = None,
    source_action: str | None = None,
    database: Any | None = None,
) -> dict[str, Any]:
    database = database if database is not None else db
    rows = await database.event_registrations.find(
        {
            "event_id": event_id,
            "status": {"$in": list(PENDING_QUEUE_STATUSES)},
        }
    ).to_list(length=2000)
    snapshot = _build_queue_snapshot(rows, created_at_field="created_at", signature_prefix="enrollment")
    return await _persist_shared_queue_snapshot(
        scope_type="event",
        scope_id=event_id,
        queue_type="enrollment",
        snapshot=snapshot,
        changed_by_user_id=changed_by_user_id,
        source_action=source_action,
        database=database,
    )
