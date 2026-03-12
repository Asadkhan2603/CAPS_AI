from datetime import datetime, timezone
import re
from typing import Any
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import CLASS_SLOT_SCHEMA_VERSION
from app.core.security import require_roles
from app.models.class_slots import class_slot_public
from app.schemas.class_slot import ClassSlotCreate, ClassSlotOut, ClassSlotUpdate

router = APIRouter()


async def _distinct_strings(collection: Any, field: str, query: dict[str, Any], *, fallback_length: int) -> list[str]:
    distinct = getattr(collection, "distinct", None)
    if callable(distinct):
        try:
            return sorted({str(value) for value in await distinct(field, query) if value is not None})
        except Exception:
            pass
    rows = await collection.find(query, {field: 1}).to_list(length=fallback_length)
    return sorted({str(item.get(field)) for item in rows if item.get(field) is not None})


def _time_to_minutes(value: str) -> int:
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def _overlaps(a_start: str, a_end: str, b_start: str, b_end: str) -> bool:
    s1, e1, s2, e2 = _time_to_minutes(a_start), _time_to_minutes(a_end), _time_to_minutes(b_start), _time_to_minutes(b_end)
    return max(s1, s2) < min(e1, e2)


async def _get_offering_or_400(offering_id: str) -> dict:
    offering = await db.course_offerings.find_one({"_id": parse_object_id(offering_id), "is_active": True})
    if not offering:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course offering not found")
    return offering


async def _ensure_offering_write_access(*, current_user: dict, offering: dict) -> None:
    if current_user.get("role") == "admin":
        return
    section = await db.classes.find_one({"_id": parse_object_id(offering["section_id"]), "is_active": True})
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    if section.get("class_coordinator_user_id") != str(current_user.get("_id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only class coordinator can manage class slots")


async def _validate_slot_conflicts(
    *,
    slot_id: str | None,
    offering: dict,
    day: str,
    start_time: str,
    end_time: str,
    room_code: str,
) -> None:
    if _time_to_minutes(start_time) >= _time_to_minutes(end_time):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="start_time must be before end_time")

    teacher_user_id = offering.get("teacher_user_id")
    teacher_offering_ids = (
        await _distinct_strings(
            db.course_offerings,
            "_id",
            {"teacher_user_id": teacher_user_id, "is_active": True},
            fallback_length=5000,
        )
        if teacher_user_id
        else []
    )

    or_filters: list[dict[str, Any]] = [
        {"room_code": {"$regex": f"^{re.escape(room_code.strip())}$", "$options": "i"}}
    ]
    if teacher_offering_ids:
        or_filters.append({"course_offering_id": {"$in": teacher_offering_ids}})
    rows = await db.class_slots.find(
        {"day": day, "is_active": True, "$or": or_filters},
        {"course_offering_id": 1, "room_code": 1, "start_time": 1, "end_time": 1},
    ).to_list(length=5000)

    for row in rows:
        if slot_id and str(row.get("_id")) == slot_id:
            continue
        if not _overlaps(start_time, end_time, row.get("start_time"), row.get("end_time")):
            continue

        if row.get("course_offering_id") in teacher_offering_ids:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Teacher conflict on selected day/time")
        if (row.get("room_code") or "").strip().lower() == room_code.strip().lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room conflict on selected day/time")


@router.get("/", response_model=List[ClassSlotOut])
async def list_class_slots(
    course_offering_id: str | None = Query(default=None),
    day: str | None = Query(default=None),
    section_id: str | None = Query(default=None),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[ClassSlotOut]:
    query = {}
    if course_offering_id:
        query["course_offering_id"] = course_offering_id
    if day:
        query["day"] = day
    if is_active is not None:
        query["is_active"] = is_active

    if section_id:
        offering_ids = await _distinct_strings(
            db.course_offerings,
            "_id",
            {"section_id": section_id, "is_active": True},
            fallback_length=5000,
        )
        if not offering_ids:
            return []
        query["course_offering_id"] = {"$in": offering_ids}

    if current_user.get("role") == "student":
        student = await db.students.find_one({"email": current_user.get("email"), "is_active": True})
        if not student or not student.get("class_id"):
            return []
        ids = await _distinct_strings(
            db.course_offerings,
            "_id",
            {
                "section_id": student["class_id"],
                "is_active": True,
                "$or": [{"group_id": None}, {"group_id": student.get("group_id")}],
            },
            fallback_length=5000,
        )
        if not ids:
            return []
        query["course_offering_id"] = {"$in": ids}

    rows = await db.class_slots.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [ClassSlotOut(**class_slot_public(item)) for item in rows]


@router.get("/my", response_model=List[ClassSlotOut])
async def my_slots(
    current_user=Depends(require_roles(["student"])),
) -> List[ClassSlotOut]:
    student = await db.students.find_one({"email": current_user.get("email"), "is_active": True})
    if not student or not student.get("class_id"):
        return []
    ids = await _distinct_strings(
        db.course_offerings,
        "_id",
        {
            "section_id": student["class_id"],
            "is_active": True,
            "$or": [{"group_id": None}, {"group_id": student.get("group_id")}],
        },
        fallback_length=5000,
    )
    if not ids:
        return []
    rows = await db.class_slots.find({"course_offering_id": {"$in": ids}, "is_active": True}).to_list(length=5000)
    return [ClassSlotOut(**class_slot_public(item)) for item in rows]


@router.post("/", response_model=ClassSlotOut, status_code=status.HTTP_201_CREATED)
async def create_class_slot(
    payload: ClassSlotCreate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> ClassSlotOut:
    offering = await _get_offering_or_400(payload.course_offering_id)
    await _ensure_offering_write_access(current_user=current_user, offering=offering)
    await _validate_slot_conflicts(
        slot_id=None,
        offering=offering,
        day=payload.day,
        start_time=payload.start_time,
        end_time=payload.end_time,
        room_code=payload.room_code,
    )
    document = {
        "course_offering_id": payload.course_offering_id,
        "day": payload.day,
        "start_time": payload.start_time,
        "end_time": payload.end_time,
        "room_code": payload.room_code.strip(),
        "is_active": True,
        "created_by_user_id": str(current_user.get("_id")),
        "created_at": datetime.now(timezone.utc),
        "schema_version": CLASS_SLOT_SCHEMA_VERSION,
    }
    result = await db.class_slots.insert_one(document)
    created = await db.class_slots.find_one({"_id": result.inserted_id})
    return ClassSlotOut(**class_slot_public(created))


@router.put("/{slot_id}", response_model=ClassSlotOut)
async def update_class_slot(
    slot_id: str,
    payload: ClassSlotUpdate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> ClassSlotOut:
    slot_obj_id = parse_object_id(slot_id)
    current = await db.class_slots.find_one({"_id": slot_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class slot not found")
    offering = await _get_offering_or_400(current["course_offering_id"])
    await _ensure_offering_write_access(current_user=current_user, offering=offering)
    update_data = payload.model_dump(exclude_none=True)
    target_day = update_data.get("day", current.get("day"))
    target_start = update_data.get("start_time", current.get("start_time"))
    target_end = update_data.get("end_time", current.get("end_time"))
    target_room = update_data.get("room_code", current.get("room_code"))
    await _validate_slot_conflicts(
        slot_id=slot_id,
        offering=offering,
        day=target_day,
        start_time=target_start,
        end_time=target_end,
        room_code=target_room,
    )
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    await db.class_slots.update_one(
        {"_id": slot_obj_id},
        {"$set": {**update_data, "schema_version": CLASS_SLOT_SCHEMA_VERSION}},
    )
    updated = await db.class_slots.find_one({"_id": slot_obj_id})
    return ClassSlotOut(**class_slot_public(updated))


@router.delete("/{slot_id}")
async def delete_class_slot(
    slot_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> dict:
    slot_obj_id = parse_object_id(slot_id)
    current = await db.class_slots.find_one({"_id": slot_obj_id, "is_active": True})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class slot not found")
    offering = await _get_offering_or_400(current["course_offering_id"])
    await _ensure_offering_write_access(current_user=current_user, offering=offering)
    await db.class_slots.update_one(
        {"_id": slot_obj_id},
        {
            "$set": {
                "is_active": False,
                "deleted_at": datetime.now(timezone.utc),
                "schema_version": CLASS_SLOT_SCHEMA_VERSION,
            }
        },
    )
    return {"message": "Class slot archived"}
