from typing import Any, Dict


def semester_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "batch_id": document.get("batch_id"),
        "semester_number": document.get("semester_number"),
        "label": document.get("label", ""),
        "is_active": document.get("is_active", True),
        "deleted_at": document.get("deleted_at"),
        "deleted_by": document.get("deleted_by"),
        "created_at": document.get("created_at"),
    }
