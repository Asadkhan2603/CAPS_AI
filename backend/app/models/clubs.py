from typing import Any, Dict

from app.core.schema_versions import (
    CLUB_APPLICATION_SCHEMA_VERSION,
    CLUB_MEMBER_SCHEMA_VERSION,
    CLUB_SCHEMA_VERSION,
    normalize_schema_version,
)
from app.services.public_ids import apply_public_identity, build_user_label


def club_public(document: Dict[str, Any]) -> Dict[str, Any]:
    status = document.get("status")
    if not status:
        status = "active" if document.get("is_active", True) else "closed"

    payload = {
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
        "coordinator_label": build_user_label(document.get("coordinator_user_id"), full_name=document.get("coordinator_name"), email=document.get("coordinator_email")),
        "president_user_id": document.get("president_user_id"),
        "president_name": document.get("president_name"),
        "president_email": document.get("president_email"),
        "president_label": build_user_label(document.get("president_user_id"), full_name=document.get("president_name"), email=document.get("president_email")),
        "status": status,
        "registration_open": document.get("registration_open", False),
        "membership_type": document.get("membership_type", "approval_required"),
        "max_members": document.get("max_members"),
        "member_count": int(document.get("member_count") or 0),
        "logo_url": document.get("logo_url"),
        "banner_url": document.get("banner_url"),
        "tagline": document.get("tagline"),
        "achievement_highlights": document.get("achievement_highlights", []) or [],
        "recruitment_headline": document.get("recruitment_headline"),
        "recruitment_cta_label": document.get("recruitment_cta_label"),
        "public_contact_url": document.get("public_contact_url"),
        "sponsorship_target_amount": document.get("sponsorship_target_amount"),
        "sponsorship_committed_amount": document.get("sponsorship_committed_amount"),
        "sponsorship_notes": document.get("sponsorship_notes"),
        "created_by": document.get("created_by"),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "archived_at": document.get("archived_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=CLUB_SCHEMA_VERSION,
        ),
        # Legacy field preserved for old UI paths.
        "is_active": document.get("is_active", status in {"active", "registration_closed"}),
    }
    return apply_public_identity(payload, kind="club", document=document, display_name=document.get("name"))


def club_member_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "club_id": document.get("club_id"),
        "student_user_id": document.get("student_user_id"),
        "student_name": document.get("student_name"),
        "student_email": document.get("student_email"),
        "student_label": build_user_label(document.get("student_user_id"), full_name=document.get("student_name"), email=document.get("student_email")),
        "role": document.get("role", "member"),
        "status": document.get("status", "active"),
        "joined_at": document.get("joined_at"),
        "left_at": document.get("left_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=CLUB_MEMBER_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="club_member", document=document, display_name=document.get("student_name"))


def club_application_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "id": str(document["_id"]),
        "club_id": document.get("club_id"),
        "student_user_id": document.get("student_user_id"),
        "student_name": document.get("student_name"),
        "student_email": document.get("student_email"),
        "student_label": build_user_label(document.get("student_user_id"), full_name=document.get("student_name"), email=document.get("student_email")),
        "status": document.get("status", "pending"),
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
        "applied_at": document.get("applied_at"),
        "reviewed_by": document.get("reviewed_by"),
        "reviewed_by_label": build_user_label(document.get("reviewed_by"), full_name=document.get("reviewed_by_name"), email=document.get("reviewed_by_email")),
        "reviewed_at": document.get("reviewed_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=CLUB_APPLICATION_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="club_application", document=document, display_name=document.get("student_name"))
