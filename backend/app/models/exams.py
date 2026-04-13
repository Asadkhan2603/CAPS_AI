from typing import Any, Dict

from app.core.schema_versions import EXAM_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity


def exam_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "title": document.get("title", ""),
        "code": document.get("code"),
        "description": document.get("description"),
        "subject_id": document.get("subject_id"),
        "batch_id": document.get("batch_id"),
        "semester_id": document.get("semester_id"),
        "section_id": document.get("section_id"),
        "assignment_id": document.get("assignment_id"),
        "teacher_user_id": document.get("teacher_user_id"),
        "exam_type": document.get("exam_type", "internal"),
        "scheduled_for": document.get("scheduled_for"),
        "duration_minutes": int(document.get("duration_minutes") or 60),
        "room_code": document.get("room_code"),
        "max_marks": float(document.get("max_marks") or 100),
        "status": document.get("status", "draft"),
        "created_by": document.get("created_by"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=EXAM_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="exam", document=document, display_name=document.get("title"))
