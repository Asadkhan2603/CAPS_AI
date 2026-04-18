from __future__ import annotations

from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from statistics import mean
from typing import Any

from app.core.config import settings
from app.services.ai_runtime import get_ai_semantic_rollout_settings
from app.services.semantic_rollout_readiness import (
    ALLOWED_CALIBRATION_MATCH_SCOPES,
    calibration_eligible,
    language_bucket_for_row,
    normalize_match_scope,
    scope_bucket_for_row,
)

_FINAL_STATUSES = {"fixed", "reopened"}
_KNOWN_REVIEW_STATUSES = ("open", "in_progress", "fixed", "reopened")
_KNOWN_LANGUAGE_BUCKETS = ("latin_only", "mixed_transliterated", "non_latin")
_LEGACY_VALIDATION_REASON_LABELS = {
    "missing_review_finalized_at": "Missing review_finalized_at",
    "missing_semantic_shadow_score": "Missing semantic shadow score",
    "disallowed_match_scope": "Disallowed or missing match scope",
}
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


def _aware_utc(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _semantic_config_float(config: dict[str, Any], key: str, fallback: float) -> float:
    value = config.get(key)
    if isinstance(value, (int, float)):
        return float(value)
    return float(fallback)


def _semantic_config_int(config: dict[str, Any], key: str, fallback: int) -> int:
    value = config.get(key)
    if isinstance(value, int):
        return int(value)
    if isinstance(value, float):
        return int(value)
    return int(fallback)


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
    value = row.get("review_finalized_at") or row.get("reviewed_at") or row.get("created_at")
    return _aware_utc(value)


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
    total = len(rows)
    for row in rows:
        label = _categorize_reopened_reason(row.get("review_reason_code"), row.get("review_notes"))
        bucket = grouped.setdefault(
            label,
            {"reason": label, "count": 0, "share": 0.0, "example_note": None},
        )
        bucket["count"] += 1
        note = str(row.get("review_notes") or "").strip()
        if note and not bucket["example_note"]:
            bucket["example_note"] = note[:160]
    for bucket in grouped.values():
        bucket["share"] = _rounded((int(bucket["count"]) / total) if total else 0.0, 4)
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


def _legacy_validation_reasons(row: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    if _normalize_status(row.get("review_status")) not in _FINAL_STATUSES:
        return reasons
    if not isinstance(row.get("review_finalized_at"), datetime):
        reasons.append("missing_review_finalized_at")
    if _numeric(row.get("semantic_shadow_score")) is None:
        reasons.append("missing_semantic_shadow_score")
    if normalize_match_scope(row) not in ALLOWED_CALIBRATION_MATCH_SCOPES:
        reasons.append("disallowed_match_scope")
    return reasons


def _build_legacy_validation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    finalized_rows = [row for row in rows if _normalize_status(row.get("review_status")) in _FINAL_STATUSES]
    invalid_rows: list[dict[str, Any]] = []
    reason_counts = {key: 0 for key in _LEGACY_VALIDATION_REASON_LABELS}

    for row in finalized_rows:
        reasons = _legacy_validation_reasons(row)
        if not reasons:
            continue
        for reason in reasons:
            reason_counts[reason] = int(reason_counts.get(reason) or 0) + 1
        invalid_rows.append(
            {
                "id": str(row.get("_id")),
                "review_status": _normalize_status(row.get("review_status")),
                "review_finalized_at": _review_timestamp(row).isoformat() if _review_timestamp(row) else None,
                "reasons": reasons,
            }
        )

    return {
        "finalized_rows": len(finalized_rows),
        "invalid_finalized_rows": len(invalid_rows),
        "eligible_finalized_rows": len([row for row in finalized_rows if calibration_eligible(row)]),
        "invalid_rate": _rounded((len(invalid_rows) / len(finalized_rows)) if finalized_rows else 0.0, 4),
        "reason_counts": [
            {
                "reason": key,
                "label": _LEGACY_VALIDATION_REASON_LABELS[key],
                "count": int(value),
            }
            for key, value in reason_counts.items()
            if int(value) > 0
        ],
        "examples": invalid_rows[:5],
    }


def _build_readiness_trend(
    rows: list[dict[str, Any]],
    *,
    semantic_rollout_settings: dict[str, Any],
) -> list[dict[str, Any]]:
    ordered_rows = sorted(
        [row for row in rows if _review_timestamp(row) is not None],
        key=lambda row: _review_timestamp(row) or datetime.min.replace(tzinfo=timezone.utc),
    )
    rows_by_day: OrderedDict[str, list[dict[str, Any]]] = OrderedDict()
    for row in ordered_rows:
        timestamp = _review_timestamp(row)
        if not timestamp:
            continue
        rows_by_day.setdefault(timestamp.date().isoformat(), []).append(row)

    same_min = max(
        3,
        _semantic_config_int(
            semantic_rollout_settings,
            "semantic_same_assignment_min_sample_size",
            int(settings.semantic_same_assignment_min_sample_size),
        ),
    )
    cross_min = max(
        5,
        _semantic_config_int(
            semantic_rollout_settings,
            "semantic_cross_assignment_min_sample_size",
            int(settings.semantic_cross_assignment_min_sample_size),
        ),
    )

    trend: list[dict[str, Any]] = []
    cumulative_rows: list[dict[str, Any]] = []
    for day, day_rows in rows_by_day.items():
        cumulative_rows.extend(day_rows)
        same_scope_rows = _scope_rows(cumulative_rows, "same_assignment")
        cross_scope_rows = _scope_rows(cumulative_rows, "cross_assignment")
        same_scope_summary = _compute_scope_separation(same_scope_rows)
        cross_scope_summary = _compute_scope_separation(cross_scope_rows)
        language_coverage = _build_language_coverage(
            cumulative_rows,
            semantic_rollout_settings=semantic_rollout_settings,
        )
        recommendations = _build_recommendations(
            same_scope=same_scope_summary,
            cross_scope=cross_scope_summary,
            language_coverage=language_coverage,
            semantic_rollout_settings=semantic_rollout_settings,
        )
        trend.append(
            {
                "date": day,
                "eligible_sample_count": len(cumulative_rows),
                "fixed_count": int(same_scope_summary.get("fixed_count") or 0) + int(cross_scope_summary.get("fixed_count") or 0),
                "reopened_count": int(same_scope_summary.get("reopened_count") or 0) + int(cross_scope_summary.get("reopened_count") or 0),
                "same_assignment": {
                    "eligible_sample_count": int(same_scope_summary.get("reviewed_final_count") or 0),
                    "sample_gap": max(0, same_min - int(same_scope_summary.get("reviewed_final_count") or 0)),
                    "drift_gap": same_scope_summary.get("drift_gap"),
                    "semantic_gap": same_scope_summary.get("semantic_gap"),
                    "promotion_ready": bool(recommendations.get("promotion_ready_same_assignment")),
                },
                "cross_assignment": {
                    "eligible_sample_count": int(cross_scope_summary.get("reviewed_final_count") or 0),
                    "sample_gap": max(0, cross_min - int(cross_scope_summary.get("reviewed_final_count") or 0)),
                    "drift_gap": cross_scope_summary.get("drift_gap"),
                    "semantic_gap": cross_scope_summary.get("semantic_gap"),
                    "promotion_ready": bool(recommendations.get("promotion_ready_cross_assignment")),
                },
                "language_coverage_ready": bool(language_coverage.get("coverage_ready")),
                "blocker_reasons": list(recommendations.get("blocker_reasons") or []),
                "blocker_count": len(recommendations.get("blocker_reasons") or []),
            }
        )
    return trend


def _build_blocker_aging(
    readiness_trend: list[dict[str, Any]],
    current_blockers: list[str],
    *,
    generated_at: datetime,
) -> list[dict[str, Any]]:
    if not current_blockers:
        return []

    entries: list[dict[str, Any]] = []
    latest_snapshot_date = readiness_trend[-1]["date"] if readiness_trend else generated_at.date().isoformat()
    for blocker in current_blockers:
        matching_points = [point for point in readiness_trend if blocker in (point.get("blocker_reasons") or [])]
        first_seen_date = matching_points[0]["date"] if matching_points else latest_snapshot_date
        latest_seen_date = matching_points[-1]["date"] if matching_points else latest_snapshot_date
        days_active = None
        try:
            first_seen_dt = datetime.fromisoformat(str(first_seen_date))
            latest_seen_dt = datetime.fromisoformat(str(latest_seen_date))
            days_active = max(0, (latest_seen_dt.date() - first_seen_dt.date()).days)
        except ValueError:
            days_active = None
        entries.append(
            {
                "reason": blocker,
                "first_seen_date": first_seen_date,
                "latest_seen_date": latest_seen_date,
                "days_active": days_active,
            }
        )
    return entries


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


def _build_reviewer_outcome_pipeline(
    *,
    rows: list[dict[str, Any]],
    eligible_rows: list[dict[str, Any]],
    semantic_rollout_settings: dict[str, Any],
) -> dict[str, Any]:
    open_rows = [row for row in rows if _normalize_status(row.get("review_status")) == "open"]
    in_progress_rows = [row for row in rows if _normalize_status(row.get("review_status")) == "in_progress"]
    finalized_rows = [row for row in rows if _normalize_status(row.get("review_status")) in _FINAL_STATUSES]
    finalized_fixed_rows = [row for row in finalized_rows if _normalize_status(row.get("review_status")) == "fixed"]
    finalized_reopened_rows = [row for row in finalized_rows if _normalize_status(row.get("review_status")) == "reopened"]

    now = datetime.now(timezone.utc)
    stale_open_count = 0
    stale_in_progress_count = 0
    finalize_durations_hours: list[float] = []
    finalized_last_7d = 0
    for row in rows:
        status = _normalize_status(row.get("review_status"))
        updated_at = _aware_utc(row.get("review_updated_at") or row.get("reviewed_at") or row.get("created_at"))
        if updated_at:
            age_hours = max(0.0, (now - updated_at).total_seconds() / 3600.0)
            if status == "open" and age_hours >= 48:
                stale_open_count += 1
            if status == "in_progress" and age_hours >= 72:
                stale_in_progress_count += 1
        finalized_at = _aware_utc(row.get("review_finalized_at"))
        created_at = _aware_utc(row.get("created_at"))
        if finalized_at and created_at:
            finalize_durations_hours.append(max(0.0, (finalized_at - created_at).total_seconds() / 3600.0))
            if now - finalized_at <= timedelta(days=7):
                finalized_last_7d += 1

    minimum_sample_target = max(
        5,
        _semantic_config_int(
            semantic_rollout_settings,
            "semantic_same_assignment_min_sample_size",
            int(settings.semantic_same_assignment_min_sample_size),
        ),
    )
    minimum_sample_gap = max(0, minimum_sample_target - len(eligible_rows))
    if len(eligible_rows) <= 0:
        calibration_blocker_reason = "No accessible finalized reviewer outcomes yet."
    elif minimum_sample_gap > 0:
        calibration_blocker_reason = (
            f"Need {minimum_sample_gap} more finalized semantic-review outcomes before rollout guidance is statistically useful."
        )
    else:
        calibration_blocker_reason = "Finalized semantic outcomes satisfy minimum sample volume for readiness guidance."

    return {
        "open_count": len(open_rows),
        "in_progress_count": len(in_progress_rows),
        "finalized_count": len(finalized_rows),
        "finalized_fixed_count": len(finalized_fixed_rows),
        "finalized_reopened_count": len(finalized_reopened_rows),
        "stale_open_count": stale_open_count,
        "stale_in_progress_count": stale_in_progress_count,
        "finalization_rate_7d": _rounded(finalized_last_7d / 7.0 if finalized_last_7d else 0.0, 4),
        "median_hours_to_finalize": _rounded(_percentile(finalize_durations_hours, 0.5), 2),
        "minimum_sample_target": minimum_sample_target,
        "minimum_sample_gap": minimum_sample_gap,
        "calibration_blocker_reason": calibration_blocker_reason,
        "stale_threshold_hours": {"open": 48, "in_progress": 72},
    }


def _scope_rows(rows: list[dict[str, Any]], scope_bucket: str) -> list[dict[str, Any]]:
    return [row for row in rows if scope_bucket_for_row(row) == scope_bucket]


def _compute_scope_separation(rows: list[dict[str, Any]]) -> dict[str, Any]:
    fixed_rows = [row for row in rows if _normalize_status(row.get("review_status")) == "fixed"]
    reopened_rows = [row for row in rows if _normalize_status(row.get("review_status")) == "reopened"]
    fixed_drifts = [value for value in (_semantic_drift(row) for row in fixed_rows) if value is not None]
    reopened_drifts = [value for value in (_semantic_drift(row) for row in reopened_rows) if value is not None]
    fixed_semantic = [value for value in (_numeric(row.get("semantic_shadow_score")) for row in fixed_rows) if value is not None]
    reopened_semantic = [value for value in (_numeric(row.get("semantic_shadow_score")) for row in reopened_rows) if value is not None]
    fixed_lexical = [value for value in (_numeric(row.get("score")) for row in fixed_rows) if value is not None]
    reopened_lexical = [value for value in (_numeric(row.get("score")) for row in reopened_rows) if value is not None]

    fixed_drift_p25 = _percentile(fixed_drifts, 0.25)
    reopened_drift_p90 = _percentile(reopened_drifts, 0.9)
    fixed_semantic_p25 = _percentile(fixed_semantic, 0.25)
    reopened_semantic_p90 = _percentile(reopened_semantic, 0.9)
    fixed_lexical_p25 = _percentile(fixed_lexical, 0.25)
    reopened_lexical_p90 = _percentile(reopened_lexical, 0.9)
    drift_gap = (
        float(fixed_drift_p25) - float(reopened_drift_p90)
        if fixed_drift_p25 is not None and reopened_drift_p90 is not None
        else None
    )
    semantic_gap = (
        float(fixed_semantic_p25) - float(reopened_semantic_p90)
        if fixed_semantic_p25 is not None and reopened_semantic_p90 is not None
        else None
    )
    lexical_gap = (
        float(fixed_lexical_p25) - float(reopened_lexical_p90)
        if fixed_lexical_p25 is not None and reopened_lexical_p90 is not None
        else None
    )
    return {
        "fixed_count": len(fixed_rows),
        "reopened_count": len(reopened_rows),
        "reviewed_final_count": len(rows),
        "reopened_rate": _rounded(len(reopened_rows) / len(rows), 4) if rows else 0.0,
        "fixed_drift_p25": _rounded(fixed_drift_p25, 4),
        "reopened_drift_p90": _rounded(reopened_drift_p90, 4),
        "fixed_semantic_p25": _rounded(fixed_semantic_p25, 4),
        "reopened_semantic_p90": _rounded(reopened_semantic_p90, 4),
        "fixed_lexical_p25": _rounded(fixed_lexical_p25, 4),
        "reopened_lexical_p90": _rounded(reopened_lexical_p90, 4),
        "drift_gap": _rounded(drift_gap, 4),
        "semantic_gap": _rounded(semantic_gap, 4),
        "lexical_gap": _rounded(lexical_gap, 4),
        "decision_mode_counts": {
            "flagged": sum(1 for row in rows if str(row.get("decision_mode") or "").strip().lower() == "flagged"),
            "assist_only": sum(1 for row in rows if str(row.get("decision_mode") or "").strip().lower() == "assist_only"),
            "suppressed": sum(1 for row in rows if str(row.get("decision_mode") or "").strip().lower() == "suppressed"),
        },
    }


def _build_language_coverage(rows: list[dict[str, Any]], *, semantic_rollout_settings: dict[str, Any]) -> dict[str, Any]:
    coverage = {bucket: {"count": 0, "fixed": 0, "reopened": 0} for bucket in _KNOWN_LANGUAGE_BUCKETS}
    for row in rows:
        bucket = language_bucket_for_row(row)
        if bucket not in coverage:
            continue
        status = _normalize_status(row.get("review_status"))
        coverage[bucket]["count"] += 1
        if status == "fixed":
            coverage[bucket]["fixed"] += 1
        if status == "reopened":
            coverage[bucket]["reopened"] += 1

    minimum = max(
        1,
        _semantic_config_int(
            semantic_rollout_settings,
            "semantic_multilingual_min_sample_size",
            int(settings.semantic_multilingual_min_sample_size),
        ),
    )
    coverage_ready = all(
        coverage[bucket]["count"] >= minimum for bucket in ("mixed_transliterated", "non_latin")
    )
    return {
        "minimum_sample_size": minimum,
        "coverage": coverage,
        "coverage_ready": coverage_ready,
    }


def _build_recommendations(
    *,
    same_scope: dict[str, Any],
    cross_scope: dict[str, Any],
    language_coverage: dict[str, Any],
    semantic_rollout_settings: dict[str, Any],
) -> dict[str, Any]:
    same_min = max(
        3,
        _semantic_config_int(
            semantic_rollout_settings,
            "semantic_same_assignment_min_sample_size",
            int(settings.semantic_same_assignment_min_sample_size),
        ),
    )
    cross_min = max(
        5,
        _semantic_config_int(
            semantic_rollout_settings,
            "semantic_cross_assignment_min_sample_size",
            int(settings.semantic_cross_assignment_min_sample_size),
        ),
    )
    blockers: list[str] = []

    same_has_samples = int(same_scope.get("reviewed_final_count") or 0) >= same_min
    cross_has_samples = int(cross_scope.get("reviewed_final_count") or 0) >= cross_min
    same_separation = (same_scope.get("drift_gap") or 0) > 0 and (same_scope.get("semantic_gap") or 0) > 0
    cross_separation = (cross_scope.get("drift_gap") or 0) > 0 and (cross_scope.get("semantic_gap") or 0) > 0

    if not same_has_samples:
        blockers.append(
            f"Same-assignment semantic calibration needs {same_min} eligible finalized rows; found {int(same_scope.get('reviewed_final_count') or 0)}."
        )
    if same_has_samples and not same_separation:
        blockers.append("Same-assignment fixed vs reopened distributions are still overlapping.")
    if not cross_has_samples:
        blockers.append(
            f"Cross-assignment semantic calibration needs {cross_min} eligible finalized rows; found {int(cross_scope.get('reviewed_final_count') or 0)}."
        )
    if cross_has_samples and not cross_separation:
        blockers.append("Cross-assignment fixed vs reopened distributions are still overlapping.")
    if not bool(language_coverage.get("coverage_ready")):
        blockers.append("Multilingual coverage is below minimum sample targets for mixed/transliterated or non-Latin buckets.")

    recommended_same_drift = same_scope.get("fixed_drift_p25")
    if recommended_same_drift is None:
        recommended_same_drift = _semantic_config_float(
            semantic_rollout_settings,
            "semantic_same_assignment_drift_threshold",
            float(settings.semantic_same_assignment_drift_threshold),
        )
    recommended_cross_drift = cross_scope.get("fixed_drift_p25")
    if recommended_cross_drift is None:
        recommended_cross_drift = _semantic_config_float(
            semantic_rollout_settings,
            "semantic_cross_assignment_drift_threshold",
            float(settings.semantic_cross_assignment_drift_threshold),
        )

    recommended_min_semantic = same_scope.get("fixed_semantic_p25")
    if recommended_min_semantic is None:
        recommended_min_semantic = _semantic_config_float(
            semantic_rollout_settings,
            "semantic_same_assignment_min_score",
            float(settings.semantic_same_assignment_min_score),
        )

    promotion_ready_same = same_has_samples and same_separation
    promotion_ready_cross = cross_has_samples and cross_separation and bool(language_coverage.get("coverage_ready"))
    return {
        "recommended_same_assignment_drift_threshold": _rounded(float(recommended_same_drift), 4),
        "recommended_cross_assignment_drift_threshold": _rounded(float(recommended_cross_drift), 4),
        "recommended_min_semantic_score": _rounded(float(recommended_min_semantic), 4),
        "recommended_min_sample_size": {"same_assignment": same_min, "cross_assignment": cross_min},
        "promotion_ready_same_assignment": promotion_ready_same,
        "promotion_ready_cross_assignment": promotion_ready_cross,
        "blocker_reasons": blockers,
    }


async def build_reviewer_outcome_calibration_report(
    *,
    database: Any,
    similarity_scope_query: dict[str, Any] | None = None,
    sample_limit: int = 5000,
    semantic_rollout_settings_override: dict[str, Any] | None = None,
) -> dict[str, Any]:
    semantic_rollout_settings = semantic_rollout_settings_override or await get_ai_semantic_rollout_settings(database=database)
    generated_at = datetime.now(timezone.utc)
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
            "decision_mode": 1,
            "suppression_reason": 1,
            "semantic_review_candidate": 1,
            "match_scope": 1,
            "language_profile": 1,
            "created_at": 1,
            "reviewed_at": 1,
            "review_updated_at": 1,
            "review_finalized_at": 1,
            "review_finalized_by_user_id": 1,
        },
    ).sort("created_at", -1).limit(sample_limit).to_list(length=sample_limit)

    for row in rows:
        row["match_scope"] = normalize_match_scope(row)
        row["language_bucket"] = language_bucket_for_row(row)
        row["calibration_eligible"] = calibration_eligible(row)

    by_status: dict[str, list[dict[str, Any]]] = {status: [] for status in _KNOWN_REVIEW_STATUSES}
    for row in rows:
        by_status[_normalize_status(row.get("review_status"))].append(row)

    final_rows = [row for row in rows if bool(row.get("calibration_eligible"))]
    threshold_snapshot = _build_threshold_snapshot(final_rows)
    fixed_rows = threshold_snapshot["fixed_rows"]
    reopened_rows = threshold_snapshot["reopened_rows"]
    status_breakdown = [_summarize_status(status, by_status[status]) for status in _KNOWN_REVIEW_STATUSES]
    semantic_rows = [row for row in rows if _numeric(row.get("semantic_shadow_score")) is not None]
    latest_reviewed_row = next((row for row in final_rows if _review_timestamp(row) is not None), None)
    latest_reviewed_value = _review_timestamp(latest_reviewed_row) if latest_reviewed_row else None

    drift_bucket_summary = _build_drift_bucket_summary(final_rows)
    reopened_reason_summary = _build_reopened_reason_summary(reopened_rows)
    reopened_reason_trends = _build_reopened_reason_trends(reopened_rows)
    threshold_trend = _build_threshold_trend(final_rows)
    readiness_trend = _build_readiness_trend(
        final_rows,
        semantic_rollout_settings=semantic_rollout_settings,
    )
    reviewer_outcome_pipeline = _build_reviewer_outcome_pipeline(
        rows=rows,
        eligible_rows=final_rows,
        semantic_rollout_settings=semantic_rollout_settings,
    )
    legacy_validation = _build_legacy_validation(rows)

    same_scope_rows = _scope_rows(final_rows, "same_assignment")
    cross_scope_rows = _scope_rows(final_rows, "cross_assignment")
    same_scope_summary = _compute_scope_separation(same_scope_rows)
    cross_scope_summary = _compute_scope_separation(cross_scope_rows)
    cross_scope_reopened_rows = [
        row for row in cross_scope_rows if _normalize_status(row.get("review_status")) == "reopened"
    ]
    cross_scope_fixed_rows = [
        row for row in cross_scope_rows if _normalize_status(row.get("review_status")) == "fixed"
    ]
    cross_assignment_reversal_ranking = _build_reopened_reason_summary(cross_scope_reopened_rows)
    cross_assignment_reopened_reason_trends = _build_reopened_reason_trends(cross_scope_reopened_rows)
    language_coverage = _build_language_coverage(
        final_rows,
        semantic_rollout_settings=semantic_rollout_settings,
    )
    recommendations_ext = _build_recommendations(
        same_scope=same_scope_summary,
        cross_scope=cross_scope_summary,
        language_coverage=language_coverage,
        semantic_rollout_settings=semantic_rollout_settings,
    )

    promotion_ready = bool(recommendations_ext.get("promotion_ready_same_assignment"))
    promotion_thresholds = None
    if promotion_ready:
        promotion_thresholds = {
            "semantic_shadow_score_min": recommendations_ext["recommended_min_semantic_score"],
            "semantic_advantage_min": recommendations_ext["recommended_same_assignment_drift_threshold"],
        }

    same_blockers = []
    cross_blockers = []
    for reason in recommendations_ext.get("blocker_reasons") or []:
        normalized_reason = str(reason).lower()
        if "same-assignment" in normalized_reason:
            same_blockers.append(reason)
        if "cross-assignment" in normalized_reason or "multilingual" in normalized_reason:
            cross_blockers.append(reason)
    blocker_aging = _build_blocker_aging(
        readiness_trend,
        list(recommendations_ext.get("blocker_reasons") or []),
        generated_at=generated_at,
    )

    readiness = {
        "same_assignment": {
            "eligible_sample_count": int(same_scope_summary.get("reviewed_final_count") or 0),
            "finalized_outcomes": {
                "fixed": int(same_scope_summary.get("fixed_count") or 0),
                "reopened": int(same_scope_summary.get("reopened_count") or 0),
            },
            "drift_separation": {
                "fixed_drift_p25": same_scope_summary.get("fixed_drift_p25"),
                "reopened_drift_p90": same_scope_summary.get("reopened_drift_p90"),
                "drift_gap": same_scope_summary.get("drift_gap"),
            },
            "configured_thresholds": {
                "drift_threshold": _semantic_config_float(
                    semantic_rollout_settings,
                    "semantic_same_assignment_drift_threshold",
                    float(settings.semantic_same_assignment_drift_threshold),
                ),
                "min_semantic_score": _semantic_config_float(
                    semantic_rollout_settings,
                    "semantic_same_assignment_min_score",
                    float(settings.semantic_same_assignment_min_score),
                ),
                "minimum_sample_size": _semantic_config_int(
                    semantic_rollout_settings,
                    "semantic_same_assignment_min_sample_size",
                    int(settings.semantic_same_assignment_min_sample_size),
                ),
            },
            "recommended_thresholds": {
                "drift_threshold": recommendations_ext.get("recommended_same_assignment_drift_threshold"),
                "min_semantic_score": recommendations_ext.get("recommended_min_semantic_score"),
            },
            "promotion_ready": bool(recommendations_ext.get("promotion_ready_same_assignment")),
            "blocker_reasons": same_blockers,
        },
        "cross_assignment": {
            "eligible_sample_count": int(cross_scope_summary.get("reviewed_final_count") or 0),
            "finalized_outcomes": {
                "fixed": int(cross_scope_summary.get("fixed_count") or 0),
                "reopened": int(cross_scope_summary.get("reopened_count") or 0),
            },
            "drift_separation": {
                "fixed_drift_p25": cross_scope_summary.get("fixed_drift_p25"),
                "reopened_drift_p90": cross_scope_summary.get("reopened_drift_p90"),
                "drift_gap": cross_scope_summary.get("drift_gap"),
            },
            "configured_thresholds": {
                "drift_threshold": _semantic_config_float(
                    semantic_rollout_settings,
                    "semantic_cross_assignment_drift_threshold",
                    float(settings.semantic_cross_assignment_drift_threshold),
                ),
                "min_semantic_score": _semantic_config_float(
                    semantic_rollout_settings,
                    "semantic_cross_assignment_min_score",
                    float(settings.semantic_cross_assignment_min_score),
                ),
                "minimum_sample_size": _semantic_config_int(
                    semantic_rollout_settings,
                    "semantic_cross_assignment_min_sample_size",
                    int(settings.semantic_cross_assignment_min_sample_size),
                ),
            },
            "recommended_thresholds": {
                "drift_threshold": recommendations_ext.get("recommended_cross_assignment_drift_threshold"),
                "min_semantic_score": recommendations_ext.get("recommended_min_semantic_score"),
            },
            "promotion_ready": bool(recommendations_ext.get("promotion_ready_cross_assignment")),
            "blocker_reasons": cross_blockers,
        },
        "language_coverage": language_coverage,
        "language_buckets": language_coverage.get("coverage") or {},
        "blocker_reasons": list(recommendations_ext.get("blocker_reasons") or []),
        "blocker_aging": blocker_aging,
        "readiness_trend": readiness_trend,
        "manual_promotion_guidance_only": True,
    }

    return {
        "generated_at": generated_at.isoformat(),
        "scope": {
            "sample_limit": sample_limit,
            "status_inference": (
                "Uses review_status as the reviewer outcome signal. "
                "`fixed` is treated as resolved-positive evidence, while `reopened` is a conservative drift-negative proxy."
            ),
            "allowed_match_scopes": sorted(ALLOWED_CALIBRATION_MATCH_SCOPES),
            "required_fields_for_calibration": [
                "review_status in {fixed,reopened}",
                "review_finalized_at",
                "semantic_shadow_score",
                "match_scope in calibration scopes",
            ],
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
            "fixed_low_semantic": _rounded(threshold_snapshot["fixed_low_semantic"], 4),
            "reopened_high_semantic": _rounded(threshold_snapshot["reopened_high_semantic"], 4),
            "fixed_low_drift": _rounded(threshold_snapshot["fixed_low_drift"], 4),
            "reopened_high_drift": _rounded(threshold_snapshot["reopened_high_drift"], 4),
        },
        "recommendations": {
            "keep_shadow_only": True,
            "assist_only_semantic_advantage_threshold": threshold_snapshot["assist_only_threshold"],
            "promotion_thresholds": promotion_thresholds,
            "requires_manual_rollout_approval": True,
            "next_focus": (
                "Expand reviewer-confirmed outcomes before semantic signals influence any automated flagging."
                if not promotion_ready
                else "Same-assignment recommendation is numerically viable; keep semantic signals review-only until manual rollout approval."
            ),
            **recommendations_ext,
        },
        "gates": {
            "promotion_ready": promotion_ready,
            "failures": list(recommendations_ext.get("blocker_reasons") or []),
        },
        "analytics": {
            "review_status_counts": {status: len(by_status[status]) for status in _KNOWN_REVIEW_STATUSES},
            "drift_buckets": drift_bucket_summary,
            "top_reopened_reasons": reopened_reason_summary,
            "reopened_reason_trends": reopened_reason_trends,
            "threshold_trend": threshold_trend,
            "readiness_trend": readiness_trend,
            "legacy_validation": legacy_validation,
            "scope_breakdown": {
                "same_assignment": same_scope_summary,
                "cross_assignment": cross_scope_summary,
            },
            "cross_assignment_review_outcomes": {
                "reviewed_final_count": len(cross_scope_rows),
                "fixed_count": len(cross_scope_fixed_rows),
                "reopened_count": len(cross_scope_reopened_rows),
                "reopened_rate": _rounded(
                    (len(cross_scope_reopened_rows) / len(cross_scope_rows)) if cross_scope_rows else 0.0,
                    4,
                ),
            },
            "cross_assignment_reversal_ranking": cross_assignment_reversal_ranking,
            "cross_assignment_reopened_reason_trends": cross_assignment_reopened_reason_trends,
            "language_bucket_coverage": language_coverage.get("coverage") or {},
        },
        "reviewer_outcome_pipeline": reviewer_outcome_pipeline,
        "semantic_rollout_readiness": readiness,
    }
