from typing import Any, Dict


def course_offering_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "subject_id": document.get("subject_id"),
        "teacher_user_id": document.get("teacher_user_id"),
        "batch_id": document.get("batch_id"),
        "semester_id": document.get("semester_id"),
        "section_id": document.get("section_id"),
        "group_id": document.get("group_id"),
        "academic_year": document.get("academic_year"),
        "offering_type": document.get("offering_type", "theory"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
    }
