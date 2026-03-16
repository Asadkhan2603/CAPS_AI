from typing import Any, Dict

from app.core.schema_versions import DEPARTMENT_SCHEMA_VERSION, normalize_schema_version


def department_public(document: Dict[str, Any]) -> Dict[str, Any]:
    department_name = document.get("department_name") or document.get("name", "")
    department_code = document.get("department_code") or document.get("code", "")
    return {
        "id": str(document["_id"]),
        "department_id": document.get("department_id") or department_code or str(document.get("_id")),
        "department_code": department_code,
        "department_name": department_name,
        "name": department_name,
        "code": department_code,
        "faculty_id": document.get("faculty_id"),
        "faculty_master_id": document.get("faculty_master_id"),
        "faculty_code": document.get("faculty_code"),
        "faculty_name": document.get("faculty_name"),
        "university_master_id": document.get("university_master_id"),
        "university_name": document.get("university_name"),
        "university_code": document.get("university_code") or document.get("university_master_id"),
        "is_active": document.get("is_active", True),
        "deleted_at": document.get("deleted_at"),
        "deleted_by": document.get("deleted_by"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=DEPARTMENT_SCHEMA_VERSION,
        ),
    }
