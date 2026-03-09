from typing import Any, Dict


def batch_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "program_id": document.get("program_id"),
        "specialization_id": document.get("specialization_id"),
        "name": document.get("name", ""),
        "code": document.get("code", ""),
        "start_year": document.get("start_year"),
        "end_year": document.get("end_year"),
        "is_active": document.get("is_active", True),
        "deleted_at": document.get("deleted_at"),
        "deleted_by": document.get("deleted_by"),
        "created_at": document.get("created_at"),
    }
