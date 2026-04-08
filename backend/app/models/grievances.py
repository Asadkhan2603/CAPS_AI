from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.schema_versions import GRIEVANCE_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity, build_user_label


def _normalize_datetime(value: Any) -> Any:
    if isinstance(value, datetime) and value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _timeline_entry_public(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "entry_id": str(entry.get("entry_id") or ""),
        "kind": entry.get("kind", "public_comment"),
        "visibility": entry.get("visibility", "public"),
        "message": entry.get("message", ""),
        "stage": entry.get("stage"),
        "actor_user_id": entry.get("actor_user_id"),
        "actor_label": build_user_label(
            entry.get("actor_user_id"),
            full_name=entry.get("actor_name"),
            email=entry.get("actor_email"),
        ),
        "forwarded_to_user_id": entry.get("forwarded_to_user_id"),
        "forwarded_to_label": build_user_label(
            entry.get("forwarded_to_user_id"),
            full_name=entry.get("forwarded_to_name"),
            email=entry.get("forwarded_to_email"),
        ),
        "created_at": entry.get("created_at"),
        "metadata": entry.get("metadata"),
    }


def grievance_public(document: dict[str, Any], *, include_internal: bool = False) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    stage_due_at = _normalize_datetime(document.get("stage_due_at"))
    resolved_at = _normalize_datetime(document.get("resolved_at"))
    forwarded_at = _normalize_datetime(document.get("forwarded_at"))
    created_at = _normalize_datetime(document.get("created_at"))
    raw_timeline = list(document.get("timeline") or [])
    filtered_timeline = []
    for entry in raw_timeline:
        if not include_internal and entry.get("visibility") == "internal":
            continue
        filtered_timeline.append(_timeline_entry_public(entry))

    payload = {
        "id": str(document["_id"]),
        "category": document.get("category", "general"),
        "title": document.get("title", ""),
        "description": document.get("description", ""),
        "student_user_id": document.get("student_user_id", ""),
        "student_id": document.get("student_id"),
        "student_label": build_user_label(
            document.get("student_user_id"),
            full_name=document.get("student_name"),
            email=document.get("student_email"),
        ),
        "section_id": document.get("section_id"),
        "section_name": document.get("section_name"),
        "department_id": document.get("department_id"),
        "department_name": document.get("department_name"),
        "current_stage": document.get("current_stage", "coordinator"),
        "status": document.get("status", "open"),
        "stage_due_at": stage_due_at,
        "resolved_at": resolved_at,
        "resolved_by_user_id": document.get("resolved_by_user_id"),
        "resolved_by_label": build_user_label(
            document.get("resolved_by_user_id"),
            full_name=document.get("resolved_by_name"),
            email=document.get("resolved_by_email"),
        ),
        "assigned_resolver_user_id": document.get("assigned_resolver_user_id"),
        "assigned_resolver_label": build_user_label(
            document.get("assigned_resolver_user_id"),
            full_name=document.get("assigned_resolver_name"),
            email=document.get("assigned_resolver_email"),
        ),
        "forwarded_by_user_id": document.get("forwarded_by_user_id"),
        "forwarded_by_label": build_user_label(
            document.get("forwarded_by_user_id"),
            full_name=document.get("forwarded_by_name"),
            email=document.get("forwarded_by_email"),
        ),
        "forwarded_at": forwarded_at,
        "attachment_filename": document.get("attachment_original_filename"),
        "attachment_mime_type": document.get("attachment_mime_type"),
        "attachment_size_bytes": document.get("attachment_size_bytes"),
        "attachment_url": (
            f"/api/v1/grievances/{document['_id']}/attachment"
            if document.get("attachment_stored_filename")
            else None
        ),
        "is_overdue": bool(
            stage_due_at
            and document.get("status") in {"open", "in_progress", "reopened"}
            and stage_due_at <= now
        ),
        "created_at": created_at,
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=GRIEVANCE_SCHEMA_VERSION,
        ),
        "timeline": filtered_timeline,
    }
    return apply_public_identity(payload, kind="grievance", document=document, display_name=document.get("title"))
