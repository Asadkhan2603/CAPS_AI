from typing import Any, Dict

from app.core.schema_versions import FACULTY_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity


def faculty_public(document: Dict[str, Any]) -> Dict[str, Any]:
    faculty_name = document.get("faculty_name") or document.get("name", "")
    faculty_code = document.get("faculty_code") or document.get("code", "")
    payload = {
        "id": str(document["_id"]),
        "faculty_id": document.get("faculty_id") or faculty_code or str(document.get("_id")),
        "faculty_code": faculty_code,
        "faculty_name": faculty_name,
        "name": faculty_name,
        "code": faculty_code,
        "university_id": document.get("university_id"),
        "university_master_id": document.get("university_master_id"),
        "university_name": document.get("university_name"),
        "university_code": document.get("university_code") or document.get("university_master_id"),
        "is_active": document.get("is_active", True),
        "deleted_at": document.get("deleted_at"),
        "deleted_by": document.get("deleted_by"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=FACULTY_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="faculty", document=document, display_name=faculty_name)
