from typing import Any, Dict

from app.core.schema_versions import SEMESTER_SCHEMA_VERSION, normalize_schema_version


def semester_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "batch_id": document.get("batch_id"),
        "faculty_id": document.get("faculty_id"),
        "department_id": document.get("department_id"),
        "program_id": document.get("program_id"),
        "specialization_id": document.get("specialization_id"),
        "semester_number": document.get("semester_number"),
        "label": document.get("label", ""),
        "academic_year_start": document.get("academic_year_start"),
        "academic_year_end": document.get("academic_year_end"),
        "academic_year_label": document.get("academic_year_label"),
        "university_name": document.get("university_name"),
        "university_code": document.get("university_code"),
        "is_active": document.get("is_active", True),
        "deleted_at": document.get("deleted_at"),
        "deleted_by": document.get("deleted_by"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=SEMESTER_SCHEMA_VERSION,
        ),
    }
