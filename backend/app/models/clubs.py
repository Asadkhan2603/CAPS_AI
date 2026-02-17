from typing import Any, Dict


def club_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "name": document.get("name", ""),
        "description": document.get("description"),
        "coordinator_user_id": document.get("coordinator_user_id"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
    }
