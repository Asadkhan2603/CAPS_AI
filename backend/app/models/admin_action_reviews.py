from typing import Any, Dict

from app.core.schema_versions import ADMIN_ACTION_REVIEW_SCHEMA_VERSION, normalize_schema_version


def admin_action_review_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document.get("_id")),
        "review_type": document.get("review_type"),
        "action": document.get("action"),
        "entity_type": document.get("entity_type"),
        "entity_id": document.get("entity_id"),
        "reason": document.get("reason"),
        "status": document.get("status"),
        "requested_by": document.get("requested_by"),
        "reviewed_by": document.get("reviewed_by"),
        "reviewed_at": document.get("reviewed_at"),
        "executed_by": document.get("executed_by"),
        "executed_at": document.get("executed_at"),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=ADMIN_ACTION_REVIEW_SCHEMA_VERSION,
        ),
    }
