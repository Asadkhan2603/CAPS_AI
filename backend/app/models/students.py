from typing import Any, Dict

from app.core.schema_versions import STUDENT_SCHEMA_VERSION, normalize_schema_version


def student_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "full_name": document.get("full_name", ""),
        "roll_number": document.get("roll_number", ""),
        "email": document.get("email"),
        "class_id": document.get("class_id"),
        "group_id": document.get("group_id"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=STUDENT_SCHEMA_VERSION,
        ),
    }
