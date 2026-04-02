from typing import Any, Dict

from app.core.schema_versions import REVIEW_TICKET_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity, build_entity_label, build_user_label


def review_ticket_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "evaluation_id": document.get("evaluation_id"),
        "evaluation_label": build_entity_label("evaluation", document.get("evaluation_id"), entity_name=document.get("evaluation_name")),
        "requested_by_user_id": document.get("requested_by_user_id"),
        "requested_by_label": build_user_label(document.get("requested_by_user_id"), full_name=document.get("requested_by_name"), email=document.get("requested_by_email")),
        "reason": document.get("reason", ""),
        "status": document.get("status", "pending"),
        "resolved_by_user_id": document.get("resolved_by_user_id"),
        "resolved_by_label": build_user_label(document.get("resolved_by_user_id"), full_name=document.get("resolved_by_name"), email=document.get("resolved_by_email")),
        "resolved_at": document.get("resolved_at"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=REVIEW_TICKET_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="review_ticket", document=document, display_name=document.get("reason"))
