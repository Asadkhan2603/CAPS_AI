from typing import Any, Dict

from app.core.schema_versions import NOTIFICATION_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity, build_user_label


def notification_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "title": document.get("title", ""),
        "message": document.get("message", ""),
        "priority": document.get("priority", "normal"),
        "scope": document.get("scope", "global"),
        "target_user_id": document.get("target_user_id"),
        "target_user_label": build_user_label(document.get("target_user_id"), full_name=document.get("target_user_name"), email=document.get("target_user_email")),
        "created_by": document.get("created_by"),
        "created_by_label": build_user_label(document.get("created_by"), full_name=document.get("created_by_name"), email=document.get("created_by_email")),
        "is_read": document.get("is_read", False),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=NOTIFICATION_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="notification", document=document, display_name=document.get("title"))
