from datetime import datetime, timezone
from typing import Any

from starlette.concurrency import run_in_threadpool

from app.core.schema_versions import AI_EVALUATION_RUN_SCHEMA_VERSION
from app.services.evaluation_ai_module import build_ai_insight, build_ai_payload_from_summary, normalize_rubric_criteria
from app.services.grading import grade_from_total, grand_total, internal_total


def compute_evaluation_totals(payload: dict[str, Any]) -> tuple[float, float, str]:
    internal = internal_total(
        payload["attendance_percent"],
        payload["skill"],
        payload["behavior"],
        payload["report"],
        payload["viva"],
    )
    total = grand_total(
        payload["attendance_percent"],
        payload["skill"],
        payload["behavior"],
        payload["report"],
        payload["viva"],
        payload["final_exam"],
    )
    grade = grade_from_total(total)
    return float(internal), float(total), grade


async def build_ai_insight_async(
    *,
    submission_text: str,
    attendance_percent: int,
    internal_total_value: float,
    grand_total_value: float,
    grade: str,
    rubric_criteria: list[dict[str, Any]] | None = None,
    runtime_settings: dict | None = None,
) -> dict:
    return await run_in_threadpool(
        build_ai_insight,
        submission_text=submission_text,
        attendance_percent=attendance_percent,
        internal_total=internal_total_value,
        grand_total=grand_total_value,
        grade=grade,
        rubric_criteria=normalize_rubric_criteria(rubric_criteria),
        runtime_settings=runtime_settings,
    )


def build_submission_reuse_ai_payload(
    submission: dict[str, Any],
    *,
    rubric_criteria: list[dict[str, Any]] | None = None,
) -> dict[str, Any] | None:
    if submission.get("ai_score") is None or not submission.get("ai_feedback"):
        return None

    payload = build_ai_payload_from_summary(
        ai_score=submission.get("ai_score"),
        ai_feedback=submission.get("ai_feedback"),
        ai_status=submission.get("ai_status"),
        ai_provider=submission.get("ai_provider"),
        ai_prompt_version=submission.get("ai_prompt_version"),
        ai_runtime_snapshot=submission.get("ai_runtime_snapshot"),
        submission_text=str(submission.get("extracted_text") or ""),
        rubric_criteria=normalize_rubric_criteria(rubric_criteria),
    )
    payload["ai_risk_flags"] = []
    return payload


def ai_payload_update_fields(ai_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "ai_score": ai_payload.get("ai_score"),
        "ai_feedback": ai_payload.get("ai_feedback"),
        "ai_status": ai_payload.get("ai_status"),
        "ai_provider": ai_payload.get("ai_provider"),
        "ai_prompt_version": ai_payload.get("ai_prompt_version"),
        "ai_runtime_snapshot": ai_payload.get("ai_runtime_snapshot"),
        "ai_confidence": ai_payload.get("ai_confidence"),
        "ai_confidence_mode": ai_payload.get("ai_confidence_mode"),
        "ai_risk_flags": ai_payload.get("ai_risk_flags") or [],
        "ai_strengths": ai_payload.get("ai_strengths") or [],
        "ai_gaps": ai_payload.get("ai_gaps") or [],
        "ai_suggestions": ai_payload.get("ai_suggestions") or [],
        "ai_criterion_scores": ai_payload.get("ai_criterion_scores") or [],
        "ai_criterion_rationales": ai_payload.get("ai_criterion_rationales") or [],
        "ai_academic_rationale": ai_payload.get("ai_academic_rationale") or [],
        "rubric_criteria": ai_payload.get("rubric_criteria") or [],
    }


async def persist_ai_trace(
    *,
    database: Any,
    evaluation_id: str | None,
    submission_id: str,
    actor_user_id: str,
    ai_payload: dict[str, Any],
    totals_payload: dict[str, Any],
) -> None:
    document = {
        "evaluation_id": evaluation_id,
        "submission_id": submission_id,
        "actor_user_id": actor_user_id,
        "ai_score": ai_payload.get("ai_score"),
        "ai_feedback": ai_payload.get("ai_feedback"),
        "ai_status": ai_payload.get("ai_status"),
        "ai_provider": ai_payload.get("ai_provider"),
        "ai_prompt_version": ai_payload.get("ai_prompt_version"),
        "ai_runtime_snapshot": ai_payload.get("ai_runtime_snapshot"),
        "ai_confidence": ai_payload.get("ai_confidence"),
        "ai_confidence_mode": ai_payload.get("ai_confidence_mode"),
        "ai_strengths": ai_payload.get("ai_strengths") or [],
        "ai_gaps": ai_payload.get("ai_gaps") or [],
        "ai_suggestions": ai_payload.get("ai_suggestions") or [],
        "ai_criterion_scores": ai_payload.get("ai_criterion_scores") or [],
        "ai_criterion_rationales": ai_payload.get("ai_criterion_rationales") or [],
        "ai_academic_rationale": ai_payload.get("ai_academic_rationale") or [],
        "ai_risk_flags": ai_payload.get("ai_risk_flags") or [],
        "rubric_criteria": ai_payload.get("rubric_criteria") or [],
        "grade": totals_payload.get("grade"),
        "internal_total": totals_payload.get("internal_total"),
        "grand_total": totals_payload.get("grand_total"),
        "schema_version": AI_EVALUATION_RUN_SCHEMA_VERSION,
        "created_at": datetime.now(timezone.utc),
    }
    await database.ai_evaluation_runs.insert_one(document)
