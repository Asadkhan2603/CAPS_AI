from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.ai_similarity_views import list_shared_similarity_views

DEFAULT_SIMILARITY_QUEUES = [
    {"id": "all", "label": "All flagged", "filters": {}},
    {"id": "needs-review", "label": "Needs review", "filters": {"review_status": "open"}},
    {"id": "reopened", "label": "Reopened", "filters": {"review_status": "reopened"}},
    {"id": "low-text-risk", "label": "Low text risk", "filters": {"low_extraction_quality": True}},
    {"id": "high-drift", "label": "High semantic drift", "filters": {"semantic_drift_present": True, "review_status": "open"}},
    {"id": "cap-reached", "label": "Cap reached", "filters": {"cap_reached": True}},
]


def _normalize_datetime(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _has_low_extraction_quality(item: dict[str, Any]) -> bool:
    extraction_quality = item.get("extraction_quality")
    if not isinstance(extraction_quality, dict):
        return False
    values = [
        float(value)
        for value in (extraction_quality.get("source"), extraction_quality.get("matched"))
        if isinstance(value, (int, float))
    ]
    return any(value < 0.5 for value in values)


def _has_semantic_drift(item: dict[str, Any], *, semantic_drift_threshold: float) -> bool:
    lexical_score = item.get("score")
    semantic_score = item.get("semantic_shadow_score")
    if not isinstance(lexical_score, (int, float)) or not isinstance(semantic_score, (int, float)):
        return False
    return float(semantic_score) - float(lexical_score) >= float(semantic_drift_threshold)


def _matches_search(item: dict[str, Any], search: str) -> bool:
    normalized = str(search or "").strip().lower()
    if not normalized:
        return True
    haystack = " ".join(
        str(value or "")
        for value in (
            item.get("source_submission_id"),
            item.get("matched_submission_id"),
            item.get("source_assignment_id"),
            item.get("matched_assignment_id"),
            item.get("review_notes"),
        )
    ).lower()
    return normalized in haystack


def _matches_filters(item: dict[str, Any], filters: dict[str, Any], *, semantic_drift_threshold: float) -> bool:
    review_status = str(filters.get("review_status") or "").strip().lower()
    if review_status and str(item.get("review_status") or "").strip().lower() != review_status:
        return False
    if filters.get("semantic_drift_present") and not _has_semantic_drift(item, semantic_drift_threshold=semantic_drift_threshold):
        return False
    if filters.get("cap_reached") and not bool(item.get("cap_reached")):
        return False
    if filters.get("low_extraction_quality") and not _has_low_extraction_quality(item):
        return False
    if filters.get("min_score") not in {None, ""}:
        score = item.get("score")
        if not isinstance(score, (int, float)) or float(score) < float(filters.get("min_score")):
            return False
    if filters.get("max_score") not in {None, ""}:
        score = item.get("score")
        if not isinstance(score, (int, float)) or float(score) > float(filters.get("max_score")):
            return False
    if not _matches_search(item, str(filters.get("search") or "")):
        return False
    return True


def _build_metric_entry(
    *,
    queue_id: str,
    label: str,
    filters: dict[str, Any],
    rows: list[dict[str, Any]],
    semantic_drift_threshold: float,
    created_by_label: str | None = None,
    created_by_user_id: str | None = None,
) -> dict[str, Any]:
    matched_rows = [row for row in rows if _matches_filters(row, filters, semantic_drift_threshold=semantic_drift_threshold)]
    status_counts = {"open": 0, "in_progress": 0, "fixed": 0, "reopened": 0}
    low_extraction_count = 0
    semantic_drift_count = 0
    cap_reached_count = 0
    age_hours: list[float] = []
    now = datetime.now(timezone.utc)

    for row in matched_rows:
        normalized_status = str(row.get("review_status") or "open").strip().lower()
        if normalized_status in status_counts:
            status_counts[normalized_status] += 1
        if _has_low_extraction_quality(row):
            low_extraction_count += 1
        if _has_semantic_drift(row, semantic_drift_threshold=semantic_drift_threshold):
            semantic_drift_count += 1
        if row.get("cap_reached"):
            cap_reached_count += 1
        created_at = _normalize_datetime(row.get("created_at"))
        if created_at is not None:
            age_hours.append(max(0.0, (now - created_at).total_seconds() / 3600.0))

    count = len(matched_rows)
    return {
        "id": queue_id,
        "label": label,
        "filters": filters,
        "count": count,
        "status_counts": status_counts,
        "open_count": status_counts["open"],
        "reopened_count": status_counts["reopened"],
        "low_extraction_count": low_extraction_count,
        "semantic_drift_count": semantic_drift_count,
        "cap_reached_count": cap_reached_count,
        "average_age_hours": round(sum(age_hours) / len(age_hours), 2) if age_hours else None,
        "oldest_age_hours": round(max(age_hours), 2) if age_hours else None,
        "reopened_rate": round(status_counts["reopened"] / count, 3) if count else 0.0,
        "low_extraction_rate": round(low_extraction_count / count, 3) if count else 0.0,
        "semantic_drift_rate": round(semantic_drift_count / count, 3) if count else 0.0,
        "created_by_label": created_by_label,
        "created_by_user_id": created_by_user_id,
    }


def _forecast_from_metric(metric: dict[str, Any]) -> dict[str, Any]:
    count = int(metric.get("count") or 0)
    average_age_hours = metric.get("average_age_hours")
    oldest_age_hours = metric.get("oldest_age_hours")
    numeric_oldest = float(oldest_age_hours) if isinstance(oldest_age_hours, (int, float)) else 0.0

    backlog_risk = "low"
    reason = "Queue is within the expected reviewer handling window."
    if count >= 15 or numeric_oldest >= 72:
        backlog_risk = "high"
        reason = "Queue volume or oldest case age is high enough to risk delayed reviewer action."
    elif count >= 7 or numeric_oldest >= 24:
        backlog_risk = "medium"
        reason = "Queue is growing or aging; reviewers should triage this view soon."

    return {
        "id": metric.get("id"),
        "label": metric.get("label"),
        "count": count,
        "average_age_hours": average_age_hours,
        "oldest_age_hours": oldest_age_hours,
        "backlog_risk": backlog_risk,
        "attention_badge": backlog_risk in {"medium", "high"},
        "reason": reason,
        "created_by_label": metric.get("created_by_label"),
        "created_by_user_id": metric.get("created_by_user_id"),
    }


async def build_similarity_queue_metrics(
    *,
    database: Any,
    similarity_scope_query: dict[str, Any],
    semantic_drift_threshold: float,
) -> dict[str, Any]:
    scoped_query = similarity_scope_query.copy() if similarity_scope_query else {}
    scoped_query["is_flagged"] = True
    rows = await database.similarity_logs.find(scoped_query).to_list(length=5000)
    shared_views = await list_shared_similarity_views(database=database)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "default_queues": [
            _build_metric_entry(
                queue_id=queue["id"],
                label=queue["label"],
                filters=queue["filters"],
                rows=rows,
                semantic_drift_threshold=semantic_drift_threshold,
            )
            for queue in DEFAULT_SIMILARITY_QUEUES
        ],
        "shared_views": [
            _build_metric_entry(
                queue_id=view["id"],
                label=str(view.get("name") or "Shared view"),
                filters=view.get("filters") or {},
                rows=rows,
                semantic_drift_threshold=semantic_drift_threshold,
                created_by_label=view.get("created_by_label"),
                created_by_user_id=view.get("created_by_user_id"),
            )
            for view in shared_views
        ],
    }


def build_similarity_queue_forecast(queue_metrics: dict[str, Any]) -> dict[str, Any]:
    default_queues = [
        _forecast_from_metric(metric)
        for metric in (queue_metrics.get("default_queues") or [])
        if isinstance(metric, dict)
    ]
    shared_views = [
        _forecast_from_metric(metric)
        for metric in (queue_metrics.get("shared_views") or [])
        if isinstance(metric, dict)
    ]
    return {
        "generated_at": queue_metrics.get("generated_at"),
        "default_queues": default_queues,
        "shared_views": shared_views,
    }
