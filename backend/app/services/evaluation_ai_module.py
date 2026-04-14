from __future__ import annotations

from typing import Any

from app.services.ai_evaluation import generate_ai_feedback
from app.services.ai_runtime import clone_runtime_snapshot
from app.services.similarity_rollout import tokenize_for_similarity


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


def _confidence_mode(ai_status: str | None, provider: str | None) -> str:
    if ai_status == "completed" and provider and provider != "local":
        return "provider"
    return "fallback"


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


def normalize_rubric_criteria(rubric_criteria: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in rubric_criteria or []:
        if hasattr(item, "model_dump"):
            item = item.model_dump()
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "").strip()
        if not label:
            continue
        try:
            max_score = max(0.0, float(item.get("max_score") or 0.0))
        except (TypeError, ValueError):
            max_score = 0.0
        keywords = [
            str(keyword).strip().lower()
            for keyword in (item.get("keywords") or [])
            if str(keyword).strip()
        ]
        notes = str(item.get("notes") or "").strip() or None
        normalized.append(
            {
                "label": label[:200],
                "max_score": round(max_score, 2),
                "keywords": keywords[:12],
                "notes": notes[:500] if notes else None,
            }
        )
    return normalized


def _score_rubric_criteria(submission_text: str, rubric_criteria: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    criteria = normalize_rubric_criteria(rubric_criteria)
    if not criteria:
        return []

    answer_tokens = set(tokenize_for_similarity(submission_text))
    response_depth = min(len(answer_tokens) / 80.0, 1.0)
    scored: list[dict[str, Any]] = []
    for criterion in criteria:
        label_tokens = tokenize_for_similarity(criterion["label"])
        note_tokens = tokenize_for_similarity(str(criterion.get("notes") or ""))
        keyword_tokens = [tokenize_for_similarity(keyword)[0] for keyword in criterion.get("keywords") or [] if tokenize_for_similarity(keyword)]
        reference_tokens = set(label_tokens + note_tokens + keyword_tokens)
        if not reference_tokens:
            reference_tokens = set(label_tokens)
        matched_tokens = sorted(reference_tokens.intersection(answer_tokens))
        keyword_hits = sorted(set(keyword_tokens).intersection(answer_tokens))
        coverage = len(matched_tokens) / max(len(reference_tokens), 1)
        keyword_coverage = len(keyword_hits) / max(len(keyword_tokens), 1) if keyword_tokens else coverage
        normalized_score = min(1.0, (0.55 * coverage) + (0.25 * keyword_coverage) + (0.20 * response_depth))
        awarded_score = round(float(criterion["max_score"]) * normalized_score, 2)
        if coverage >= 0.7:
            rationale = f"Strong direct coverage for {criterion['label']} with explicit rubric-term support."
        elif coverage >= 0.35:
            rationale = f"Partial support for {criterion['label']}; more direct evidence would improve confidence."
        else:
            rationale = f"Limited explicit support for {criterion['label']}; reviewer should verify this criterion manually."
        scored.append(
            {
                "label": criterion["label"],
                "max_score": round(float(criterion["max_score"]), 2),
                "awarded_score": awarded_score,
                "evidence_coverage": round(coverage, 3),
                "rationale": rationale,
                "keywords_hit": keyword_hits[:8],
            }
        )
    return scored


def _criterion_rationales(criterion_scores: list[dict[str, Any]]) -> list[str]:
    return [str(item.get("rationale") or "") for item in criterion_scores if str(item.get("rationale") or "").strip()][:8]


def _blend_fallback_score_with_rubric(
    *,
    ai_score: float,
    ai_status: str | None,
    ai_provider: str | None,
    criterion_scores: list[dict[str, Any]],
) -> float:
    if ai_status == "completed" and ai_provider and ai_provider != "local":
        return round(ai_score, 2)
    if not criterion_scores:
        return round(ai_score, 2)
    max_total = sum(float(item.get("max_score") or 0.0) for item in criterion_scores)
    awarded_total = sum(float(item.get("awarded_score") or 0.0) for item in criterion_scores)
    if max_total <= 0:
        return round(ai_score, 2)
    rubric_score = (awarded_total / max_total) * 10.0
    return round((0.45 * ai_score) + (0.55 * rubric_score), 2)


def build_ai_insight(
    *,
    submission_text: str,
    attendance_percent: int,
    internal_total: float,
    grand_total: float,
    grade: str,
    rubric_criteria: list[dict[str, Any]] | None = None,
    runtime_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ai = generate_ai_feedback(submission_text, max_score=10.0, runtime_settings=runtime_settings)
    ai_score = _safe_float(ai.get("score"), 0.0)
    summary = str(ai.get("summary") or "No AI summary generated")
    strengths, gaps, suggestions = _split_insight_lines(summary)
    normalized_rubric_criteria = normalize_rubric_criteria(rubric_criteria)
    criterion_scores = _score_rubric_criteria(submission_text, normalized_rubric_criteria)
    criterion_rationales = _criterion_rationales(criterion_scores)
    ai_score = _blend_fallback_score_with_rubric(
        ai_score=ai_score,
        ai_status=str(ai.get("status") or "fallback"),
        ai_provider=str(ai.get("provider") or "local"),
        criterion_scores=criterion_scores,
    )

    confidence = 0.45
    if ai.get("status") == "completed":
        confidence = 0.8
    elif ai_score >= 7:
        confidence = 0.7
    confidence_mode = _confidence_mode(str(ai.get("status") or "fallback"), str(ai.get("provider") or "local"))

    risk_flags = _risk_flags(
        attendance_percent=attendance_percent,
        grand_total=grand_total,
        ai_score=ai_score,
    )
    if grade in {"Needs Improvement", "C"}:
        risk_flags.append("manual_review_recommended")
    academic_rationale = criterion_rationales[:4] if criterion_rationales else strengths[:2] + gaps[:2]

    return {
        "ai_score": round(ai_score, 2),
        "ai_feedback": summary[:1600],
        "ai_status": str(ai.get("status") or "fallback"),
        "ai_provider": str(ai.get("provider") or "local"),
        "ai_prompt_version": str(ai.get("prompt_version") or ""),
        "ai_runtime_snapshot": clone_runtime_snapshot(ai.get("runtime_snapshot") if isinstance(ai.get("runtime_snapshot"), dict) else runtime_settings),
        "ai_confidence": max(0.0, min(confidence, 1.0)),
        "ai_confidence_mode": confidence_mode,
        "ai_strengths": strengths,
        "ai_gaps": gaps,
        "ai_suggestions": suggestions,
        "ai_criterion_scores": criterion_scores,
        "ai_criterion_rationales": criterion_rationales,
        "ai_academic_rationale": academic_rationale,
        "ai_risk_flags": sorted(set(risk_flags)),
        "rubric_criteria": normalized_rubric_criteria,
        "insight": {
            "summary": summary[:1600],
            "strengths": strengths,
            "gaps": gaps,
            "suggestions": suggestions,
            "risk_flags": sorted(set(risk_flags)),
            "criterion_scores": criterion_scores,
            "criterion_rationales": criterion_rationales,
            "academic_rationale": academic_rationale,
            "risk_context": sorted(set(risk_flags)),
            "confidence": max(0.0, min(confidence, 1.0)),
            "confidence_mode": confidence_mode,
            "status": str(ai.get("status") or "fallback"),
            "provider": str(ai.get("provider") or "local"),
            "prompt_version": str(ai.get("prompt_version") or ""),
            "runtime_snapshot": clone_runtime_snapshot(ai.get("runtime_snapshot") if isinstance(ai.get("runtime_snapshot"), dict) else runtime_settings),
        },
    }


def build_ai_payload_from_summary(
    *,
    ai_score: float | None,
    ai_feedback: str | None,
    ai_status: str | None,
    ai_provider: str | None,
    ai_prompt_version: str | None,
    ai_runtime_snapshot: dict | None,
    submission_text: str = "",
    rubric_criteria: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    summary = str(ai_feedback or "No AI summary generated")
    strengths, gaps, suggestions = _split_insight_lines(summary)
    score_value = _safe_float(ai_score, 0.0)
    normalized_rubric_criteria = normalize_rubric_criteria(rubric_criteria)
    criterion_scores = _score_rubric_criteria(submission_text, normalized_rubric_criteria)
    criterion_rationales = _criterion_rationales(criterion_scores)
    score_value = _blend_fallback_score_with_rubric(
        ai_score=score_value,
        ai_status=str(ai_status or "fallback"),
        ai_provider=str(ai_provider or "local"),
        criterion_scores=criterion_scores,
    )
    confidence = 0.45
    if ai_status == "completed":
        confidence = 0.8
    elif score_value >= 7:
        confidence = 0.7
    confidence_mode = _confidence_mode(str(ai_status or "fallback"), str(ai_provider or "local"))
    return {
        "ai_score": round(score_value, 2),
        "ai_feedback": summary[:1600],
        "ai_status": str(ai_status or "fallback"),
        "ai_provider": str(ai_provider or "local"),
        "ai_prompt_version": str(ai_prompt_version or ""),
        "ai_runtime_snapshot": clone_runtime_snapshot(ai_runtime_snapshot),
        "ai_confidence": max(0.0, min(confidence, 1.0)),
        "ai_confidence_mode": confidence_mode,
        "ai_strengths": strengths,
        "ai_gaps": gaps,
        "ai_suggestions": suggestions,
        "ai_criterion_scores": criterion_scores,
        "ai_criterion_rationales": criterion_rationales,
        "ai_academic_rationale": criterion_rationales[:4] if criterion_rationales else strengths[:2] + gaps[:2],
        "ai_risk_flags": [],
        "rubric_criteria": normalized_rubric_criteria,
        "insight": {
            "summary": summary[:1600],
            "strengths": strengths,
            "gaps": gaps,
            "suggestions": suggestions,
            "risk_flags": [],
            "criterion_scores": criterion_scores,
            "criterion_rationales": criterion_rationales,
            "academic_rationale": criterion_rationales[:4] if criterion_rationales else strengths[:2] + gaps[:2],
            "risk_context": [],
            "confidence": max(0.0, min(confidence, 1.0)),
            "confidence_mode": confidence_mode,
            "status": str(ai_status or "fallback"),
            "provider": str(ai_provider or "local"),
            "prompt_version": str(ai_prompt_version or ""),
            "runtime_snapshot": clone_runtime_snapshot(ai_runtime_snapshot),
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
        "ai_confidence_mode": payload.get("ai_confidence_mode"),
        "ai_risk_flags": list(payload.get("ai_risk_flags") or []),
        "ai_feedback": payload.get("ai_feedback"),
        "ai_strengths": list(payload.get("ai_strengths") or []),
        "ai_gaps": list(payload.get("ai_gaps") or []),
        "ai_suggestions": list(payload.get("ai_suggestions") or []),
        "ai_criterion_scores": list(payload.get("ai_criterion_scores") or []),
        "ai_criterion_rationales": list(payload.get("ai_criterion_rationales") or []),
        "ai_academic_rationale": list(payload.get("ai_academic_rationale") or []),
        "rubric_criteria": list(payload.get("rubric_criteria") or []),
        "created_at": payload.get("created_at"),
    }
