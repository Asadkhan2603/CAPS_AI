from __future__ import annotations

from typing import Any

from app.services.ai_evaluation import generate_ai_feedback
from app.services.ai_runtime import clone_runtime_snapshot


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _split_insight_lines(text: str) -> tuple[list[str], list[str], list[str]]:
    raw_parts = [part.strip() for part in (text or "").split(".") if part.strip()]
    strengths: list[str] = []
    gaps: list[str] = []
    suggestions: list[str] = []
    for part in raw_parts:
        lower = part.lower()
        if "strength" in lower or "good" in lower or "clear" in lower:
            strengths.append(part)
        elif "gap" in lower or "missing" in lower or "improve" in lower:
            gaps.append(part)
        elif "suggest" in lower or "add" in lower or "recommend" in lower:
            suggestions.append(part)

    if not strengths and raw_parts:
        strengths.append(raw_parts[0])
    if not gaps and len(raw_parts) > 1:
        gaps.append(raw_parts[min(1, len(raw_parts) - 1)])
    if not suggestions:
        suggestions.append("Add concrete examples and align directly with rubric checkpoints.")

    return strengths[:4], gaps[:4], suggestions[:4]


def _risk_flags(*, attendance_percent: int, grand_total: float, ai_score: float | None) -> list[str]:
    flags: list[str] = []
    if attendance_percent < 75:
        flags.append("low_attendance")
    if grand_total < 45:
        flags.append("critical_academic_risk")
    if grand_total < 60:
        flags.append("below_passing_trend")
    if ai_score is not None and ai_score < 4:
        flags.append("weak_submission_quality")
    return flags


def build_ai_insight(
    *,
    submission_text: str,
    attendance_percent: int,
    internal_total: float,
    grand_total: float,
    grade: str,
    runtime_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ai = generate_ai_feedback(submission_text, max_score=10.0, runtime_settings=runtime_settings)
    ai_score = _safe_float(ai.get("score"), 0.0)
    summary = str(ai.get("summary") or "No AI summary generated")
    strengths, gaps, suggestions = _split_insight_lines(summary)

    confidence = 0.45
    if ai.get("status") == "completed":
        confidence = 0.8
    elif ai_score >= 7:
        confidence = 0.7

    risk_flags = _risk_flags(
        attendance_percent=attendance_percent,
        grand_total=grand_total,
        ai_score=ai_score,
    )
    if grade in {"Needs Improvement", "C"}:
        risk_flags.append("manual_review_recommended")

    return {
        "ai_score": round(ai_score, 2),
        "ai_feedback": summary[:1600],
        "ai_status": str(ai.get("status") or "fallback"),
        "ai_provider": str(ai.get("provider") or "local"),
        "ai_prompt_version": str(ai.get("prompt_version") or ""),
        "ai_runtime_snapshot": clone_runtime_snapshot(ai.get("runtime_snapshot") if isinstance(ai.get("runtime_snapshot"), dict) else runtime_settings),
        "ai_confidence": max(0.0, min(confidence, 1.0)),
        "ai_strengths": strengths,
        "ai_gaps": gaps,
        "ai_suggestions": suggestions,
        "ai_risk_flags": sorted(set(risk_flags)),
        "insight": {
            "summary": summary[:1600],
            "strengths": strengths,
            "gaps": gaps,
            "suggestions": suggestions,
            "risk_flags": sorted(set(risk_flags)),
            "confidence": max(0.0, min(confidence, 1.0)),
            "status": str(ai.get("status") or "fallback"),
            "provider": str(ai.get("provider") or "local"),
            "prompt_version": str(ai.get("prompt_version") or ""),
            "runtime_snapshot": clone_runtime_snapshot(ai.get("runtime_snapshot") if isinstance(ai.get("runtime_snapshot"), dict) else runtime_settings),
        },
    }


def build_trace_record(*, evaluation_id: str | None, submission_id: str, actor_user_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "evaluation_id": evaluation_id,
        "submission_id": submission_id,
        "actor_user_id": actor_user_id,
        "ai_status": payload.get("ai_status"),
        "ai_provider": payload.get("ai_provider"),
        "ai_prompt_version": payload.get("ai_prompt_version"),
        "ai_runtime_snapshot": clone_runtime_snapshot(payload.get("ai_runtime_snapshot")),
        "ai_score": payload.get("ai_score"),
        "ai_confidence": payload.get("ai_confidence"),
        "ai_risk_flags": list(payload.get("ai_risk_flags") or []),
        "ai_feedback": payload.get("ai_feedback"),
        "ai_strengths": list(payload.get("ai_strengths") or []),
        "ai_gaps": list(payload.get("ai_gaps") or []),
        "ai_suggestions": list(payload.get("ai_suggestions") or []),
        "created_at": payload.get("created_at"),
    }
