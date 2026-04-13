from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from app.core.config import settings


_FINAL_STATUSES = {"fixed", "reopened"}
_KNOWN_REVIEW_STATUSES = ("open", "in_progress", "fixed", "reopened")
_REOPENED_REASON_LABELS = {
    "low_evidence": "Low evidence",
    "extraction_quality": "Extraction quality",
    "common_prompt_language": "Common prompt language",
    "allowed_collaboration": "Allowed collaboration",
    "multilingual_mismatch": "Multilingual mismatch",
    "assignment_context_mismatch": "Assignment context mismatch",
    "other": "Other reviewer reason",
}
_REOPENED_REASON_RULES = (
    ("Low evidence", ("insufficient", "not enough evidence", "weak evidence", "unclear", "manual review", "needs more review")),
    ("Extraction quality", ("ocr", "scan", "extraction", "extract", "low text", "text missing", "pdf")),
    ("Common prompt language", ("boilerplate", "template", "common prompt", "prompt term", "same question", "provided material")),
    ("Allowed collaboration", ("legitimate collaboration", "group work", "allowed collaboration", "shared lab", "collaboration allowed")),
    ("Multilingual mismatch", ("hindi", "translation", "multilingual", "language", "unicode")),
    ("Assignment context mismatch", ("rubric", "assignment context", "reference material", "same source", "teacher-provided")),
)
_DRIFT_BUCKETS = (
    {"label": "<0.00", "min": None, "max": 0.0},
    {"label": "0.00-0.05", "min": 0.0, "max": 0.05},
    {"label": "0.05-0.15", "min": 0.05, "max": 0.15},
    {"label": "0.15-0.30", "min": 0.15, "max": 0.30},
    {"label": ">=0.30", "min": 0.30, "max": None},
)


def _normalize_status(value: Any) -> str:
    normalized = str(value or "open").strip().lower()
    return normalized if normalized in _KNOWN_REVIEW_STATUSES else "open"


def _numeric(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _rounded(value: float | None, digits: int = 4) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def _percentile(values: list[float], target: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * target)))
    return ordered[index]


def _semantic_drift(row: dict[str, Any]) -> float | None:
    semantic_score = _numeric(row.get("semantic_shadow_score"))
    lexical_score = _numeric(row.get("score"))
    if semantic_score is None or lexical_score is None:
        return None
    return semantic_score - lexical_score


def _review_timestamp(row: dict[str, Any]) -> datetime | None:
    value = row.get("reviewed_at") or row.get("created_at")
    return value if isinstance(value, datetime) else None


def _build_threshold_snapshot(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fixed_rows = [row for row in rows if _normalize_status(row.get("review_status")) == "fixed"]
    reopened_rows = [row for row in rows if _normalize_status(row.get("review_status")) == "reopened"]
    fixed_drifts = [value for value in (_semantic_drift(row) for row in fixed_rows) if value is not None]
    reopened_drifts = [value for value in (_semantic_drift(row) for row in reopened_rows) if value is not None]
    fixed_semantic_scores = [value for value in (_numeric(row.get("semantic_shadow_score")) for row in fixed_rows) if value is not None]
    reopened_semantic_scores = [value for value in (_numeric(row.get("semantic_shadow_score")) for row in reopened_rows) if value is not None]
    fixed_low_drift = _percentile(fixed_drifts, 0.25)
    reopened_high_drift = _percentile(reopened_drifts, 0.9)
    fixed_low_semantic = _percentile(fixed_semantic_scores, 0.25)
    reopened_high_semantic = _percentile(reopened_semantic_scores, 0.9)
    assist_only_threshold = _rounded(
        max(
            float(settings.semantic_shadow_calibration_paraphrase_advantage_min),
            float(fixed_low_drift)
            if fixed_low_drift is not None
            else float(settings.semantic_shadow_calibration_paraphrase_advantage_min),
        ),
        4,
    )
    promotion_ready = (
        len(fixed_rows) >= 3
        and len(reopened_rows) >= 2
        and fixed_low_drift is not None
        and reopened_high_drift is not None
        and fixed_low_semantic is not None
        and reopened_high_semantic is not None
        and fixed_low_drift > reopened_high_drift
        and fixed_low_semantic > reopened_high_semantic
    )
    return {
        "fixed_rows": fixed_rows,
        "reopened_rows": reopened_rows,
        "fixed_drifts": fixed_drifts,
        "reopened_drifts": reopened_drifts,
        "fixed_low_drift": fixed_low_drift,
        "reopened_high_drift": reopened_high_drift,
        "fixed_low_semantic": fixed_low_semantic,
        "reopened_high_semantic": reopened_high_semantic,
        "assist_only_threshold": assist_only_threshold,
        "promotion_ready": promotion_ready,
    }


def _categorize_reopened_reason(reason_code: str | None, note: str | None) -> str:
    normalized_code = str(reason_code or "").strip().lower()
    if normalized_code in _REOPENED_REASON_LABELS:
        return _REOPENED_REASON_LABELS[normalized_code]
    normalized = str(note or "").strip().lower()
    if not normalized:
        return "No reviewer note"
    for label, keywords in _REOPENED_REASON_RULES:
        if any(keyword in normalized for keyword in keywords):
            return label
    return "Other reviewer reason"


def _build_reopened_reason_summary(rows: list[dict[str, Any]], *, limit: int = 5) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        label = _categorize_reopened_reason(row.get("review_reason_code"), row.get("review_notes"))
        bucket = grouped.setdefault(
            label,
            {"reason": label, "count": 0, "example_note": None},
        )
        bucket["count"] += 1
        note = str(row.get("review_notes") or "").strip()
        if note and not bucket["example_note"]:
            bucket["example_note"] = note[:160]
    return sorted(grouped.values(), key=lambda item: (-int(item["count"]), str(item["reason"])))[:limit]


def _trend_symbol(delta: int) -> tuple[str, str]:
    if delta > 0:
        return "up", "↑"
    if delta < 0:
        return "down", "↓"
    return "flat", "→"


def _build_reopened_reason_trends(rows: list[dict[str, Any]], *, window_days: int = 7, limit: int = 6) -> list[dict[str, Any]]:
    timed_rows = []
    for row in rows:
        timestamp = _review_timestamp(row)
        if not timestamp:
            continue
        timed_rows.append((timestamp, row))
    if not timed_rows:
        return []

    latest_timestamp = max(timestamp for timestamp, _ in timed_rows)
    recent_start = latest_timestamp - timedelta(days=window_days)
    previous_start = recent_start - timedelta(days=window_days)

    buckets: dict[str, dict[str, Any]] = {}
    for timestamp, row in timed_rows:
        label = _categorize_reopened_reason(row.get("review_reason_code"), row.get("review_notes"))
        bucket = buckets.setdefault(
            label,
            {
                "reason": label,
                "recent_count": 0,
                "previous_count": 0,
                "example_note": None,
            },
        )
        note = str(row.get("review_notes") or "").strip()
        if note and not bucket["example_note"]:
            bucket["example_note"] = note[:160]
        if timestamp >= recent_start:
            bucket["recent_count"] += 1
        elif timestamp >= previous_start:
            bucket["previous_count"] += 1

    trends: list[dict[str, Any]] = []
    for bucket in buckets.values():
        if bucket["recent_count"] == 0 and bucket["previous_count"] == 0:
            continue
        delta = int(bucket["recent_count"]) - int(bucket["previous_count"])
        trend_key, trend_symbol = _trend_symbol(delta)
        trends.append(
            {
                "reason": bucket["reason"],
                "recent_count": int(bucket["recent_count"]),
                "previous_count": int(bucket["previous_count"]),
                "delta": delta,
                "trend": trend_key,
                "trend_symbol": trend_symbol,
                "window_days": window_days,
                "example_note": bucket["example_note"],
            }
        )

    return sorted(
        trends,
        key=lambda item: (-abs(int(item["delta"])), -int(item["recent_count"]), str(item["reason"])),
    )[:limit]


def _is_in_bucket(value: float, bucket: dict[str, float | str | None]) -> bool:
    minimum = bucket.get("min")
    maximum = bucket.get("max")
    if minimum is not None and value < float(minimum):
        return False
    if maximum is None:
        return True
    return value < float(maximum)


def _build_drift_bucket_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets = [
        {
            "label": str(bucket["label"]),
            "count": 0,
            "fixed_count": 0,
            "reopened_count": 0,
            "status_counts": {status: 0 for status in _KNOWN_REVIEW_STATUSES},
        }
        for bucket in _DRIFT_BUCKETS
    ]
    for row in rows:
        drift = _semantic_drift(row)
        if drift is None:
            continue
        status = _normalize_status(row.get("review_status"))
        for bucket_def, bucket_summary in zip(_DRIFT_BUCKETS, buckets):
            if _is_in_bucket(drift, bucket_def):
                bucket_summary["count"] += 1
                bucket_summary["status_counts"][status] += 1
                if status == "fixed":
                    bucket_summary["fixed_count"] += 1
                if status == "reopened":
                    bucket_summary["reopened_count"] += 1
                break
    return buckets


def _build_threshold_trend(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ordered_rows = sorted(
        [row for row in rows if _semantic_drift(row) is not None and _review_timestamp(row) is not None],
        key=lambda row: _review_timestamp(row) or datetime.min.replace(tzinfo=timezone.utc),
    )
    rows_by_day: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for row in ordered_rows:
        timestamp = _review_timestamp(row)
        if not timestamp:
            continue
        rows_by_day.setdefault(timestamp.date().isoformat(), []).append(row)

    trend: list[dict[str, Any]] = []
    cumulative_rows: list[dict[str, Any]] = []
    for day, day_rows in rows_by_day.items():
        cumulative_rows.extend(day_rows)
        snapshot = _build_threshold_snapshot(cumulative_rows)
        trend.append(
            {
                "date": day,
                "reviewed_final_count": len(cumulative_rows),
                "fixed_count": len(snapshot["fixed_rows"]),
                "reopened_count": len(snapshot["reopened_rows"]),
                "assist_only_semantic_advantage_threshold": snapshot["assist_only_threshold"],
                "promotion_ready": snapshot["promotion_ready"],
                "fixed_low_drift": _rounded(snapshot["fixed_low_drift"], 4),
                "reopened_high_drift": _rounded(snapshot["reopened_high_drift"], 4),
            }
        )
    return trend


def _summarize_status(status: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    lexical_scores = [value for value in (_numeric(row.get("score")) for row in rows) if value is not None]
    semantic_scores = [value for value in (_numeric(row.get("semantic_shadow_score")) for row in rows) if value is not None]
    semantic_drifts = [value for value in (_semantic_drift(row) for row in rows) if value is not None]
    return {
        "review_status": status,
        "count": len(rows),
        "semantic_coverage_count": len(semantic_scores),
        "flagged_count": sum(1 for row in rows if bool(row.get("is_flagged"))),
        "avg_lexical_similarity": _rounded(mean(lexical_scores), 4) if lexical_scores else None,
        "avg_semantic_shadow_score": _rounded(mean(semantic_scores), 4) if semantic_scores else None,
        "avg_semantic_drift": _rounded(mean(semantic_drifts), 4) if semantic_drifts else None,
        "lexical_p90": _rounded(_percentile(lexical_scores, 0.9), 4),
        "semantic_p90": _rounded(_percentile(semantic_scores, 0.9), 4),
        "drift_p90": _rounded(_percentile(semantic_drifts, 0.9), 4),
    }


async def build_reviewer_outcome_calibration_report(
    *,
    database: Any,
    similarity_scope_query: dict[str, Any] | None = None,
    sample_limit: int = 5000,
) -> dict[str, Any]:
    base_query = similarity_scope_query or {}
    rows = await database.similarity_logs.find(
        base_query,
        {
            "_id": 1,
            "score": 1,
            "semantic_shadow_score": 1,
            "review_status": 1,
            "review_reason_code": 1,
            "review_notes": 1,
            "is_flagged": 1,
            "created_at": 1,
            "reviewed_at": 1,
        },
    ).sort("created_at", -1).limit(sample_limit).to_list(length=sample_limit)

    by_status: dict[str, list[dict[str, Any]]] = {status: [] for status in _KNOWN_REVIEW_STATUSES}
    for row in rows:
        by_status[_normalize_status(row.get("review_status"))].append(row)

    final_rows = [
        row
        for row in rows
        if _normalize_status(row.get("review_status")) in _FINAL_STATUSES and _numeric(row.get("semantic_shadow_score")) is not None
    ]
    threshold_snapshot = _build_threshold_snapshot(final_rows)
    fixed_rows = threshold_snapshot["fixed_rows"]
    reopened_rows = threshold_snapshot["reopened_rows"]

    required_fixed = 3
    required_reopened = 2
    final_reasons: list[str] = []
    fixed_low_semantic = threshold_snapshot["fixed_low_semantic"]
    reopened_high_semantic = threshold_snapshot["reopened_high_semantic"]
    fixed_low_drift = threshold_snapshot["fixed_low_drift"]
    reopened_high_drift = threshold_snapshot["reopened_high_drift"]
    assist_only_drift_threshold = threshold_snapshot["assist_only_threshold"]

    promotion_thresholds: dict[str, float] | None = None
    promotion_ready = False
    if len(fixed_rows) < required_fixed:
        final_reasons.append(
            f"Need at least {required_fixed} fixed reviewer outcomes with semantic shadow scores; found {len(fixed_rows)}."
        )
    if len(reopened_rows) < required_reopened:
        final_reasons.append(
            f"Need at least {required_reopened} reopened reviewer outcomes with semantic shadow scores; found {len(reopened_rows)}."
        )

    if not final_reasons and None not in {fixed_low_semantic, reopened_high_semantic, fixed_low_drift, reopened_high_drift}:
        if threshold_snapshot["promotion_ready"]:
            promotion_thresholds = {
                "semantic_shadow_score_min": round((float(fixed_low_semantic) + float(reopened_high_semantic)) / 2.0, 4),
                "semantic_advantage_min": round((float(fixed_low_drift) + float(reopened_high_drift)) / 2.0, 4),
            }
            promotion_ready = True
        else:
            final_reasons.append(
                "Reviewer-outcome distributions still overlap, so semantic shadow remains assist-only."
            )

    status_breakdown = [_summarize_status(status, by_status[status]) for status in _KNOWN_REVIEW_STATUSES]
    semantic_rows = [row for row in rows if _numeric(row.get("semantic_shadow_score")) is not None]
    latest_reviewed_row = next(
        (row for row in rows if _normalize_status(row.get("review_status")) in _FINAL_STATUSES),
        None,
    )

    latest_reviewed_value = None
    if latest_reviewed_row:
        latest_reviewed_value = latest_reviewed_row.get("reviewed_at") or latest_reviewed_row.get("created_at")
    drift_bucket_summary = _build_drift_bucket_summary(final_rows)
    reopened_reason_summary = _build_reopened_reason_summary(reopened_rows)
    reopened_reason_trends = _build_reopened_reason_trends(reopened_rows)
    threshold_trend = _build_threshold_trend(final_rows)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": {
            "sample_limit": sample_limit,
            "status_inference": (
                "Uses review_status as the real reviewer outcome signal. "
                "`fixed` is treated as resolved-positive evidence, while `reopened` is a conservative drift-negative proxy."
            ),
        },
        "summary": {
            "logs_considered": len(rows),
            "semantic_coverage_count": len(semantic_rows),
            "reviewed_final_count": len(final_rows),
            "fixed_count": len(fixed_rows),
            "reopened_count": len(reopened_rows),
            "status_counts": {status: len(by_status[status]) for status in _KNOWN_REVIEW_STATUSES},
            "latest_reviewed_at": latest_reviewed_value.isoformat() if isinstance(latest_reviewed_value, datetime) else None,
        },
        "status_breakdown": status_breakdown,
        "calibration_window": {
            "fixed_low_semantic": _rounded(fixed_low_semantic, 4),
            "reopened_high_semantic": _rounded(reopened_high_semantic, 4),
            "fixed_low_drift": _rounded(fixed_low_drift, 4),
            "reopened_high_drift": _rounded(reopened_high_drift, 4),
        },
        "recommendations": {
            "keep_shadow_only": True,
            "assist_only_semantic_advantage_threshold": assist_only_drift_threshold,
            "promotion_thresholds": promotion_thresholds,
            "requires_manual_rollout_approval": True,
            "next_focus": (
                "Expand reviewer-confirmed outcomes before semantic signals influence any automated flagging."
                if not promotion_ready
                else "Promotion looks numerically viable, but keep semantic signals review-only until human rollout approval."
            ),
        },
        "gates": {
            "promotion_ready": promotion_ready,
            "failures": final_reasons,
        },
        "analytics": {
            "review_status_counts": {status: len(by_status[status]) for status in _KNOWN_REVIEW_STATUSES},
            "drift_buckets": drift_bucket_summary,
            "top_reopened_reasons": reopened_reason_summary,
            "reopened_reason_trends": reopened_reason_trends,
            "threshold_trend": threshold_trend,
        },
    }
