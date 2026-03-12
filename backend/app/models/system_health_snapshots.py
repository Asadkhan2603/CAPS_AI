from __future__ import annotations

from typing import Any

from app.core.schema_versions import (
    SYSTEM_HEALTH_SNAPSHOT_SCHEMA_VERSION,
    normalize_schema_version,
)


def system_health_snapshot_public(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "bucket_minute": document.get("bucket_minute"),
        "recorded_at": document.get("recorded_at"),
        "db_status": document.get("db_status"),
        "alert_count": int(document.get("alert_count") or 0),
        "requests_15m": int(document.get("requests_15m") or 0),
        "server_error_rate_pct_15m": float(document.get("server_error_rate_pct_15m") or 0.0),
        "p95_duration_ms_15m": document.get("p95_duration_ms_15m"),
        "queued_jobs": int(document.get("queued_jobs") or 0),
        "running_jobs": int(document.get("running_jobs") or 0),
        "failed_jobs": int(document.get("failed_jobs") or 0),
        "oldest_queued_age_seconds": document.get("oldest_queued_age_seconds"),
        "fallback_rate_pct_15m": float(document.get("fallback_rate_pct_15m") or 0.0),
        "similarity_candidate_count": document.get("similarity_candidate_count"),
        "retained_rows": int(document.get("retained_rows") or 0),
        "max_retained_rows": int(document.get("max_retained_rows") or 0),
        "last_pruned_deleted_count": int(document.get("last_pruned_deleted_count") or 0),
        "is_within_retention_bound": bool(document.get("is_within_retention_bound", True)),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=SYSTEM_HEALTH_SNAPSHOT_SCHEMA_VERSION,
        ),
    }
