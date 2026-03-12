from datetime import datetime, timezone
from typing import Any, Optional

from app.core.database import db as core_db
from app.core.mongo import parse_object_id
from app.services.access_control import teacher_can_access_assignment


def get_ai_db() -> Any:
    from app.api.v1.endpoints import ai as ai_endpoint_module

    return getattr(ai_endpoint_module, "db", core_db)


async def teacher_can_access_assignment_in_scope(teacher_user_id: str, assignment_id: str) -> bool:
    return await teacher_can_access_assignment(
        teacher_user_id,
        assignment_id,
        database=get_ai_db(),
    )


def and_query(*parts: dict[str, Any]) -> dict[str, Any]:
    filtered = [part for part in parts if part]
    if not filtered:
        return {}
    if len(filtered) == 1:
        return filtered[0]
    return {"$and": filtered}


async def distinct_strings(collection: Any, field: str, query: dict[str, Any]) -> list[str]:
    distinct = getattr(collection, "distinct", None)
    if callable(distinct):
        try:
            values = await distinct(field, query)
            return sorted({str(value) for value in values if value is not None})
        except Exception:
            pass

    rows = await collection.find(query, {field: 1}).to_list(length=5000)
    return sorted({str(row.get(field)) for row in rows if row.get(field) is not None})


async def teacher_assignment_scope_ids(teacher_user_id: str) -> list[str]:
    active_db = get_ai_db()
    created_assignment_ids = await distinct_strings(
        active_db.assignments,
        "_id",
        {"created_by": teacher_user_id, "is_deleted": {"$in": [False, None]}},
    )
    coordinated_class_ids = await distinct_strings(
        active_db.classes,
        "_id",
        {"class_coordinator_user_id": teacher_user_id},
    )

    coordinated_assignment_ids: list[str] = []
    if coordinated_class_ids:
        coordinated_assignment_ids = await distinct_strings(
            active_db.assignments,
            "_id",
            {"class_id": {"$in": coordinated_class_ids}, "is_deleted": {"$in": [False, None]}},
        )

    return sorted(set(created_assignment_ids + coordinated_assignment_ids))


def provider_mode_payload(runtime_settings: dict[str, Any]) -> dict[str, Any]:
    openai_configured = bool(runtime_settings.get("openai_configured"))
    effective_provider_enabled = bool(runtime_settings.get("effective_provider_enabled"))
    return {
        "openai_configured": openai_configured,
        "provider_enabled": bool(runtime_settings.get("provider_enabled")),
        "mode": "openai+fallback" if effective_provider_enabled else "fallback-only",
        "model": runtime_settings.get("openai_model") if openai_configured else None,
        "timeout_seconds": runtime_settings.get("openai_timeout_seconds"),
        "max_output_tokens": runtime_settings.get("openai_max_output_tokens"),
        "similarity_threshold": runtime_settings.get("similarity_threshold"),
    }


def serialize_dt(value: Any) -> str | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo:
        return value.isoformat()
    return value.replace(tzinfo=timezone.utc).isoformat()


async def resolve_submission(student_id: str, exam_id: str, submission_id: Optional[str]) -> Optional[dict]:
    active_db = get_ai_db()
    if submission_id:
        submission = await active_db.submissions.find_one({"_id": parse_object_id(submission_id)})
        return submission
    return await active_db.submissions.find_one({"student_user_id": student_id, "assignment_id": exam_id})
