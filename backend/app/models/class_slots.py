from typing import Any, Dict

from app.core.schema_versions import CLASS_SLOT_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity


def class_slot_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "course_offering_id": document.get("course_offering_id"),
        "day": document.get("day"),
        "start_time": document.get("start_time"),
        "end_time": document.get("end_time"),
        "room_code": document.get("room_code"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=CLASS_SLOT_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="class_slot", document=document, display_name=document.get("room_code"))
