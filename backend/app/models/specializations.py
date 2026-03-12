from typing import Any, Dict

from app.core.schema_versions import SPECIALIZATION_SCHEMA_VERSION, normalize_schema_version


def specialization_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "name": document.get("name", ""),
        "code": document.get("code", ""),
        "program_id": document.get("program_id"),
        "description": document.get("description"),
        "is_active": document.get("is_active", True),
        "deleted_at": document.get("deleted_at"),
        "deleted_by": document.get("deleted_by"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=SPECIALIZATION_SCHEMA_VERSION,
        ),
    }
