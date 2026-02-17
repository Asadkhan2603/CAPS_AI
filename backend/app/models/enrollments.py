from typing import Any, Dict


def enrollment_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "class_id": document.get("class_id"),
        "student_id": document.get("student_id"),
        "section_id": document.get("section_id"),
        "assigned_by_user_id": document.get("assigned_by_user_id"),
        "created_at": document.get("created_at"),
    }
