"""Shared academic hierarchy rules used across backend endpoints.

Authoritative hybrid model:
University -> Faculty -> Department -> Program -> (optional) Specialization
-> Batch -> Semester -> Section -> Group

Specialization remains optional at the program level. Programs may own direct
batches, or specialization-specific batches. Once a batch is bound to a
specialization, all descendants must stay inside that specialization branch.
"""

from __future__ import annotations

from typing import Any


ACADEMIC_HIERARCHY_MODEL = (
    "University -> Faculty -> Department -> Program -> "
    "(optional) Specialization -> Batch -> Semester -> Section -> Group"
)

PROGRAM_DURATION_TO_SEMESTERS = {
    1: 2,
    2: 4,
    3: 6,
    4: 8,
    5: 10,
}

DEFAULT_PROGRAM_DURATION_YEARS = 4
MIN_PROGRAM_DURATION_YEARS = min(PROGRAM_DURATION_TO_SEMESTERS)
MAX_PROGRAM_DURATION_YEARS = max(PROGRAM_DURATION_TO_SEMESTERS)


def coerce_duration_years(raw_value: Any, *, default: int = DEFAULT_PROGRAM_DURATION_YEARS) -> int:
    try:
        duration_years = int(raw_value)
    except (TypeError, ValueError):
        duration_years = default
    return max(MIN_PROGRAM_DURATION_YEARS, min(MAX_PROGRAM_DURATION_YEARS, duration_years))


def expected_total_semesters(duration_years: int | str) -> int:
    try:
        normalized_duration = int(duration_years)
    except (TypeError, ValueError) as exc:
        raise ValueError("Program duration must be an integer between 1 and 5 years.") from exc

    total_semesters = PROGRAM_DURATION_TO_SEMESTERS.get(normalized_duration)
    if total_semesters is None:
        raise ValueError("Program duration must be between 1 and 5 years.")
    return total_semesters


def validate_program_duration(duration_years: int | str) -> int:
    try:
        normalized_duration = int(duration_years)
    except (TypeError, ValueError) as exc:
        raise ValueError("Program duration must be an integer between 1 and 5 years.") from exc

    if normalized_duration not in PROGRAM_DURATION_TO_SEMESTERS:
        raise ValueError("Program duration must be between 1 and 5 years.")
    return normalized_duration


def validate_duration_and_semesters(duration_years: int | str, total_semesters: int | str | None) -> tuple[int, int]:
    normalized_duration = validate_program_duration(duration_years)
    expected_semesters = expected_total_semesters(normalized_duration)

    if total_semesters is None:
        return normalized_duration, expected_semesters

    try:
        normalized_total_semesters = int(total_semesters)
    except (TypeError, ValueError) as exc:
        raise ValueError("Total semesters must be a positive integer.") from exc

    if normalized_total_semesters != expected_semesters:
        raise ValueError(
            f"{normalized_duration}-year programs must have exactly {expected_semesters} semesters."
        )
    return normalized_duration, normalized_total_semesters


def normalize_program_duration_record(program: dict[str, Any]) -> tuple[int, int]:
    duration_years = coerce_duration_years(program.get("duration_years"))
    raw_total_semesters = program.get("total_semesters")
    if raw_total_semesters is None:
        return duration_years, expected_total_semesters(duration_years)

    try:
        return validate_duration_and_semesters(duration_years, raw_total_semesters)
    except ValueError:
        return duration_years, expected_total_semesters(duration_years)


def validate_semester_number_for_program(
    semester_number: int | str,
    *,
    program: dict[str, Any] | None = None,
    duration_years: int | str | None = None,
    total_semesters: int | str | None = None,
) -> int:
    try:
        normalized_semester_number = int(semester_number)
    except (TypeError, ValueError) as exc:
        raise ValueError("Semester number must be a positive integer.") from exc

    if normalized_semester_number < 1:
        raise ValueError("Semester number must be a positive integer.")

    if program is not None:
        resolved_duration_years, resolved_total_semesters = normalize_program_duration_record(program)
    else:
        resolved_duration_years, resolved_total_semesters = validate_duration_and_semesters(
            duration_years,
            total_semesters,
        )

    if normalized_semester_number > resolved_total_semesters:
        raise ValueError(
            "Semester number "
            f"{normalized_semester_number} exceeds the maximum of {resolved_total_semesters} "
            f"allowed for this {resolved_duration_years}-year program."
        )
    return normalized_semester_number


def validate_batch_specialization_scope(
    *,
    batch_specialization_id: str | None,
    child_specialization_id: str | None,
    child_label: str = "Section",
) -> None:
    if not batch_specialization_id and child_specialization_id:
        raise ValueError(
            f"{child_label} cannot declare a specialization when the parent batch is program-level."
        )
    if batch_specialization_id and child_specialization_id != batch_specialization_id:
        raise ValueError(
            f"{child_label} specialization must match the specialization assigned to the parent batch."
        )


def validate_section_branch(
    *,
    section: dict[str, Any],
    batch_id: str,
    semester_id: str,
) -> None:
    if section.get("batch_id") != batch_id:
        raise ValueError("section_id does not belong to provided batch_id")
    if section.get("semester_id") != semester_id:
        raise ValueError("section_id does not belong to provided semester_id")
