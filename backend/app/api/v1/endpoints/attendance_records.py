from datetime import datetime, timedelta, timezone
from typing import Any, List

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
    AttendanceAnalyticsOut,
    AttendanceRecordBulkCreate,
    AttendanceRecordCreate,
    AttendanceRecordOut,
    AttendanceRosterOut,
    AttendanceRosterStudentOut,
    AttendanceSectionSummaryOut,
    AttendanceStudentSummaryOut,
)
from app.services.public_ids import build_public_id
from app.services.academic_students import (
    list_students_for_section,
    resolve_active_section_id_for_student,
    resolve_student_academic_context_for_user,
)
from app.services.attendance_summary import build_attendance_analytics, build_attendance_section_summary
from app.services.class_slot_read_models import sync_class_slot_read_models_for_offering_query, sync_class_slot_read_models_for_query

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
    canonical_section_id = await resolve_active_section_id_for_student(student, database=db)
    if canonical_section_id != offering.get("section_id"):
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
    if updated:
        public_id = build_public_id("attendance_record", updated, prefer_existing=False)
        if public_id and updated.get("public_id") != public_id:
            await db.attendance_records.update_one({"_id": updated["_id"]}, {"$set": {"public_id": public_id}})
            updated["public_id"] = public_id
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
    student = await resolve_student_academic_context_for_user(current_user, database=db)
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    return student


async def _attendance_percent_for_student(*, student: dict, section_id: str, group_id: str | None) -> float | None:
    offering_query: dict[str, Any] = {"section_id": section_id, "is_active": True}
    if group_id:
        offering_query["$or"] = [{"group_id": None}, {"group_id": group_id}]
    else:
        offering_query["group_id"] = None

    offerings = await db.course_offerings.find(offering_query, {"_id": 1}).to_list(length=2000)
    offering_ids = [str(item["_id"]) for item in offerings if item.get("_id")]
    if not offering_ids:
        return None
    slots = await db.class_slots.find(
        {"course_offering_id": {"$in": offering_ids}, "is_active": True},
        {"_id": 1},
    ).to_list(length=5000)
    slot_ids = [str(item["_id"]) for item in slots if item.get("_id")]
    if not slot_ids:
        return None

    records = await db.attendance_records.find(
        {"class_slot_id": {"$in": slot_ids}, "student_id": str(student["_id"])},
        {"status": 1},
    ).to_list(length=5000)
    if not records:
        return None

    present_like = sum(1 for item in records if item.get("status") in {"present", "late", "excused"})
    total = len(records)
    return round((present_like / total) * 100, 2) if total else None


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
        student = await resolve_student_academic_context_for_user(current_user, database=db)
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


@router.get("/marking-lookups")
async def attendance_marking_lookups(
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> dict:
    slot_rows: list[dict] = []
    if current_user.get("role") == "admin":
        await sync_class_slot_read_models_for_query(query={"is_active": True}, database=db)
        slot_rows = await db.class_slot_read_models.find({"is_active": True}).to_list(length=5000)
    else:
        teacher_user_id = str(current_user.get("_id"))
        coordinator_section_ids = await db.classes.distinct(
            "_id",
            {"class_coordinator_user_id": teacher_user_id, "is_active": True},
        )
        offering_rows = await db.course_offering_read_models.find(
            {
                "is_active": True,
                "$or": [
                    {"teacher_user_id": teacher_user_id},
                    {"section_id": {"$in": [str(item) for item in coordinator_section_ids if item]}},
                ],
            }
        ).to_list(length=5000)
        offering_ids = [str(item["_id"]) for item in offering_rows if item.get("_id")]
        if offering_ids:
            await sync_class_slot_read_models_for_offering_query(
                offering_query={"_id": {"$in": [parse_object_id(value) for value in offering_ids]}},
                database=db,
            )
            slot_rows = await db.class_slot_read_models.find(
                {"course_offering_id": {"$in": offering_ids}, "is_active": True}
            ).to_list(length=5000)

    slot_rows.sort(key=lambda item: (str(item.get("section_name") or ""), str(item.get("day") or ""), str(item.get("start_time") or "")))
    return {"items": slot_rows}


@router.get("/roster/{class_slot_id}", response_model=AttendanceRosterOut)
async def attendance_roster(
    class_slot_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> AttendanceRosterOut:
    slot, offering = await _get_slot_with_offering(class_slot_id)
    await _ensure_mark_access(current_user=current_user, offering=offering)

    await db.class_slot_read_models.find_one({"_id": parse_object_id(class_slot_id)})  # warm fake db compatibility
    read_slot = await db.class_slot_read_models.find_one({"_id": parse_object_id(class_slot_id)}) or slot
    students = await list_students_for_section(
        offering["section_id"],
        group_id=offering.get("group_id"),
        database=db,
    )
    student_ids = [str(item["_id"]) for item in students if item.get("_id")]
    existing_rows = await db.attendance_records.find(
        {"class_slot_id": class_slot_id, "student_id": {"$in": student_ids}},
    ).to_list(length=5000)
    existing_map = {str(item.get("student_id")): item for item in existing_rows}

    rows: list[AttendanceRosterStudentOut] = []
    status_counts = {"present": 0, "absent": 0, "late": 0, "excused": 0, "unmarked": 0}
    for student in students:
        existing = existing_map.get(str(student["_id"]))
        status = existing.get("status") if existing else None
        if status in status_counts:
            status_counts[status] += 1
        else:
            status_counts["unmarked"] += 1
        rows.append(
            AttendanceRosterStudentOut(
                student_id=str(student["_id"]),
                student_name=str(student.get("full_name") or ""),
                roll_number=student.get("roll_number"),
                group_id=student.get("group_id"),
                group_name=read_slot.get("group_name"),
                status=status,
                note=existing.get("note") if existing else None,
                attendance_percent=await _attendance_percent_for_student(
                    student=student,
                    section_id=offering["section_id"],
                    group_id=student.get("group_id"),
                ),
            )
        )

    marked_total = len(rows) - status_counts["unmarked"]
    return AttendanceRosterOut(
        class_slot_id=class_slot_id,
        section_id=offering.get("section_id"),
        section_name=read_slot.get("section_name"),
        group_id=offering.get("group_id"),
        group_name=read_slot.get("group_name"),
        subject_name=read_slot.get("subject_name"),
        teacher_name=read_slot.get("teacher_name"),
        day=slot.get("day"),
        start_time=slot.get("start_time"),
        end_time=slot.get("end_time"),
        room_code=slot.get("room_code"),
        summary={
            "total_students": len(rows),
            "marked_students": marked_total,
            "present": status_counts["present"],
            "absent": status_counts["absent"],
            "late": status_counts["late"],
            "excused": status_counts["excused"],
            "unmarked": status_counts["unmarked"],
        },
        students=rows,
    )


@router.get("/summary", response_model=AttendanceSectionSummaryOut)
async def attendance_section_summary(
    section_id: str | None = Query(default=None),
    group_id: str | None = Query(default=None),
    shortage_threshold: float = Query(default=75, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> AttendanceSectionSummaryOut:
    resolved_section_id = str(section_id or "").strip()
    resolved_group_id = str(group_id or "").strip() or None

    if current_user.get("role") == "teacher":
        teacher_user_id = str(current_user.get("_id"))
        coordinator_section_ids = {
            str(item)
            for item in await db.classes.distinct("_id", {"class_coordinator_user_id": teacher_user_id, "is_active": True})
            if item
        }
        if not resolved_section_id:
            resolved_section_id = next(iter(coordinator_section_ids), "")
        teaching_offerings = await db.course_offerings.find(
            {"teacher_user_id": teacher_user_id, "is_active": True},
            {"section_id": 1, "group_id": 1},
        ).to_list(length=5000)
        teaching_section_ids = {str(item.get("section_id")) for item in teaching_offerings if item.get("section_id")}
        allowed_section_ids = coordinator_section_ids | teaching_section_ids
        if not resolved_section_id or resolved_section_id not in allowed_section_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this attendance summary")

    if not resolved_section_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="section_id is required")

    return await build_attendance_section_summary(
        section_id=resolved_section_id,
        group_id=resolved_group_id,
        shortage_threshold=shortage_threshold,
        database=db,
    )


@router.get("/my-summary", response_model=AttendanceStudentSummaryOut)
async def my_attendance_summary(
    shortage_threshold: float = Query(default=75, ge=1, le=100),
    current_user=Depends(require_roles(["student"])),
) -> AttendanceStudentSummaryOut:
    student = await _student_profile_from_user(current_user)
    section_id = str(student.get("canonical_class_id") or "").strip()
    if not section_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student section not found")

    summary = await build_attendance_section_summary(
        section_id=section_id,
        group_id=str(student.get("canonical_group_id") or "").strip() or None,
        shortage_threshold=shortage_threshold,
        database=db,
    )
    student_id = str(student.get("_id"))
    match = next((item for item in summary.students if item.student_id == student_id), None)
    if match:
        return match
    return AttendanceStudentSummaryOut(
        student_id=student_id,
        student_name=str(student.get("full_name") or ""),
        roll_number=student.get("roll_number"),
        group_id=student.get("canonical_group_id"),
        total_marked_slots=0,
        present_like_slots=0,
        absent_slots=0,
        attendance_percent=0,
        shortage_threshold=shortage_threshold,
        shortage_risk=False,
    )


@router.get("/analytics", response_model=AttendanceAnalyticsOut)
async def attendance_analytics(
    section_id: str | None = Query(default=None),
    group_id: str | None = Query(default=None),
    range_days: int = Query(default=30, ge=7, le=180),
    shortage_threshold: float = Query(default=75, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> AttendanceAnalyticsOut:
    resolved_section_id = str(section_id or "").strip()
    resolved_group_id = str(group_id or "").strip() or None

    if current_user.get("role") == "teacher":
        teacher_user_id = str(current_user.get("_id"))
        coordinator_section_ids = {
            str(item)
            for item in await db.classes.distinct("_id", {"class_coordinator_user_id": teacher_user_id, "is_active": True})
            if item
        }
        teaching_offerings = await db.course_offerings.find(
            {"teacher_user_id": teacher_user_id, "is_active": True},
            {"section_id": 1},
        ).to_list(length=5000)
        teaching_section_ids = {str(item.get("section_id")) for item in teaching_offerings if item.get("section_id")}
        allowed_section_ids = coordinator_section_ids | teaching_section_ids
        if not resolved_section_id:
            resolved_section_id = next(iter(allowed_section_ids), "")
        if not resolved_section_id or resolved_section_id not in allowed_section_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this attendance analytics")

    if not resolved_section_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="section_id is required")

    return await build_attendance_analytics(
        section_id=resolved_section_id,
        group_id=resolved_group_id,
        range_days=range_days,
        shortage_threshold=shortage_threshold,
        database=db,
    )


@router.get("/my-analytics", response_model=AttendanceAnalyticsOut)
async def my_attendance_analytics(
    range_days: int = Query(default=30, ge=7, le=180),
    shortage_threshold: float = Query(default=75, ge=1, le=100),
    current_user=Depends(require_roles(["student"])),
) -> AttendanceAnalyticsOut:
    student = await _student_profile_from_user(current_user)
    section_id = str(student.get("canonical_class_id") or "").strip()
    if not section_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student section not found")

    return await build_attendance_analytics(
        section_id=section_id,
        group_id=str(student.get("canonical_group_id") or "").strip() or None,
        student_id=str(student.get("_id") or ""),
        range_days=range_days,
        shortage_threshold=shortage_threshold,
        database=db,
    )


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
