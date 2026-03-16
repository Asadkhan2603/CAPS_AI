from typing import Any, Dict

from app.core.schema_versions import UNIVERSITY_SCHEMA_VERSION, normalize_schema_version


def university_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "university_id": document.get("university_id", ""),
        "university_name": document.get("university_name", ""),
        "is_active": document.get("is_active", True),
        "deleted_at": document.get("deleted_at"),
        "deleted_by": document.get("deleted_by"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=UNIVERSITY_SCHEMA_VERSION,
        ),
    }
