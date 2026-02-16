from typing import Any, Dict


def section_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "name": document.get("name", ""),
        "program": document.get("program", ""),
        "academic_year": document.get("academic_year", ""),
        "semester": document.get("semester", 1),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
    }
