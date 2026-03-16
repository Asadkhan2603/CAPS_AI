import argparse
import asyncio
from collections import Counter
import json
from pathlib import Path
import sys

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import db
from app.core.mongo import parse_object_id
from app.services.academic_hierarchy import (
    ACADEMIC_HIERARCHY_MODEL,
    validate_semester_number_for_program,
    validate_batch_specialization_scope,
    validate_duration_and_semesters,
    validate_section_branch,
)


async def _find_one_by_id(collection, value):
    if value is None:
        return None
    try:
        return await collection.find_one({"_id": parse_object_id(value)})
    except Exception:
        return await collection.find_one({"_id": value})


async def audit_program_durations() -> list[dict]:
    findings = []
    async for program in db.programs.find({}, {"duration_years": 1, "total_semesters": 1, "name": 1, "code": 1}):
        try:
            validate_duration_and_semesters(program.get("duration_years"), program.get("total_semesters"))
        except ValueError as exc:
            findings.append(
                {
                    "program_id": str(program["_id"]),
                    "program_name": program.get("name"),
                    "program_code": program.get("code"),
                    "detail": str(exc),
                }
            )
    return findings


async def audit_semester_bounds() -> list[dict]:
    findings = []
    async for semester in db.semesters.find({}, {"batch_id": 1, "semester_number": 1, "label": 1, "program_id": 1}):
        batch = await _find_one_by_id(db.batches, semester.get("batch_id"))
        if not batch:
            findings.append(
                {
                    "semester_id": str(semester["_id"]),
                    "semester_label": semester.get("label"),
                    "detail": "Parent batch not found.",
                }
            )
            continue
        program = await _find_one_by_id(db.programs, batch.get("program_id"))
        if not program:
            findings.append(
                {
                    "semester_id": str(semester["_id"]),
                    "semester_label": semester.get("label"),
                    "batch_id": str(batch["_id"]),
                    "detail": "Parent program not found for batch.",
                }
            )
            continue
        try:
            validate_semester_number_for_program(semester.get("semester_number"), program=program)
        except ValueError as exc:
            findings.append(
                {
                    "semester_id": str(semester["_id"]),
                    "semester_label": semester.get("label"),
                    "batch_id": str(batch["_id"]),
                    "program_id": str(program["_id"]),
                    "detail": str(exc),
                }
            )
    return findings


async def audit_orphaned_sections() -> list[dict]:
    findings = []
    async for section in db.classes.find({}, {"batch_id": 1, "semester_id": 1, "name": 1}):
        batch = await _find_one_by_id(db.batches, section.get("batch_id"))
        semester = await _find_one_by_id(db.semesters, section.get("semester_id"))
        if batch and semester:
            continue
        detail_parts = []
        if not batch:
            detail_parts.append("Parent batch not found.")
        if not section.get("semester_id"):
            detail_parts.append("Section is missing semester_id.")
        elif not semester:
            detail_parts.append("Parent semester not found.")
        findings.append(
            {
                "section_id": str(section["_id"]),
                "section_name": section.get("name"),
                "detail": " ".join(detail_parts),
            }
        )
    return findings


async def audit_section_branch_integrity() -> list[dict]:
    findings = []
    async for section in db.classes.find({}, {"batch_id": 1, "semester_id": 1, "program_id": 1, "name": 1}):
        batch = await _find_one_by_id(db.batches, section.get("batch_id"))
        semester = await _find_one_by_id(db.semesters, section.get("semester_id"))
        if not batch or not semester:
            continue
        detail_messages: list[str] = []
        if semester.get("batch_id") != section.get("batch_id"):
            detail_messages.append("section.semester_id points to a semester in a different batch.")
        if batch.get("program_id") and section.get("program_id") and batch.get("program_id") != section.get("program_id"):
            detail_messages.append("section.program_id does not match the parent batch program.")
        if detail_messages:
            findings.append(
                {
                    "section_id": str(section["_id"]),
                    "section_name": section.get("name"),
                    "batch_id": str(batch["_id"]),
                    "semester_id": str(semester["_id"]),
                    "detail": " ".join(detail_messages),
                }
            )
    return findings


async def audit_section_specializations() -> list[dict]:
    findings = []
    async for section in db.classes.find({}, {"batch_id": 1, "specialization_id": 1, "name": 1}):
        batch_id = section.get("batch_id")
        if not batch_id:
            continue
        batch = await _find_one_by_id(db.batches, batch_id)
        if not batch:
            findings.append(
                {
                    "section_id": str(section["_id"]),
                    "section_name": section.get("name"),
                    "detail": "Parent batch not found.",
                }
            )
            continue
        try:
            validate_batch_specialization_scope(
                batch_specialization_id=batch.get("specialization_id"),
                child_specialization_id=section.get("specialization_id"),
            )
        except ValueError as exc:
            findings.append(
                {
                    "section_id": str(section["_id"]),
                    "section_name": section.get("name"),
                    "batch_id": str(batch["_id"]),
                    "detail": str(exc),
                }
            )
    return findings


async def audit_course_offerings() -> list[dict]:
    findings = []
    async for offering in db.course_offerings.find({}, {"section_id": 1, "batch_id": 1, "semester_id": 1, "subject_id": 1}):
        section = await _find_one_by_id(db.classes, offering.get("section_id"))
        if not section:
            findings.append(
                {
                    "offering_id": str(offering["_id"]),
                    "detail": "Section not found.",
                }
            )
            continue
        try:
            validate_section_branch(
                section=section,
                batch_id=offering.get("batch_id"),
                semester_id=offering.get("semester_id"),
            )
        except ValueError as exc:
            findings.append(
                {
                    "offering_id": str(offering["_id"]),
                    "section_id": str(section["_id"]),
                    "detail": str(exc),
                }
            )
    return findings


async def run_audit() -> dict[str, list[dict]]:
    (
        duration_findings,
        semester_bound_findings,
        orphaned_section_findings,
        section_branch_findings,
        section_specialization_findings,
        offering_findings,
    ) = await asyncio.gather(
        audit_program_durations(),
        audit_semester_bounds(),
        audit_orphaned_sections(),
        audit_section_branch_integrity(),
        audit_section_specializations(),
        audit_course_offerings(),
    )

    return {
        "program_duration_findings": duration_findings,
        "semester_bound_findings": semester_bound_findings,
        "orphaned_section_findings": orphaned_section_findings,
        "section_branch_findings": section_branch_findings,
        "section_specialization_findings": section_specialization_findings,
        "course_offering_findings": offering_findings,
    }


def summarize_findings(findings: dict[str, list[dict]]) -> Counter[str]:
    return Counter({key: len(value) for key, value in findings.items()})


def total_findings(summary: Counter[str]) -> int:
    return sum(summary.values())


def render_human_readable(findings: dict[str, list[dict]], summary: Counter[str]) -> str:
    lines = [
        "Academic hierarchy model:",
        f"  {ACADEMIC_HIERARCHY_MODEL}",
        "",
        "Integrity summary:",
    ]
    for key, value in summary.items():
        lines.append(f"  {key}: {value}")

    labels = {
        "program_duration_findings": "Invalid program duration / semester rows",
        "semester_bound_findings": "Semester rows outside their parent program limit",
        "orphaned_section_findings": "Orphaned or incomplete sections",
        "section_branch_findings": "Section branch mismatches",
        "section_specialization_findings": "Section specialization mismatches",
        "course_offering_findings": "Course offering branch mismatches",
    }
    for key, label in labels.items():
        category_findings = findings.get(key) or []
        if not category_findings:
            continue
        lines.append("")
        lines.append(f"{label}:")
        for finding in category_findings:
            lines.append(f"  {finding}")
    return "\n".join(lines)


async def main() -> None:
    parser = argparse.ArgumentParser(description="Audit academic hierarchy integrity across programs, semesters, sections, and course offerings.")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output.")
    parser.add_argument("--fail-on-findings", action="store_true", help="Exit with status 1 if any integrity findings are present.")
    args = parser.parse_args()

    findings = await run_audit()
    summary = summarize_findings(findings)

    if args.json:
        print(json.dumps({"model": ACADEMIC_HIERARCHY_MODEL, "summary": dict(summary), "findings": findings}, indent=2))
    else:
        print(render_human_readable(findings, summary))

    if args.fail_on_findings and total_findings(summary):
        raise SystemExit(1)


if __name__ == "__main__":
    asyncio.run(main())
