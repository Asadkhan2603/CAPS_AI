from typing import Any, Dict

from app.core.schema_versions import ASSIGNMENT_SCHEMA_VERSION, normalize_schema_version


def assignment_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "title": document.get("title", ""),
        "description": document.get("description"),
        "subject_id": document.get("subject_id"),
        "class_id": document.get("class_id"),
        "due_date": document.get("due_date"),
        "total_marks": document.get("total_marks", 100.0),
        "status": document.get("status", "open"),
        "plagiarism_enabled": document.get("plagiarism_enabled", True),
        "created_by": document.get("created_by"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=ASSIGNMENT_SCHEMA_VERSION,
        ),
    }
