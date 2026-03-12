from typing import Any, Dict

from app.core.schema_versions import ENROLLMENT_SCHEMA_VERSION, normalize_schema_version


def enrollment_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "class_id": document.get("class_id"),
        "student_id": document.get("student_id"),
        "student_roll_number": document.get("student_roll_number"),
        "assigned_by_user_id": document.get("assigned_by_user_id"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=ENROLLMENT_SCHEMA_VERSION,
        ),
    }
