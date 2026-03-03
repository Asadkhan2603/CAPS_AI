from typing import Any, Dict


def class_slot_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "course_offering_id": document.get("course_offering_id"),
        "day": document.get("day"),
        "start_time": document.get("start_time"),
        "end_time": document.get("end_time"),
        "room_code": document.get("room_code"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
    }
