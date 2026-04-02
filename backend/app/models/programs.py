from typing import Any, Dict

from app.core.schema_versions import PROGRAM_SCHEMA_VERSION, normalize_schema_version
from app.services.academic_hierarchy import normalize_program_duration_record
from app.services.public_ids import apply_public_identity


def program_public(document: Dict[str, Any]) -> Dict[str, Any]:
    duration_years, total_semesters = normalize_program_duration_record(document)
    program_name = document.get("program_name") or document.get("name", "")
    program_code = document.get("program_code") or document.get("code", "")
    payload = {
        "id": str(document["_id"]),
        "program_id": document.get("program_id") or program_code or str(document.get("_id")),
        "program_code": program_code,
        "program_name": program_name,
        "name": program_name,
        "code": program_code,
        "department_id": document.get("department_id"),
        "department_master_id": document.get("department_master_id"),
        "department_name": document.get("department_name"),
        "department_code": document.get("department_code"),
        "faculty_master_id": document.get("faculty_master_id"),
        "faculty_code": document.get("faculty_code"),
        "duration_years": duration_years,
        "total_semesters": total_semesters,
        "degree_type": document.get("degree_type"),
        "description": document.get("description"),
        "is_active": document.get("is_active", True),
        "deleted_at": document.get("deleted_at"),
        "deleted_by": document.get("deleted_by"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=PROGRAM_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="program", document=document, display_name=program_name)
