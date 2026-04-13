from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.database import db
from app.core.mongo import parse_object_id
from app.schemas.attendance_record import (
    AttendanceAnalyticsOut,
    AttendanceSectionSummaryOut,
    AttendanceStudentSummaryOut,
    AttendanceSubjectSummaryOut,
    AttendanceTrendPointOut,
)
from app.services.academic_students import list_students_for_section


PRESENT_LIKE_STATUSES = {"present", "late", "excused"}


async def _resolve_section_scope(
    *,
    section_id: str,
    group_id: str | None,
    database: Any,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, list[str], dict[str, dict[str, Any]], dict[str, str]]:
    section = await database.classes.find_one({"_id": parse_object_id(section_id), "is_active": True}, {"name": 1})
    group = None
    if group_id:
        group = await database.groups.find_one({"_id": parse_object_id(group_id), "is_active": True}, {"name": 1})

    offering_query: dict[str, Any] = {"section_id": section_id, "is_active": True}
    if group_id:
        offering_query["$or"] = [{"group_id": None}, {"group_id": group_id}]
    else:
        offering_query["group_id"] = None

    offerings = await database.course_offerings.find(
        offering_query,
        {"_id": 1, "subject_id": 1},
    ).to_list(length=5000)
    offering_ids = [str(item["_id"]) for item in offerings if item.get("_id")]
    offering_map = {str(item["_id"]): item for item in offerings if item.get("_id")}

    subject_ids = sorted({str(item.get("subject_id")) for item in offerings if item.get("subject_id")})
    subject_rows = []
    if subject_ids:
        subject_rows = await database.subjects.find(
            {"_id": {"$in": [parse_object_id(value) for value in subject_ids]}},
            {"name": 1},
        ).to_list(length=len(subject_ids))
    subject_name_map = {str(item.get("_id")): str(item.get("name") or "") for item in subject_rows if item.get("_id")}
    return section, group, offering_ids, offering_map, subject_name_map


async def _load_section_slot_rows(
    *,
    offering_ids: list[str],
    database: Any,
) -> list[dict[str, Any]]:
    if not offering_ids:
        return []
    return await database.class_slots.find(
        {"course_offering_id": {"$in": offering_ids}, "is_active": True},
        {"_id": 1, "course_offering_id": 1, "day": 1, "start_time": 1},
    ).to_list(length=10000)


def _bucket_label(marked_at: datetime) -> str:
    iso_year, iso_week, _ = marked_at.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _attendance_percent(present_like: int, total_marked: int) -> float:
    return round((present_like / total_marked) * 100, 2) if total_marked else 0.0


async def build_attendance_section_summary(
    *,
    section_id: str,
    group_id: str | None = None,
    shortage_threshold: float = 75,
    database: Any = db,
) -> AttendanceSectionSummaryOut:
    students = await list_students_for_section(section_id, group_id=group_id, database=database)
    section, group, offering_ids, _, _ = await _resolve_section_scope(
        section_id=section_id,
        group_id=group_id,
        database=database,
    )
    slots = await _load_section_slot_rows(offering_ids=offering_ids, database=database)
    slot_ids = [str(item["_id"]) for item in slots if item.get("_id")]

    student_ids = [str(item["_id"]) for item in students if item.get("_id")]
    records = []
    if slot_ids and student_ids:
        records = await database.attendance_records.find(
            {
                "class_slot_id": {"$in": slot_ids},
                "student_id": {"$in": student_ids},
            },
            {"student_id": 1, "status": 1},
        ).to_list(length=50000)

    records_by_student: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        records_by_student.setdefault(str(record.get("student_id") or ""), []).append(record)

    student_summaries: list[AttendanceStudentSummaryOut] = []
    for student in students:
        student_records = records_by_student.get(str(student.get("_id") or ""), [])
        total_marked = len(student_records)
        present_like = sum(1 for item in student_records if item.get("status") in PRESENT_LIKE_STATUSES)
        absent_slots = sum(1 for item in student_records if item.get("status") == "absent")
        attendance_percent = _attendance_percent(present_like, total_marked)
        student_summaries.append(
            AttendanceStudentSummaryOut(
                student_id=str(student["_id"]),
                student_name=str(student.get("full_name") or ""),
                roll_number=student.get("roll_number"),
                group_id=student.get("group_id"),
                group_name=(group or {}).get("name") if group_id else None,
                total_marked_slots=total_marked,
                present_like_slots=present_like,
                absent_slots=absent_slots,
                attendance_percent=attendance_percent,
                shortage_threshold=shortage_threshold,
                shortage_risk=attendance_percent < shortage_threshold if total_marked else False,
            )
        )

    average_attendance = round(
        sum(item.attendance_percent for item in student_summaries) / len(student_summaries),
        2,
    ) if student_summaries else 0.0
    shortage_risk_count = sum(1 for item in student_summaries if item.shortage_risk)

    return AttendanceSectionSummaryOut(
        section_id=section_id,
        section_name=(section or {}).get("name"),
        group_id=group_id,
        group_name=(group or {}).get("name"),
        total_students=len(student_summaries),
        total_slots=len(slot_ids),
        total_marked_records=len(records),
        average_attendance_percent=average_attendance,
        shortage_threshold=shortage_threshold,
        shortage_risk_count=shortage_risk_count,
        students=student_summaries,
    )


async def build_attendance_analytics(
    *,
    section_id: str,
    group_id: str | None = None,
    student_id: str | None = None,
    range_days: int = 30,
    shortage_threshold: float = 75,
    database: Any = db,
) -> AttendanceAnalyticsOut:
    section, group, offering_ids, offering_map, subject_name_map = await _resolve_section_scope(
        section_id=section_id,
        group_id=group_id,
        database=database,
    )
    slots = await _load_section_slot_rows(offering_ids=offering_ids, database=database)
    slot_map = {str(item["_id"]): item for item in slots if item.get("_id")}
    slot_ids = sorted(slot_map)
    since = datetime.now(timezone.utc) - timedelta(days=max(1, int(range_days)))

    record_query: dict[str, Any] = {
        "class_slot_id": {"$in": slot_ids},
        "marked_at": {"$gte": since},
    }
    student_doc = None
    if student_id:
        student_doc = await database.students.find_one({"_id": parse_object_id(student_id), "is_active": True})
        record_query["student_id"] = student_id

    records = []
    if slot_ids:
        records = await database.attendance_records.find(
            record_query,
            {"class_slot_id": 1, "student_id": 1, "status": 1, "marked_at": 1},
        ).sort("marked_at", 1).to_list(length=50000)

    total_marked = len(records)
    present_like = sum(1 for item in records if item.get("status") in PRESENT_LIKE_STATUSES)
    absent_slots = sum(1 for item in records if item.get("status") == "absent")
    average_attendance = _attendance_percent(present_like, total_marked)

    trend_map: dict[str, dict[str, int]] = {}
    subject_map: dict[str, dict[str, Any]] = {}
    for record in records:
        marked_at = record.get("marked_at")
        if not marked_at:
            continue
        bucket_label = _bucket_label(marked_at)
        bucket = trend_map.setdefault(bucket_label, {"present_like": 0, "total": 0})
        bucket["total"] += 1
        if record.get("status") in PRESENT_LIKE_STATUSES:
            bucket["present_like"] += 1

        slot = slot_map.get(str(record.get("class_slot_id") or ""))
        offering = offering_map.get(str((slot or {}).get("course_offering_id") or ""))
        subject_id = str((offering or {}).get("subject_id") or "")
        subject_bucket = subject_map.setdefault(
            subject_id or "unassigned",
            {
                "subject_id": subject_id or None,
                "subject_name": subject_name_map.get(subject_id) or "Unassigned",
                "present_like": 0,
                "absent": 0,
                "total": 0,
            },
        )
        subject_bucket["total"] += 1
        if record.get("status") in PRESENT_LIKE_STATUSES:
            subject_bucket["present_like"] += 1
        if record.get("status") == "absent":
            subject_bucket["absent"] += 1

    trend = [
        AttendanceTrendPointOut(
            label=label,
            total_marked_slots=bucket["total"],
            attendance_percent=_attendance_percent(bucket["present_like"], bucket["total"]),
        )
        for label, bucket in sorted(trend_map.items())
    ]
    subjects = sorted(
        [
            AttendanceSubjectSummaryOut(
                subject_id=item["subject_id"],
                subject_name=item["subject_name"],
                total_marked_slots=item["total"],
                present_like_slots=item["present_like"],
                absent_slots=item["absent"],
                attendance_percent=_attendance_percent(item["present_like"], item["total"]),
                shortage_risk=_attendance_percent(item["present_like"], item["total"]) < shortage_threshold if item["total"] else False,
            )
            for item in subject_map.values()
        ],
        key=lambda item: ((item.subject_name or "").lower(), item.subject_id or ""),
    )

    return AttendanceAnalyticsOut(
        section_id=section_id,
        section_name=(section or {}).get("name"),
        group_id=group_id,
        group_name=(group or {}).get("name"),
        student_id=student_id,
        student_name=(student_doc or {}).get("full_name"),
        roll_number=(student_doc or {}).get("roll_number"),
        range_days=range_days,
        shortage_threshold=shortage_threshold,
        average_attendance_percent=average_attendance,
        present_like_slots=present_like,
        absent_slots=absent_slots,
        total_marked_slots=total_marked,
        shortage_risk=average_attendance < shortage_threshold if total_marked else False,
        trend=trend,
        subjects=subjects,
    )
