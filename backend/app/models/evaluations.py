from typing import Any, Dict


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
        "remarks": document.get("remarks"),
        "is_finalized": document.get("is_finalized", False),
        "created_at": document.get("created_at"),
    }
