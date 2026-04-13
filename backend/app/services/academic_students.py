from __future__ import annotations

from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import db
from app.core.mongo import parse_object_id


def _normalize_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_email(value: Any) -> str | None:
    text = _normalize_text(value)
    return text.lower() if text else None


def _student_candidate_rank(student: dict[str, Any], *, user_id: str | None, email: str | None) -> tuple[int, int, int, str]:
    created_at = student.get("created_at")
    created_at_score = int(created_at.timestamp()) if hasattr(created_at, "timestamp") else 0
    roll_number = _normalize_text(student.get("roll_number")) or ""
    auto_generated_roll = roll_number.startswith("USR-")
    return (
        1 if user_id and _normalize_text(student.get("user_id")) == user_id else 0,
        1 if _normalize_text(student.get("class_id")) else 0,
        created_at_score,
        "0" if not auto_generated_roll else "1",
    )


async def resolve_student_profile_for_user(current_user: dict[str, Any], *, database: Any = db) -> dict[str, Any] | None:
    user_id = _normalize_text(current_user.get("_id"))
    email = _normalize_email(current_user.get("email"))

    query_candidates: list[dict[str, Any]] = []
    if user_id:
        query_candidates.append({"user_id": user_id, "is_active": True})
    if email:
        query_candidates.append({"email": email, "is_active": True})

    candidates: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for query in query_candidates:
        rows = await database.students.find(query).sort("created_at", -1).to_list(length=50)
        for student in rows:
            student_id = _normalize_text(student.get("_id"))
            if not student_id or student_id in seen_ids:
                continue
            seen_ids.add(student_id)
            candidates.append(student)

    if not candidates:
        return None

    candidates.sort(key=lambda item: _student_candidate_rank(item, user_id=user_id, email=email), reverse=True)
    return candidates[0]


async def resolve_active_section_id_for_student(student: dict[str, Any], *, database: Any = db) -> str | None:
    student_id = str(student.get("_id") or "").strip()
    roll_number = _normalize_text(student.get("roll_number"))
    if not student_id and not roll_number:
        return _normalize_text(student.get("class_id"))

    enrollments = await database.enrollments.find(
        {"student_id": {"$in": [value for value in [student_id, roll_number] if value]}},
    ).sort("created_at", -1).to_list(length=100)

    for enrollment in enrollments:
        class_id = _normalize_text(enrollment.get("class_id"))
        if not class_id:
            continue
        try:
            section = await database.classes.find_one({"_id": parse_object_id(class_id), "is_active": True}, {"_id": 1})
        except HTTPException:
            section = None
        if section:
            return class_id

    raw_class_id = _normalize_text(student.get("class_id"))
    if raw_class_id and ObjectId.is_valid(raw_class_id):
        section = await database.classes.find_one({"_id": parse_object_id(raw_class_id), "is_active": True}, {"_id": 1})
        if section:
            return raw_class_id

    return raw_class_id


async def resolve_student_placement_snapshot(
    student: dict[str, Any],
    *,
    database: Any = db,
) -> dict[str, Any]:
    student_id = str(student.get("_id") or "").strip()
    roll_number = _normalize_text(student.get("roll_number"))

    enrollments = await database.enrollments.find(
        {"student_id": {"$in": [value for value in [student_id, roll_number] if value]}},
    ).sort("created_at", -1).to_list(length=100)

    for enrollment in enrollments:
        class_id = _normalize_text(enrollment.get("class_id"))
        if not class_id:
            continue
        try:
            section = await database.classes.find_one({"_id": parse_object_id(class_id), "is_active": True}, {"_id": 1})
        except HTTPException:
            section = None
        if section:
            return {
                "canonical_class_id": class_id,
                "canonical_group_id": _normalize_text(student.get("group_id")),
                "placement_source": "enrollment",
            }

    raw_class_id = _normalize_text(student.get("class_id"))
    if raw_class_id and ObjectId.is_valid(raw_class_id):
        section = await database.classes.find_one({"_id": parse_object_id(raw_class_id), "is_active": True}, {"_id": 1})
        if section:
            return {
                "canonical_class_id": raw_class_id,
                "canonical_group_id": _normalize_text(student.get("group_id")),
                "placement_source": "student_profile",
            }

    return {
        "canonical_class_id": raw_class_id,
        "canonical_group_id": _normalize_text(student.get("group_id")),
        "placement_source": "student_profile" if raw_class_id else None,
    }


async def resolve_student_academic_context_for_user(
    current_user: dict[str, Any],
    *,
    database: Any = db,
    raise_not_found: bool = False,
) -> dict[str, Any] | None:
    student = await resolve_student_profile_for_user(current_user, database=database)
    if not student:
        if raise_not_found:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
        return None

    placement = await resolve_student_placement_snapshot(student, database=database)
    return {
        **student,
        **placement,
    }


async def list_students_for_section(
    section_id: str,
    *,
    group_id: str | None = None,
    database: Any = db,
) -> list[dict[str, Any]]:
    section_id = str(section_id or "").strip()
    group_id = str(group_id or "").strip() or None
    if not section_id:
        return []

    enrollments = await database.enrollments.find({"class_id": section_id}).sort("created_at", -1).to_list(length=5000)
    canonical_student_ids: list[str] = []
    seen_student_ids: set[str] = set()
    for enrollment in enrollments:
        student_id = _normalize_text(enrollment.get("student_id"))
        if not student_id or student_id in seen_student_ids or not ObjectId.is_valid(student_id):
            continue
        seen_student_ids.add(student_id)
        canonical_student_ids.append(student_id)

    students: list[dict[str, Any]] = []
    if canonical_student_ids:
        students = await database.students.find(
            {"_id": {"$in": [ObjectId(value) for value in canonical_student_ids]}, "is_active": True}
        ).to_list(length=5000)
    else:
        students = await database.students.find({"class_id": section_id, "is_active": True}).to_list(length=5000)

    if group_id:
        students = [item for item in students if str(item.get("group_id") or "") == group_id]

    students.sort(key=lambda item: (str(item.get("full_name") or "").lower(), str(item.get("roll_number") or "")))
    return students
