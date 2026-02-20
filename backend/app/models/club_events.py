from typing import Any, Dict


def club_event_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "club_id": document.get("club_id"),
        "title": document.get("title", ""),
        "description": document.get("description"),
        "event_date": document.get("event_date"),
        "capacity": document.get("capacity", 0),
        "status": document.get("status", "open"),
        "result_summary": document.get("result_summary"),
        "created_by": document.get("created_by"),
        "created_at": document.get("created_at"),
    }
