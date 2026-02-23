from typing import Any, Dict


def club_public(document: Dict[str, Any]) -> Dict[str, Any]:
    status = document.get("status")
    if not status:
        status = "active" if document.get("is_active", True) else "closed"

    return {
        "id": str(document["_id"]),
        "name": document.get("name", ""),
        "slug": document.get("slug"),
        "description": document.get("description"),
        "category": document.get("category"),
        "department_id": document.get("department_id"),
        "academic_year": document.get("academic_year"),
        "coordinator_user_id": document.get("coordinator_user_id"),
        "coordinator_name": document.get("coordinator_name"),
        "coordinator_email": document.get("coordinator_email"),
        "president_user_id": document.get("president_user_id"),
        "president_name": document.get("president_name"),
        "president_email": document.get("president_email"),
        "status": status,
        "registration_open": document.get("registration_open", False),
        "membership_type": document.get("membership_type", "approval_required"),
        "max_members": document.get("max_members"),
        "member_count": int(document.get("member_count") or 0),
        "logo_url": document.get("logo_url"),
        "banner_url": document.get("banner_url"),
        "created_by": document.get("created_by"),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "archived_at": document.get("archived_at"),
        # Legacy field preserved for old UI paths.
        "is_active": document.get("is_active", status in {"active", "draft"}),
    }


def club_member_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "club_id": document.get("club_id"),
        "student_user_id": document.get("student_user_id"),
        "student_name": document.get("student_name"),
        "student_email": document.get("student_email"),
        "role": document.get("role", "member"),
        "status": document.get("status", "active"),
        "joined_at": document.get("joined_at"),
        "left_at": document.get("left_at"),
    }


def club_application_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "club_id": document.get("club_id"),
        "student_user_id": document.get("student_user_id"),
        "student_name": document.get("student_name"),
        "student_email": document.get("student_email"),
        "status": document.get("status", "pending"),
        "applied_at": document.get("applied_at"),
        "reviewed_by": document.get("reviewed_by"),
        "reviewed_at": document.get("reviewed_at"),
    }
