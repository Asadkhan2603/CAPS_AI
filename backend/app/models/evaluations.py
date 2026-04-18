from typing import Any, Dict

from app.core.schema_versions import EVALUATION_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity


def _stringify_reference(value: Any) -> Any:
    return str(value) if value is not None else None


def _normalize_rubric_criteria(value: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in list(value or []):
        if not isinstance(item, dict):
            continue
        output.append(
            {
                "label": item.get("label") or item.get("name") or "Criterion",
                "max_score": item.get("max_score") if item.get("max_score") is not None else item.get("marks", 0),
                "keywords": list(item.get("keywords") or []),
                "notes": item.get("notes"),
            }
        )
    return output


def evaluation_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "submission_id": _stringify_reference(document.get("submission_id")),
        "submission_label": document.get("submission_label"),
        "student_user_id": _stringify_reference(document.get("student_user_id")),
        "student_label": document.get("student_label"),
        "teacher_user_id": _stringify_reference(document.get("teacher_user_id")),
        "teacher_label": document.get("teacher_label"),
        "attendance_percent": document.get("attendance_percent", 0),
        "skill": document.get("skill", 0.0),
        "behavior": document.get("behavior", 0.0),
        "report": document.get("report", 0.0),
        "viva": document.get("viva", 0.0),
        "final_exam": document.get("final_exam", 0),
        "internal_total": document.get("internal_total", 0.0),
        "grand_total": document.get("grand_total", 0.0),
        "grade": document.get("grade", "Needs Improvement"),
        "rubric_criteria": _normalize_rubric_criteria(document.get("rubric_criteria")),
        "ai_score": document.get("ai_score"),
        "ai_feedback": document.get("ai_feedback"),
        "ai_status": document.get("ai_status"),
        "ai_provider": document.get("ai_provider"),
        "ai_prompt_version": document.get("ai_prompt_version"),
        "ai_runtime_snapshot": document.get("ai_runtime_snapshot"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=EVALUATION_SCHEMA_VERSION,
        ),
        "ai_confidence": document.get("ai_confidence"),
        "ai_confidence_mode": document.get("ai_confidence_mode"),
        "ai_risk_flags": list(document.get("ai_risk_flags") or []),
        "ai_strengths": list(document.get("ai_strengths") or []),
        "ai_gaps": list(document.get("ai_gaps") or []),
        "ai_suggestions": list(document.get("ai_suggestions") or []),
        "ai_criterion_scores": list(document.get("ai_criterion_scores") or []),
        "ai_criterion_rationales": list(document.get("ai_criterion_rationales") or []),
        "ai_academic_rationale": list(document.get("ai_academic_rationale") or []),
        "remarks": document.get("remarks"),
        "is_finalized": document.get("is_finalized", False),
        "finalized_at": document.get("finalized_at"),
        "finalized_by_user_id": document.get("finalized_by_user_id"),
        "result_status": document.get("result_status", "released" if document.get("released_at") else ("finalized_unreleased" if document.get("is_finalized") else "draft")),
        "released_at": document.get("released_at"),
        "released_by_user_id": document.get("released_by_user_id"),
        "result_version": document.get("result_version", 1),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
    }
    return apply_public_identity(payload, kind="evaluation", document=document, display_name=document.get("grade"))
