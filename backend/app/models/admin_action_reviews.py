from typing import Any, Dict

from app.core.schema_versions import ADMIN_ACTION_REVIEW_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity, build_entity_label, build_user_label


def admin_action_review_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document.get("_id")),
        "review_type": document.get("review_type"),
        "action": document.get("action"),
        "entity_type": document.get("entity_type"),
        "entity_id": document.get("entity_id"),
        "entity_label": build_entity_label(document.get("entity_type"), document.get("entity_id"), entity_name=document.get("entity_name")),
        "reason": document.get("reason"),
        "status": document.get("status"),
        "requested_by": document.get("requested_by"),
        "requested_by_label": build_user_label(document.get("requested_by"), full_name=document.get("requested_by_name"), email=document.get("requested_by_email")),
        "reviewed_by": document.get("reviewed_by"),
        "reviewed_by_label": build_user_label(document.get("reviewed_by"), full_name=document.get("reviewed_by_name"), email=document.get("reviewed_by_email")),
        "reviewed_at": document.get("reviewed_at"),
        "executed_by": document.get("executed_by"),
        "executed_by_label": build_user_label(document.get("executed_by"), full_name=document.get("executed_by_name"), email=document.get("executed_by_email")),
        "executed_at": document.get("executed_at"),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=ADMIN_ACTION_REVIEW_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="admin_action_review", document=document, display_name=document.get("action"))
