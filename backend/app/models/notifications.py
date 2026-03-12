from typing import Any, Dict

from app.core.schema_versions import NOTIFICATION_SCHEMA_VERSION, normalize_schema_version


def notification_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "title": document.get("title", ""),
        "message": document.get("message", ""),
        "priority": document.get("priority", "normal"),
        "scope": document.get("scope", "global"),
        "target_user_id": document.get("target_user_id"),
        "created_by": document.get("created_by"),
        "is_read": document.get("is_read", False),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=NOTIFICATION_SCHEMA_VERSION,
        ),
    }
