from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import CLASS_SCHEMA_VERSION, USER_SCHEMA_VERSION
from app.services.academic_students import resolve_student_academic_context_for_user
from app.services.section_read_models import sync_section_read_models_for_ids

CR_SEATS = {"cr_1", "cr_2"}


def build_class_representative_scope(section: dict[str, Any] | None, seat: str | None) -> dict[str, Any]:
    section = section or {}
    return {
        "faculty_id": section.get("faculty_id"),
        "department_id": section.get("department_id"),
        "program_id": section.get("program_id"),
        "specialization_id": section.get("specialization_id"),
        "batch_id": section.get("batch_id"),
        "semester_id": section.get("semester_id"),
        "class_id": str(section.get("_id")) if section.get("_id") is not None else None,
        "seat": seat,
    }


async def _find_student_user(user_id: str) -> dict[str, Any] | None:
    return await _find_student_user_in_database(user_id, database=db)


async def _find_student_user_in_database(user_id: str, *, database) -> dict[str, Any] | None:
    normalized = str(user_id or "").strip()
    if not normalized:
        return None
    return await database.users.find_one({"_id": parse_object_id(normalized), "role": "student"})


async def _student_academic_context(student_user: dict[str, Any], *, database) -> dict[str, Any]:
    context = await resolve_student_academic_context_for_user(student_user, database=database)
    if not context:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student profile not found")
    return context


async def validate_class_representative_assignment(
    *,
    section: dict[str, Any],
    student_user_id: str,
    seat: str,
    database=db,
) -> tuple[dict[str, Any], dict[str, Any]]:
    if seat not in CR_SEATS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid representative seat")

    student_user = await _find_student_user_in_database(student_user_id, database=database)
    if not student_user or student_user.get("is_active") is False:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="student_user_id must reference an active student user")

    student_context = await _student_academic_context(student_user, database=database)
    section_id = str(section.get("_id") or "")
    if str(student_context.get("canonical_class_id") or "") != section_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student is not assigned to the selected section")

    return student_user, student_context


async def _sync_student_class_representative_state(
    *,
    student_user_id: str,
    section: dict[str, Any] | None,
    seat: str | None,
    database=db,
) -> dict[str, Any] | None:
    student = await _find_student_user_in_database(student_user_id, database=database)
    if not student:
        return None

    extended_roles = [role for role in list(student.get("extended_roles") or []) if role != "class_representative"]
    role_scope = dict(student.get("role_scope") or {})
    role_scope.pop("class_representative", None)

    if section and seat:
        extended_roles.append("class_representative")
        role_scope["class_representative"] = build_class_representative_scope(section, seat)

    await database.users.update_one(
        {"_id": student["_id"]},
        {
            "$set": {
                "extended_roles": extended_roles,
                "role_scope": role_scope,
                "updated_at": datetime.now(timezone.utc),
                "schema_version": USER_SCHEMA_VERSION,
            }
        },
    )
    return await database.users.find_one({"_id": student["_id"]})


def normalize_class_representatives(section: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    source = (section or {}).get("class_representatives", {}) or {}
    return {
        "cr_1": {
            "user_id": (source.get("cr_1") or {}).get("user_id"),
            "full_name": (source.get("cr_1") or {}).get("full_name"),
        },
        "cr_2": {
            "user_id": (source.get("cr_2") or {}).get("user_id"),
            "full_name": (source.get("cr_2") or {}).get("full_name"),
        },
    }


async def assign_section_class_representative(
    *,
    section_id: str,
    seat: str,
    student_user_id: str,
    database=db,
) -> tuple[dict[str, Any], dict[str, Any] | None, str | None]:
    section = await database.classes.find_one({"_id": parse_object_id(section_id), "is_active": True})
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    student_user, _student_context = await validate_class_representative_assignment(
        section=section,
        student_user_id=student_user_id,
        seat=seat,
        database=database,
    )

    representatives = normalize_class_representatives(section)
    previous_seat_user_id = str(representatives.get(seat, {}).get("user_id") or "").strip() or None
    other_seat = "cr_2" if seat == "cr_1" else "cr_1"
    other_seat_user_id = str(representatives.get(other_seat, {}).get("user_id") or "").strip() or None
    if other_seat_user_id and other_seat_user_id == str(student_user.get("_id")):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Student already occupies the other CR seat for this section")

    previous_sections = await database.classes.find(
        {
            "_id": {"$ne": section["_id"]},
            "$or": [
                {"class_representatives.cr_1.user_id": str(student_user.get("_id"))},
                {"class_representatives.cr_2.user_id": str(student_user.get("_id"))},
            ],
        }
    ).to_list(length=200)
    affected_section_ids = {section_id}
    for previous_section in previous_sections:
        previous_section_id = str(previous_section.get("_id"))
        affected_section_ids.add(previous_section_id)
        previous_representatives = normalize_class_representatives(previous_section)
        for previous_seat in ("cr_1", "cr_2"):
            if str(previous_representatives.get(previous_seat, {}).get("user_id") or "") == str(student_user.get("_id")):
                previous_representatives[previous_seat] = {"user_id": None, "full_name": None}
        await database.classes.update_one(
            {"_id": previous_section["_id"]},
            {"$set": {"class_representatives": previous_representatives, "schema_version": CLASS_SCHEMA_VERSION}},
        )

    representatives[seat] = {"user_id": str(student_user.get("_id")), "full_name": student_user.get("full_name")}
    await database.classes.update_one(
        {"_id": section["_id"]},
        {"$set": {"class_representatives": representatives, "schema_version": CLASS_SCHEMA_VERSION}},
    )

    if previous_seat_user_id and previous_seat_user_id != str(student_user.get("_id")):
        await _sync_student_class_representative_state(
            student_user_id=previous_seat_user_id,
            section=None,
            seat=None,
            database=database,
        )

    updated_user = await _sync_student_class_representative_state(
        student_user_id=str(student_user.get("_id")),
        section=section,
        seat=seat,
        database=database,
    )
    await sync_section_read_models_for_ids(section_ids=sorted(affected_section_ids), database=database)
    updated_section = await database.classes.find_one({"_id": section["_id"]})
    return updated_section or section, updated_user, previous_seat_user_id


async def clear_section_class_representative(
    *,
    section_id: str,
    seat: str,
    database=db,
) -> tuple[dict[str, Any], str | None]:
    section = await database.classes.find_one({"_id": parse_object_id(section_id), "is_active": True})
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    if seat not in CR_SEATS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid representative seat")

    representatives = normalize_class_representatives(section)
    previous_user_id = str(representatives.get(seat, {}).get("user_id") or "").strip() or None
    representatives[seat] = {"user_id": None, "full_name": None}
    await database.classes.update_one(
        {"_id": section["_id"]},
        {"$set": {"class_representatives": representatives, "schema_version": CLASS_SCHEMA_VERSION}},
    )
    if previous_user_id:
        await _sync_student_class_representative_state(student_user_id=previous_user_id, section=None, seat=None, database=database)
    await sync_section_read_models_for_ids(section_ids=[section_id], database=database)
    updated_section = await database.classes.find_one({"_id": section["_id"]})
    return updated_section or section, previous_user_id


async def synchronize_student_class_representative_binding(
    *,
    student_user_id: str,
    scope: dict[str, Any] | None,
    clear_existing: bool,
    database=db,
) -> tuple[dict[str, Any], set[str]]:
    next_scope = dict(scope or {})
    affected_section_ids: set[str] = set()
    seat = str(next_scope.get("seat") or "").strip()
    class_id = str(next_scope.get("class_id") or "").strip()

    previous_sections = await database.classes.find(
        {
            "$or": [
                {"class_representatives.cr_1.user_id": student_user_id},
                {"class_representatives.cr_2.user_id": student_user_id},
            ]
        }
    ).to_list(length=100)
    if clear_existing:
        for previous_section in previous_sections:
            previous_section_id = str(previous_section.get("_id"))
            affected_section_ids.add(previous_section_id)
            previous_representatives = normalize_class_representatives(previous_section)
            changed = False
            for previous_seat in ("cr_1", "cr_2"):
                if str(previous_representatives.get(previous_seat, {}).get("user_id") or "") == student_user_id:
                    previous_representatives[previous_seat] = {"user_id": None, "full_name": None}
                    changed = True
            if changed:
                await database.classes.update_one(
                    {"_id": previous_section["_id"]},
                    {"$set": {"class_representatives": previous_representatives, "schema_version": CLASS_SCHEMA_VERSION}},
                )

    if class_id and seat:
        updated_section, _updated_user, _previous_user_id = await assign_section_class_representative(
            section_id=class_id,
            seat=seat,
            student_user_id=student_user_id,
            database=database,
        )
        affected_section_ids.add(str(updated_section.get("_id")))
        next_scope = build_class_representative_scope(updated_section, seat)
    else:
        next_scope = {}

    return next_scope, affected_section_ids
