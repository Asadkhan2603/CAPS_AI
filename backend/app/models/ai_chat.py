from typing import Any, Dict


def ai_chat_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "teacher_id": document.get("teacher_id"),
        "student_id": document.get("student_id"),
        "exam_id": document.get("exam_id"),
        "question_id": document.get("question_id"),
        "messages": document.get("messages", []),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
    }
