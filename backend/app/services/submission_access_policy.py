from typing import Any

from app.services.access_control import teacher_can_access_assignment


async def _distinct_strings(
    collection: Any,
    field: str,
    query: dict[str, Any],
    *,
    fallback_length: int,
) -> list[str]:
    distinct = getattr(collection, "distinct", None)
    if callable(distinct):
        try:
            return sorted({str(value) for value in await distinct(field, query) if value is not None})
        except Exception:
            pass
    rows = await collection.find(query, {field: 1}).to_list(length=fallback_length)
    return sorted({str(row.get(field)) for row in rows if row.get(field) is not None})


async def teacher_accessible_assignment_ids(
    teacher_user_id: str,
    *,
    database: Any,
) -> set[str]:
    created_ids = set(
        await _distinct_strings(
            database.assignments,
            "_id",
            {"created_by": teacher_user_id},
            fallback_length=5000,
        )
    )

    class_ids = await _distinct_strings(
        database.classes,
        "_id",
        {"class_coordinator_user_id": teacher_user_id, "is_active": True},
        fallback_length=5000,
    )
    if not class_ids:
        return created_ids

    class_assignment_ids = set(
        await _distinct_strings(
            database.assignments,
            "_id",
            {"class_id": {"$in": class_ids}},
            fallback_length=10000,
        )
    )
    return created_ids.union(class_assignment_ids)


async def teacher_can_access_submission(
    teacher_user_id: str,
    submission: dict[str, Any],
    *,
    database: Any,
) -> bool:
    assignment_id = submission.get("assignment_id")
    if not assignment_id:
        return False
    return await teacher_can_access_assignment(
        teacher_user_id,
        assignment_id,
        database=database,
    )
