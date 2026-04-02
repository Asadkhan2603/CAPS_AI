from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from openpyxl import Workbook


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
DEFAULT_OUTPUTS = [REPO_ROOT / "export" / "ACADEMIC_DATA.xlsx", REPO_ROOT / "exports" / "ACADEMIC_DATA.xlsx"]
CATALOG = [
    ("FOENG", "Engineering", "CSE", "Computer Science Engineering", "BTECH-CSE", "B.Tech Computer Science Engineering", "AI-DS", "Artificial Intelligence and Data Science", 4, {1: 2, 2: 2, 3: 2, 4: 2, 5: 1, 6: 1, 7: 1, 8: 1}, ["Programming Fundamentals", "Engineering Mathematics I", "Data Structures", "Digital Logic", "Database Management Systems", "Operating Systems"]),
    ("FOENG", "Engineering", "ECE", "Electronics and Communication Engineering", "BTECH-ECE", "B.Tech Electronics and Communication Engineering", "VLSI", "VLSI Systems", 4, {1: 2, 2: 2, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1, 8: 1}, ["Electronic Devices", "Circuit Theory", "Signals and Systems", "Network Analysis", "Digital Communication"]),
    ("FOMGT", "Management", "MBA", "Management Studies", "MBA", "Master of Business Administration", "MKT", "Marketing and Strategy", 2, {1: 1, 2: 1, 3: 1, 4: 1}, ["Managerial Economics", "Organizational Behavior", "Financial Management", "Marketing Management"]),
    ("FOMGT", "Management", "BBA", "Business Administration", "BBA", "Bachelor of Business Administration", "BA", "Business Analytics", 3, {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1}, ["Principles of Management", "Business Communication", "Financial Accounting", "Business Statistics", "Business Analytics Fundamentals"]),
]


def safe(v: Any) -> Any:
    if v is None or isinstance(v, (bool, int, float, str)):
        return v
    return json.dumps(v, ensure_ascii=True) if isinstance(v, (list, dict)) else str(v)


def write_book(path: Path, data: dict[str, list[dict[str, Any]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    wb = Workbook()
    first = True
    for name, rows in data.items():
        ws = wb.active if first else wb.create_sheet(title=name)
        if first:
            ws.title = name
            first = False
        headers = list(rows[0].keys()) if rows else []
        if headers:
            ws.append(headers)
        for row in rows:
            ws.append([safe(row.get(h)) for h in headers])
    wb.save(path)


def build_sample(students_per_section: int) -> dict[str, list[dict[str, Any]]]:
    institutions = [{"institution_id": "UNI-001", "institution_code": "MEDICAPS", "institution_name": "Medi-Caps University", "institution_type": "university", "status": "active", "source_model": "canonical", "notes": "Primary academic root"}]
    faculties: list[dict[str, Any]] = []
    departments: list[dict[str, Any]] = []
    programs: list[dict[str, Any]] = []
    courses: list[dict[str, Any]] = []
    specializations: list[dict[str, Any]] = []
    batches: list[dict[str, Any]] = []
    semesters: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    subjects: list[dict[str, Any]] = []
    users = [
        {"user_id": "USR-001", "full_name": "Platform Super Admin", "email": "super.admin@medicaps.example", "role_code": "ROLE-ADMIN", "admin_type": "super_admin", "department_id": None, "program_id": None, "course_id": None, "section_id": None, "is_active": True, "notes": "Global platform owner"},
        {"user_id": "USR-002", "full_name": "Academic Admin Engineering", "email": "academic.eng@medicaps.example", "role_code": "ROLE-ACADEMIC-ADMIN", "admin_type": "academic_admin", "department_id": "DEP-001", "program_id": "PRG-001", "course_id": "CRS-001", "section_id": None, "is_active": True, "notes": "Engineering hierarchy owner"},
        {"user_id": "USR-003", "full_name": "Academic Admin Management", "email": "academic.mgmt@medicaps.example", "role_code": "ROLE-ACADEMIC-ADMIN", "admin_type": "academic_admin", "department_id": "DEP-003", "program_id": "PRG-003", "course_id": "CRS-003", "section_id": None, "is_active": True, "notes": "Management hierarchy owner"},
    ]
    students: list[dict[str, Any]] = []
    enrollments: list[dict[str, Any]] = []
    offerings: list[dict[str, Any]] = []
    slots: list[dict[str, Any]] = []
    timetables: list[dict[str, Any]] = []
    ttmaps: list[dict[str, Any]] = []
    roles = [
        {"role_code": "ROLE-ADMIN", "role_name": "admin", "role_category": "platform", "scope_type": "global", "description": "Full platform administration"},
        {"role_code": "ROLE-ACADEMIC-ADMIN", "role_name": "academic_admin", "role_category": "platform", "scope_type": "academic", "description": "Academic hierarchy and onboarding administration"},
        {"role_code": "ROLE-TEACHER", "role_name": "teacher", "role_category": "delivery", "scope_type": "section_or_course", "description": "Teaching and section operations"},
        {"role_code": "ROLE-CLASS-COORDINATOR", "role_name": "class_coordinator", "role_category": "delivery", "scope_type": "section", "description": "Section coordination and mapping authority"},
        {"role_code": "ROLE-STUDENT", "role_name": "student", "role_category": "learner", "scope_type": "section", "description": "Student access scoped to a section"},
    ]
    faculty_seen: set[str] = set()
    dept_seen: set[str] = set()
    semester_id = section_id = group_id = subject_id = teacher_id = student_id = offering_id = slot_id = timetable_id = ttmap_id = 1
    for idx, (fcode, flabel, dcode, dname, pcode, pname, scode, sname, years, section_plan, subject_names) in enumerate(CATALOG, start=1):
        fac_id, dep_id, prog_id, course_id, spec_id, batch_id = f"FAC-{1 if fcode=='FOENG' else 2:03d}", f"DEP-{idx:03d}", f"PRG-{idx:03d}", f"CRS-{idx:03d}", f"SPC-{idx:03d}", f"BAT-{idx:03d}"
        if fac_id not in faculty_seen:
            faculties.append({"faculty_id": fac_id, "faculty_code": fcode, "faculty_name": f"Faculty of {flabel}", "institution_id": "UNI-001", "status": "active", "source_model": "canonical"})
            faculty_seen.add(fac_id)
        if dep_id not in dept_seen:
            departments.append({"department_id": dep_id, "department_code": dcode, "department_name": dname, "faculty_id": fac_id, "institution_id": "UNI-001", "status": "active", "source_model": "canonical"})
            dept_seen.add(dep_id)
        programs.append({"program_id": prog_id, "program_code": pcode, "program_name": pname, "department_id": dep_id, "degree_type": pcode.split("-")[0], "duration_years": years, "total_semesters": years * 2, "status": "active"})
        courses.append({"course_id": course_id, "canonical_program_id": prog_id, "course_code": pcode, "course_name": pname, "department_id": dep_id, "degree_type": pcode.split("-")[0], "duration_years": years, "total_semesters": years * 2, "status": "active", "notes": "Compatibility export sheet for canonical program records"})
        specializations.append({"specialization_id": spec_id, "specialization_code": scode, "specialization_name": sname, "program_id": prog_id, "course_id": course_id, "status": "active"})
        batches.append({"batch_id": batch_id, "batch_code": f"{pcode}-{2026}", "batch_name": f"{pname} 2026", "program_id": prog_id, "course_id": course_id, "specialization_id": spec_id, "start_year": 2026, "end_year": 2026 + years, "status": "active"})
        coordinator_id = f"USR-{teacher_id + 3:03d}"
        users.append({"user_id": coordinator_id, "full_name": f"{dcode} Coordinator", "email": f"{dcode.lower()}.coordinator@medicaps.example", "role_code": "ROLE-TEACHER", "admin_type": None, "department_id": dep_id, "program_id": prog_id, "course_id": course_id, "section_id": None, "is_active": True, "notes": "Section coordinator"})
        teacher_pool = [coordinator_id]
        teacher_id += 4
        for label in ("alpha", "beta"):
            uid = f"USR-{teacher_id:03d}"
            users.append({"user_id": uid, "full_name": f"{dcode} Faculty {label.title()}", "email": f"{dcode.lower()}.{label}@medicaps.example", "role_code": "ROLE-TEACHER", "admin_type": None, "department_id": dep_id, "program_id": prog_id, "course_id": course_id, "section_id": None, "is_active": True, "notes": "Teaching faculty"})
            teacher_pool.append(uid)
            teacher_id += 1
        sem_map: dict[int, str] = {}
        for sem_no in range(1, years * 2 + 1):
            sid = f"SEM-{semester_id:03d}"
            semesters.append({"semester_id": sid, "semester_code": f"{batch_id.replace('-', '')}-SEM{sem_no}", "semester_label": f"Semester {sem_no}", "batch_id": batch_id, "semester_number": sem_no, "status": "active"})
            sem_map[sem_no] = sid
            semester_id += 1
        for sem_no, count in section_plan.items():
            for section_no in range(count):
                sec = f"SEC-{section_id:03d}"
                sections.append({"section_id": sec, "section_code": f"SEC-{dcode}-S{sem_no}-{chr(65 + section_no)}", "section_name": f"Section {chr(65 + section_no)}", "program_id": prog_id, "course_id": course_id, "specialization_id": spec_id, "batch_id": batch_id, "semester_id": sem_map[sem_no], "department_id": dep_id, "faculty_id": fac_id, "canonical_storage_collection": "classes", "compatibility_class_id": sec, "status": "active"})
                if users[-3]["program_id"] == prog_id and users[-3]["section_id"] is None:
                    users[-3]["section_id"] = sec
                for g in range(1, (3 if sem_no <= 2 and dcode in {"CSE", "ECE"} else 2)):
                    groups.append({"group_id": f"GRP-{group_id:03d}", "group_code": f"{sec.replace('-', '')}-G{g}", "group_name": f"Group {g}", "section_id": sec, "status": "active"})
                    group_id += 1
                section_id += 1
                for n in range(1, students_per_section + 1):
                    suid = f"USR-{100 + student_id:03d}"
                    display = f"Student {student_id:03d}"
                    users.append({"user_id": suid, "full_name": display, "email": f"student.{student_id:03d}@medicaps.example", "role_code": "ROLE-STUDENT", "admin_type": None, "department_id": dep_id, "program_id": prog_id, "course_id": course_id, "section_id": sec, "is_active": True, "notes": "Student account"})
                    students.append({"student_id": f"STU-{student_id:03d}", "user_id": suid, "roll_number": f"{dcode}{student_id:05d}", "enrollment_number": f"ENR{student_id:05d}", "full_name": display, "department_id": dep_id, "program_id": prog_id, "course_id": course_id, "section_id": sec, "compatibility_class_id": sec, "status": "active"})
                    enrollments.append({"enrollment_id": f"ENR-{student_id:03d}", "student_id": f"STU-{student_id:03d}", "section_id": sec, "compatibility_class_id": sec, "semester_id": sem_map[sem_no], "batch_id": batch_id, "status": "active", "notes": "Primary enrollment"})
                    student_id += 1
        for pos, name in enumerate(subject_names, start=1):
            sem_no = min(pos, years * 2)
            sub = f"SUB-{subject_id:03d}"
            subjects.append({"subject_id": sub, "subject_code": f"{dcode}{100 + pos}", "subject_name": name, "program_id": prog_id, "course_id": course_id, "semester_id": sem_map[sem_no], "department_id": dep_id, "status": "active"})
            for sec in [row for row in sections if row["program_id"] == prog_id and row["semester_id"] == sem_map[sem_no]]:
                tid = teacher_pool[(pos - 1) % len(teacher_pool)]
                off = f"OFF-{offering_id:03d}"
                offerings.append({"offering_id": off, "subject_id": sub, "section_id": sec["section_id"], "program_id": prog_id, "course_id": course_id, "semester_id": sem_map[sem_no], "teacher_user_id": tid, "status": "active"})
                slt = f"SLOT-{slot_id:03d}"
                slots.append({"class_slot_id": slt, "course_offering_id": off, "section_id": sec["section_id"], "day": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"][(offering_id - 1) % 5], "start_time": ["09:00", "10:15", "11:30", "13:30", "14:45"][(offering_id - 1) % 5], "end_time": ["10:00", "11:15", "12:30", "14:30", "15:45"][(offering_id - 1) % 5], "room_code": f"R-{100 + ((offering_id - 1) % 25)}", "status": "active"})
                tbl = f"TBL-{timetable_id:03d}"
                timetables.append({"timetable_id": tbl, "timetable_code": f"TT-{sec['section_code']}", "section_id": sec["section_id"], "semester_id": sem_map[sem_no], "batch_id": batch_id, "status": "active"})
                ttmaps.append({"timetable_map_id": f"TTM-{ttmap_id:03d}", "timetable_id": tbl, "class_slot_id": slt, "subject_id": sub, "teacher_user_id": tid, "section_id": sec["section_id"], "status": "active"})
                offering_id += 1
                slot_id += 1
                timetable_id += 1
                ttmap_id += 1
            subject_id += 1
    mappings = [{"mapping_id": f"MAP-{i + 1:03d}", "mapping_type": "user_role" if row["role_code"] != "ROLE-STUDENT" else "student_section", "user_id": row["user_id"], "role_code": row["role_code"] if row["role_code"] != "ROLE-TEACHER" or "Coordinator" not in str(row["full_name"]) else "ROLE-CLASS-COORDINATOR", "section_id": row["section_id"], "program_id": row["program_id"], "course_id": row["course_id"], "department_id": row["department_id"], "scope_entity": "section" if row["section_id"] else "global", "scope_ref_id": row["section_id"] or "GLOBAL", "status": "active" if row["is_active"] else "inactive", "notes": row["notes"]} for i, row in enumerate(users)]
    return {"Institutions": institutions, "Faculties": faculties, "Departments": departments, "Programs": programs, "Courses": courses, "Specializations": specializations, "Batches": batches, "Semesters": semesters, "Sections": sections, "Groups": groups, "Users": users, "Students": students, "Enrollments": enrollments, "Subjects": subjects, "CourseOfferings": offerings, "ClassSlots": slots, "Timetables": timetables, "TimetableSubjectTeacherMaps": ttmaps, "Roles": roles, "Mappings": mappings}


async def build_db() -> dict[str, list[dict[str, Any]]]:
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    from app.core.database import db  # type: ignore
    async def rows(name: str, fields: dict[str, int]) -> list[dict[str, Any]]:
        return await getattr(db, name).find({}, fields).to_list(length=10000)
    universities = await rows("universities", {"university_id": 1, "university_name": 1, "university_code": 1, "name": 1, "code": 1, "is_active": 1})
    faculties = await rows("faculties", {"faculty_id": 1, "faculty_code": 1, "faculty_name": 1, "name": 1, "code": 1, "university_master_id": 1, "university_id": 1, "is_active": 1})
    departments = await rows("departments", {"department_id": 1, "department_code": 1, "department_name": 1, "name": 1, "code": 1, "faculty_master_id": 1, "faculty_id": 1, "university_master_id": 1, "is_active": 1})
    programs = await rows("programs", {"program_id": 1, "program_code": 1, "program_name": 1, "name": 1, "code": 1, "department_master_id": 1, "department_id": 1, "duration_years": 1, "total_semesters": 1, "degree_type": 1, "is_active": 1})
    specializations = await rows("specializations", {"specialization_id": 1, "specialization_code": 1, "specialization_name": 1, "name": 1, "code": 1, "program_master_id": 1, "program_id": 1, "is_active": 1})
    batches = await rows("batches", {"_id": 1, "name": 1, "code": 1, "program_id": 1, "specialization_id": 1, "start_year": 1, "end_year": 1, "is_active": 1})
    semesters = await rows("semesters", {"_id": 1, "label": 1, "code": 1, "batch_id": 1, "semester_number": 1, "is_active": 1})
    sections = await rows("classes", {"_id": 1, "name": 1, "code": 1, "program_id": 1, "specialization_id": 1, "batch_id": 1, "semester_id": 1, "department_id": 1, "faculty_id": 1, "is_active": 1})
    groups = await rows("groups", {"_id": 1, "name": 1, "code": 1, "section_id": 1, "is_active": 1})
    users = await rows("users", {"_id": 1, "full_name": 1, "email": 1, "role": 1, "admin_type": 1, "department_id": 1, "program_id": 1, "class_id": 1, "is_active": 1})
    students = await rows("students", {"_id": 1, "user_id": 1, "roll_number": 1, "enrollment_number": 1, "full_name": 1, "department_id": 1, "program_id": 1, "class_id": 1, "is_active": 1})
    enrollments = await rows("enrollments", {"_id": 1, "student_id": 1, "class_id": 1, "semester_id": 1, "batch_id": 1, "is_active": 1})
    subjects = await rows("subjects", {"_id": 1, "code": 1, "name": 1, "program_id": 1, "semester_id": 1, "department_id": 1, "is_active": 1})
    offerings = await rows("course_offerings", {"_id": 1, "subject_id": 1, "section_id": 1, "semester_id": 1, "teacher_user_id": 1, "is_active": 1})
    slots = await rows("class_slots", {"_id": 1, "course_offering_id": 1, "day": 1, "start_time": 1, "end_time": 1, "room_code": 1, "is_active": 1})
    timetables = await rows("timetables", {"_id": 1, "class_id": 1, "semester": 1, "status": 1, "is_active": 1})
    ttmaps = await rows("timetable_subject_teacher_maps", {"_id": 1, "class_id": 1, "subject_id": 1, "teacher_user_id": 1, "is_active": 1})
    roles = sorted({str(r.get("role", "")).strip().lower() for r in users if r.get("role")})
    return {
        "Institutions": [{"institution_id": r.get("university_id") or str(r["_id"]), "institution_code": r.get("university_code") or r.get("code"), "institution_name": r.get("university_name") or r.get("name"), "institution_type": "university", "status": "active" if r.get("is_active", True) else "inactive", "source_model": "db", "notes": ""} for r in universities],
        "Faculties": [{"faculty_id": r.get("faculty_id") or str(r["_id"]), "faculty_code": r.get("faculty_code") or r.get("code"), "faculty_name": r.get("faculty_name") or r.get("name"), "institution_id": r.get("university_master_id") or r.get("university_id"), "status": "active" if r.get("is_active", True) else "inactive", "source_model": "db"} for r in faculties],
        "Departments": [{"department_id": r.get("department_id") or str(r["_id"]), "department_code": r.get("department_code") or r.get("code"), "department_name": r.get("department_name") or r.get("name"), "faculty_id": r.get("faculty_master_id") or r.get("faculty_id"), "institution_id": r.get("university_master_id"), "status": "active" if r.get("is_active", True) else "inactive", "source_model": "db"} for r in departments],
        "Programs": [{"program_id": r.get("program_id") or str(r["_id"]), "program_code": r.get("program_code") or r.get("code"), "program_name": r.get("program_name") or r.get("name"), "department_id": r.get("department_master_id") or r.get("department_id"), "degree_type": r.get("degree_type"), "duration_years": r.get("duration_years"), "total_semesters": r.get("total_semesters"), "status": "active" if r.get("is_active", True) else "inactive"} for r in programs],
        "Specializations": [{"specialization_id": r.get("specialization_id") or str(r["_id"]), "specialization_code": r.get("specialization_code") or r.get("code"), "specialization_name": r.get("specialization_name") or r.get("name"), "program_id": r.get("program_master_id") or r.get("program_id"), "course_id": None, "status": "active" if r.get("is_active", True) else "inactive"} for r in specializations],
        "Batches": [{"batch_id": str(r["_id"]), "batch_code": r.get("code"), "batch_name": r.get("name"), "program_id": r.get("program_id"), "course_id": None, "specialization_id": r.get("specialization_id"), "start_year": r.get("start_year"), "end_year": r.get("end_year"), "status": "active" if r.get("is_active", True) else "inactive"} for r in batches],
        "Semesters": [{"semester_id": str(r["_id"]), "semester_code": r.get("code"), "semester_label": r.get("label"), "batch_id": r.get("batch_id"), "semester_number": r.get("semester_number"), "status": "active" if r.get("is_active", True) else "inactive"} for r in semesters],
        "Sections": [{"section_id": str(r["_id"]), "section_code": r.get("code"), "section_name": r.get("name"), "program_id": r.get("program_id"), "course_id": None, "specialization_id": r.get("specialization_id"), "batch_id": r.get("batch_id"), "semester_id": r.get("semester_id"), "department_id": r.get("department_id"), "faculty_id": r.get("faculty_id"), "canonical_storage_collection": "classes", "compatibility_class_id": str(r["_id"]), "status": "active" if r.get("is_active", True) else "inactive"} for r in sections],
        "Groups": [{"group_id": str(r["_id"]), "group_code": r.get("code"), "group_name": r.get("name"), "section_id": r.get("section_id"), "status": "active" if r.get("is_active", True) else "inactive"} for r in groups],
        "Users": [{"user_id": str(r["_id"]), "full_name": r.get("full_name"), "email": r.get("email"), "role_code": f"ROLE-{str(r.get('role', 'unknown')).upper().replace('-', '_')}", "admin_type": r.get("admin_type"), "department_id": r.get("department_id"), "program_id": r.get("program_id"), "course_id": None, "section_id": r.get("class_id"), "is_active": bool(r.get("is_active", True)), "notes": "Derived from live user records"} for r in users],
        "Students": [{"student_id": str(r["_id"]), "user_id": r.get("user_id"), "roll_number": r.get("roll_number"), "enrollment_number": r.get("enrollment_number"), "full_name": r.get("full_name"), "department_id": r.get("department_id"), "program_id": r.get("program_id"), "course_id": None, "section_id": r.get("class_id"), "compatibility_class_id": r.get("class_id"), "status": "active" if r.get("is_active", True) else "inactive"} for r in students],
        "Enrollments": [{"enrollment_id": str(r["_id"]), "student_id": r.get("student_id"), "section_id": r.get("class_id"), "compatibility_class_id": r.get("class_id"), "semester_id": r.get("semester_id"), "batch_id": r.get("batch_id"), "status": "active" if r.get("is_active", True) else "inactive", "notes": ""} for r in enrollments],
        "Subjects": [{"subject_id": str(r["_id"]), "subject_code": r.get("code"), "subject_name": r.get("name"), "program_id": r.get("program_id"), "course_id": None, "semester_id": r.get("semester_id"), "department_id": r.get("department_id"), "status": "active" if r.get("is_active", True) else "inactive"} for r in subjects],
        "CourseOfferings": [{"offering_id": str(r["_id"]), "subject_id": r.get("subject_id"), "section_id": r.get("section_id"), "program_id": None, "course_id": None, "semester_id": r.get("semester_id"), "teacher_user_id": r.get("teacher_user_id"), "status": "active" if r.get("is_active", True) else "inactive"} for r in offerings],
        "ClassSlots": [{"class_slot_id": str(r["_id"]), "course_offering_id": r.get("course_offering_id"), "section_id": None, "day": r.get("day"), "start_time": r.get("start_time"), "end_time": r.get("end_time"), "room_code": r.get("room_code"), "status": "active" if r.get("is_active", True) else "inactive"} for r in slots],
        "Timetables": [{"timetable_id": str(r["_id"]), "timetable_code": f"TT-{r['_id']}", "section_id": r.get("class_id"), "semester_id": r.get("semester"), "batch_id": None, "status": r.get("status") or ("active" if r.get("is_active", True) else "inactive")} for r in timetables],
        "TimetableSubjectTeacherMaps": [{"timetable_map_id": str(r["_id"]), "timetable_id": None, "class_slot_id": None, "subject_id": r.get("subject_id"), "teacher_user_id": r.get("teacher_user_id"), "section_id": r.get("class_id"), "status": "active" if r.get("is_active", True) else "inactive"} for r in ttmaps],
        "Roles": [{"role_code": f"ROLE-{name.upper().replace('-', '_')}", "role_name": name, "role_category": "db", "scope_type": "mixed", "description": "Derived from live user roles"} for name in roles],
        "Mappings": [{"mapping_id": f"MAP-{i + 1:03d}", "mapping_type": "user_role", "user_id": str(r["_id"]), "role_code": f"ROLE-{str(r.get('role', 'unknown')).upper().replace('-', '_')}", "section_id": r.get("class_id"), "program_id": r.get("program_id"), "course_id": None, "department_id": r.get("department_id"), "scope_entity": "section" if r.get("class_id") else "global", "scope_ref_id": r.get("class_id") or "GLOBAL", "status": "active" if r.get("is_active", True) else "inactive", "notes": "Derived from live user records"} for i, r in enumerate(users)],
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Generate academic export workbook from sample data or live Mongo collections.")
    parser.add_argument("--source", choices=("sample", "db"), default="sample")
    parser.add_argument("--students-per-section", type=int, default=4)
    parser.add_argument("--output", action="append")
    args = parser.parse_args()
    data = build_sample(args.students_per_section) if args.source == "sample" else await build_db()
    for target in ([Path(p) for p in args.output] if args.output else DEFAULT_OUTPUTS):
        write_book(target, data)
        print(target)


if __name__ == "__main__":
    asyncio.run(main())
