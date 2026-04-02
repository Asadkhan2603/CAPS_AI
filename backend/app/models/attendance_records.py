from typing import Any, Dict

from app.core.schema_versions import ATTENDANCE_RECORD_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity, build_user_label


def attendance_record_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "class_slot_id": document.get("class_slot_id"),
        "student_id": document.get("student_id"),
        "status": document.get("status"),
        "note": document.get("note"),
        "marked_by_user_id": document.get("marked_by_user_id"),
        "marked_by_label": build_user_label(document.get("marked_by_user_id"), full_name=document.get("marked_by_name"), email=document.get("marked_by_email")),
        "marked_at": document.get("marked_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=ATTENDANCE_RECORD_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="attendance_record", document=document, display_name=document.get("status"))
