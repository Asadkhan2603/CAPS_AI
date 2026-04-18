from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bson import ObjectId

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.v1.endpoints.timetables import _build_slots
from app.core.database import db
from app.core.schema_versions import (
    AI_EVALUATION_RUN_SCHEMA_VERSION,
    AI_JOB_SCHEMA_VERSION,
    ANALYTICS_SNAPSHOT_SCHEMA_VERSION,
    ASSIGNMENT_SCHEMA_VERSION,
    ATTENDANCE_RECORD_SCHEMA_VERSION,
    AUDIT_LOG_SCHEMA_VERSION,
    BATCH_SCHEMA_VERSION,
    CLASS_SCHEMA_VERSION,
    CLASS_SLOT_SCHEMA_VERSION,
    CLUB_APPLICATION_SCHEMA_VERSION,
    CLUB_EVENT_SCHEMA_VERSION,
    CLUB_MEMBER_SCHEMA_VERSION,
    CLUB_SCHEMA_VERSION,
    COMMUNICATION_DELIVERY_SCHEMA_VERSION,
    COURSE_OFFERING_SCHEMA_VERSION,
    DEPARTMENT_SCHEMA_VERSION,
    ENROLLMENT_SCHEMA_VERSION,
    EVALUATION_SCHEMA_VERSION,
    EVENT_REGISTRATION_SCHEMA_VERSION,
    EXAM_SCHEMA_VERSION,
    FACULTY_SCHEMA_VERSION,
    GRIEVANCE_SCHEMA_VERSION,
    GROUP_SCHEMA_VERSION,
    NOTICE_SCHEMA_VERSION,
    NOTIFICATION_SCHEMA_VERSION,
    PROGRAM_SCHEMA_VERSION,
    REVIEW_TICKET_SCHEMA_VERSION,
    SEMESTER_SCHEMA_VERSION,
    SIMILARITY_LOG_SCHEMA_VERSION,
    SPECIALIZATION_SCHEMA_VERSION,
    STUDENT_SCHEMA_VERSION,
    SUBJECT_SCHEMA_VERSION,
    SUBMISSION_SCHEMA_VERSION,
    SYSTEM_HEALTH_SNAPSHOT_SCHEMA_VERSION,
    TIMETABLE_SCHEMA_VERSION,
    TIMETABLE_SUBJECT_TEACHER_MAP_SCHEMA_VERSION,
    UNIVERSITY_SCHEMA_VERSION,
    USER_SCHEMA_VERSION,
    USER_SESSION_SCHEMA_VERSION,
)
from app.core.security import get_password_hash
from app.services.academic_batching import (
    build_batch_document,
    build_batch_identity,
    build_semester_document,
    resolve_program_academic_context,
)
from app.services.batch_read_models import sync_batch_read_models_for_ids
from app.services.class_representative_governance import assign_section_class_representative
from app.services.class_slot_read_models import sync_class_slot_read_models_for_ids
from app.services.club_governance import assign_student_as_club_president
from app.services.course_offering_read_models import sync_course_offering_read_models_for_ids
from app.services.master_hierarchy import (
    build_department_business_id,
    build_faculty_business_id,
    build_program_business_id,
    build_specialization_business_id,
)
from app.services.public_ids import persist_public_id, persist_public_id_update
from app.services.section_read_models import sync_section_read_models_for_ids
from app.services.semester_read_models import sync_semester_read_models_for_ids


PASSWORD = "CapsDemo@2026!"
ACADEMIC_YEAR = "2026-2027"
UNIVERSITY_CODE = "CAPSDEMO"
FACULTY_CODE = "ENG"
DEPARTMENT_CODE = "CSE"
PROGRAM_CODE = "BTECHAI"
SPECIALIZATION_CODE = "AIDS"
BATCH_START_YEAR = 2024
DURATION_YEARS = 4
SEMESTER_NUMBER = 5
SECTION_NAME = "AI-5-A"
GROUP_CODE = "TEAM-A"
SUBJECT_CODE = "AID501"
NOTICE_TEMPLATE_KEY = "seed.feature.demo"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def iso_date(value: datetime) -> str:
    return value.date().isoformat()


def object_id(value: Any) -> str:
    return str(value.get("_id") if isinstance(value, dict) else value)


def user_label(user: dict[str, Any]) -> str:
    return f"{user.get('full_name')} ({user.get('email')})"


async def upsert_document(
    collection_name: str,
    query: dict[str, Any],
    document: dict[str, Any],
    *,
    kind: str | None = None,
) -> tuple[dict[str, Any], str]:
    collection = getattr(db, collection_name)
    existing = await collection.find_one(query)
    now = utc_now()
    if existing:
        payload = dict(document)
        if existing.get("created_at") is not None or payload.get("created_at") is not None:
            payload["created_at"] = existing.get("created_at") or payload.get("created_at") or now
        payload["updated_at"] = now
        if kind:
            persist_public_id_update(existing, payload, kind=kind)
        await collection.update_one({"_id": existing["_id"]}, {"$set": payload})
        return await collection.find_one({"_id": existing["_id"]}), "updated"

    payload = {"_id": ObjectId(), **document}
    payload.setdefault("created_at", now)
    payload.setdefault("updated_at", now)
    if kind:
        persist_public_id(payload, kind=kind)
    await collection.insert_one(payload)
    return await collection.find_one({"_id": payload["_id"]}), "created"


async def upsert_user(
    *,
    email: str,
    full_name: str,
    role: str,
    admin_type: str | None = None,
    extended_roles: list[str] | None = None,
    role_scope: dict[str, Any] | None = None,
    profile: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    now = utc_now()
    return await upsert_document(
        "users",
        {"email": email.lower()},
        {
            "full_name": full_name,
            "email": email.lower(),
            "hashed_password": get_password_hash(PASSWORD),
            "role": role,
            "admin_type": admin_type,
            "extended_roles": extended_roles or [],
            "role_scope": role_scope or {},
            "profile": profile or {},
            "communication_preferences": {"email": True, "in_app": True, "push": False},
            "is_active": True,
            "must_change_password": False,
            "failed_login_attempts": 0,
            "last_failed_login_at": None,
            "lockout_until": None,
            "last_active_at": now,
            "created_at": now,
            "updated_at": now,
            "schema_version": USER_SCHEMA_VERSION,
        },
    )


async def seed_users() -> dict[str, dict[str, Any]]:
    admin, _ = await upsert_user(
        email="seed.admin@capsdemo.local",
        full_name="Feature Seed Admin",
        role="admin",
        admin_type="super_admin",
        profile={"department": "Platform", "designation": "System Administrator"},
    )
    teacher, _ = await upsert_user(
        email="seed.teacher@capsdemo.local",
        full_name="Feature Seed Teacher",
        role="teacher",
        extended_roles=["class_coordinator", "club_coordinator"],
        profile={"department": "Computer Science", "designation": "Assistant Professor"},
    )
    student, _ = await upsert_user(
        email="seed.student@capsdemo.local",
        full_name="Feature Seed Student",
        role="student",
    )
    cr_one, _ = await upsert_user(
        email="seed.cr1@capsdemo.local",
        full_name="Feature Seed CR One",
        role="student",
    )
    cr_two, _ = await upsert_user(
        email="seed.cr2@capsdemo.local",
        full_name="Feature Seed CR Two",
        role="student",
    )
    return {
        "admin": admin,
        "teacher": teacher,
        "student": student,
        "cr_one": cr_one,
        "cr_two": cr_two,
    }


async def seed_academic_hierarchy() -> dict[str, dict[str, Any]]:
    now = utc_now()
    university, _ = await upsert_document(
        "universities",
        {"university_id": UNIVERSITY_CODE},
        {
            "university_id": UNIVERSITY_CODE,
            "university_code": UNIVERSITY_CODE,
            "university_name": "CAPS Demo University",
            "name": "CAPS Demo University",
            "location": "Indore",
            "is_active": True,
            "schema_version": UNIVERSITY_SCHEMA_VERSION,
        },
        kind="university",
    )
    faculty_business_id = build_faculty_business_id(FACULTY_CODE)
    faculty, _ = await upsert_document(
        "faculties",
        {"faculty_id": faculty_business_id},
        {
            "faculty_id": faculty_business_id,
            "faculty_code": FACULTY_CODE,
            "faculty_name": "Faculty of Engineering",
            "code": FACULTY_CODE,
            "name": "Faculty of Engineering",
            "university_id": object_id(university),
            "university_master_id": UNIVERSITY_CODE,
            "university_code": UNIVERSITY_CODE,
            "university_name": university["university_name"],
            "is_active": True,
            "schema_version": FACULTY_SCHEMA_VERSION,
        },
        kind="faculty",
    )
    department_business_id = build_department_business_id(faculty_code=FACULTY_CODE, department_code=DEPARTMENT_CODE)
    department, _ = await upsert_document(
        "departments",
        {"department_id": department_business_id},
        {
            "department_id": department_business_id,
            "department_code": DEPARTMENT_CODE,
            "department_name": "Department of Computer Science and Engineering",
            "code": DEPARTMENT_CODE,
            "name": "Department of Computer Science and Engineering",
            "faculty_id": object_id(faculty),
            "faculty_master_id": faculty_business_id,
            "faculty_code": FACULTY_CODE,
            "faculty_name": faculty["faculty_name"],
            "university_id": object_id(university),
            "university_master_id": UNIVERSITY_CODE,
            "university_code": UNIVERSITY_CODE,
            "university_name": university["university_name"],
            "is_active": True,
            "schema_version": DEPARTMENT_SCHEMA_VERSION,
        },
        kind="department",
    )
    program_business_id = build_program_business_id(
        faculty_code=FACULTY_CODE,
        department_code=DEPARTMENT_CODE,
        program_code=PROGRAM_CODE,
    )
    program, _ = await upsert_document(
        "programs",
        {"program_id": program_business_id},
        {
            "program_id": program_business_id,
            "program_code": PROGRAM_CODE,
            "program_name": "B.Tech Artificial Intelligence",
            "code": PROGRAM_CODE,
            "name": "B.Tech Artificial Intelligence",
            "department_id": object_id(department),
            "department_master_id": department_business_id,
            "department_code": DEPARTMENT_CODE,
            "department_name": department["department_name"],
            "faculty_id": object_id(faculty),
            "faculty_code": FACULTY_CODE,
            "faculty_name": faculty["faculty_name"],
            "university_id": object_id(university),
            "university_code": UNIVERSITY_CODE,
            "university_name": university["university_name"],
            "duration_years": DURATION_YEARS,
            "total_semesters": DURATION_YEARS * 2,
            "degree_type": "bachelor",
            "is_active": True,
            "schema_version": PROGRAM_SCHEMA_VERSION,
        },
        kind="program",
    )
    specialization_business_id = build_specialization_business_id(
        faculty_code=FACULTY_CODE,
        department_code=DEPARTMENT_CODE,
        program_code=PROGRAM_CODE,
        specialization_code=SPECIALIZATION_CODE,
    )
    specialization, _ = await upsert_document(
        "specializations",
        {"specialization_id": specialization_business_id},
        {
            "specialization_id": specialization_business_id,
            "specialization_code": SPECIALIZATION_CODE,
            "specialization_name": "Artificial Intelligence and Data Science",
            "code": SPECIALIZATION_CODE,
            "name": "Artificial Intelligence and Data Science",
            "program_id": object_id(program),
            "program_master_id": program_business_id,
            "program_code": PROGRAM_CODE,
            "program_name": program["program_name"],
            "department_id": object_id(department),
            "department_code": DEPARTMENT_CODE,
            "department_name": department["department_name"],
            "faculty_id": object_id(faculty),
            "faculty_code": FACULTY_CODE,
            "faculty_name": faculty["faculty_name"],
            "university_id": object_id(university),
            "university_code": UNIVERSITY_CODE,
            "university_name": university["university_name"],
            "is_active": True,
            "schema_version": SPECIALIZATION_SCHEMA_VERSION,
        },
        kind="specialization",
    )

    program_context = await resolve_program_academic_context(db, program=program)
    end_year = BATCH_START_YEAR + DURATION_YEARS
    batch_name, batch_code = build_batch_identity(
        program_batch_prefix="B.Tech AI",
        start_year=BATCH_START_YEAR,
        end_year=end_year,
        university_code=UNIVERSITY_CODE,
        specialization_code=SPECIALIZATION_CODE,
    )
    batch_doc = build_batch_document(
        program_context=program_context,
        specialization_id=object_id(specialization),
        name=batch_name,
        code=batch_code,
        start_year=BATCH_START_YEAR,
        end_year=end_year,
        now=now,
        auto_generated=False,
    )
    batch_doc.update(
        {
            "program_name": program["program_name"],
            "program_code": PROGRAM_CODE,
            "program_duration_years": DURATION_YEARS,
            "specialization_name": specialization["specialization_name"],
            "specialization_code": SPECIALIZATION_CODE,
            "schema_version": BATCH_SCHEMA_VERSION,
        }
    )
    batch, _ = await upsert_document("batches", {"code": batch_code, "program_id": object_id(program)}, batch_doc, kind="batch")

    semester_doc = build_semester_document(batch={**batch, "id": object_id(batch)}, semester_number=SEMESTER_NUMBER, now=now)
    semester_doc.update(
        {
            "batch_name": batch["name"],
            "batch_code": batch["code"],
            "program_name": program["program_name"],
            "program_code": PROGRAM_CODE,
            "specialization_name": specialization["specialization_name"],
            "specialization_code": SPECIALIZATION_CODE,
            "schema_version": SEMESTER_SCHEMA_VERSION,
        }
    )
    semester, _ = await upsert_document(
        "semesters",
        {"batch_id": object_id(batch), "semester_number": SEMESTER_NUMBER},
        semester_doc,
        kind="semester",
    )
    return {
        "university": university,
        "faculty": faculty,
        "department": department,
        "program": program,
        "specialization": specialization,
        "batch": batch,
        "semester": semester,
    }


async def seed_section_and_group(
    hierarchy: dict[str, dict[str, Any]],
    users: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    teacher = users["teacher"]
    batch = hierarchy["batch"]
    semester = hierarchy["semester"]
    section, _ = await upsert_document(
        "classes",
        {"name": SECTION_NAME, "batch_id": object_id(batch), "semester_id": object_id(semester)},
        {
            "name": SECTION_NAME,
            "section_name": SECTION_NAME,
            "section_code": "A",
            "batch_id": object_id(batch),
            "batch_name": batch["name"],
            "batch_code": batch["code"],
            "semester_id": object_id(semester),
            "semester_number": SEMESTER_NUMBER,
            "semester_label": semester["label"],
            "faculty_id": batch.get("faculty_id"),
            "department_id": batch.get("department_id"),
            "program_id": batch.get("program_id"),
            "specialization_id": batch.get("specialization_id"),
            "program_name": batch.get("program_name"),
            "program_code": batch.get("program_code"),
            "specialization_name": batch.get("specialization_name"),
            "specialization_code": batch.get("specialization_code"),
            "academic_year": ACADEMIC_YEAR,
            "class_coordinator_user_id": object_id(teacher),
            "class_coordinator_name": teacher["full_name"],
            "class_representatives": {
                "cr_1": {"user_id": None, "full_name": None},
                "cr_2": {"user_id": None, "full_name": None},
            },
            "mapping_locked": False,
            "student_count": 3,
            "is_active": True,
            "schema_version": CLASS_SCHEMA_VERSION,
        },
        kind="section",
    )
    await db.users.update_one(
        {"_id": teacher["_id"]},
        {
            "$set": {
                "extended_roles": ["class_coordinator", "club_coordinator"],
                "role_scope": {
                    "class_coordinator": {
                        "class_id": object_id(section),
                        "batch_id": object_id(batch),
                        "semester_id": object_id(semester),
                    }
                },
                "updated_at": utc_now(),
                "schema_version": USER_SCHEMA_VERSION,
            }
        },
    )
    users["teacher"] = await db.users.find_one({"_id": teacher["_id"]})

    group, _ = await upsert_document(
        "groups",
        {"section_id": object_id(section), "code": GROUP_CODE},
        {
            "name": "Project Team A",
            "code": GROUP_CODE,
            "section_id": object_id(section),
            "class_id": object_id(section),
            "batch_id": object_id(batch),
            "semester_id": object_id(semester),
            "program_id": batch.get("program_id"),
            "department_id": batch.get("department_id"),
            "faculty_id": batch.get("faculty_id"),
            "is_active": True,
            "schema_version": GROUP_SCHEMA_VERSION,
        },
        kind="group",
    )
    return {"section": section, "group": group}


async def seed_students(
    hierarchy: dict[str, dict[str, Any]],
    section_data: dict[str, dict[str, Any]],
    users: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    section = section_data["section"]
    group = section_data["group"]
    batch = hierarchy["batch"]
    semester = hierarchy["semester"]
    specs = [
        ("student", "CAPSDEMO-AI-001", group),
        ("cr_one", "CAPSDEMO-AI-002", group),
        ("cr_two", "CAPSDEMO-AI-003", None),
    ]
    student_docs: dict[str, dict[str, Any]] = {}
    for key, roll_number, assigned_group in specs:
        user = users[key]
        student, _ = await upsert_document(
            "students",
            {"user_id": object_id(user)},
            {
                "user_id": object_id(user),
                "full_name": user["full_name"],
                "email": user["email"],
                "roll_number": roll_number,
                "class_id": object_id(section),
                "section_id": object_id(section),
                "class_name": section["name"],
                "group_id": object_id(assigned_group) if assigned_group else None,
                "group_name": assigned_group.get("name") if assigned_group else None,
                "canonical_class_id": object_id(section),
                "canonical_group_id": object_id(assigned_group) if assigned_group else None,
                "batch_id": object_id(batch),
                "batch_name": batch["name"],
                "semester_id": object_id(semester),
                "semester_number": SEMESTER_NUMBER,
                "department_id": batch.get("department_id"),
                "program_id": batch.get("program_id"),
                "specialization_id": batch.get("specialization_id"),
                "academic_year": ACADEMIC_YEAR,
                "placement_source": "seed_feature_demo_data",
                "is_active": True,
                "schema_version": STUDENT_SCHEMA_VERSION,
            },
            kind="student",
        )
        await db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "profile": {
                        "roll_number": roll_number,
                        "class_id": object_id(section),
                        "class_name": section["name"],
                        "group_id": object_id(assigned_group) if assigned_group else None,
                        "department": "Computer Science",
                    },
                    "updated_at": utc_now(),
                    "schema_version": USER_SCHEMA_VERSION,
                }
            },
        )
        users[key] = await db.users.find_one({"_id": user["_id"]})
        enrollment, _ = await upsert_document(
            "enrollments",
            {"class_id": object_id(section), "student_id": object_id(student)},
            {
                "class_id": object_id(section),
                "student_id": object_id(student),
                "student_user_id": object_id(user),
                "student_name": user["full_name"],
                "student_email": user["email"],
                "student_roll_number": roll_number,
                "assigned_by_user_id": object_id(users["admin"]),
                "assigned_at": utc_now(),
                "is_active": True,
                "schema_version": ENROLLMENT_SCHEMA_VERSION,
            },
        )
        student_docs[key] = student
        student_docs[f"{key}_enrollment"] = enrollment

    section, _, _ = await assign_section_class_representative(
        section_id=object_id(section),
        seat="cr_1",
        student_user_id=object_id(users["cr_one"]),
    )
    section, _, _ = await assign_section_class_representative(
        section_id=object_id(section),
        seat="cr_2",
        student_user_id=object_id(users["cr_two"]),
    )
    section_data["section"] = section
    users["cr_one"] = await db.users.find_one({"_id": users["cr_one"]["_id"]})
    users["cr_two"] = await db.users.find_one({"_id": users["cr_two"]["_id"]})
    return student_docs


async def seed_academic_activity(
    hierarchy: dict[str, dict[str, Any]],
    section_data: dict[str, dict[str, Any]],
    users: dict[str, dict[str, Any]],
    students: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    now = utc_now()
    batch = hierarchy["batch"]
    semester = hierarchy["semester"]
    section = section_data["section"]
    group = section_data["group"]
    teacher = users["teacher"]
    subject, _ = await upsert_document(
        "subjects",
        {"code": SUBJECT_CODE},
        {
            "code": SUBJECT_CODE,
            "name": "Applied Machine Learning",
            "short_name": "AML",
            "description": "Demo subject for full-platform testing.",
            "weekly_limit": 4,
            "department_id": batch.get("department_id"),
            "program_id": batch.get("program_id"),
            "semester_number": SEMESTER_NUMBER,
            "credits": 4,
            "is_active": True,
            "schema_version": SUBJECT_SCHEMA_VERSION,
        },
        kind="subject",
    )
    offering, _ = await upsert_document(
        "course_offerings",
        {"section_id": object_id(section), "subject_id": object_id(subject), "teacher_user_id": object_id(teacher)},
        {
            "subject_id": object_id(subject),
            "subject_code": subject["code"],
            "subject_name": subject["name"],
            "teacher_user_id": object_id(teacher),
            "teacher_name": teacher["full_name"],
            "batch_id": object_id(batch),
            "semester_id": object_id(semester),
            "section_id": object_id(section),
            "class_id": object_id(section),
            "group_id": object_id(group),
            "academic_year": ACADEMIC_YEAR,
            "offering_type": "theory",
            "room_code": "LAB-AI-1",
            "is_active": True,
            "schema_version": COURSE_OFFERING_SCHEMA_VERSION,
        },
        kind="course_offering",
    )
    class_slot, _ = await upsert_document(
        "class_slots",
        {"course_offering_id": object_id(offering), "day": "Monday", "start_time": "09:00", "end_time": "10:00"},
        {
            "course_offering_id": object_id(offering),
            "subject_id": object_id(subject),
            "subject_code": subject["code"],
            "subject_name": subject["name"],
            "teacher_user_id": object_id(teacher),
            "teacher_name": teacher["full_name"],
            "batch_id": object_id(batch),
            "semester_id": object_id(semester),
            "section_id": object_id(section),
            "class_id": object_id(section),
            "day": "Monday",
            "start_time": "09:00",
            "end_time": "10:00",
            "room_code": "LAB-AI-1",
            "slot_type": "lecture",
            "is_active": True,
            "schema_version": CLASS_SLOT_SCHEMA_VERSION,
        },
        kind="class_slot",
    )
    timetable, _ = await upsert_document(
        "timetables",
        {"class_id": object_id(section), "semester": str(SEMESTER_NUMBER), "shift_id": "shift_1", "version": 1},
        {
            "class_id": object_id(section),
            "class_name": section["name"],
            "batch_id": object_id(batch),
            "semester_id": object_id(semester),
            "semester": str(SEMESTER_NUMBER),
            "shift_id": "shift_1",
            "version": 1,
            "status": "published",
            "days": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            "slots": _build_slots("shift_1"),
            "entries": [
                {
                    "day": "Monday",
                    "slot_key": "p1",
                    "subject_id": object_id(subject),
                    "subject_code": subject["code"],
                    "subject_name": subject["name"],
                    "teacher_user_id": object_id(teacher),
                    "teacher_name": teacher["full_name"],
                    "room_code": "LAB-AI-1",
                    "session_type": "theory",
                }
            ],
            "admin_locked": False,
            "published_at": now,
            "published_by_user_id": object_id(users["admin"]),
            "created_by_user_id": object_id(teacher),
            "is_active": True,
            "schema_version": TIMETABLE_SCHEMA_VERSION,
        },
    )
    teacher_map, _ = await upsert_document(
        "timetable_subject_teacher_maps",
        {"class_id": object_id(section), "subject_id": object_id(subject)},
        {
            "class_id": object_id(section),
            "subject_id": object_id(subject),
            "subject_code": subject["code"],
            "subject_name": subject["name"],
            "teacher_user_ids": [object_id(teacher)],
            "teacher_names": [teacher["full_name"]],
            "schema_version": TIMETABLE_SUBJECT_TEACHER_MAP_SCHEMA_VERSION,
        },
    )
    attendance, _ = await upsert_document(
        "attendance_records",
        {"class_slot_id": object_id(class_slot), "student_id": object_id(students["student"])},
        {
            "class_slot_id": object_id(class_slot),
            "student_id": object_id(students["student"]),
            "student_user_id": object_id(users["student"]),
            "student_name": users["student"]["full_name"],
            "student_roll_number": students["student"]["roll_number"],
            "class_id": object_id(section),
            "subject_id": object_id(subject),
            "subject_name": subject["name"],
            "status": "present",
            "recorded_on": iso_date(now),
            "marked_by_user_id": object_id(teacher),
            "marked_by_name": teacher["full_name"],
            "note": "Seeded present record",
            "schema_version": ATTENDANCE_RECORD_SCHEMA_VERSION,
        },
        kind="attendance_record",
    )
    return {
        "subject": subject,
        "course_offering": offering,
        "class_slot": class_slot,
        "timetable": timetable,
        "teacher_map": teacher_map,
        "attendance": attendance,
    }


async def seed_assessment_and_ai(
    hierarchy: dict[str, dict[str, Any]],
    section_data: dict[str, dict[str, Any]],
    users: dict[str, dict[str, Any]],
    students: dict[str, dict[str, Any]],
    academics: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    now = utc_now()
    section = section_data["section"]
    subject = academics["subject"]
    assignment, _ = await upsert_document(
        "assignments",
        {"title": "Feature Seed Assignment", "class_id": object_id(section)},
        {
            "title": "Feature Seed Assignment",
            "description": "Upload a short explanation of supervised learning and model validation.",
            "subject_id": object_id(subject),
            "subject_code": subject["code"],
            "subject_name": subject["name"],
            "class_id": object_id(section),
            "section_id": object_id(section),
            "batch_id": object_id(hierarchy["batch"]),
            "semester_id": object_id(hierarchy["semester"]),
            "due_date": now + timedelta(days=10),
            "total_marks": 20,
            "status": "published",
            "plagiarism_check_enabled": True,
            "created_by_user_id": object_id(users["teacher"]),
            "created_by_name": users["teacher"]["full_name"],
            "schema_version": ASSIGNMENT_SCHEMA_VERSION,
        },
        kind="assignment",
    )

    async def seed_submission(key: str, suffix: str, score: float) -> dict[str, Any]:
        user = users[key]
        student = students[key]
        submission, _ = await upsert_document(
            "submissions",
            {"assignment_id": object_id(assignment), "student_user_id": object_id(user)},
            {
                "assignment_id": object_id(assignment),
                "student_user_id": object_id(user),
                "student_profile_id": object_id(student),
                "student_name": user["full_name"],
                "student_email": user["email"],
                "student_roll_number": student["roll_number"],
                "original_filename": f"feature-seed-{suffix}.txt",
                "stored_filename": f"feature-seed-{suffix}.txt",
                "file_path": f"seed://submissions/feature-seed-{suffix}.txt",
                "mime_type": "text/plain",
                "file_size": 428,
                "text_length": 428,
                "notes": "Seeded answer for assessment and AI review testing.",
                "status": "submitted",
                "submitted_at": now - timedelta(hours=2),
                "ai_status": "completed",
                "ai_score": score,
                "ai_feedback": "Strong answer with clear terminology and useful examples.",
                "ai_provider": "seed-local",
                "ai_prompt_version": "seed-v1",
                "ai_runtime_snapshot": {"provider": "local", "model": "seed"},
                "similarity_score": 0.86 if key == "student" else 0.82,
                "extracted_text": "Supervised learning uses labelled examples to learn a mapping from inputs to outputs.",
                "extraction_quality": "high",
                "ocr_used": False,
                "ocr_confidence": None,
                "schema_version": SUBMISSION_SCHEMA_VERSION,
            },
            kind="submission",
        )
        return submission

    submission_one = await seed_submission("student", "student", 18.0)
    submission_two = await seed_submission("cr_one", "cr-one", 16.5)
    evaluation, _ = await upsert_document(
        "evaluations",
        {"submission_id": object_id(submission_one)},
        {
            "assignment_id": object_id(assignment),
            "submission_id": object_id(submission_one),
            "student_user_id": object_id(users["student"]),
            "student_name": users["student"]["full_name"],
            "teacher_user_id": object_id(users["teacher"]),
            "teacher_name": users["teacher"]["full_name"],
            "marks_awarded": 18,
            "total_marks": 20,
            "grade": "A+",
            "rubric_criteria": [
                {"name": "Concept clarity", "marks": 8, "awarded": 7},
                {"name": "Examples", "marks": 6, "awarded": 5},
                {"name": "Model validation", "marks": 6, "awarded": 6},
            ],
            "ai_score": 18.0,
            "ai_feedback": "Answer is well structured and close to the rubric.",
            "is_finalized": True,
            "released_to_student": True,
            "evaluated_at": now - timedelta(hours=1),
            "schema_version": EVALUATION_SCHEMA_VERSION,
        },
        kind="evaluation",
    )
    ai_run, _ = await upsert_document(
        "ai_evaluation_runs",
        {"evaluation_id": object_id(evaluation), "submission_id": object_id(submission_one)},
        {
            "evaluation_id": object_id(evaluation),
            "submission_id": object_id(submission_one),
            "assignment_id": object_id(assignment),
            "status": "completed",
            "provider": "seed-local",
            "model": "seed-model",
            "prompt_version": "seed-v1",
            "score": 18.0,
            "feedback": "Seeded AI run completed successfully.",
            "runtime_snapshot": {"provider_enabled": False, "mode": "seed"},
            "started_at": now - timedelta(hours=1, minutes=5),
            "completed_at": now - timedelta(hours=1),
            "schema_version": AI_EVALUATION_RUN_SCHEMA_VERSION,
        },
    )
    ai_job, _ = await upsert_document(
        "ai_jobs",
        {"idempotency_key": "seed-feature-demo-job"},
        {
            "job_type": "bulk_submission_ai",
            "idempotency_key": "seed-feature-demo-job",
            "status": "completed",
            "params": {"submission_ids": [object_id(submission_one), object_id(submission_two)]},
            "progress": {"completed": 2, "total": 2},
            "summary": {"completed": 2, "failed": 0},
            "requested_by_user_id": object_id(users["teacher"]),
            "requested_at": now - timedelta(hours=1, minutes=10),
            "started_at": now - timedelta(hours=1, minutes=5),
            "completed_at": now - timedelta(hours=1),
            "schema_version": AI_JOB_SCHEMA_VERSION,
        },
    )
    ai_chat, _ = await upsert_document(
        "ai_evaluation_chats",
        {"exam_id": "seed-exam-chat", "student_id": object_id(users["student"]), "question_id": "Q1"},
        {
            "teacher_id": object_id(users["teacher"]),
            "student_id": object_id(users["student"]),
            "exam_id": "seed-exam-chat",
            "question_id": "Q1",
            "messages": [
                {"role": "teacher", "content": "Explain why the answer deserves high marks.", "created_at": now},
                {"role": "assistant", "content": "The response covers concepts, examples, and validation.", "created_at": now},
            ],
            "created_at": now,
            "updated_at": now,
        },
    )
    similarity, _ = await upsert_document(
        "similarity_logs",
        {"source_submission_id": object_id(submission_one), "matched_submission_id": object_id(submission_two)},
        {
            "assignment_id": object_id(assignment),
            "source_submission_id": object_id(submission_one),
            "matched_submission_id": object_id(submission_two),
            "source_student_user_id": object_id(users["student"]),
            "matched_student_user_id": object_id(users["cr_one"]),
            "score": 0.86,
            "threshold": 0.8,
            "is_flagged": True,
            "evidence": "Seeded high-overlap demo pair.",
            "overlap_stats": {"shared_terms": 31, "source_terms": 58, "matched_terms": 55},
            "extraction_quality": "high",
            "review_status": "confirmed",
            "visible_to_extensions": ["class_coordinator"],
            "schema_version": SIMILARITY_LOG_SCHEMA_VERSION,
        },
        kind="similarity_log",
    )
    exam, _ = await upsert_document(
        "exams",
        {"code": "EXM-AID501-DEMO"},
        {
            "code": "EXM-AID501-DEMO",
            "title": "Applied ML Midterm Demo",
            "subject_id": object_id(subject),
            "subject_code": subject["code"],
            "subject_name": subject["name"],
            "batch_id": object_id(hierarchy["batch"]),
            "semester_id": object_id(hierarchy["semester"]),
            "section_id": object_id(section),
            "assignment_id": object_id(assignment),
            "teacher_user_id": object_id(users["teacher"]),
            "exam_type": "internal",
            "scheduled_for": now + timedelta(days=14),
            "duration_minutes": 90,
            "room_code": "LAB-AI-1",
            "max_marks": 40,
            "status": "draft",
            "schema_version": EXAM_SCHEMA_VERSION,
        },
    )
    review_ticket, _ = await upsert_document(
        "review_tickets",
        {"evaluation_id": object_id(evaluation), "requested_by_user_id": object_id(users["student"])},
        {
            "evaluation_id": object_id(evaluation),
            "submission_id": object_id(submission_one),
            "assignment_id": object_id(assignment),
            "requested_by_user_id": object_id(users["student"]),
            "requested_by_name": users["student"]["full_name"],
            "assigned_to_user_id": object_id(users["teacher"]),
            "assigned_to_name": users["teacher"]["full_name"],
            "reason": "Please review the validation section once more.",
            "status": "pending",
            "priority": "normal",
            "schema_version": REVIEW_TICKET_SCHEMA_VERSION,
        },
        kind="review_ticket",
    )
    return {
        "assignment": assignment,
        "submission_one": submission_one,
        "submission_two": submission_two,
        "evaluation": evaluation,
        "ai_run": ai_run,
        "ai_job": ai_job,
        "ai_chat": ai_chat,
        "similarity": similarity,
        "exam": exam,
        "review_ticket": review_ticket,
    }


async def seed_campus_and_ops(
    hierarchy: dict[str, dict[str, Any]],
    section_data: dict[str, dict[str, Any]],
    users: dict[str, dict[str, Any]],
    students: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    now = utc_now()
    section = section_data["section"]
    department = hierarchy["department"]
    notice, _ = await upsert_document(
        "notices",
        {"template_key": NOTICE_TEMPLATE_KEY, "scope_ref_id": object_id(section)},
        {
            "template_key": NOTICE_TEMPLATE_KEY,
            "scope": "section",
            "scope_ref_id": object_id(section),
            "scope_label": section["name"],
            "priority": "urgent",
            "title": "Feature Demo Notice",
            "message": "This seeded notice verifies communication and audience filtering.",
            "created_by_user_id": object_id(users["admin"]),
            "created_by_name": users["admin"]["full_name"],
            "expires_at": now + timedelta(days=30),
            "seen_by": [object_id(users["student"])],
            "fanout_status": "sent",
            "delivery_summary": {
                "email": {"sent": 0, "failed": 0},
                "in_app": {"sent": 3, "failed": 0},
                "schema_version": COMMUNICATION_DELIVERY_SCHEMA_VERSION,
            },
            "is_active": True,
            "schema_version": NOTICE_SCHEMA_VERSION,
        },
        kind="notice",
    )
    notification, _ = await upsert_document(
        "notifications",
        {"target_user_id": object_id(users["student"]), "title": "Feature Demo Notification"},
        {
            "target_user_id": object_id(users["student"]),
            "target_user_label": user_label(users["student"]),
            "created_by_user_id": object_id(users["admin"]),
            "created_by_label": user_label(users["admin"]),
            "title": "Feature Demo Notification",
            "message": "Seed notification for in-app notification testing.",
            "category": "notice",
            "status": "unread",
            "delivery_summary": {"in_app": "sent"},
            "schema_version": NOTIFICATION_SCHEMA_VERSION,
        },
        kind="notification",
    )
    club, _ = await upsert_document(
        "clubs",
        {"slug": "feature-seed-ai-club"},
        {
            "name": "Feature Seed AI Club",
            "slug": "feature-seed-ai-club",
            "description": "Demo club for membership, applications, events, and certificates.",
            "department_id": object_id(department),
            "department_name": department["department_name"],
            "coordinator_user_id": object_id(users["teacher"]),
            "coordinator_name": users["teacher"]["full_name"],
            "president_user_id": object_id(users["cr_one"]),
            "status": "active",
            "registration_open": True,
            "member_count": 2,
            "tags": ["ai", "demo", "seed"],
            "is_active": True,
            "schema_version": CLUB_SCHEMA_VERSION,
        },
        kind="club",
    )
    await assign_student_as_club_president(object_id(users["cr_one"]), object_id(club))
    club = await db.clubs.find_one({"_id": club["_id"]})
    users["cr_one"] = await db.users.find_one({"_id": users["cr_one"]["_id"]})
    member, _ = await upsert_document(
        "club_members",
        {"club_id": object_id(club), "student_user_id": object_id(users["student"])},
        {
            "club_id": object_id(club),
            "student_user_id": object_id(users["student"]),
            "student_name": users["student"]["full_name"],
            "student_email": users["student"]["email"],
            "role": "member",
            "status": "active",
            "joined_at": now - timedelta(days=3),
            "left_at": None,
            "schema_version": CLUB_MEMBER_SCHEMA_VERSION,
        },
        kind="club_member",
    )
    application, _ = await upsert_document(
        "club_applications",
        {"club_id": object_id(club), "student_user_id": object_id(users["cr_two"])},
        {
            "club_id": object_id(club),
            "student_user_id": object_id(users["cr_two"]),
            "student_name": users["cr_two"]["full_name"],
            "student_email": users["cr_two"]["email"],
            "motivation": "I want to help organize AI demos.",
            "status": "pending",
            "submitted_at": now - timedelta(days=1),
            "schema_version": CLUB_APPLICATION_SCHEMA_VERSION,
        },
        kind="club_application",
    )
    event, _ = await upsert_document(
        "club_events",
        {"club_id": object_id(club), "title": "Feature Seed AI Workshop"},
        {
            "club_id": object_id(club),
            "club_name": club["name"],
            "title": "Feature Seed AI Workshop",
            "description": "Hands-on model evaluation workshop for seeded testing.",
            "event_type": "workshop",
            "event_date": now + timedelta(days=7),
            "location": "Innovation Lab",
            "capacity": 40,
            "status": "open",
            "approval_required": True,
            "certificate_enabled": True,
            "created_by_user_id": object_id(users["teacher"]),
            "schema_version": CLUB_EVENT_SCHEMA_VERSION,
        },
        kind="club_event",
    )
    registration, _ = await upsert_document(
        "event_registrations",
        {"event_id": object_id(event), "student_user_id": object_id(users["student"])},
        {
            "event_id": object_id(event),
            "club_id": object_id(club),
            "student_user_id": object_id(users["student"]),
            "student_name": users["student"]["full_name"],
            "student_email": users["student"]["email"],
            "student_roll_number": students["student"]["roll_number"],
            "status": "approved",
            "attendance_status": "present",
            "certificate_issued": True,
            "registered_at": now - timedelta(days=1),
            "schema_version": EVENT_REGISTRATION_SCHEMA_VERSION,
        },
        kind="event_registration",
    )
    grievance, _ = await upsert_document(
        "grievances",
        {"title": "Feature Seed Grievance", "student_user_id": object_id(users["student"])},
        {
            "category": "academic",
            "title": "Feature Seed Grievance",
            "description": "Seeded grievance for coordinator workflow testing.",
            "student_user_id": object_id(users["student"]),
            "student_name": users["student"]["full_name"],
            "student_email": users["student"]["email"],
            "student_roll_number": students["student"]["roll_number"],
            "section_id": object_id(section),
            "section_name": section["name"],
            "department_id": object_id(department),
            "department_name": department["department_name"],
            "current_stage": "coordinator",
            "status": "open",
            "stage_due_at": now + timedelta(days=3),
            "assigned_to_user_id": object_id(users["teacher"]),
            "assigned_to_name": users["teacher"]["full_name"],
            "timeline": [
                {
                    "status": "submitted",
                    "by_user_id": object_id(users["student"]),
                    "by_name": users["student"]["full_name"],
                    "at": now,
                    "note": "Seeded grievance submitted.",
                }
            ],
            "schema_version": GRIEVANCE_SCHEMA_VERSION,
        },
        kind="grievance",
    )
    audit_log, _ = await upsert_document(
        "audit_logs",
        {"action": "seed.feature_demo_data", "entity_id": object_id(section)},
        {
            "actor_user_id": object_id(users["admin"]),
            "actor_label": user_label(users["admin"]),
            "action": "seed.feature_demo_data",
            "action_type": "system",
            "entity_type": "section",
            "entity_id": object_id(section),
            "detail": "Seeded full demo feature graph.",
            "severity": "info",
            "created_at": now,
            "schema_version": AUDIT_LOG_SCHEMA_VERSION,
        },
        kind="audit_log",
    )
    session, _ = await upsert_document(
        "user_sessions",
        {"user_id": object_id(users["student"]), "fingerprint": "seed-feature-demo-session"},
        {
            "user_id": object_id(users["student"]),
            "user_email": users["student"]["email"],
            "fingerprint": "seed-feature-demo-session",
            "ip_address": "127.0.0.1",
            "user_agent": "CAPS seed demo",
            "created_at": now - timedelta(hours=2),
            "last_seen_at": now,
            "expires_at": now + timedelta(days=7),
            "is_active": True,
            "schema_version": USER_SESSION_SCHEMA_VERSION,
        },
        kind="user_session",
    )
    return {
        "notice": notice,
        "notification": notification,
        "club": club,
        "club_member": member,
        "club_application": application,
        "club_event": event,
        "event_registration": registration,
        "grievance": grievance,
        "audit_log": audit_log,
        "user_session": session,
    }


async def seed_snapshots() -> dict[str, dict[str, Any]]:
    now = utc_now()
    analytics, _ = await upsert_document(
        "analytics_snapshots",
        {"date": iso_date(now)},
        {
            "date": iso_date(now),
            "users_total": await db.users.count_documents({}),
            "students_total": await db.students.count_documents({}),
            "programs_total": await db.programs.count_documents({}),
            "batches_total": await db.batches.count_documents({}),
            "semesters_total": await db.semesters.count_documents({}),
            "classes_total": await db.classes.count_documents({}),
            "subjects_total": await db.subjects.count_documents({}),
            "assignments_total": await db.assignments.count_documents({}),
            "submissions_total": await db.submissions.count_documents({}),
            "evaluations_total": await db.evaluations.count_documents({}),
            "similarity_flags_total": await db.similarity_logs.count_documents({"is_flagged": True}),
            "notices_total": await db.notices.count_documents({"is_active": True}),
            "clubs_total": await db.clubs.count_documents({"status": {"$in": ["active", "registration_closed"]}}),
            "club_events_total": await db.club_events.count_documents({}),
            "daily_active_users": 1,
            "login_count_24h": 1,
            "assignment_completion_pct": 100.0,
            "club_participation_pct": 66.67,
            "event_attendance_pct": 100.0,
            "pending_review_tickets": await db.review_tickets.count_documents({"status": {"$in": ["pending", "open"]}}),
            "system_errors_24h": 0,
            "review_ticket_sla_hours": 0.0,
            "active_clubs": await db.clubs.count_documents({"status": {"$in": ["active", "registration_closed"]}}),
            "events_this_week": await db.club_events.count_documents({"event_date": {"$gte": now, "$lte": now + timedelta(days=7)}}),
            "updated_at": now,
            "schema_version": ANALYTICS_SNAPSHOT_SCHEMA_VERSION,
        },
    )
    bucket = now.replace(second=0, microsecond=0).isoformat()
    health, _ = await upsert_document(
        "system_health_snapshots",
        {"bucket_minute": bucket},
        {
            "bucket_minute": bucket,
            "recorded_at": now,
            "db_status": "healthy",
            "alert_count": 0,
            "requests_15m": 3,
            "server_error_rate_pct_15m": 0.0,
            "p95_duration_ms_15m": 120.0,
            "club_requests_15m": 2,
            "club_slow_requests_15m": 0,
            "club_server_errors_15m": 0,
            "club_p95_duration_ms_15m": 95.0,
            "queued_jobs": 0,
            "running_jobs": 0,
            "failed_jobs": 0,
            "oldest_queued_age_seconds": None,
            "fallback_rate_pct_15m": 0.0,
            "similarity_candidate_count": 2,
            "payload": {"source": "seed_feature_demo_data", "db_status": "healthy"},
            "retained_rows": await db.system_health_snapshots.count_documents({}) + 1,
            "max_retained_rows": 20161,
            "is_within_retention_bound": True,
            "schema_version": SYSTEM_HEALTH_SNAPSHOT_SCHEMA_VERSION,
        },
    )
    return {"analytics_snapshot": analytics, "system_health_snapshot": health}


async def sync_read_models(
    hierarchy: dict[str, dict[str, Any]],
    section_data: dict[str, dict[str, Any]],
    academics: dict[str, dict[str, Any]],
) -> None:
    await sync_batch_read_models_for_ids(batch_ids=[object_id(hierarchy["batch"])], database=db)
    await sync_semester_read_models_for_ids(semester_ids=[object_id(hierarchy["semester"])], database=db)
    await sync_section_read_models_for_ids(section_ids=[object_id(section_data["section"])], database=db)
    await sync_course_offering_read_models_for_ids(
        offering_ids=[object_id(academics["course_offering"])],
        database=db,
    )
    await sync_class_slot_read_models_for_ids(slot_ids=[object_id(academics["class_slot"])], database=db)


async def main() -> None:
    users = await seed_users()
    hierarchy = await seed_academic_hierarchy()
    section_data = await seed_section_and_group(hierarchy, users)
    students = await seed_students(hierarchy, section_data, users)
    academics = await seed_academic_activity(hierarchy, section_data, users, students)
    assessment = await seed_assessment_and_ai(hierarchy, section_data, users, students, academics)
    campus = await seed_campus_and_ops(hierarchy, section_data, users, students)
    snapshots = await seed_snapshots()
    await sync_read_models(hierarchy, section_data, academics)

    summary = {
        "message": "Feature demo data seeded successfully.",
        "password": PASSWORD,
        "users": {
            "admin": users["admin"]["email"],
            "teacher": users["teacher"]["email"],
            "student": users["student"]["email"],
            "class_rep_one": users["cr_one"]["email"],
            "class_rep_two": users["cr_two"]["email"],
        },
        "academic_graph": {
            "university": hierarchy["university"]["university_name"],
            "faculty": hierarchy["faculty"]["faculty_name"],
            "department": hierarchy["department"]["department_name"],
            "program": hierarchy["program"]["program_name"],
            "specialization": hierarchy["specialization"]["specialization_name"],
            "batch": hierarchy["batch"]["code"],
            "semester": hierarchy["semester"]["label"],
            "section": section_data["section"]["name"],
            "group": section_data["group"]["code"],
            "subject": academics["subject"]["code"],
        },
        "feature_records": {
            "assignment_id": object_id(assessment["assignment"]),
            "exam_id": object_id(assessment["exam"]),
            "club_id": object_id(campus["club"]),
            "club_event_id": object_id(campus["club_event"]),
            "grievance_id": object_id(campus["grievance"]),
            "analytics_date": snapshots["analytics_snapshot"]["date"],
        },
        "roll_numbers": {
            "student": students["student"]["roll_number"],
            "class_rep_one": students["cr_one"]["roll_number"],
            "class_rep_two": students["cr_two"]["roll_number"],
        },
    }
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
