from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.core.database import db
from app.core.schema_versions import SYSTEM_HEALTH_SNAPSHOT_SCHEMA_VERSION
from app.models.system_health_snapshots import system_health_snapshot_public

SYSTEM_HEALTH_SNAPSHOT_RETENTION_DAYS = 14
SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES = SYSTEM_HEALTH_SNAPSHOT_RETENTION_DAYS * 24 * 60
SYSTEM_HEALTH_SNAPSHOT_HISTORY_LIMIT = 720
_last_pruned_bucket: str | None = None
_last_pruned_at: datetime | None = None
_last_pruned_deleted_count = 0


def _as_utc_datetime(value: Any) -> datetime | None:
    if value is None:
        return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _minute_bucket(value: datetime) -> str:
    normalized = value.astimezone(timezone.utc).replace(second=0, microsecond=0)
    return normalized.isoformat()


def _retention_cutoff_bucket(value: datetime) -> str:
    return _minute_bucket(value.replace(second=0, microsecond=0) - timedelta(minutes=SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES))


def _bucket_start(value: datetime, *, minutes: int) -> datetime:
    normalized = value.astimezone(timezone.utc).replace(second=0, microsecond=0)
    bucket_minute = (normalized.minute // minutes) * minutes
    return normalized.replace(minute=0) + timedelta(minutes=bucket_minute)


def _club_pressure_level(*, requests_peak: int, p95_peak: float | int | None, slow_total: int, error_total: int) -> str:
    slow_threshold_ms = int(settings.observability_slow_request_ms)
    slow_alert_threshold = max(3, int(settings.observability_slow_request_count_alert_threshold) // 2)
    if error_total > 0:
        return "critical"
    if requests_peak >= 5 and isinstance(p95_peak, (int, float)) and p95_peak >= slow_threshold_ms * 2:
        return "critical"
    if slow_total >= slow_alert_threshold:
        return "critical"
    if requests_peak >= 5 and (
        (isinstance(p95_peak, (int, float)) and p95_peak >= slow_threshold_ms)
        or slow_total > 0
    ):
        return "warning"
    return "ok"


def _bucketized_club_history(rows: list[dict[str, Any]], *, bucket_minutes: int) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        recorded_at = _as_utc_datetime(row.get("recorded_at"))
        if not recorded_at:
            continue
        bucket_start = _bucket_start(recorded_at, minutes=bucket_minutes)
        bucket_key = bucket_start.isoformat()
        entry = grouped.setdefault(
            bucket_key,
            {
                "bucket_start": bucket_start,
                "requests": [],
                "p95": [],
                "slow_total": 0,
                "error_total": 0,
                "samples": 0,
            },
        )
        entry["samples"] += 1
        entry["requests"].append(int(row.get("club_requests_15m") or 0))
        p95 = row.get("club_p95_duration_ms_15m")
        if isinstance(p95, (int, float)):
            entry["p95"].append(float(p95))
        entry["slow_total"] += int(row.get("club_slow_requests_15m") or 0)
        entry["error_total"] += int(row.get("club_server_errors_15m") or 0)

    points: list[dict[str, Any]] = []
    for entry in sorted(grouped.values(), key=lambda item: item["bucket_start"]):
        requests_values = entry["requests"]
        p95_values = entry["p95"]
        requests_peak = max(requests_values, default=0)
        p95_peak = max(p95_values, default=None)
        point = {
            "bucket_start": entry["bucket_start"].isoformat(),
            "samples": entry["samples"],
            "club_requests_avg": round(sum(requests_values) / len(requests_values), 2) if requests_values else 0.0,
            "club_requests_peak": requests_peak,
            "club_p95_duration_ms_avg": round(sum(p95_values) / len(p95_values), 2) if p95_values else None,
            "club_p95_duration_ms_peak": round(p95_peak, 2) if isinstance(p95_peak, (int, float)) else None,
            "club_slow_requests_total": entry["slow_total"],
            "club_server_errors_total": entry["error_total"],
        }
        point["pressure_level"] = _club_pressure_level(
            requests_peak=requests_peak,
            p95_peak=point["club_p95_duration_ms_peak"],
            slow_total=entry["slow_total"],
            error_total=entry["error_total"],
        )
        points.append(point)
    return points


def _summarize_club_history(*, hourly_24h: list[dict[str, Any]], daily_14d: list[dict[str, Any]]) -> dict[str, Any]:
    pressure_windows_24h = [point for point in hourly_24h if point["pressure_level"] in {"warning", "critical"}]
    critical_windows_24h = [point for point in pressure_windows_24h if point["pressure_level"] == "critical"]
    pressure_days_14d = [point for point in daily_14d if point["pressure_level"] in {"warning", "critical"}]
    return {
        "retention_days": SYSTEM_HEALTH_SNAPSHOT_RETENTION_DAYS,
        "hourly_windows_24h": len(hourly_24h),
        "pressure_windows_24h": len(pressure_windows_24h),
        "critical_windows_24h": len(critical_windows_24h),
        "active_windows_24h": sum(1 for point in hourly_24h if point["club_requests_peak"] > 0),
        "peak_requests_24h": max((point["club_requests_peak"] for point in hourly_24h), default=0),
        "peak_p95_duration_ms_24h": max(
            (point["club_p95_duration_ms_peak"] or 0 for point in hourly_24h),
            default=0,
        ),
        "pressure_days_14d": len(pressure_days_14d),
        "peak_requests_14d": max((point["club_requests_peak"] for point in daily_14d), default=0),
        "peak_p95_duration_ms_14d": max(
            (point["club_p95_duration_ms_peak"] or 0 for point in daily_14d),
            default=0,
        ),
        "latest_pressure_level": hourly_24h[-1]["pressure_level"] if hourly_24h else "ok",
    }


async def _get_raw_system_health_snapshot_rows(
    *,
    limit: int,
    database: Any = db,
) -> list[dict[str, Any]]:
    scoped_limit = max(1, min(SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES + 1, int(limit)))
    return await database.system_health_snapshots.find({}).sort("bucket_minute", -1).limit(scoped_limit).to_list(length=scoped_limit)


def _snapshot_store_status_from_document(document: dict[str, Any]) -> dict[str, Any]:
    retained_rows = int(document.get("retained_rows") or 0)
    max_retained_rows = int(document.get("max_retained_rows") or (SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES + 1))
    return {
        "retention_minutes": SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES,
        "retention_days": SYSTEM_HEALTH_SNAPSHOT_RETENTION_DAYS,
        "max_retained_rows": max_retained_rows,
        "retained_rows": retained_rows,
        "last_pruned_bucket": document.get("last_pruned_bucket") or _last_pruned_bucket,
        "last_pruned_at": document.get("last_pruned_at") or _last_pruned_at,
        "last_pruned_deleted_count": int(document.get("last_pruned_deleted_count") or 0),
        "is_within_retention_bound": bool(document.get("is_within_retention_bound", retained_rows <= max_retained_rows)),
    }


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
    clubs_metrics = observability.get("clubs_metrics") or {}
    ai_metrics = observability.get("ai_metrics") or {}

    document = {
        "bucket_minute": _minute_bucket(now),
        "recorded_at": now,
        "db_status": payload.get("db_status"),
        "alert_count": int(payload.get("alert_count") or 0),
        "requests_15m": int(request_metrics.get("requests_15m") or 0),
        "server_error_rate_pct_15m": float(request_metrics.get("server_error_rate_pct_15m") or 0.0),
        "p95_duration_ms_15m": request_metrics.get("p95_duration_ms_15m"),
        "club_requests_15m": int(clubs_metrics.get("requests_15m") or 0),
        "club_slow_requests_15m": int(clubs_metrics.get("slow_requests_15m") or 0),
        "club_server_errors_15m": int(clubs_metrics.get("server_errors_15m") or 0),
        "club_p95_duration_ms_15m": clubs_metrics.get("p95_duration_ms_15m"),
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
        "last_pruned_bucket": _last_pruned_bucket,
        "last_pruned_at": _last_pruned_at,
        "is_within_retention_bound": retained_rows <= max_retained_rows,
    }
    stored_payload = deepcopy(payload)
    stored_payload.pop("snapshot_history", None)
    stored_payload["snapshot_store"] = _snapshot_store_status_from_document({**document, **retention_fields})
    document["payload"] = stored_payload
    document.update(retention_fields)
    await database.system_health_snapshots.update_one(
        {"bucket_minute": document["bucket_minute"]},
        {"$set": {"payload": stored_payload, **retention_fields}},
        upsert=False,
    )
    return system_health_snapshot_public(document)


async def get_system_health_snapshot_history(
    *,
    limit: int = 120,
    database: Any = db,
) -> list[dict[str, Any]]:
    scoped_limit = max(1, min(SYSTEM_HEALTH_SNAPSHOT_HISTORY_LIMIT, int(limit)))
    rows = await _get_raw_system_health_snapshot_rows(limit=scoped_limit, database=database)
    return [system_health_snapshot_public(row) for row in rows]


async def get_clubs_observability_history(
    *,
    database: Any = db,
) -> dict[str, Any]:
    rows = await _get_raw_system_health_snapshot_rows(
        limit=SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES + 1,
        database=database,
    )
    normalized_rows = []
    for row in rows:
        normalized_rows.append({**row, "recorded_at": _as_utc_datetime(row.get("recorded_at"))})
    ordered_rows = sorted(
        normalized_rows,
        key=lambda item: item.get("recorded_at") or datetime.min.replace(tzinfo=timezone.utc),
    )
    now = datetime.now(timezone.utc)
    last_24h_cutoff = now - timedelta(hours=24)
    last_14d_cutoff = now - timedelta(days=SYSTEM_HEALTH_SNAPSHOT_RETENTION_DAYS)
    rows_24h = [
        row for row in ordered_rows
        if row.get("recorded_at") and row["recorded_at"] >= last_24h_cutoff
    ]
    rows_14d = [
        row for row in ordered_rows
        if row.get("recorded_at") and row["recorded_at"] >= last_14d_cutoff
    ]
    hourly_24h = _bucketized_club_history(rows_24h, bucket_minutes=60)
    daily_14d = _bucketized_club_history(rows_14d, bucket_minutes=24 * 60)
    recent_pressure_windows = [
        point for point in reversed(hourly_24h)
        if point["pressure_level"] in {"warning", "critical"}
    ][:8]
    return {
        "summary": _summarize_club_history(hourly_24h=hourly_24h, daily_14d=daily_14d),
        "hourly_24h": hourly_24h,
        "daily_14d": daily_14d,
        "recent_pressure_windows": recent_pressure_windows,
    }


async def get_system_health_snapshot_store_status(
    *,
    database: Any = db,
) -> dict[str, Any]:
    retained_rows = await database.system_health_snapshots.count_documents({})
    max_retained_rows = SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES + 1
    return {
        "retention_minutes": SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES,
        "retention_days": SYSTEM_HEALTH_SNAPSHOT_RETENTION_DAYS,
        "max_retained_rows": max_retained_rows,
        "retained_rows": int(retained_rows),
        "last_pruned_bucket": _last_pruned_bucket,
        "last_pruned_at": _last_pruned_at,
        "last_pruned_deleted_count": int(_last_pruned_deleted_count),
        "is_within_retention_bound": int(retained_rows) <= max_retained_rows,
    }


async def get_latest_system_health_snapshot_payload(
    *,
    max_age_seconds: int | None = None,
    database: Any = db,
) -> tuple[dict[str, Any] | None, int | None]:
    document = await database.system_health_snapshots.find_one({}, sort=[("recorded_at", -1)])
    if not document:
        return None, None

    recorded_at = document.get("recorded_at")
    if not isinstance(recorded_at, datetime):
        return None, None
    if recorded_at.tzinfo is None:
        recorded_at = recorded_at.replace(tzinfo=timezone.utc)
    else:
        recorded_at = recorded_at.astimezone(timezone.utc)

    age_seconds = max(0, int((datetime.now(timezone.utc) - recorded_at).total_seconds()))
    freshness_seconds = max_age_seconds
    if freshness_seconds is None:
        freshness_seconds = max(1, int(settings.system_health_snapshot_freshness_seconds))
    if age_seconds > freshness_seconds:
        return None, age_seconds

    payload = deepcopy(document.get("payload") or {})
    if not payload:
        return None, age_seconds

    payload["snapshot_store"] = _snapshot_store_status_from_document(document)
    payload["snapshot_history"] = await get_system_health_snapshot_history(database=database)
    payload["clubs_observability"] = await get_clubs_observability_history(database=database)
    return payload, age_seconds
