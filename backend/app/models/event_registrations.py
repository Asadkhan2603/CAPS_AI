from typing import Any, Dict

from app.core.schema_versions import EVENT_REGISTRATION_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity, build_user_label


def event_registration_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "event_id": document.get("event_id"),
        "student_user_id": document.get("student_user_id"),
        "enrollment_number": document.get("enrollment_number"),
        "full_name": document.get("full_name"),
        "email": document.get("email"),
        "year": document.get("year"),
        "course_branch": document.get("course_branch"),
        "class_name": document.get("class_name"),
        "phone_number": document.get("phone_number"),
        "whatsapp_number": document.get("whatsapp_number"),
        "payment_qr_code": document.get("payment_qr_code"),
        "payment_receipt_original_filename": document.get("payment_receipt_original_filename"),
        "payment_receipt_stored_filename": document.get("payment_receipt_stored_filename"),
        "payment_receipt_mime_type": document.get("payment_receipt_mime_type"),
        "payment_receipt_size_bytes": document.get("payment_receipt_size_bytes"),
        "student_name": document.get("student_name"),
        "student_email": document.get("student_email"),
        "student_label": build_user_label(document.get("student_user_id"), full_name=document.get("student_name") or document.get("full_name"), email=document.get("student_email") or document.get("email")),
        "status": document.get("status", "registered"),
        "queue_owner_user_id": document.get("queue_owner_user_id"),
        "queue_owner_label": build_user_label(
            document.get("queue_owner_user_id"),
            full_name=document.get("queue_owner_name"),
            email=document.get("queue_owner_email"),
        ),
        "coordinator_note": document.get("coordinator_note"),
        "last_touched_by": document.get("last_touched_by"),
        "last_touched_by_label": build_user_label(
            document.get("last_touched_by"),
            full_name=document.get("last_touched_by_name"),
            email=document.get("last_touched_by_email"),
        ),
        "last_touched_at": document.get("last_touched_at"),
        "attendance_status": document.get("attendance_status"),
        "certificate_issued": bool(document.get("certificate_issued", False)),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=EVENT_REGISTRATION_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="event_registration", document=document, display_name=document.get("student_name") or document.get("full_name"))

