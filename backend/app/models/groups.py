from typing import Any, Dict

from app.core.schema_versions import GROUP_SCHEMA_VERSION, normalize_schema_version


def group_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "section_id": document.get("section_id"),
        "name": document.get("name", ""),
        "code": document.get("code", ""),
        "description": document.get("description"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=GROUP_SCHEMA_VERSION,
        ),
    }
