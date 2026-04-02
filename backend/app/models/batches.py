from typing import Any, Dict

from app.core.schema_versions import BATCH_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity


def batch_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "faculty_id": document.get("faculty_id"),
        "department_id": document.get("department_id"),
        "program_id": document.get("program_id"),
        "program_name": document.get("program_name"),
        "program_code": document.get("program_code"),
        "program_duration_years": document.get("program_duration_years"),
        "specialization_id": document.get("specialization_id"),
        "specialization_name": document.get("specialization_name"),
        "specialization_code": document.get("specialization_code"),
        "name": document.get("name", ""),
        "code": document.get("code", ""),
        "start_year": document.get("start_year"),
        "end_year": document.get("end_year"),
        "academic_span_label": document.get("academic_span_label"),
        "university_name": document.get("university_name"),
        "university_code": document.get("university_code"),
        "auto_generated": document.get("auto_generated", False),
        "is_active": document.get("is_active", True),
        "deleted_at": document.get("deleted_at"),
        "deleted_by": document.get("deleted_by"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=BATCH_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="batch", document=document, display_name=document.get("name"))
