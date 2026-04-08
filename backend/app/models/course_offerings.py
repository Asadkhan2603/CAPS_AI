from typing import Any, Dict

from app.core.schema_versions import COURSE_OFFERING_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity


def course_offering_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "subject_id": document.get("subject_id"),
        "teacher_user_id": document.get("teacher_user_id"),
        "batch_id": document.get("batch_id"),
        "semester_id": document.get("semester_id"),
        "section_id": document.get("section_id"),
        "group_id": document.get("group_id"),
        "academic_year": document.get("academic_year"),
        "offering_type": document.get("offering_type", "theory"),
        "subject_name": document.get("subject_name"),
        "subject_code": document.get("subject_code"),
        "teacher_name": document.get("teacher_name"),
        "batch_name": document.get("batch_name"),
        "section_name": document.get("section_name"),
        "group_name": document.get("group_name"),
        "semester_label": document.get("semester_label"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=COURSE_OFFERING_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="course_offering", document=document, display_name=document.get("subject_name"))
