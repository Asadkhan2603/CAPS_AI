from typing import Any, Dict


def club_event_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "club_id": document.get("club_id"),
        "title": document.get("title", ""),
        "description": document.get("description"),
        "event_type": document.get("event_type", "workshop"),
        "visibility": document.get("visibility", "public"),
        "registration_start": document.get("registration_start"),
        "registration_end": document.get("registration_end"),
        "event_date": document.get("event_date"),
        "capacity": document.get("capacity", 0),
        "approval_required": bool(document.get("approval_required", False)),
        "certificate_enabled": bool(document.get("certificate_enabled", False)),
        "status": document.get("status", "draft"),
        "result_summary": document.get("result_summary"),
        "created_by": document.get("created_by"),
        "created_at": document.get("created_at"),
    }
