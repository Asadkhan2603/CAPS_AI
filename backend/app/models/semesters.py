from typing import Any, Dict

from app.core.schema_versions import SEMESTER_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity


def semester_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "batch_id": document.get("batch_id"),
        "batch_name": document.get("batch_name"),
        "batch_code": document.get("batch_code"),
        "faculty_id": document.get("faculty_id"),
        "department_id": document.get("department_id"),
        "program_id": document.get("program_id"),
        "program_name": document.get("program_name"),
        "program_code": document.get("program_code"),
        "specialization_id": document.get("specialization_id"),
        "specialization_name": document.get("specialization_name"),
        "specialization_code": document.get("specialization_code"),
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
    return apply_public_identity(payload, kind="semester", document=document, display_name=document.get("label"))
