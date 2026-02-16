from typing import Any, Dict


def user_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "full_name": document.get("full_name", ""),
        "email": document.get("email", ""),
        "role": document.get("role", ""),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
    }
