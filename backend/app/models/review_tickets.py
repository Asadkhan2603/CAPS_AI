from typing import Any, Dict


def review_ticket_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "evaluation_id": document.get("evaluation_id"),
        "requested_by_user_id": document.get("requested_by_user_id"),
        "reason": document.get("reason", ""),
        "status": document.get("status", "pending"),
        "resolved_by_user_id": document.get("resolved_by_user_id"),
        "resolved_at": document.get("resolved_at"),
        "created_at": document.get("created_at"),
    }
