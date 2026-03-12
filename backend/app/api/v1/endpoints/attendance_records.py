from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import settings
from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import ATTENDANCE_RECORD_SCHEMA_VERSION, INTERNSHIP_SESSION_SCHEMA_VERSION
from app.core.security import require_roles
from app.schemas.internship_session import (
    InternshipClockInRequest,
    InternshipClockOutRequest,
    InternshipSessionOut,
)
from app.models.attendance_records import attendance_record_public
from app.schemas.attendance_record import (
    AttendanceRecordBulkCreate,
    AttendanceRecordCreate,
    AttendanceRecordOut,
)

router = APIRouter()


async def _resolve_student(student_id: str) -> dict | None:
    try:
        student = await db.students.find_one({"_id": parse_object_id(student_id), "is_active": True})
    except HTTPException:
        student = None
    if student:
        return student
    return await db.students.find_one({"roll_number": student_id, "is_active": True})


async def _get_slot_with_offering(slot_id: str) -> tuple[dict, dict]:
    slot = await db.class_slots.find_one({"_id": parse_object_id(slot_id), "is_active": True})
    if not slot:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Class slot not found")
    offering = await db.course_offerings.find_one({"_id": parse_object_id(slot["course_offering_id"]), "is_active": True})
    if not offering:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course offering not found for class slot")
    return slot, offering


async def _ensure_mark_access(*, current_user: dict, offering: dict) -> None:
    if current_user.get("role") == "admin":
        return
    if current_user.get("role") != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    section = await db.classes.find_one({"_id": parse_object_id(offering["section_id"]), "is_active": True})
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    if section.get("class_coordinator_user_id") != str(current_user.get("_id")) and offering.get("teacher_user_id") != str(current_user.get("_id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only mapped teacher or class coordinator can mark attendance")


async def _mark_single(*, payload: AttendanceRecordCreate, actor_user_id: str) -> dict:
    slot, offering = await _get_slot_with_offering(payload.class_slot_id)
    student = await _resolve_student(payload.student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student not found")
    if student.get("class_id") != offering.get("section_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student is not in offering section")
    if offering.get("group_id") and student.get("group_id") != offering.get("group_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student is not in offering group")

    document = {
        "class_slot_id": payload.class_slot_id,
        "student_id": str(student["_id"]),
        "status": payload.status,
        "note": payload.note,
        "marked_by_user_id": actor_user_id,
        "marked_at": datetime.now(timezone.utc),
        "schema_version": ATTENDANCE_RECORD_SCHEMA_VERSION,
    }
    await db.attendance_records.update_one(
        {"class_slot_id": payload.class_slot_id, "student_id": str(student["_id"])},
        {"$set": document},
        upsert=True,
    )
    updated = await db.attendance_records.find_one({"class_slot_id": payload.class_slot_id, "student_id": str(student["_id"])})
    return updated


def _internship_public(document: dict) -> dict:
    return {
        "id": str(document.get("_id")),
        "student_user_id": document.get("student_user_id"),
        "student_id": document.get("student_id"),
        "status": document.get("status"),
        "clock_in_at": document.get("clock_in_at"),
        "clock_out_at": document.get("clock_out_at"),
        "total_minutes": document.get("total_minutes"),
        "auto_closed": bool(document.get("auto_closed", False)),
        "note": document.get("note"),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "schema_version": document.get("schema_version", INTERNSHIP_SESSION_SCHEMA_VERSION),
    }


async def _student_profile_from_user(current_user: dict) -> dict:
    student = await db.students.find_one({"email": current_user.get("email"), "is_active": True})
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    return student


def _auto_logout_cutoff(clock_in_at: datetime) -> datetime:
    return clock_in_at + timedelta(hours=max(1, settings.internship_auto_logout_hours))


async def _auto_close_internship_session(session: dict, *, now: datetime) -> dict:
    if not session or session.get("status") != "active":
        return session
    clock_in_at = session.get("clock_in_at")
    if not clock_in_at:
        return session
    cutoff = _auto_logout_cutoff(clock_in_at)
    if now < cutoff:
        return session
    total_minutes = max(0, int((cutoff - clock_in_at).total_seconds() // 60))
    await db.internship_sessions.update_one(
        {"_id": session["_id"]},
        {
            "$set": {
                "status": "auto_closed",
                "clock_out_at": cutoff,
                "auto_closed": True,
                "total_minutes": total_minutes,
                "updated_at": now,
                "schema_version": INTERNSHIP_SESSION_SCHEMA_VERSION,
            }
        },
    )
    return await db.internship_sessions.find_one({"_id": session["_id"]})


@router.get("/", response_model=List[AttendanceRecordOut])
async def list_attendance_records(
    class_slot_id: str | None = Query(default=None),
    student_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[AttendanceRecordOut]:
    query = {}
    if class_slot_id:
        query["class_slot_id"] = class_slot_id
    if student_id:
        student = await _resolve_student(student_id)
        if not student:
            return []
        query["student_id"] = str(student["_id"])

    if current_user.get("role") == "student":
        student = await db.students.find_one({"email": current_user.get("email"), "is_active": True})
        if not student:
            return []
        query["student_id"] = str(student["_id"])

    rows = await db.attendance_records.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [AttendanceRecordOut(**attendance_record_public(row)) for row in rows]


@router.post("/mark", response_model=AttendanceRecordOut, status_code=status.HTTP_201_CREATED)
async def mark_attendance(
    payload: AttendanceRecordCreate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> AttendanceRecordOut:
    _, offering = await _get_slot_with_offering(payload.class_slot_id)
    await _ensure_mark_access(current_user=current_user, offering=offering)
    record = await _mark_single(payload=payload, actor_user_id=str(current_user.get("_id")))
    return AttendanceRecordOut(**attendance_record_public(record))


@router.post("/mark-bulk", response_model=List[AttendanceRecordOut])
async def mark_attendance_bulk(
    payload: AttendanceRecordBulkCreate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[AttendanceRecordOut]:
    _, offering = await _get_slot_with_offering(payload.class_slot_id)
    await _ensure_mark_access(current_user=current_user, offering=offering)
    out = []
    for record_payload in payload.records:
        single = AttendanceRecordCreate(
            class_slot_id=payload.class_slot_id,
            student_id=record_payload.student_id,
            status=record_payload.status,
            note=record_payload.note,
        )
        updated = await _mark_single(payload=single, actor_user_id=str(current_user.get("_id")))
        out.append(AttendanceRecordOut(**attendance_record_public(updated)))
    return out


@router.post("/internship/clock-in", response_model=InternshipSessionOut, status_code=status.HTTP_201_CREATED)
async def internship_clock_in(
    payload: InternshipClockInRequest,
    current_user=Depends(require_roles(["student"])),
) -> InternshipSessionOut:
    student = await _student_profile_from_user(current_user)
    now = datetime.now(timezone.utc)

    active = await db.internship_sessions.find_one(
        {"student_user_id": str(current_user.get("_id")), "status": "active"},
        sort=[("clock_in_at", -1)],
    )
    if active:
        active = await _auto_close_internship_session(active, now=now)
    if active and active.get("status") == "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Internship session already active")

    document = {
        "student_user_id": str(current_user.get("_id")),
        "student_id": str(student.get("_id")),
        "status": "active",
        "clock_in_at": now,
        "clock_out_at": None,
        "auto_closed": False,
        "total_minutes": None,
        "note": payload.note,
        "created_at": now,
        "updated_at": now,
        "schema_version": INTERNSHIP_SESSION_SCHEMA_VERSION,
    }
    result = await db.internship_sessions.insert_one(document)
    created = await db.internship_sessions.find_one({"_id": result.inserted_id})
    return InternshipSessionOut(**_internship_public(created))


@router.post("/internship/clock-out", response_model=InternshipSessionOut)
async def internship_clock_out(
    payload: InternshipClockOutRequest,
    current_user=Depends(require_roles(["student"])),
) -> InternshipSessionOut:
    now = datetime.now(timezone.utc)
    active = await db.internship_sessions.find_one(
        {"student_user_id": str(current_user.get("_id")), "status": "active"},
        sort=[("clock_in_at", -1)],
    )
    if not active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active internship session")
    active = await _auto_close_internship_session(active, now=now)
    if active.get("status") != "active":
        return InternshipSessionOut(**_internship_public(active))

    clock_in_at = active.get("clock_in_at")
    total_minutes = max(0, int((now - clock_in_at).total_seconds() // 60))
    await db.internship_sessions.update_one(
        {"_id": active["_id"]},
        {
            "$set": {
                "status": "closed",
                "clock_out_at": now,
                "total_minutes": total_minutes,
                "auto_closed": False,
                "note": payload.note or active.get("note"),
                "updated_at": now,
                "schema_version": INTERNSHIP_SESSION_SCHEMA_VERSION,
            }
        },
    )
    updated = await db.internship_sessions.find_one({"_id": active["_id"]})
    return InternshipSessionOut(**_internship_public(updated))


@router.get("/internship/status", response_model=InternshipSessionOut | None)
async def internship_status(
    current_user=Depends(require_roles(["student"])),
) -> InternshipSessionOut | None:
    session = await db.internship_sessions.find_one(
        {"student_user_id": str(current_user.get("_id"))},
        sort=[("clock_in_at", -1)],
    )
    if not session:
        return None
    session = await _auto_close_internship_session(session, now=datetime.now(timezone.utc))
    return InternshipSessionOut(**_internship_public(session))
