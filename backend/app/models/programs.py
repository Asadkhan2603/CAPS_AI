from typing import Any, Dict

from app.core.schema_versions import PROGRAM_SCHEMA_VERSION, normalize_schema_version


def _normalize_duration_years(raw_value: Any) -> int:
    try:
        duration_years = int(raw_value)
    except (TypeError, ValueError):
        duration_years = 4
    return max(3, min(5, duration_years))


def program_public(document: Dict[str, Any]) -> Dict[str, Any]:
    duration_years = _normalize_duration_years(document.get("duration_years"))
    total_semesters = duration_years * 2
    return {
        "id": str(document["_id"]),
        "name": document.get("name", ""),
        "code": document.get("code", ""),
        "department_id": document.get("department_id"),
        "duration_years": duration_years,
        "total_semesters": total_semesters,
        "description": document.get("description"),
        "is_active": document.get("is_active", True),
        "deleted_at": document.get("deleted_at"),
        "deleted_by": document.get("deleted_by"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=PROGRAM_SCHEMA_VERSION,
        ),
    }
