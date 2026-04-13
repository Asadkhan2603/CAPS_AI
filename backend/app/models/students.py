from typing import Any, Dict

from app.core.schema_versions import STUDENT_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity


def student_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "full_name": document.get("full_name", ""),
        "roll_number": document.get("roll_number", ""),
        "email": document.get("email"),
        "user_id": document.get("user_id"),
        "class_id": document.get("class_id"),
        "group_id": document.get("group_id"),
        "canonical_class_id": document.get("canonical_class_id"),
        "canonical_group_id": document.get("canonical_group_id"),
        "placement_source": document.get("placement_source"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=STUDENT_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="student", document=document, display_name=document.get("full_name"))
