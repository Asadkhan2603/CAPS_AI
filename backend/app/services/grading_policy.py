from __future__ import annotations

from copy import deepcopy
from typing import Any

DEFAULT_GRADE_POINTS = {
    "A+": 4.0,
    "A": 3.7,
    "B": 3.0,
    "C": 2.3,
    "Needs Improvement": 0.0,
}

DEFAULT_GRADING_POLICY = {
    "grade_points": deepcopy(DEFAULT_GRADE_POINTS),
    "transcript_precision": 2,
}


def normalize_grading_policy(payload: dict[str, Any] | None) -> dict[str, Any]:
    merged = deepcopy(DEFAULT_GRADING_POLICY)
    payload = payload or {}
    raw_points = payload.get("grade_points") or {}
    merged["grade_points"] = {
        grade: float(raw_points.get(grade, DEFAULT_GRADE_POINTS[grade]))
        for grade in DEFAULT_GRADE_POINTS
    }
    precision = int(payload.get("transcript_precision", DEFAULT_GRADING_POLICY["transcript_precision"]))
    merged["transcript_precision"] = max(0, min(4, precision))
    return merged


async def get_grading_policy(*, database: Any) -> dict[str, Any]:
    row = (
        await database.settings.find_one({"key": "academic_grading_policy"})
        if getattr(database, "settings", None) is not None
        else None
    )
    return normalize_grading_policy((row or {}).get("value") or {})


async def set_grading_policy(*, payload: dict[str, Any], database: Any) -> dict[str, Any]:
    normalized = normalize_grading_policy(payload)
    if getattr(database, "settings", None) is not None:
        await database.settings.update_one(
            {"key": "academic_grading_policy"},
            {"$set": {"key": "academic_grading_policy", "value": normalized}},
            upsert=True,
        )
    return normalized
