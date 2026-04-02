from typing import Any, Dict

from app.core.schema_versions import NOTICE_SCHEMA_VERSION, normalize_schema_version


def notice_public(document: Dict[str, Any], *, current_user_id: str | None = None) -> Dict[str, Any]:
    seen_by = [str(item) for item in (document.get("seen_by", []) or []) if item]
    current_user_key = str(current_user_id) if current_user_id else None
    return {
        "id": str(document["_id"]),
        "title": document.get("title", ""),
        "message": document.get("message", ""),
        "priority": document.get("priority", "normal"),
        "scope": document.get("scope", "college"),
        "scope_ref_id": document.get("scope_ref_id"),
        "expires_at": document.get("expires_at"),
        "images": document.get("images", []) or [],
        "is_pinned": document.get("is_pinned", False),
        "scheduled_at": document.get("scheduled_at"),
        "read_count": int(document.get("read_count", 0) or 0),
        "seen_by": seen_by,
        "is_read": bool(current_user_key and current_user_key in seen_by),
        "created_by": document.get("created_by"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=NOTICE_SCHEMA_VERSION,
        ),
    }
