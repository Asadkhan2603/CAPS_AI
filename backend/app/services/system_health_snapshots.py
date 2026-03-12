from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.database import db
from app.core.schema_versions import SYSTEM_HEALTH_SNAPSHOT_SCHEMA_VERSION
from app.models.system_health_snapshots import system_health_snapshot_public

SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES = 24 * 60
_last_pruned_bucket: str | None = None
_last_pruned_at: datetime | None = None
_last_pruned_deleted_count = 0


def _minute_bucket(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc).replace(second=0, microsecond=0)
    return normalized.isoformat()


def _retention_cutoff_bucket(value: datetime) -> str:
    return _minute_bucket(value.replace(second=0, microsecond=0) - timedelta(minutes=SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES))


async def prune_system_health_snapshots(
    *,
    now: datetime,
    database: Any = db,
) -> int:
    global _last_pruned_bucket, _last_pruned_at, _last_pruned_deleted_count

    current_bucket = _minute_bucket(now)
    if _last_pruned_bucket == current_bucket:
        return 0

    cutoff_bucket = _retention_cutoff_bucket(now)
    result = await database.system_health_snapshots.delete_many(
        {"bucket_minute": {"$lt": cutoff_bucket}},
    )
    _last_pruned_bucket = current_bucket
    _last_pruned_at = now
    _last_pruned_deleted_count = int(getattr(result, "deleted_count", 0) or 0)
    return _last_pruned_deleted_count


async def persist_system_health_snapshot(
    *,
    payload: dict[str, Any],
    database: Any = db,
) -> dict[str, Any]:
    now = payload.get("timestamp")
    if not isinstance(now, datetime):
        now = datetime.now(timezone.utc)

    observability = payload.get("observability") or {}
    request_metrics = observability.get("request_metrics") or {}
    ai_metrics = observability.get("ai_metrics") or {}

    document = {
        "bucket_minute": _minute_bucket(now),
        "recorded_at": now,
        "db_status": payload.get("db_status"),
        "alert_count": int(payload.get("alert_count") or 0),
        "requests_15m": int(request_metrics.get("requests_15m") or 0),
        "server_error_rate_pct_15m": float(request_metrics.get("server_error_rate_pct_15m") or 0.0),
        "p95_duration_ms_15m": request_metrics.get("p95_duration_ms_15m"),
        "queued_jobs": int(ai_metrics.get("queued_jobs") or 0),
        "running_jobs": int(ai_metrics.get("running_jobs") or 0),
        "failed_jobs": int(ai_metrics.get("failed_jobs") or 0),
        "oldest_queued_age_seconds": ai_metrics.get("oldest_queued_age_seconds"),
        "fallback_rate_pct_15m": float(ai_metrics.get("fallback_rate_pct_15m") or 0.0),
        "similarity_candidate_count": ai_metrics.get("last_similarity_candidate_count"),
        "schema_version": SYSTEM_HEALTH_SNAPSHOT_SCHEMA_VERSION,
    }

    await database.system_health_snapshots.update_one(
        {"bucket_minute": document["bucket_minute"]},
        {"$set": document},
        upsert=True,
    )
    await prune_system_health_snapshots(now=now, database=database)

    retained_rows = int(await database.system_health_snapshots.count_documents({}))
    max_retained_rows = SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES + 1
    retention_fields = {
        "retained_rows": retained_rows,
        "max_retained_rows": max_retained_rows,
        "last_pruned_deleted_count": int(_last_pruned_deleted_count),
        "is_within_retention_bound": retained_rows <= max_retained_rows,
    }
    document.update(retention_fields)
    await database.system_health_snapshots.update_one(
        {"bucket_minute": document["bucket_minute"]},
        {"$set": retention_fields},
        upsert=False,
    )
    return system_health_snapshot_public(document)


async def get_system_health_snapshot_history(
    *,
    limit: int = 120,
    database: Any = db,
) -> list[dict[str, Any]]:
    scoped_limit = max(1, min(720, int(limit)))
    rows = await database.system_health_snapshots.find({}).sort("bucket_minute", -1).limit(scoped_limit).to_list(length=scoped_limit)
    return [system_health_snapshot_public(row) for row in rows]


async def get_system_health_snapshot_store_status(
    *,
    database: Any = db,
) -> dict[str, Any]:
    retained_rows = await database.system_health_snapshots.count_documents({})
    max_retained_rows = SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES + 1
    return {
        "retention_minutes": SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES,
        "max_retained_rows": max_retained_rows,
        "retained_rows": int(retained_rows),
        "last_pruned_bucket": _last_pruned_bucket,
        "last_pruned_at": _last_pruned_at,
        "last_pruned_deleted_count": int(_last_pruned_deleted_count),
        "is_within_retention_bound": int(retained_rows) <= max_retained_rows,
    }
