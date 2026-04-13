from __future__ import annotations

from datetime import datetime, timezone
from statistics import mean
from typing import Any

from app.core.config import settings


_FINAL_STATUSES = {"fixed", "reopened"}
_KNOWN_REVIEW_STATUSES = ("open", "in_progress", "fixed", "reopened")


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


def _summarize_status(status: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    lexical_scores = [value for value in (_numeric(row.get("score")) for row in rows) if value is not None]
    semantic_scores = [value for value in (_numeric(row.get("semantic_shadow_score")) for row in rows) if value is not None]
    semantic_drifts = [
        value
        for value in (
            _numeric(row.get("semantic_shadow_score")) - _numeric(row.get("score"))
            if _numeric(row.get("semantic_shadow_score")) is not None and _numeric(row.get("score")) is not None
            else None
            for row in rows
        )
        if value is not None
    ]
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
    fixed_rows = [row for row in final_rows if _normalize_status(row.get("review_status")) == "fixed"]
    reopened_rows = [row for row in final_rows if _normalize_status(row.get("review_status")) == "reopened"]
    fixed_semantic_scores = [float(row["semantic_shadow_score"]) for row in fixed_rows if _numeric(row.get("semantic_shadow_score")) is not None]
    reopened_semantic_scores = [
        float(row["semantic_shadow_score"])
        for row in reopened_rows
        if _numeric(row.get("semantic_shadow_score")) is not None
    ]
    fixed_drifts = [
        float(row["semantic_shadow_score"]) - float(row["score"])
        for row in fixed_rows
        if _numeric(row.get("semantic_shadow_score")) is not None and _numeric(row.get("score")) is not None
    ]
    reopened_drifts = [
        float(row["semantic_shadow_score"]) - float(row["score"])
        for row in reopened_rows
        if _numeric(row.get("semantic_shadow_score")) is not None and _numeric(row.get("score")) is not None
    ]

    required_fixed = 3
    required_reopened = 2
    final_reasons: list[str] = []
    fixed_low_semantic = _percentile(fixed_semantic_scores, 0.25)
    reopened_high_semantic = _percentile(reopened_semantic_scores, 0.9)
    fixed_low_drift = _percentile(fixed_drifts, 0.25)
    reopened_high_drift = _percentile(reopened_drifts, 0.9)
    assist_only_drift_threshold = _rounded(
        max(
            float(settings.semantic_shadow_calibration_paraphrase_advantage_min),
            float(fixed_low_drift)
            if fixed_low_drift is not None
            else float(settings.semantic_shadow_calibration_paraphrase_advantage_min),
        ),
        4,
    )

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
        if fixed_low_semantic > reopened_high_semantic and fixed_low_drift > reopened_high_drift:
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
            "latest_reviewed_at": (
                latest_reviewed_row.get("reviewed_at") or latest_reviewed_row.get("created_at")
            ).isoformat()
            if isinstance(latest_reviewed_row.get("reviewed_at") or latest_reviewed_row.get("created_at"), datetime)
            else None,
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
    }
