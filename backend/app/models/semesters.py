from typing import Any, Dict


def semester_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "batch_id": document.get("batch_id"),
        "semester_number": document.get("semester_number"),
        "label": document.get("label", ""),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
    }
