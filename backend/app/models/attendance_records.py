from typing import Any, Dict


def attendance_record_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "class_slot_id": document.get("class_slot_id"),
        "student_id": document.get("student_id"),
        "status": document.get("status"),
        "note": document.get("note"),
        "marked_by_user_id": document.get("marked_by_user_id"),
        "marked_at": document.get("marked_at"),
    }
