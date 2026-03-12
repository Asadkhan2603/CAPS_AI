from typing import Any, Dict

from app.core.schema_versions import NOTICE_SCHEMA_VERSION, normalize_schema_version


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
        "is_pinned": document.get("is_pinned", False),
        "scheduled_at": document.get("scheduled_at"),
        "read_count": int(document.get("read_count", 0) or 0),
        "seen_by": document.get("seen_by", []) or [],
        "created_by": document.get("created_by"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=NOTICE_SCHEMA_VERSION,
        ),
    }
