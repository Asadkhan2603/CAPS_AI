from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from fastapi import HTTPException, status

from app.core.mongo import parse_object_id

SEMESTERS_PER_YEAR = 2


def resolve_batch_years(*, start_year: int | None, end_year: int | None, duration_years: int) -> tuple[int | None, int | None]:
    if start_year is not None and end_year is None:
        end_year = start_year + duration_years
    elif end_year is not None and start_year is None:
        start_year = end_year - duration_years

    if start_year is not None and end_year is not None:
        if end_year < start_year:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End year cannot be earlier than start year")
        expected_end_year = start_year + duration_years
        if end_year != expected_end_year:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch span must match program duration of {duration_years} years.",
            )

    return start_year, end_year


def build_batch_span_label(start_year: int | None, end_year: int | None) -> str | None:
    if start_year is None or end_year is None:
        return None
    return f"{start_year}-{end_year}"


def build_program_batch_prefix(*, program_name: str | None, program_code: str | None, university_code: str | None = None) -> str | None:
    if program_name:
        raw_name = re.split(r"\s*(?:\(|-)\s*", str(program_name).strip(), maxsplit=1)[0]
        cleaned_name = re.sub(r"\s+", " ", raw_name).strip()
        if cleaned_name:
            return cleaned_name

    if program_code:
        cleaned_code = str(program_code).strip().upper()
        if cleaned_code:
            return cleaned_code

    if university_code:
        cleaned_university_code = str(university_code).strip().upper()
        if cleaned_university_code:
            return cleaned_university_code

    return None


def build_batch_identity(*, program_batch_prefix: str | None, start_year: int, end_year: int, university_code: str | None = None) -> tuple[str, str]:
    start_short = str(start_year)[-2:]
    end_short = str(end_year)[-2:]
    span_label = build_batch_span_label(start_year, end_year) or str(start_year)

    name = f"Batch {span_label}"
    code_parts = [str(program_batch_prefix or "").strip(), f"B{start_short}-{end_short}"]
    code = "-".join(part for part in code_parts if part)
    if not code and university_code:
        code = f"{str(university_code).strip().upper()}-B{start_short}-{end_short}"
    if not code:
        code = f"B{start_short}-{end_short}"
    return name, code


def build_semester_academic_year(*, batch_start_year: int | None, semester_number: int) -> tuple[int | None, int | None, str | None]:
    if batch_start_year is None:
        return None, None, None
    academic_year_start = batch_start_year + ((semester_number - 1) // SEMESTERS_PER_YEAR)
    academic_year_end = academic_year_start + 1
    return academic_year_start, academic_year_end, f"{academic_year_start}-{academic_year_end}"


def build_semester_label(*, semester_number: int, batch_start_year: int | None) -> str:
    _academic_year_start, _academic_year_end, academic_year_label = build_semester_academic_year(
        batch_start_year=batch_start_year,
        semester_number=semester_number,
    )
    if academic_year_label:
        return f"Semester {semester_number} ({academic_year_label})"
    return f"Semester {semester_number}"


async def resolve_program_academic_context(db, *, program: dict[str, Any]) -> dict[str, Any]:
    department = None
    faculty = None

    department_id = program.get("department_id")
    departments = getattr(db, "departments", None)
    faculties = getattr(db, "faculties", None)
    if department_id and departments is not None:
        department = await db.departments.find_one({"_id": parse_object_id(department_id)})

    faculty_id = department.get("faculty_id") if department else None
    if faculty_id and faculties is not None:
        faculty = await db.faculties.find_one({"_id": parse_object_id(faculty_id)})

    university_name = None
    university_code = None
    if department:
        university_name = department.get("university_name") or None
        university_code = department.get("university_code") or None
    if faculty:
        university_name = university_name or faculty.get("university_name") or None
        university_code = university_code or faculty.get("university_code") or None

    return {
        "faculty_id": faculty_id,
        "department_id": department_id,
        "program_id": str(program.get("_id")) if program.get("_id") else program.get("id"),
        "program_name": str(program.get("name") or "").strip() or None,
        "program_code": str(program.get("code") or "").strip().upper() or None,
        "program_batch_prefix": build_program_batch_prefix(
            program_name=program.get("name"),
            program_code=program.get("code"),
            university_code=university_code,
        ),
        "university_name": university_name,
        "university_code": str(university_code).strip().upper() if university_code else None,
    }


def build_batch_document(
    *,
    program_context: dict[str, Any],
    specialization_id: str | None,
    name: str,
    code: str,
    start_year: int | None,
    end_year: int | None,
    now: datetime,
    auto_generated: bool = False,
) -> dict[str, Any]:
    return {
        "faculty_id": program_context.get("faculty_id"),
        "department_id": program_context.get("department_id"),
        "program_id": program_context.get("program_id"),
        "specialization_id": specialization_id,
        "name": name.strip(),
        "code": code.strip(),
        "start_year": start_year,
        "end_year": end_year,
        "academic_span_label": build_batch_span_label(start_year, end_year),
        "university_name": program_context.get("university_name"),
        "university_code": program_context.get("university_code"),
        "is_active": True,
        "auto_generated": auto_generated,
        "created_at": now,
    }


def build_semester_document(*, batch: dict[str, Any], semester_number: int, now: datetime) -> dict[str, Any]:
    academic_year_start, academic_year_end, academic_year_label = build_semester_academic_year(
        batch_start_year=batch.get("start_year"),
        semester_number=semester_number,
    )
    return {
        "batch_id": batch["id"],
        "faculty_id": batch.get("faculty_id"),
        "department_id": batch.get("department_id"),
        "program_id": batch.get("program_id"),
        "specialization_id": batch.get("specialization_id"),
        "semester_number": semester_number,
        "label": build_semester_label(semester_number=semester_number, batch_start_year=batch.get("start_year")),
        "academic_year_start": academic_year_start,
        "academic_year_end": academic_year_end,
        "academic_year_label": academic_year_label,
        "university_name": batch.get("university_name"),
        "university_code": batch.get("university_code"),
        "is_active": True,
        "created_at": now,
    }

