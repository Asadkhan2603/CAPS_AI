from __future__ import annotations

import re
from typing import Any


MASTER_HIERARCHY_MODEL = "University -> Faculty -> Department -> Program -> optional Specialization"

CANONICAL_MASTER_FIELD_CONTRACT = {
    "universities": ("university_id", "university_name"),
    "faculties": ("faculty_id", "faculty_code", "faculty_name", "university_id"),
    "departments": ("department_id", "department_code", "department_name", "faculty_id"),
    "programs": (
        "program_id",
        "program_code",
        "program_name",
        "department_id",
        "duration_years",
        "total_semesters",
        "degree_type",
    ),
    "specializations": ("specialization_id", "specialization_code", "specialization_name", "program_id"),
}

LEGACY_MASTER_FIELD_ALIASES = {
    "faculties": {"faculty_name": "name", "faculty_code": "code"},
    "departments": {"department_name": "name", "department_code": "code"},
    "programs": {"program_name": "name", "program_code": "code"},
    "specializations": {"specialization_name": "name", "specialization_code": "code"},
}

MASTER_HIERARCHY_DEPENDENCIES = {
    "university": (("faculties", "university_id", "faculties"),),
    "faculty": (
        ("departments", "faculty_id", "departments"),
        ("users", "faculty_id", "users"),
        ("classes", "faculty_id", "sections"),
    ),
    "department": (
        ("programs", "department_id", "programs"),
        ("users", "department_id", "users"),
        ("classes", "department_id", "sections"),
    ),
    "program": (
        ("specializations", "program_id", "specializations"),
        ("batches", "program_id", "batches"),
        ("semesters", "program_id", "semesters"),
        ("classes", "program_id", "sections"),
        ("users", "program_id", "users"),
    ),
    "specialization": (
        ("batches", "specialization_id", "batches"),
        ("semesters", "specialization_id", "semesters"),
        ("classes", "specialization_id", "sections"),
        ("users", "specialization_id", "users"),
    ),
}


BUSINESS_ID_PATTERNS = {
    "faculty": re.compile(r"^FAC-[A-Z0-9]+(?:-[A-Z0-9]+)*$"),
    "department": re.compile(r"^DEP-[A-Z0-9]+(?:-[A-Z0-9]+)*-[A-Z0-9]+(?:-[A-Z0-9]+)*$"),
    "program": re.compile(r"^PRG-[A-Z0-9]+(?:-[A-Z0-9]+)*-[A-Z0-9]+(?:-[A-Z0-9]+)*-[A-Z0-9]+(?:-[A-Z0-9]+)*$"),
    "specialization": re.compile(
        r"^SPC-[A-Z0-9]+(?:-[A-Z0-9]+)*-[A-Z0-9]+(?:-[A-Z0-9]+)*-[A-Z0-9]+(?:-[A-Z0-9]+)*-[A-Z0-9]+(?:-[A-Z0-9]+)*$"
    ),
}


def normalize_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def normalize_code(value: Any) -> str | None:
    text = normalize_text(value)
    return text.upper() if text else None


def coalesce_text(*values: Any) -> str | None:
    for value in values:
        text = normalize_text(value)
        if text:
            return text
    return None


def coalesce_code(*values: Any) -> str | None:
    for value in values:
        code = normalize_code(value)
        if code:
            return code
    return None


def build_faculty_business_id(faculty_code: str) -> str:
    code = normalize_code(faculty_code)
    if not code:
        raise ValueError("Faculty code is required to generate faculty_id.")
    return f"FAC-{code}"


def build_department_business_id(*, faculty_code: str, department_code: str) -> str:
    faculty = normalize_code(faculty_code)
    department = normalize_code(department_code)
    if not faculty or not department:
        raise ValueError("Faculty code and department code are required to generate department_id.")
    return f"DEP-{faculty}-{department}"


def build_program_business_id(*, faculty_code: str, department_code: str, program_code: str) -> str:
    faculty = normalize_code(faculty_code)
    department = normalize_code(department_code)
    program = normalize_code(program_code)
    if not faculty or not department or not program:
        raise ValueError("Faculty, department, and program codes are required to generate program_id.")
    return f"PRG-{faculty}-{department}-{program}"


def build_specialization_business_id(
    *,
    faculty_code: str,
    department_code: str,
    program_code: str,
    specialization_code: str,
) -> str:
    faculty = normalize_code(faculty_code)
    department = normalize_code(department_code)
    program = normalize_code(program_code)
    specialization = normalize_code(specialization_code)
    if not faculty or not department or not program or not specialization:
        raise ValueError(
            "Faculty, department, program, and specialization codes are required to generate specialization_id."
        )
    return f"SPC-{faculty}-{department}-{program}-{specialization}"


def validate_business_identifier(kind: str, value: Any) -> str:
    text = normalize_code(value)
    if not text:
        raise ValueError(f"{kind} identifier is required.")
    pattern = BUSINESS_ID_PATTERNS.get(kind)
    if pattern is None:
        raise ValueError(f"Unsupported identifier kind: {kind}")
    if not pattern.fullmatch(text):
        raise ValueError(f"{kind} identifier '{text}' does not match the expected pattern.")
    return text


def format_dependency_summary(blockers: list[dict[str, Any]]) -> str:
    if not blockers:
        return "no active descendants"
    return ", ".join(f"{item['count']} {item['label']}" for item in blockers)


async def collect_master_dependency_blockers(database: Any, entity_kind: str, entity_doc_id: str) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    for collection_name, field_name, label in MASTER_HIERARCHY_DEPENDENCIES.get(entity_kind, ()):
        collection = getattr(database, collection_name, None)
        if collection is None:
            continue
        query = {field_name: entity_doc_id}
        if collection_name != "review_tickets":
            query["is_active"] = True
        count = await collection.count_documents(query)
        if count:
            blockers.append(
                {
                    "collection": collection_name,
                    "field": field_name,
                    "label": label,
                    "count": int(count),
                }
            )
    return blockers


async def ensure_master_hierarchy_change_is_safe(
    database: Any,
    *,
    entity_kind: str,
    entity_doc_id: str,
    operation: str,
) -> None:
    blockers = await collect_master_dependency_blockers(database, entity_kind, entity_doc_id)
    if blockers:
        raise ValueError(
            f"Cannot {operation} this {entity_kind} while active descendants or dependent records still exist: "
            f"{format_dependency_summary(blockers)}."
        )
