from typing import Any

from app.services.access_control import teacher_can_access_assignment


async def class_coordinator_class_ids(
    user_id: str,
    *,
    database: Any,
) -> set[str]:
    classes = await database.classes.find({"class_coordinator_user_id": user_id}).to_list(length=1000)
    return {str(item.get("_id")) for item in classes if item.get("_id")}


async def can_view_similarity_log(
    current_user: dict[str, Any],
    item: dict[str, Any],
    *,
    database: Any,
) -> bool:
    if current_user.get("role") == "admin":
        return True
    if current_user.get("role") != "teacher":
        return False

    user_id = str(current_user["_id"])
    extensions = current_user.get("extended_roles", [])
    if "year_head" in extensions:
        return True

    if "class_coordinator" in extensions:
        coordinator_classes = await class_coordinator_class_ids(user_id, database=database)
        if item.get("source_class_id") in coordinator_classes or item.get("matched_class_id") in coordinator_classes:
            return True

    source_assignment_id = item.get("source_assignment_id")
    matched_assignment_id = item.get("matched_assignment_id")
    if source_assignment_id and await teacher_can_access_assignment(user_id, source_assignment_id, database=database):
        return True
    if matched_assignment_id and await teacher_can_access_assignment(user_id, matched_assignment_id, database=database):
        return True
    return False


async def filter_similarity_logs_for_user(
    current_user: dict[str, Any],
    items: list[dict[str, Any]],
    *,
    database: Any,
) -> list[dict[str, Any]]:
    if current_user.get("role") != "teacher":
        return items
    scoped: list[dict[str, Any]] = []
    for item in items:
        if await can_view_similarity_log(current_user, item, database=database):
            scoped.append(item)
    return scoped


async def teacher_can_run_similarity_for_assignment(
    teacher_user_id: str,
    assignment_id: str,
    *,
    database: Any,
) -> bool:
    return await teacher_can_access_assignment(
        teacher_user_id,
        assignment_id,
        database=database,
    )
