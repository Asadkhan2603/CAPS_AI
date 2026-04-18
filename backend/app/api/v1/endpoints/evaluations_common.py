from typing import Any

from bson import ObjectId

from app.core.database import db as core_db
from app.services.public_ids import build_display_label, build_public_id, build_user_label


def get_evaluations_db() -> Any:
    from app.api.v1.endpoints import evaluations as evaluations_endpoint_module

    return getattr(evaluations_endpoint_module, "db", core_db)


def _normalize_object_id_value(value: Any) -> str | None:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, str) and ObjectId.is_valid(value):
        return value
    return None


async def attach_evaluation_labels(items: list[dict], *, database: Any) -> list[dict]:
    if not items:
        return items

    submission_ids = {
        value
        for item in items
        for value in (_normalize_object_id_value(item.get("submission_id")),)
        if value
    }
    user_ids = {
        value
        for item in items
        for value in (
            _normalize_object_id_value(item.get("student_user_id")),
            _normalize_object_id_value(item.get("teacher_user_id")),
        )
        if value
    }

    submissions_by_id: dict[str, dict] = {}
    if submission_ids:
        submission_rows = await database.submissions.find(
            {"_id": {"$in": [ObjectId(value) for value in submission_ids]}},
            {"_id": 1, "public_id": 1, "original_filename": 1},
        ).to_list(length=len(submission_ids))
        submissions_by_id = {
            str(item.get("_id")): item
            for item in submission_rows
            if item.get("_id")
        }

    users_by_id: dict[str, dict] = {}
    if user_ids:
        user_rows = await database.users.find(
            {"_id": {"$in": [ObjectId(value) for value in user_ids]}},
            {"_id": 1, "full_name": 1, "email": 1},
        ).to_list(length=len(user_ids))
        users_by_id = {
            str(item.get("_id")): item
            for item in user_rows
            if item.get("_id")
        }

    enriched: list[dict] = []
    for item in items:
        submission_id = item.get("submission_id")
        student_user_id = item.get("student_user_id")
        teacher_user_id = item.get("teacher_user_id")
        submission_doc = submissions_by_id.get(_normalize_object_id_value(submission_id))
        student_doc = users_by_id.get(_normalize_object_id_value(student_user_id))
        teacher_doc = users_by_id.get(_normalize_object_id_value(teacher_user_id))

        submission_public_id = (
            submission_doc.get("public_id") if isinstance(submission_doc, dict) else None
        ) or build_public_id("submission", submission_doc or {"_id": submission_id})
        submission_label = build_display_label(
            "submission",
            submission_doc or {"_id": submission_id},
            public_id=submission_public_id,
            display_name=(submission_doc or {}).get("original_filename"),
        ) if submission_doc or submission_id else None

        enriched.append(
            {
                **item,
                "submission_label": submission_label or submission_public_id or str(submission_id) if submission_id is not None else None,
                "student_label": build_user_label(
                    student_user_id,
                    full_name=(student_doc or {}).get("full_name"),
                    email=(student_doc or {}).get("email"),
                ),
                "teacher_label": build_user_label(
                    teacher_user_id,
                    full_name=(teacher_doc or {}).get("full_name"),
                    email=(teacher_doc or {}).get("email"),
                ),
            }
        )
    return enriched
