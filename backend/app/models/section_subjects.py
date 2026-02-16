from typing import Any, Dict


def section_subject_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "section_id": document.get("section_id"),
        "subject_id": document.get("subject_id"),
        "teacher_user_id": document.get("teacher_user_id"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
    }
