from typing import Any, Dict


def user_public(document: Dict[str, Any]) -> Dict[str, Any]:
    user_id = str(document["_id"])
    return {
        "id": user_id,
        "full_name": document.get("full_name", ""),
        "email": document.get("email", ""),
        "role": document.get("role", ""),
        "extended_roles": document.get("extended_roles", []),
        "role_scope": document.get("role_scope", {}) or {},
        "is_active": document.get("is_active", True),
        "profile": document.get("profile", {}) or {},
        "avatar_url": f"/api/v1/auth/profile/avatar/{user_id}" if document.get("avatar_filename") else None,
        "avatar_updated_at": document.get("avatar_updated_at"),
        "created_at": document.get("created_at"),
    }
