from typing import Any, Dict

from app.core.schema_versions import CLUB_EVENT_SCHEMA_VERSION, normalize_schema_version


def club_event_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "club_id": document.get("club_id"),
        "title": document.get("title", ""),
        "description": document.get("description"),
        "event_type": document.get("event_type", "workshop"),
        "visibility": document.get("visibility", "public"),
        "registration_start": document.get("registration_start"),
        "registration_end": document.get("registration_end"),
        "event_date": document.get("event_date"),
        "capacity": document.get("capacity", 0),
        "registration_enabled": bool(document.get("registration_enabled", True)),
        "approval_required": bool(document.get("approval_required", False)),
        "payment_required": bool(document.get("payment_required", False)),
        "payment_qr_image_url": document.get("payment_qr_image_url"),
        "payment_amount": document.get("payment_amount"),
        "certificate_enabled": bool(document.get("certificate_enabled", False)),
        "status": document.get("status", "draft"),
        "result_summary": document.get("result_summary"),
        "created_by": document.get("created_by"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=CLUB_EVENT_SCHEMA_VERSION,
        ),
    }
