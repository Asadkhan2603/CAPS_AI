from typing import Any, Dict


def audit_log_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "actor_user_id": document.get("actor_user_id"),
        "action": document.get("action", ""),
        "entity_type": document.get("entity_type", ""),
        "entity_id": document.get("entity_id"),
        "detail": document.get("detail"),
        "created_at": document.get("created_at"),
    }
