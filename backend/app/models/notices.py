from typing import Any, Dict


def notice_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "title": document.get("title", ""),
        "message": document.get("message", ""),
        "priority": document.get("priority", "normal"),
        "scope": document.get("scope", "college"),
        "scope_ref_id": document.get("scope_ref_id"),
        "expires_at": document.get("expires_at"),
        "images": document.get("images", []) or [],
        "created_by": document.get("created_by"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
    }
