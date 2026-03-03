from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from bson import ObjectId

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import get_current_user, require_roles
from app.schemas.timetable import (
    DayName,
    ShiftId,
    TimetableCreate,
    TimetableGenerateRequest,
    TimetableLockRequest,
    TimetableOut,
    TimetablePublishResponse,
    TimetableSlotOut,
    TimetableUpdate,
)

router = APIRouter()

SHIFT_CONFIG: dict[str, dict[str, str]] = {
    "shift_1": {
        "label": "Shift 1 (Morning)",
        "start_time": "08:30",
        "end_time": "14:20",
        "lunch_start": "12:00",
        "lunch_end": "12:50",
    },
    "shift_2": {
        "label": "Shift 2 (Mid)",
        "start_time": "11:20",
        "end_time": "16:50",
        "lunch_start": "12:50",
        "lunch_end": "13:40",
    },
}
DEFAULT_DAYS: list[DayName] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
MIN_SLOT_MINUTES = 35
DEFAULT_PERIOD_MINUTES = 50


def _to_minutes(hhmm: str) -> int:
    hour_str, minute_str = hhmm.split(":")
    return int(hour_str) * 60 + int(minute_str)


def _fmt_minutes(total_minutes: int) -> str:
    hour = max(0, total_minutes // 60)
    minute = max(0, total_minutes % 60)
    return f"{hour:02d}:{minute:02d}"


def _build_slots(shift_id: ShiftId) -> list[dict[str, Any]]:
    config = SHIFT_CONFIG[shift_id]
    day_start = _to_minutes(config["start_time"])
    day_end = _to_minutes(config["end_time"])
    lunch_start = _to_minutes(config["lunch_start"])
    lunch_end = _to_minutes(config["lunch_end"])

    slots: list[dict[str, Any]] = []
    pointer = day_start
    period_idx = 1
    while pointer < day_end:
        if pointer == lunch_start:
            slots.append(
                {
                    "slot_key": "lunch",
                    "start_time": _fmt_minutes(lunch_start),
                    "end_time": _fmt_minutes(lunch_end),
                    "is_lunch": True,
                    "is_editable": False,
                    "label": "Lunch Break",
                }
            )
            pointer = lunch_end
            continue

        cap = lunch_start if pointer < lunch_start else day_end
        end_pointer = min(pointer + DEFAULT_PERIOD_MINUTES, cap)
        if end_pointer - pointer < MIN_SLOT_MINUTES:
            break
        slots.append(
            {
                "slot_key": f"p{period_idx}",
                "start_time": _fmt_minutes(pointer),
                "end_time": _fmt_minutes(end_pointer),
                "is_lunch": False,
                "is_editable": True,
                "label": f"Period {period_idx}",
            }
        )
        period_idx += 1
        pointer = end_pointer
    return slots


async def _ensure_class_scope_access(*, current_user: dict, class_id: str, write_mode: bool = False) -> dict:
    class_doc = await db.classes.find_one({"_id": parse_object_id(class_id), "is_active": True})
    if not class_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class not found")

    if current_user.get("role") == "admin":
        return class_doc
    if current_user.get("role") != "teacher":
        if write_mode:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only coordinator can manage timetable")
        return class_doc

    is_class_coordinator = "class_coordinator" in (current_user.get("extended_roles") or [])
    owns_class = class_doc.get("class_coordinator_user_id") == str(current_user.get("_id"))
    scoped_class_id = (
        (current_user.get("role_scope") or {})
        .get("class_coordinator", {})
        .get("class_id")
    )
    in_scoped_section = not scoped_class_id or scoped_class_id == class_id
    if write_mode and not (is_class_coordinator and owns_class):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to manage this class timetable")
    if write_mode and not in_scoped_section:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Class coordinator can manage only assigned section timetable")
    if not write_mode and not owns_class and current_user.get("role") != "admin":
        # Teacher read view is restricted to assigned classes.
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this class timetable")
    return class_doc


def _slot_map(shift_id: ShiftId) -> dict[str, dict[str, Any]]:
    return {slot["slot_key"]: slot for slot in _build_slots(shift_id)}


def _valid_object_ids(values: set[str]) -> list[ObjectId]:
    return [ObjectId(value) for value in values if value and ObjectId.is_valid(value)]


async def _hydrate_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    subject_ids = sorted({entry.get("subject_id") for entry in entries if entry.get("subject_id")})
    teacher_ids = sorted({entry.get("teacher_user_id") for entry in entries if entry.get("teacher_user_id")})
    subject_rows = await db.subjects.find({"_id": {"$in": _valid_object_ids(set(subject_ids))}}, {"name": 1, "code": 1}).to_list(length=2000) if subject_ids else []
    teacher_rows = await db.users.find({"_id": {"$in": _valid_object_ids(set(teacher_ids))}}, {"full_name": 1}).to_list(length=2000) if teacher_ids else []
    subject_map = {str(row["_id"]): row for row in subject_rows if row.get("_id")}
    teacher_map = {str(row["_id"]): row for row in teacher_rows if row.get("_id")}
    hydrated = []
    for entry in entries:
        subject = subject_map.get(entry.get("subject_id"), {})
        teacher = teacher_map.get(entry.get("teacher_user_id"), {})
        hydrated.append(
            {
                **entry,
                "subject_name": subject.get("name"),
                "subject_code": subject.get("code"),
                "teacher_name": teacher.get("full_name"),
            }
        )
    return hydrated


def _find_overlap(start_a: str, end_a: str, start_b: str, end_b: str) -> bool:
    a1 = _to_minutes(start_a)
    a2 = _to_minutes(end_a)
    b1 = _to_minutes(start_b)
    b2 = _to_minutes(end_b)
    return max(a1, b1) < min(a2, b2)


async def _validate_entries(*, timetable_id: str | None, shift_id: ShiftId, class_id: str, semester: str, days: list[DayName], entries: list[dict[str, Any]]) -> None:
    slot_map = _slot_map(shift_id)
    seen_class_slots: set[tuple[str, str]] = set()
    subject_counts: dict[str, int] = {}

    subject_ids: set[str] = set()
    teacher_ids: set[str] = set()

    for entry in entries:
        slot_key = entry.get("slot_key")
        day = entry.get("day")
        if day not in days:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Day {day} is not allowed")
        if slot_key not in slot_map:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid slot_key: {slot_key}")
        if slot_map[slot_key]["is_lunch"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Lunch slot cannot be edited")
        dedupe_key = (day, slot_key)
        if dedupe_key in seen_class_slots:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Duplicate allocation for {day} {slot_key}")
        seen_class_slots.add(dedupe_key)

        subject_id = entry.get("subject_id")
        teacher_id = entry.get("teacher_user_id")
        room_code = (entry.get("room_code") or "").strip()
        subject_counts[subject_id] = subject_counts.get(subject_id, 0) + 1
        subject_ids.add(subject_id)
        teacher_ids.add(teacher_id)

    # Subject existence and optional weekly limit.
    subject_docs = await db.subjects.find({"_id": {"$in": _valid_object_ids(subject_ids)}}, {"weekly_limit": 1, "name": 1}).to_list(length=2000) if subject_ids else []
    subject_map = {str(row["_id"]): row for row in subject_docs if row.get("_id")}
    for subject_id in subject_ids:
        if subject_id not in subject_map:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Subject not found: {subject_id}")
    for subject_id, count in subject_counts.items():
        limit = int(subject_map.get(subject_id, {}).get("weekly_limit") or 6)
        if count > limit:
            subject_name = subject_map.get(subject_id, {}).get("name") or subject_id
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Weekly limit exceeded for subject {subject_name} ({count}>{limit})")

    # Teacher existence and role check.
    teacher_docs = await db.users.find({"_id": {"$in": _valid_object_ids(teacher_ids)}}, {"role": 1, "full_name": 1}).to_list(length=2000) if teacher_ids else []
    teacher_map = {str(row["_id"]): row for row in teacher_docs if row.get("_id")}
    for teacher_id in teacher_ids:
        user_doc = teacher_map.get(teacher_id)
        if not user_doc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Teacher not found: {teacher_id}")
        if user_doc.get("role") not in {"teacher", "admin"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid teacher assignment for user: {teacher_id}")

    # Subject-teacher mapping consistency for this class.
    mapping_rows = await db.timetable_subject_teacher_maps.find(
        {"class_id": class_id},
        {"subject_id": 1, "teacher_user_ids": 1},
    ).to_list(length=3000)
    mapped_teachers_by_subject = {
        row.get("subject_id"): set(row.get("teacher_user_ids") or [])
        for row in mapping_rows
        if row.get("subject_id")
    }
    for entry in entries:
        subject_id = entry.get("subject_id")
        teacher_id = entry.get("teacher_user_id")
        allowed = mapped_teachers_by_subject.get(subject_id) or set()
        if allowed and teacher_id not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teacher is not mapped for this subject in the selected class",
            )

    # Validate conflict against active timetables (draft + published).
    teacher_ids = sorted({entry.get("teacher_user_id") for entry in entries if entry.get("teacher_user_id")})
    raw_room_codes = sorted({(entry.get("room_code") or "").strip() for entry in entries if (entry.get("room_code") or "").strip()})
    room_codes = sorted({value.lower() for value in raw_room_codes})
    room_codes_query = sorted({variant for value in raw_room_codes for variant in {value, value.lower(), value.upper()}})
    conflict_or_conditions: list[dict[str, Any]] = []
    if teacher_ids:
        conflict_or_conditions.append({"entries.teacher_user_id": {"$in": teacher_ids}})
    if room_codes_query:
        conflict_or_conditions.append({"entries.room_code": {"$in": room_codes_query}})

    timetable_query: dict[str, Any] = {
        "status": {"$in": ["draft", "published"]},
        "is_active": True,
        "semester": semester,
        "class_id": {"$ne": class_id},
    }
    if timetable_id:
        timetable_query["_id"] = {"$ne": parse_object_id(timetable_id)}
    if conflict_or_conditions:
        timetable_query["$or"] = conflict_or_conditions

    published_rows = await db.timetables.find(
        timetable_query,
        {"entries": 1, "slots": 1, "class_id": 1},
    ).to_list(length=2000)
    for entry in entries:
        day = entry["day"]
        slot_key = entry["slot_key"]
        local_slot = slot_map[slot_key]
        teacher_id = entry.get("teacher_user_id")
        room_code = (entry.get("room_code") or "").strip().lower()
        for timetable in published_rows:
            if timetable.get("class_id") == class_id:
                continue
            foreign_slots = {slot.get("slot_key"): slot for slot in timetable.get("slots", [])}
            for foreign in timetable.get("entries", []):
                if foreign.get("day") != day:
                    continue
                foreign_slot = foreign_slots.get(foreign.get("slot_key"))
                if not foreign_slot:
                    continue
                if not _find_overlap(local_slot["start_time"], local_slot["end_time"], foreign_slot.get("start_time"), foreign_slot.get("end_time")):
                    continue
                if teacher_id and teacher_id == foreign.get("teacher_user_id"):
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Teacher conflict on {day} {local_slot['start_time']}-{local_slot['end_time']}")
                if room_code and room_code == (foreign.get("room_code") or "").strip().lower():
                    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Room conflict on {day} {local_slot['start_time']}-{local_slot['end_time']}")


async def _upsert_subject_teacher_map(*, class_id: str, entries: list[dict[str, Any]]) -> None:
    grouped: dict[str, set[str]] = {}
    for entry in entries:
        subject_id = entry.get("subject_id")
        teacher_id = entry.get("teacher_user_id")
        if not subject_id or not teacher_id:
            continue
        grouped.setdefault(subject_id, set()).add(teacher_id)
    now = datetime.now(timezone.utc)
    for subject_id, teacher_ids in grouped.items():
        await db.timetable_subject_teacher_maps.update_one(
            {"class_id": class_id, "subject_id": subject_id},
            {
                "$set": {
                    "teacher_user_ids": sorted(teacher_ids),
                    "updated_at": now,
                }
            },
            upsert=True,
        )


async def _subject_teacher_map_for_class(class_id: str) -> dict[str, list[str]]:
    rows = await db.timetable_subject_teacher_maps.find(
        {"class_id": class_id},
        {"subject_id": 1, "teacher_user_ids": 1},
    ).to_list(length=3000)
    result: dict[str, list[str]] = {}
    for row in rows:
        subject_id = row.get("subject_id")
        if not subject_id:
            continue
        result[subject_id] = list(row.get("teacher_user_ids") or [])
    return result


async def _to_out(document: dict) -> TimetableOut:
    entries = await _hydrate_entries(document.get("entries", []))
    return TimetableOut(
        id=str(document["_id"]),
        class_id=document.get("class_id"),
        semester=document.get("semester"),
        shift_id=document.get("shift_id"),
        shift_label=SHIFT_CONFIG.get(document.get("shift_id"), {}).get("label", document.get("shift_id")),
        days=document.get("days", DEFAULT_DAYS),
        slots=[TimetableSlotOut(**slot) for slot in document.get("slots", [])],
        entries=entries,
        status=document.get("status", "draft"),
        version=int(document.get("version", 1)),
        admin_locked=bool(document.get("admin_locked", False)),
        published_at=document.get("published_at"),
        published_by_user_id=document.get("published_by_user_id"),
        created_by_user_id=document.get("created_by_user_id"),
        created_at=document.get("created_at"),
        updated_at=document.get("updated_at"),
    )


@router.get("/shifts")
async def list_shift_templates(
    _current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> dict[str, Any]:
    templates = []
    for shift_id, config in SHIFT_CONFIG.items():
        templates.append(
            {
                "id": shift_id,
                "label": config["label"],
                "start_time": config["start_time"],
                "end_time": config["end_time"],
                "lunch_start": config["lunch_start"],
                "lunch_end": config["lunch_end"],
                "slots": _build_slots(shift_id),  # includes lunch lock
            }
        )
    return {"shifts": templates}


@router.post("/generate-grid")
async def generate_grid(
    payload: TimetableGenerateRequest,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> dict[str, Any]:
    return {
        "shift_id": payload.shift_id,
        "shift_label": SHIFT_CONFIG[payload.shift_id]["label"],
        "days": payload.days,
        "slots": _build_slots(payload.shift_id),
    }


@router.get("/lookups")
async def timetable_lookups(
    class_id: str | None = Query(default=None),
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> dict[str, Any]:
    if current_user.get("role") == "admin":
        classes = await db.classes.find({"is_active": True}, {"name": 1, "faculty_name": 1, "branch_name": 1}).sort("name", 1).to_list(length=500)
    else:
        scoped_class_id = (
            (current_user.get("role_scope") or {})
            .get("class_coordinator", {})
            .get("class_id")
        )
        query: dict[str, Any] = {
            "is_active": True,
            "class_coordinator_user_id": str(current_user.get("_id")),
        }
        if scoped_class_id:
            query["_id"] = parse_object_id(scoped_class_id)
        classes = await db.classes.find(
            query,
            {"name": 1, "faculty_name": 1, "branch_name": 1},
        ).sort("name", 1).to_list(length=500)

    subjects = await db.subjects.find({"is_active": True}, {"name": 1, "code": 1}).sort("name", 1).to_list(length=2000)
    teachers = await db.users.find({"role": {"$in": ["teacher", "admin"]}, "is_active": True}, {"full_name": 1, "email": 1, "role": 1}).sort("full_name", 1).to_list(length=2000)
    selected_class_id = class_id or (classes[0].get("_id") and str(classes[0]["_id"]) if classes else None)
    if selected_class_id:
        await _ensure_class_scope_access(current_user=current_user, class_id=selected_class_id, write_mode=False)
    subject_teacher_map = await _subject_teacher_map_for_class(selected_class_id) if selected_class_id else {}
    return {
        "classes": [
            {
                "id": str(item["_id"]),
                "name": item.get("name"),
                "faculty_name": item.get("faculty_name"),
                "branch_name": item.get("branch_name"),
            }
            for item in classes
            if item.get("_id")
        ],
        "subjects": [
            {
                "id": str(item["_id"]),
                "name": item.get("name"),
                "code": item.get("code"),
            }
            for item in subjects
            if item.get("_id")
        ],
        "teachers": [
            {
                "id": str(item["_id"]),
                "name": item.get("full_name") or item.get("email"),
                "role": item.get("role"),
            }
            for item in teachers
            if item.get("_id")
        ],
        "teacher_by_subject": subject_teacher_map,
    }


@router.post("/", response_model=TimetableOut, status_code=status.HTTP_201_CREATED)
async def create_timetable(
    payload: TimetableCreate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> TimetableOut:
    await _ensure_class_scope_access(current_user=current_user, class_id=payload.class_id, write_mode=True)
    days = payload.days or DEFAULT_DAYS
    slots = _build_slots(payload.shift_id)

    entries = [entry.model_dump() for entry in payload.entries]
    if payload.template_timetable_id:
        source = await db.timetables.find_one({"_id": parse_object_id(payload.template_timetable_id), "is_active": True})
        if not source:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template timetable not found")
        if source.get("class_id") != payload.class_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Template timetable must belong to same class")
        entries = source.get("entries", [])

    await _validate_entries(
        timetable_id=None,
        shift_id=payload.shift_id,
        class_id=payload.class_id,
        semester=payload.semester,
        days=days,
        entries=entries,
    )
    latest = await db.timetables.find({"class_id": payload.class_id, "semester": payload.semester, "shift_id": payload.shift_id}, {"version": 1}).sort("version", -1).limit(1).to_list(length=1)
    version = int(latest[0].get("version", 0) + 1) if latest else 1

    document = {
        "class_id": payload.class_id,
        "semester": payload.semester,
        "shift_id": payload.shift_id,
        "days": days,
        "slots": slots,
        "entries": entries,
        "status": "draft",
        "version": version,
        "admin_locked": False,
        "is_active": True,
        "created_by_user_id": str(current_user.get("_id")),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    result = await db.timetables.insert_one(document)
    await _upsert_subject_teacher_map(class_id=payload.class_id, entries=entries)
    created = await db.timetables.find_one({"_id": result.inserted_id})
    return await _to_out(created)


@router.get("/class/{class_id}", response_model=list[TimetableOut])
async def list_class_timetables(
    class_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> list[TimetableOut]:
    if current_user.get("role") == "student":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Students should use /timetables/my")
    await _ensure_class_scope_access(current_user=current_user, class_id=class_id, write_mode=False)
    query: dict[str, Any] = {"class_id": class_id, "is_active": True}
    if status_filter:
        query["status"] = status_filter
    rows = await db.timetables.find(query).sort([("status", 1), ("version", -1)]).to_list(length=100)
    return [await _to_out(row) for row in rows]


@router.get("/my", response_model=TimetableOut)
async def my_published_timetable(
    semester: str | None = Query(default=None),
    current_user=Depends(require_roles(["student"])),
) -> TimetableOut:
    student = await db.students.find_one({"email": current_user.get("email"), "is_active": True}, {"_id": 1, "roll_number": 1})
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    enrollments = await db.enrollments.find(
        {
            "student_id": {"$in": [str(student["_id"]), student.get("roll_number")]},
        }
    ).sort("created_at", -1).to_list(length=100)
    if not enrollments:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No class enrollment found")
    document = None
    for enrollment in enrollments:
        class_doc = await db.classes.find_one({"_id": parse_object_id(enrollment["class_id"]), "is_active": True}, {"_id": 1})
        if not class_doc:
            continue
        query: dict[str, Any] = {"class_id": enrollment["class_id"], "status": "published", "is_active": True}
        if semester:
            query["semester"] = semester
        document = await db.timetables.find_one(query, sort=[("version", -1)])
        if document:
            break
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Published timetable not found")
    return await _to_out(document)


@router.put("/{timetable_id}", response_model=TimetableOut)
async def update_timetable(
    timetable_id: str,
    payload: TimetableUpdate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> TimetableOut:
    timetable = await db.timetables.find_one({"_id": parse_object_id(timetable_id), "is_active": True})
    if not timetable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable not found")
    await _ensure_class_scope_access(current_user=current_user, class_id=timetable["class_id"], write_mode=True)
    if timetable.get("admin_locked"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Published timetable is locked by admin")
    if timetable.get("status") == "published":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Edit is allowed only in draft mode")

    days = payload.days or timetable.get("days", DEFAULT_DAYS)
    entries = [entry.model_dump() for entry in payload.entries] if payload.entries is not None else timetable.get("entries", [])
    await _validate_entries(
        timetable_id=timetable_id,
        shift_id=timetable["shift_id"],
        class_id=timetable["class_id"],
        semester=timetable["semester"],
        days=days,
        entries=entries,
    )
    await db.timetables.update_one(
        {"_id": timetable["_id"]},
        {
            "$set": {
                "days": days,
                "entries": entries,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    await _upsert_subject_teacher_map(class_id=timetable["class_id"], entries=entries)
    updated = await db.timetables.find_one({"_id": timetable["_id"]})
    return await _to_out(updated)


@router.post("/{timetable_id}/publish", response_model=TimetablePublishResponse)
async def publish_timetable(
    timetable_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> TimetablePublishResponse:
    timetable = await db.timetables.find_one({"_id": parse_object_id(timetable_id), "is_active": True})
    if not timetable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable not found")
    await _ensure_class_scope_access(current_user=current_user, class_id=timetable["class_id"], write_mode=True)
    if timetable.get("admin_locked"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Published timetable is locked by admin")

    await _validate_entries(
        timetable_id=timetable_id,
        shift_id=timetable["shift_id"],
        class_id=timetable["class_id"],
        semester=timetable["semester"],
        days=timetable.get("days", DEFAULT_DAYS),
        entries=timetable.get("entries", []),
    )
    # Archive previous published version for same class/semester.
    await db.timetables.update_many(
        {
            "_id": {"$ne": timetable["_id"]},
            "class_id": timetable["class_id"],
            "semester": timetable["semester"],
            "status": "published",
            "is_active": True,
        },
        {"$set": {"is_active": False, "archived_at": datetime.now(timezone.utc)}},
    )
    await db.timetables.update_one(
        {"_id": timetable["_id"]},
        {
            "$set": {
                "status": "published",
                "published_at": datetime.now(timezone.utc),
                "published_by_user_id": str(current_user.get("_id")),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    await _upsert_subject_teacher_map(class_id=timetable["class_id"], entries=timetable.get("entries", []))
    published = await db.timetables.find_one({"_id": timetable["_id"]})
    out = await _to_out(published)
    return TimetablePublishResponse(message="Timetable published", timetable=out)


@router.post("/{timetable_id}/lock", response_model=TimetableOut)
async def set_timetable_lock(
    timetable_id: str,
    payload: TimetableLockRequest,
    _current_user=Depends(require_roles(["admin"])),
) -> TimetableOut:
    timetable = await db.timetables.find_one({"_id": parse_object_id(timetable_id), "is_active": True})
    if not timetable:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Timetable not found")
    await db.timetables.update_one(
        {"_id": timetable["_id"]},
        {"$set": {"admin_locked": payload.admin_locked, "updated_at": datetime.now(timezone.utc)}},
    )
    updated = await db.timetables.find_one({"_id": timetable["_id"]})
    return await _to_out(updated)
