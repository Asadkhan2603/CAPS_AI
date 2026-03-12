from typing import Any, Dict

from app.core.schema_versions import EVALUATION_SCHEMA_VERSION, normalize_schema_version


def evaluation_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "submission_id": document.get("submission_id"),
        "student_user_id": document.get("student_user_id"),
        "teacher_user_id": document.get("teacher_user_id"),
        "attendance_percent": document.get("attendance_percent", 0),
        "skill": document.get("skill", 0.0),
        "behavior": document.get("behavior", 0.0),
        "report": document.get("report", 0.0),
        "viva": document.get("viva", 0.0),
        "final_exam": document.get("final_exam", 0),
        "internal_total": document.get("internal_total", 0.0),
        "grand_total": document.get("grand_total", 0.0),
        "grade": document.get("grade", "Needs Improvement"),
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
        "ai_risk_flags": list(document.get("ai_risk_flags") or []),
        "ai_strengths": list(document.get("ai_strengths") or []),
        "ai_gaps": list(document.get("ai_gaps") or []),
        "ai_suggestions": list(document.get("ai_suggestions") or []),
        "remarks": document.get("remarks"),
        "is_finalized": document.get("is_finalized", False),
        "finalized_at": document.get("finalized_at"),
        "finalized_by_user_id": document.get("finalized_by_user_id"),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
    }
