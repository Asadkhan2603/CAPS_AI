from typing import Any, Dict


def event_registration_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
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
        "status": document.get("status", "registered"),
        "created_at": document.get("created_at"),
    }

