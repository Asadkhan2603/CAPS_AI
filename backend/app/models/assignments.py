from typing import Any, Dict

from app.core.schema_versions import ASSIGNMENT_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity


def _normalize_assignment_status(value: Any) -> str:
    status = str(value or "open").strip().lower()
    if status in {"closed", "archived"}:
        return "closed"
    return "open"


def assignment_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "title": document.get("title", ""),
        "description": document.get("description"),
        "subject_id": document.get("subject_id"),
        "class_id": document.get("class_id"),
        "due_date": document.get("due_date"),
        "total_marks": document.get("total_marks", 100.0),
        "status": _normalize_assignment_status(document.get("status")),
        "plagiarism_enabled": document.get("plagiarism_enabled", True),
        "created_by": document.get("created_by"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=ASSIGNMENT_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="assignment", document=document, display_name=document.get("title"))
