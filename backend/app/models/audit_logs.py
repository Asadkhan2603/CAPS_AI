from typing import Any, Dict

from app.core.schema_versions import AUDIT_LOG_SCHEMA_VERSION, normalize_schema_version


def audit_log_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "actor_user_id": document.get("actor_user_id"),
        "action": document.get("action", ""),
        "action_type": document.get("action_type"),
        "entity_type": document.get("entity_type", ""),
        "resource_type": document.get("resource_type"),
        "entity_id": document.get("entity_id"),
        "detail": document.get("detail"),
        "old_value": document.get("old_value"),
        "new_value": document.get("new_value"),
        "ip_address": document.get("ip_address"),
        "user_agent": document.get("user_agent"),
        "severity": document.get("severity"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=AUDIT_LOG_SCHEMA_VERSION,
        ),
    }
