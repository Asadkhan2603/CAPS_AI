from typing import Any

from app.core.database import db as core_db
from app.core.mongo import parse_object_id


async def teacher_can_access_assignment(
    teacher_user_id: str,
    assignment_id: str,
    *,
    database: Any | None = None,
) -> bool:
    active_db = database or core_db
    assignment = await active_db.assignments.find_one({"_id": parse_object_id(assignment_id)})
    if not assignment:
        return False
    if assignment.get("created_by") == teacher_user_id:
        return True

    class_id = assignment.get("class_id")
    if not class_id:
        return False

    class_doc = await active_db.classes.find_one({"_id": parse_object_id(class_id)})
    if not class_doc:
        return False
    return class_doc.get("class_coordinator_user_id") == teacher_user_id
