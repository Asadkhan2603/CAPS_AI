from typing import Any, Dict

from app.core.schema_versions import SPECIALIZATION_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity


def specialization_public(document: Dict[str, Any]) -> Dict[str, Any]:
    specialization_name = document.get("specialization_name") or document.get("name", "")
    specialization_code = document.get("specialization_code") or document.get("code", "")
    payload = {
        "id": str(document["_id"]),
        "specialization_id": document.get("specialization_id") or specialization_code or str(document.get("_id")),
        "specialization_code": specialization_code,
        "specialization_name": specialization_name,
        "name": specialization_name,
        "code": specialization_code,
        "program_id": document.get("program_id"),
        "program_master_id": document.get("program_master_id"),
        "program_name": document.get("program_name"),
        "program_code": document.get("program_code"),
        "department_master_id": document.get("department_master_id"),
        "department_code": document.get("department_code"),
        "faculty_master_id": document.get("faculty_master_id"),
        "faculty_code": document.get("faculty_code"),
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
    return apply_public_identity(payload, kind="specialization", document=document, display_name=specialization_name)
