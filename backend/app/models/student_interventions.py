from typing import Any


def student_intervention_public(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document.get("_id")),
        "student_id": document.get("student_id"),
        "student_name": document.get("student_name"),
        "section_id": document.get("section_id"),
        "section_name": document.get("section_name"),
        "risk_level": document.get("risk_level"),
        "status": document.get("status", "open"),
        "note": document.get("note"),
        "due_date": document.get("due_date"),
        "created_by_user_id": document.get("created_by_user_id"),
        "created_by_name": document.get("created_by_name"),
        "owner_user_id": document.get("owner_user_id"),
        "owner_name": document.get("owner_name"),
        "resolution_note": document.get("resolution_note"),
        "resolved_at": document.get("resolved_at"),
        "resolved_by_user_id": document.get("resolved_by_user_id"),
        "resolved_by_name": document.get("resolved_by_name"),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "reason_summary": document.get("reason_summary", []) or [],
        "schema_version": int(document.get("schema_version") or 1),
    }
