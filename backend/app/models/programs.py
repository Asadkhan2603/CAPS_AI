from typing import Any, Dict


def program_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "name": document.get("name", ""),
        "code": document.get("code", ""),
        "department_id": document.get("department_id"),
        "description": document.get("description"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
    }
