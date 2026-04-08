import csv
import re
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Any, List, Literal

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import (
    CLUB_APPLICATION_SCHEMA_VERSION,
    CLUB_MEMBER_SCHEMA_VERSION,
    CLUB_SCHEMA_VERSION,
)
from app.core.security import require_permission, require_roles
from app.models.clubs import club_application_public, club_member_public, club_public
from app.schemas.club import (
    ClubAnalyticsOut,
    ClubApplicationBulkReview,
    ClubApplicationOut,
    ClubArchiveCohortOut,
    ClubArchivalHistoryPointOut,
    ClubArchiveSeasonSummaryOut,
    ClubApplicationReminder,
    ClubEventTrendPointOut,
    ClubEventHistoryEntryOut,
    ClubEventHistoryOut,
    ClubEventPerformanceOut,
    ClubTrendSummaryOut,
    ClubApplicationReview,
    ClubCreate,
    ClubMembershipOut,
    ClubMembershipUpdate,
    ClubOut,
    ClubUpdate,
)
from app.services.audit import log_audit_event
from app.services.club_governance import assign_student_as_club_president, clear_student_club_president
from app.services.club_queue_insights import (
    list_shared_queue_snapshots,
    list_shared_queue_views,
    record_membership_queue_snapshot,
    save_shared_queue_view,
    delete_shared_queue_view,
)
from app.services.club_permissions import can_manage_club, is_admin, is_teacher
from app.services.notifications import create_notifications_bulk
from app.services.public_ids import build_public_id, build_user_label, persist_public_id, persist_public_id_update
from app.schemas.queue_insights import SharedQueueSnapshotOut, SharedQueueViewCreate, SharedQueueViewOut

router = APIRouter()

ACTIVE_STATES = {"active", "registration_closed"}
NON_DISCOVERABLE_STATES_FOR_STUDENT = {"draft", "pending_activation", "suspended", "archived", "dormant"}
STATE_TRANSITIONS = {
    "draft": {"pending_activation", "active", "suspended"},
    "pending_activation": {"active", "suspended", "archived"},
    "active": {"registration_closed", "closed", "suspended", "archived", "dormant"},
    "registration_closed": {"active", "closed", "suspended", "archived", "dormant"},
    "closed": {"active", "suspended", "archived", "dormant"},
    "suspended": {"active", "registration_closed", "closed", "archived"},
    "dormant": {"active", "registration_closed", "closed", "archived"},
    "archived": set(),
}


async def _resolve_user(user_id: str | None) -> dict[str, Any] | None:
    if not user_id:
        return None
    if not ObjectId.is_valid(user_id):
        return None
    try:
        return await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None

async def _can_manage_club(user: dict[str, Any], club: dict[str, Any]) -> bool:
    return can_manage_club(user, club)


async def _can_view_members(user: dict[str, Any], club: dict[str, Any]) -> bool:
    if await _can_manage_club(user, club):
        return True
    if club.get("president_user_id") == str(user.get("_id")):
        return True
    return False


async def _ensure_club(club_id: str) -> dict[str, Any]:
    club = await db.clubs.find_one({"_id": parse_object_id(club_id)})
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found")
    return club


def _normalize_status(value: str | None) -> str:
    if not value:
        return "draft"
    return value.strip().lower()


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _current_user_identity_fields(current_user: dict[str, Any], *, prefix: str) -> dict[str, Any]:
    return {
        prefix: str(current_user["_id"]),
        f"{prefix}_name": current_user.get("full_name"),
        f"{prefix}_email": current_user.get("email"),
    }


async def _resolve_club_queue_owner(club: dict[str, Any], owner_user_id: str | None) -> dict[str, Any] | None:
    owner_id = _normalize_optional_text(owner_user_id)
    if not owner_id:
        return None
    owner = await _resolve_user(owner_id)
    if not owner:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Queue owner not found")
    owner_role = owner.get("role")
    if owner_role == "admin":
        return owner
    if owner_role == "teacher" and club.get("coordinator_user_id") == str(owner.get("_id")):
        return owner
    if owner_role == "student" and club.get("president_user_id") == str(owner.get("_id")):
        return owner
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Queue owner must be a club manager for this club",
    )


async def _prepare_club_application_context_updates(
    *,
    club: dict[str, Any],
    payload_data: dict[str, Any],
    current_user: dict[str, Any],
    now: datetime,
) -> dict[str, Any]:
    update_fields: dict[str, Any] = {}

    if "queue_owner_user_id" in payload_data:
        owner = await _resolve_club_queue_owner(club, payload_data.get("queue_owner_user_id"))
        update_fields["queue_owner_user_id"] = str(owner["_id"]) if owner else None
        update_fields["queue_owner_name"] = owner.get("full_name") if owner else None
        update_fields["queue_owner_email"] = owner.get("email") if owner else None

    if "coordinator_note" in payload_data:
        update_fields["coordinator_note"] = _normalize_optional_text(payload_data.get("coordinator_note"))

    if update_fields:
        update_fields.update(_current_user_identity_fields(current_user, prefix="last_touched_by"))
        update_fields["last_touched_at"] = now

    return update_fields


def _slugify_filename_part(value: str | None, fallback: str = "club") -> str:
    raw = (value or fallback).strip().lower()
    cleaned = re.sub(r"[^a-z0-9]+", "-", raw).strip("-")
    return cleaned or fallback


def _format_csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _build_csv_response(*, rows: list[dict[str, Any]], fieldnames: list[str], filename: str) -> Response:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: _format_csv_value(row.get(field)) for field in fieldnames})
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _build_trend_summary(
    *,
    key: str,
    label: str,
    values: list[float],
    lower_is_better: bool = False,
    unit_suffix: str = "%",
) -> ClubTrendSummaryOut:
    if not values:
        return ClubTrendSummaryOut(
            key=key,
            label=label,
            direction="steady",
            current_value=0.0,
            previous_value=0.0,
            detail="No recent events yet.",
        )
    if len(values) == 1:
        current_value = round(values[-1], 2)
        return ClubTrendSummaryOut(
            key=key,
            label=label,
            direction="steady",
            current_value=current_value,
            previous_value=current_value,
            detail=f"Only one recent event is available at {current_value}{unit_suffix}.",
        )

    midpoint = max(1, len(values) // 2)
    previous_window = values[:midpoint]
    current_window = values[midpoint:]
    previous_avg = round(sum(previous_window) / len(previous_window), 2) if previous_window else 0.0
    current_avg = round(sum(current_window) / len(current_window), 2) if current_window else previous_avg
    delta = round(current_avg - previous_avg, 2)
    threshold = 5.0
    if lower_is_better:
        if delta <= -threshold:
            direction = "improving"
        elif delta >= threshold:
            direction = "declining"
        else:
            direction = "steady"
    else:
        if delta >= threshold:
            direction = "improving"
        elif delta <= -threshold:
            direction = "declining"
        else:
            direction = "steady"

    detail = (
        f"Recent average {current_avg}{unit_suffix} vs previous {previous_avg}{unit_suffix}."
        if previous_window
        else f"Current average {current_avg}{unit_suffix}."
    )
    return ClubTrendSummaryOut(
        key=key,
        label=label,
        direction=direction,
        current_value=current_avg,
        previous_value=previous_avg,
        detail=detail,
    )


async def _authorize_club_analytics_access(current_user: dict[str, Any], club: dict[str, Any]) -> None:
    if await _can_view_members(current_user, club):
        return
    if current_user.get("role") == "student" and club.get("president_user_id") == str(current_user.get("_id")):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view club analytics")


def _normalize_analytics_datetime(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _resolve_event_analytics_date(event_doc: dict[str, Any]) -> datetime | None:
    return _normalize_analytics_datetime(event_doc.get("event_date")) or _normalize_analytics_datetime(event_doc.get("created_at"))


def _archive_season_label(value: datetime | None) -> str:
    if value is None:
        return "Undated"
    quarter = ((value.month - 1) // 3) + 1
    return f"{value.year} Q{quarter}"


def _archive_period_start(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def _archive_period_label(value: datetime | None) -> str:
    if value is None:
        return "Undated"
    return value.strftime("%b %Y")


async def _build_club_analytics_payload(club_id: str) -> tuple[ClubAnalyticsOut, list[ClubEventPerformanceOut], list[dict[str, Any]], dict[str, dict[str, Any]]]:
    club_doc = await db.clubs.find_one({"_id": parse_object_id(club_id)}, {"sponsorship_target_amount": 1, "sponsorship_committed_amount": 1})
    now = datetime.now(timezone.utc)
    since_30 = now - timedelta(days=30)
    since_90 = now - timedelta(days=90)
    member_docs = await db.club_members.find(
        {"club_id": club_id},
        {
            "_id": 1,
            "student_user_id": 1,
            "status": 1,
            "joined_at": 1,
            "left_at": 1,
        },
    ).to_list(length=10000)
    total_members = len(member_docs)
    active_member_docs = [row for row in member_docs if row.get("status") == "active"]
    inactive_member_docs = [row for row in member_docs if row.get("status") in {"inactive", "removed"}]
    active_members = len(active_member_docs)
    inactive_members = len(inactive_member_docs)
    growth_30d = sum(
        1
        for row in member_docs
        if (_normalize_analytics_datetime(row.get("joined_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= since_30
    )
    member_student_ids = {
        str(row.get("student_user_id"))
        for row in member_docs
        if row.get("student_user_id")
    }
    active_member_ids = {
        str(row.get("student_user_id"))
        for row in active_member_docs
        if row.get("student_user_id")
    }
    retained_member_ids = {
        str(row.get("student_user_id"))
        for row in active_member_docs
        if row.get("student_user_id")
        and (
            (_normalize_analytics_datetime(row.get("joined_at")) is None)
            or (_normalize_analytics_datetime(row.get("joined_at")) <= since_90)
        )
    }
    departed_member_ids_90d = {
        str(row.get("student_user_id"))
        for row in inactive_member_docs
        if row.get("student_user_id")
        and (_normalize_analytics_datetime(row.get("left_at")) or datetime.min.replace(tzinfo=timezone.utc)) >= since_90
    }
    mature_active_member_ids = {
        str(row.get("student_user_id"))
        for row in active_member_docs
        if row.get("student_user_id")
        and (
            (_normalize_analytics_datetime(row.get("joined_at")) is None)
            or (_normalize_analytics_datetime(row.get("joined_at")) <= since_30)
        )
    }

    total_events = await db.club_events.count_documents({"club_id": club_id})
    upcoming_events = await db.club_events.count_documents({"club_id": club_id, "status": {"$in": ["draft", "open", "closed"]}})
    completed_events = await db.club_events.count_documents({"club_id": club_id, "status": {"$in": ["completed", "archived"]}})

    event_docs = await db.club_events.find(
        {"club_id": club_id},
        {
            "_id": 1,
            "title": 1,
            "status": 1,
            "event_date": 1,
            "created_at": 1,
            "capacity": 1,
            "certificate_enabled": 1,
            "payment_required": 1,
            "payment_amount": 1,
        },
    ).to_list(length=1000)
    event_ids = [str(item["_id"]) for item in event_docs]
    registration_docs = (
        await db.event_registrations.find({"event_id": {"$in": event_ids}}).to_list(length=5000)
        if event_ids
        else []
    )

    registrations_by_event: dict[str, list[dict[str, Any]]] = {}
    for registration in registration_docs:
        registrations_by_event.setdefault(str(registration.get("event_id")), []).append(registration)

    confirmed_event_registrations = 0
    pending_event_registrations = 0
    waitlisted_event_registrations = 0
    attendance_marked_registrations = 0
    present_attendance_count = 0
    absent_attendance_count = 0
    certificate_eligible_registrations = 0
    certificates_issued = 0
    certificate_enabled_events = 0
    events_at_capacity = 0
    waitlist_pressure_events = 0
    repeat_attention_events = 0
    total_capacity = 0
    event_performance: list[ClubEventPerformanceOut] = []
    archived_event_rows: list[dict[str, Any]] = []
    paid_events_count = 0
    free_events_count = 0
    paid_confirmed_registrations = 0
    payment_proof_submitted_count = 0
    listed_paid_revenue_inr = 0.0
    members_with_event_participation: set[str] = set()
    members_with_present_attendance: set[str] = set()
    recent_engaged_member_ids: set[str] = set()

    for event_doc in event_docs:
        event_id = str(event_doc["_id"])
        event_regs = registrations_by_event.get(event_id, [])
        event_status = str(event_doc.get("status") or "draft")
        event_date = _resolve_event_analytics_date(event_doc)
        capacity = max(1, int(event_doc.get("capacity") or 0))
        total_capacity += capacity

        confirmed = sum(1 for row in event_regs if row.get("status") in {"registered", "approved"})
        pending = sum(1 for row in event_regs if row.get("status") == "pending")
        waitlisted = sum(1 for row in event_regs if row.get("status") == "waitlisted")
        marked = sum(1 for row in event_regs if row.get("attendance_status") in {"present", "absent"})
        present = sum(1 for row in event_regs if row.get("attendance_status") == "present")
        absent = sum(1 for row in event_regs if row.get("attendance_status") == "absent")
        certificate_enabled = bool(event_doc.get("certificate_enabled", False))
        payment_required = bool(event_doc.get("payment_required", False))
        payment_amount = float(event_doc.get("payment_amount") or 0.0)
        eligible = present if certificate_enabled else 0
        issued = sum(1 for row in event_regs if row.get("certificate_issued"))
        payment_proof_submitted = sum(
            1
            for row in event_regs
            if row.get("status") in {"registered", "approved"}
            and (row.get("payment_qr_code") or row.get("payment_receipt_stored_filename"))
        )
        for row in event_regs:
            student_user_id = str(row.get("student_user_id") or "")
            if not student_user_id or student_user_id not in member_student_ids:
                continue
            if row.get("status") in {"registered", "approved"}:
                members_with_event_participation.add(student_user_id)
                if event_date and event_date >= since_90:
                    recent_engaged_member_ids.add(student_user_id)
            if row.get("attendance_status") == "present":
                members_with_present_attendance.add(student_user_id)
                if event_date and event_date >= since_90:
                    recent_engaged_member_ids.add(student_user_id)

        confirmed_event_registrations += confirmed
        pending_event_registrations += pending
        waitlisted_event_registrations += waitlisted
        attendance_marked_registrations += marked
        present_attendance_count += present
        absent_attendance_count += absent
        certificate_eligible_registrations += eligible
        certificates_issued += issued
        if payment_required:
            paid_events_count += 1
            paid_confirmed_registrations += confirmed
            payment_proof_submitted_count += payment_proof_submitted
            listed_paid_revenue_inr += round(payment_amount * confirmed, 2)
        else:
            free_events_count += 1

        if certificate_enabled:
            certificate_enabled_events += 1
        if confirmed >= capacity:
            events_at_capacity += 1
        if waitlisted > 0:
            waitlist_pressure_events += 1

        fill_pct = round((confirmed / capacity) * 100, 2) if capacity else 0.0
        attendance_marked_pct = round((marked / confirmed) * 100, 2) if confirmed else 0.0
        no_show_rate_pct = round((absent / marked) * 100, 2) if marked else 0.0
        certificate_issuance_pct = round((issued / eligible) * 100, 2) if eligible else 0.0

        health_summary = "steady"
        if waitlisted > 0:
            health_summary = "waitlist pressure"
        elif confirmed and absent and absent >= present:
            health_summary = "attendance risk"
        elif certificate_enabled and eligible and issued < eligible:
            health_summary = "certificate follow-up"
        elif fill_pct >= 90:
            health_summary = "high demand"

        if health_summary in {"waitlist pressure", "attendance risk", "certificate follow-up"}:
            repeat_attention_events += 1

        performance_row = ClubEventPerformanceOut(
            event_id=event_id,
            title=str(event_doc.get("title") or "Untitled event"),
            status=event_status,
            event_date=event_date,
            capacity=capacity,
            confirmed_registrations=confirmed,
            pending_registrations=pending,
            waitlisted_registrations=waitlisted,
            fill_pct=fill_pct,
            attendance_marked_count=marked,
            attendance_marked_pct=attendance_marked_pct,
            present_count=present,
            absent_count=absent,
            no_show_rate_pct=no_show_rate_pct,
            certificate_enabled=certificate_enabled,
            certificate_eligible_count=eligible,
            certificate_issued_count=issued,
            certificate_issuance_pct=certificate_issuance_pct,
            health_summary=health_summary,
        )
        event_performance.append(performance_row)
        if event_status == "archived":
            archived_event_rows.append(
                {
                    "event_date": event_date,
                    "confirmed_registrations": confirmed,
                    "attendance_marked_count": marked,
                    "absent_count": absent,
                    "certificate_eligible_count": eligible,
                    "certificate_issued_count": issued,
                }
            )

    regs = confirmed_event_registrations
    attendance_pct = round((regs / total_capacity) * 100, 2) if total_capacity else 0.0

    pending_applications = await db.club_applications.count_documents({"club_id": club_id, "status": "pending"})
    waitlisted_applications = await db.club_applications.count_documents({"club_id": club_id, "status": "waitlisted"})
    overall_attendance_marked_pct = round((attendance_marked_registrations / regs) * 100, 2) if regs else 0.0
    no_show_rate_pct = round((absent_attendance_count / attendance_marked_registrations) * 100, 2) if attendance_marked_registrations else 0.0
    certificate_issuance_pct = (
        round((certificates_issued / certificate_eligible_registrations) * 100, 2)
        if certificate_eligible_registrations
        else 0.0
    )
    archived_events = len(archived_event_rows)
    archived_confirmed_registrations = sum(row["confirmed_registrations"] for row in archived_event_rows)
    archived_attendance_marked_count = sum(row["attendance_marked_count"] for row in archived_event_rows)
    archived_absent_count = sum(row["absent_count"] for row in archived_event_rows)
    archived_certificate_eligible = sum(row["certificate_eligible_count"] for row in archived_event_rows)
    archived_certificates_issued = sum(row["certificate_issued_count"] for row in archived_event_rows)
    archived_attendance_marked_pct = (
        round((archived_attendance_marked_count / archived_confirmed_registrations) * 100, 2)
        if archived_confirmed_registrations
        else 0.0
    )
    archived_no_show_rate_pct = (
        round((archived_absent_count / archived_attendance_marked_count) * 100, 2)
        if archived_attendance_marked_count
        else 0.0
    )
    archived_certificate_issuance_pct = (
        round((archived_certificates_issued / archived_certificate_eligible) * 100, 2)
        if archived_certificate_eligible
        else 0.0
    )
    payment_proof_coverage_pct = (
        round((payment_proof_submitted_count / paid_confirmed_registrations) * 100, 2)
        if paid_confirmed_registrations
        else 0.0
    )
    sponsorship_target_amount = float((club_doc or {}).get("sponsorship_target_amount") or 0.0)
    sponsorship_committed_amount = float((club_doc or {}).get("sponsorship_committed_amount") or 0.0)
    sponsorship_gap_amount = round(max(sponsorship_target_amount - sponsorship_committed_amount, 0.0), 2)
    sponsorship_progress_pct = (
        round((sponsorship_committed_amount / sponsorship_target_amount) * 100, 2)
        if sponsorship_target_amount
        else 0.0
    )

    season_buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "archived_events": 0,
            "confirmed_registrations": 0,
            "attendance_marked_count": 0,
            "absent_count": 0,
            "certificate_eligible_count": 0,
            "certificates_issued": 0,
            "sort_date": None,
        }
    )
    cohort_specs = [
        ("last_90_days", "Last 90 Days"),
        ("91_to_365_days", "91-365 Days"),
        ("older_than_365_days", "Older Than 365 Days"),
    ]
    cohort_buckets: dict[str, dict[str, Any]] = {
        key: {
            "cohort_label": label,
            "archived_events": 0,
            "confirmed_registrations": 0,
            "attendance_marked_count": 0,
            "absent_count": 0,
            "certificate_eligible_count": 0,
            "certificates_issued": 0,
            "latest_event_date": None,
        }
        for key, label in cohort_specs
    }
    history_buckets: dict[datetime | None, dict[str, Any]] = defaultdict(
        lambda: {
            "archived_events": 0,
            "confirmed_registrations": 0,
            "attendance_marked_count": 0,
            "absent_count": 0,
            "certificate_eligible_count": 0,
            "certificates_issued": 0,
        }
    )
    for row in archived_event_rows:
        event_date = row["event_date"]
        season_label = _archive_season_label(event_date)
        season_bucket = season_buckets[season_label]
        season_bucket["archived_events"] += 1
        season_bucket["confirmed_registrations"] += row["confirmed_registrations"]
        season_bucket["attendance_marked_count"] += row["attendance_marked_count"]
        season_bucket["absent_count"] += row["absent_count"]
        season_bucket["certificate_eligible_count"] += row["certificate_eligible_count"]
        season_bucket["certificates_issued"] += row["certificate_issued_count"]
        if event_date and (season_bucket["sort_date"] is None or event_date > season_bucket["sort_date"]):
            season_bucket["sort_date"] = event_date

        age_days = (now - event_date).days if event_date else 9999
        if age_days <= 90:
            cohort_key = "last_90_days"
        elif age_days <= 365:
            cohort_key = "91_to_365_days"
        else:
            cohort_key = "older_than_365_days"
        cohort_bucket = cohort_buckets[cohort_key]
        cohort_bucket["archived_events"] += 1
        cohort_bucket["confirmed_registrations"] += row["confirmed_registrations"]
        cohort_bucket["attendance_marked_count"] += row["attendance_marked_count"]
        cohort_bucket["absent_count"] += row["absent_count"]
        cohort_bucket["certificate_eligible_count"] += row["certificate_eligible_count"]
        cohort_bucket["certificates_issued"] += row["certificate_issued_count"]
        latest_event_date = cohort_bucket["latest_event_date"]
        if event_date and (latest_event_date is None or event_date > latest_event_date):
            cohort_bucket["latest_event_date"] = event_date

        period_start = _archive_period_start(event_date)
        history_bucket = history_buckets[period_start]
        history_bucket["archived_events"] += 1
        history_bucket["confirmed_registrations"] += row["confirmed_registrations"]
        history_bucket["attendance_marked_count"] += row["attendance_marked_count"]
        history_bucket["absent_count"] += row["absent_count"]
        history_bucket["certificate_eligible_count"] += row["certificate_eligible_count"]
        history_bucket["certificates_issued"] += row["certificate_issued_count"]

    archive_season_summaries = [
        ClubArchiveSeasonSummaryOut(
            season_label=label,
            archived_events=values["archived_events"],
            confirmed_registrations=values["confirmed_registrations"],
            attendance_marked_count=values["attendance_marked_count"],
            attendance_marked_pct=round((values["attendance_marked_count"] / values["confirmed_registrations"]) * 100, 2)
            if values["confirmed_registrations"]
            else 0.0,
            no_show_rate_pct=round((values["absent_count"] / values["attendance_marked_count"]) * 100, 2)
            if values["attendance_marked_count"]
            else 0.0,
            certificates_issued=values["certificates_issued"],
            certificate_issuance_pct=round((values["certificates_issued"] / values["certificate_eligible_count"]) * 100, 2)
            if values["certificate_eligible_count"]
            else 0.0,
        )
        for label, values in sorted(
            season_buckets.items(),
            key=lambda item: item[1]["sort_date"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )
    ]
    archive_event_cohorts = [
        ClubArchiveCohortOut(
            cohort_key=key,
            cohort_label=values["cohort_label"],
            archived_events=values["archived_events"],
            confirmed_registrations=values["confirmed_registrations"],
            attendance_marked_pct=round((values["attendance_marked_count"] / values["confirmed_registrations"]) * 100, 2)
            if values["confirmed_registrations"]
            else 0.0,
            no_show_rate_pct=round((values["absent_count"] / values["attendance_marked_count"]) * 100, 2)
            if values["attendance_marked_count"]
            else 0.0,
            certificate_issuance_pct=round((values["certificates_issued"] / values["certificate_eligible_count"]) * 100, 2)
            if values["certificate_eligible_count"]
            else 0.0,
            latest_event_date=values["latest_event_date"],
        )
        for key, values in cohort_buckets.items()
    ]
    archival_history_points = [
        ClubArchivalHistoryPointOut(
            period_label=_archive_period_label(period_start),
            period_start=period_start,
            archived_events=values["archived_events"],
            confirmed_registrations=values["confirmed_registrations"],
            attendance_marked_pct=round((values["attendance_marked_count"] / values["confirmed_registrations"]) * 100, 2)
            if values["confirmed_registrations"]
            else 0.0,
            no_show_rate_pct=round((values["absent_count"] / values["attendance_marked_count"]) * 100, 2)
            if values["attendance_marked_count"]
            else 0.0,
            certificate_issuance_pct=round((values["certificates_issued"] / values["certificate_eligible_count"]) * 100, 2)
            if values["certificate_eligible_count"]
            else 0.0,
        )
        for period_start, values in sorted(
            history_buckets.items(),
            key=lambda item: item[0] or datetime.min.replace(tzinfo=timezone.utc),
        )[-12:]
    ]
    event_performance.sort(
        key=lambda row: (
            0 if row.health_summary == "waitlist pressure" else 1,
            0 if row.health_summary == "attendance risk" else 1,
            0 if row.health_summary == "certificate follow-up" else 1,
            -(row.waitlisted_registrations + row.pending_registrations),
            -(row.no_show_rate_pct or 0),
            -(row.fill_pct or 0),
        )
    )
    trend_candidates = sorted(
        event_performance,
        key=lambda row: row.event_date or datetime.min.replace(tzinfo=timezone.utc),
    )
    recent_trend_points = [
        ClubEventTrendPointOut(
            event_id=row.event_id,
            title=row.title,
            event_date=row.event_date,
            fill_pct=row.fill_pct,
            attendance_marked_pct=row.attendance_marked_pct,
            no_show_rate_pct=row.no_show_rate_pct,
            certificate_issuance_pct=row.certificate_issuance_pct,
            waitlisted_registrations=row.waitlisted_registrations,
            health_summary=row.health_summary,
        )
        for row in trend_candidates[-6:]
    ]
    trend_summaries = [
        _build_trend_summary(
            key="demand",
            label="Demand Trend",
            values=[row.fill_pct for row in recent_trend_points],
        ),
        _build_trend_summary(
            key="attendance",
            label="No-Show Trend",
            values=[row.no_show_rate_pct for row in recent_trend_points if row.no_show_rate_pct or row.attendance_marked_pct],
            lower_is_better=True,
        ),
        _build_trend_summary(
            key="certificate",
            label="Certificate Trend",
            values=[
                row.certificate_issuance_pct
                for row in recent_trend_points
                if row.certificate_issuance_pct or row.health_summary == "certificate follow-up"
            ],
        ),
    ]
    retained_members_90d = len(retained_member_ids)
    departed_members_90d = len(departed_member_ids_90d)
    retention_base = retained_members_90d + departed_members_90d
    member_retention_pct_90d = round((retained_members_90d / retention_base) * 100, 2) if retention_base else 0.0
    member_churn_rate_pct_90d = round((departed_members_90d / retention_base) * 100, 2) if retention_base else 0.0
    members_with_event_participation_count = len(members_with_event_participation)
    members_with_present_attendance_count = len(members_with_present_attendance)
    member_event_conversion_pct = (
        round((members_with_event_participation_count / total_members) * 100, 2)
        if total_members
        else 0.0
    )
    member_attendance_conversion_pct = (
        round((members_with_present_attendance_count / total_members) * 100, 2)
        if total_members
        else 0.0
    )
    recently_engaged_active_members_90d = len(active_member_ids & recent_engaged_member_ids)
    at_risk_active_members_90d = max(0, len(mature_active_member_ids - recent_engaged_member_ids))

    analytics = ClubAnalyticsOut(
        club_id=club_id,
        total_members=total_members,
        active_members=active_members,
        inactive_members=inactive_members,
        membership_growth_30d=growth_30d,
        retained_members_90d=retained_members_90d,
        departed_members_90d=departed_members_90d,
        member_retention_pct_90d=member_retention_pct_90d,
        member_churn_rate_pct_90d=member_churn_rate_pct_90d,
        members_with_event_participation=members_with_event_participation_count,
        members_with_present_attendance=members_with_present_attendance_count,
        member_event_conversion_pct=member_event_conversion_pct,
        member_attendance_conversion_pct=member_attendance_conversion_pct,
        recently_engaged_active_members_90d=recently_engaged_active_members_90d,
        at_risk_active_members_90d=at_risk_active_members_90d,
        total_events=total_events,
        upcoming_events=upcoming_events,
        completed_events=completed_events,
        average_attendance_pct=attendance_pct,
        pending_applications=pending_applications,
        waitlisted_applications=waitlisted_applications,
        confirmed_event_registrations=regs,
        pending_event_registrations=pending_event_registrations,
        waitlisted_event_registrations=waitlisted_event_registrations,
        events_at_capacity=events_at_capacity,
        attendance_marked_registrations=attendance_marked_registrations,
        attendance_marked_pct=overall_attendance_marked_pct,
        present_attendance_count=present_attendance_count,
        absent_attendance_count=absent_attendance_count,
        no_show_rate_pct=no_show_rate_pct,
        certificate_enabled_events=certificate_enabled_events,
        certificate_eligible_registrations=certificate_eligible_registrations,
        certificates_issued=certificates_issued,
        certificate_issuance_pct=certificate_issuance_pct,
        waitlist_pressure_events=waitlist_pressure_events,
        archived_events=archived_events,
        archived_confirmed_registrations=archived_confirmed_registrations,
        archived_attendance_marked_pct=archived_attendance_marked_pct,
        archived_no_show_rate_pct=archived_no_show_rate_pct,
        archived_certificates_issued=archived_certificates_issued,
        archived_certificate_issuance_pct=archived_certificate_issuance_pct,
        paid_events_count=paid_events_count,
        free_events_count=free_events_count,
        paid_confirmed_registrations=paid_confirmed_registrations,
        payment_proof_submitted_count=payment_proof_submitted_count,
        payment_proof_coverage_pct=payment_proof_coverage_pct,
        listed_paid_revenue_inr=round(listed_paid_revenue_inr, 2),
        sponsorship_target_amount=round(sponsorship_target_amount, 2),
        sponsorship_committed_amount=round(sponsorship_committed_amount, 2),
        sponsorship_gap_amount=sponsorship_gap_amount,
        sponsorship_progress_pct=sponsorship_progress_pct,
        event_performance=event_performance[:5],
        trend_summaries=trend_summaries,
        recent_event_trends=recent_trend_points,
        repeat_attention_events=repeat_attention_events,
        archive_season_summaries=archive_season_summaries,
        archive_event_cohorts=archive_event_cohorts,
        archival_history_points=archival_history_points,
    )
    event_docs_by_id = {str(doc["_id"]): doc for doc in event_docs}
    return analytics, event_performance, registration_docs, event_docs_by_id


def _history_action_title(
    action: str,
    *,
    entry_type: str,
    new_value: dict[str, Any] | None = None,
    old_value: dict[str, Any] | None = None,
) -> str:
    if entry_type == "queue_snapshot":
        return "Queue snapshot captured"
    mapping = {
        "create": "Event created",
        "delete": "Event archived",
        "update_event": "Event updated",
        "create_event_registration": "Registration created",
        "submit_event_registration": "Registration submitted",
        "register_event": "Registration created",
        "update_event_registration": "Registration updated",
        "auto_promote_waitlisted_registration": "Waitlist promoted",
    }
    if action in mapping:
        if action == "update_event_registration" and isinstance(new_value, dict):
            if new_value.get("attendance_status") != (old_value or {}).get("attendance_status"):
                return "Attendance updated"
            if new_value.get("certificate_issued") != (old_value or {}).get("certificate_issued"):
                return "Certificate status updated"
            if new_value.get("status") != (old_value or {}).get("status"):
                return "Registration status updated"
        return mapping[action]
    return action.replace("_", " ").strip().title() or "History updated"


def _history_status_label(
    new_value: dict[str, Any] | None = None,
    old_value: dict[str, Any] | None = None,
) -> str | None:
    for payload in (new_value, old_value):
        if not isinstance(payload, dict):
            continue
        if payload.get("status") is not None:
            return str(payload.get("status"))
    return None


def _history_detail_text(
    *,
    detail: str | None,
    new_value: dict[str, Any] | None,
    registration: dict[str, Any] | None,
    snapshot: dict[str, Any] | None = None,
) -> str | None:
    if snapshot is not None:
        return (
            f"Total {snapshot.get('total', 0)}, pending {snapshot.get('pending', 0)}, "
            f"waitlisted {snapshot.get('waitlisted', 0)}, stale {snapshot.get('stale', 0)}."
        )
    if detail:
        return detail
    if isinstance(new_value, dict):
        parts: list[str] = []
        if new_value.get("status") is not None:
            parts.append(f"status -> {new_value.get('status')}")
        if new_value.get("attendance_status") is not None:
            parts.append(f"attendance -> {new_value.get('attendance_status')}")
        if new_value.get("certificate_issued") is not None:
            parts.append(
                "certificate issued"
                if bool(new_value.get("certificate_issued"))
                else "certificate cleared"
            )
        if new_value.get("queue_owner_name") is not None:
            parts.append(f"owner -> {new_value.get('queue_owner_name')}")
        if new_value.get("coordinator_note"):
            parts.append(f"note: {new_value.get('coordinator_note')}")
        if parts:
            return ", ".join(parts)
    if registration:
        status = registration.get("status") or "registered"
        return f"Registration is currently {status}."
    return None


async def _build_club_event_history(club: dict[str, Any], event: dict[str, Any], *, limit: int) -> ClubEventHistoryOut:
    event_id = str(event["_id"])
    registrations = await db.event_registrations.find({"event_id": event_id}).to_list(length=5000)
    registration_ids = [str(item["_id"]) for item in registrations]

    event_audit_logs = await db.audit_logs.find(
        {"entity_type": "club_event", "entity_id": event_id}
    ).sort("created_at", -1).to_list(length=200)
    registration_audit_logs = (
        await db.audit_logs.find(
            {
                "entity_type": "event_registration",
                "entity_id": {"$in": registration_ids},
            }
        ).sort("created_at", -1).to_list(length=500)
        if registration_ids
        else []
    )
    snapshots = await list_shared_queue_snapshots(
        scope_type="event",
        scope_id=event_id,
        queue_type="enrollment",
        limit=min(max(limit, 1), 24),
    )

    actor_ids = sorted(
        {
            str(row.get("actor_user_id"))
            for row in [*event_audit_logs, *registration_audit_logs]
            if row.get("actor_user_id") and ObjectId.is_valid(str(row.get("actor_user_id")))
        }
    )
    users_by_id: dict[str, dict[str, Any]] = {}
    if actor_ids:
        user_docs = await db.users.find({"_id": {"$in": [ObjectId(item) for item in actor_ids]}}).to_list(length=200)
        users_by_id = {str(item["_id"]): item for item in user_docs}

    registrations_by_id = {str(item["_id"]): item for item in registrations}
    timeline: list[ClubEventHistoryEntryOut] = []

    for audit_row in [*event_audit_logs, *registration_audit_logs]:
        actor = users_by_id.get(str(audit_row.get("actor_user_id")))
        actor_label = build_user_label(
            audit_row.get("actor_user_id"),
            full_name=(actor or {}).get("full_name"),
            email=(actor or {}).get("email"),
        )
        new_value = audit_row.get("new_value") if isinstance(audit_row.get("new_value"), dict) else None
        old_value = audit_row.get("old_value") if isinstance(audit_row.get("old_value"), dict) else None
        registration = (
            registrations_by_id.get(str(audit_row.get("entity_id")))
            if audit_row.get("entity_type") == "event_registration"
            else None
        )
        timeline.append(
            ClubEventHistoryEntryOut(
                id=str(audit_row.get("_id") or audit_row.get("public_id") or audit_row.get("created_at") or len(timeline)),
                entry_type="registration" if audit_row.get("entity_type") == "event_registration" else "event",
                action=str(audit_row.get("action") or "update"),
                title=_history_action_title(
                    str(audit_row.get("action") or "update"),
                    entry_type="registration" if audit_row.get("entity_type") == "event_registration" else "event",
                    new_value=new_value,
                    old_value=old_value,
                ),
                detail=_history_detail_text(
                    detail=audit_row.get("detail"),
                    new_value=new_value,
                    registration=registration,
                ),
                actor_label=actor_label,
                subject_label=build_user_label(
                    (registration or {}).get("student_user_id"),
                    full_name=(registration or {}).get("student_name") or (registration or {}).get("full_name"),
                    email=(registration or {}).get("student_email") or (registration or {}).get("email"),
                ),
                status_label=_history_status_label(new_value, old_value),
                attendance_status=(
                    new_value.get("attendance_status")
                    if isinstance(new_value, dict) and new_value.get("attendance_status") is not None
                    else (old_value.get("attendance_status") if isinstance(old_value, dict) else None)
                ),
                certificate_issued=(
                    bool(new_value.get("certificate_issued"))
                    if isinstance(new_value, dict) and new_value.get("certificate_issued") is not None
                    else (
                        bool(old_value.get("certificate_issued"))
                        if isinstance(old_value, dict) and old_value.get("certificate_issued") is not None
                        else None
                    )
                ),
                severity=audit_row.get("severity"),
                occurred_at=audit_row.get("created_at"),
            )
        )

    for snapshot in snapshots:
        timeline.append(
            ClubEventHistoryEntryOut(
                id=f"snapshot-{snapshot.get('captured_at')}-{snapshot.get('source_action')}",
                entry_type="queue_snapshot",
                action=str(snapshot.get("source_action") or "queue_snapshot"),
                title="Queue snapshot captured",
                detail=_history_detail_text(
                    detail=None,
                    new_value=None,
                    registration=None,
                    snapshot=snapshot,
                ),
                actor_label=snapshot.get("changed_by_label"),
                subject_label=None,
                status_label=None,
                severity="low",
                occurred_at=snapshot.get("captured_at"),
            )
        )

    timeline.sort(key=lambda row: row.occurred_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    timeline = timeline[:limit]

    confirmed = sum(1 for row in registrations if row.get("status") in {"registered", "approved"})
    pending = sum(1 for row in registrations if row.get("status") == "pending")
    waitlisted = sum(1 for row in registrations if row.get("status") == "waitlisted")
    attendance_marked = sum(1 for row in registrations if row.get("attendance_status") in {"present", "absent"})
    present = sum(1 for row in registrations if row.get("attendance_status") == "present")
    absent = sum(1 for row in registrations if row.get("attendance_status") == "absent")
    certificates_issued = sum(1 for row in registrations if row.get("certificate_issued"))

    return ClubEventHistoryOut(
        event_id=event_id,
        title=str(event.get("title") or "Untitled event"),
        status=str(event.get("status") or "draft"),
        event_type=str(event.get("event_type") or "event"),
        event_date=event.get("event_date"),
        registration_enabled=bool(event.get("registration_enabled", True)),
        approval_required=bool(event.get("approval_required", False)),
        certificate_enabled=bool(event.get("certificate_enabled", False)),
        capacity=int(event.get("capacity") or 0),
        confirmed_registrations=confirmed,
        pending_registrations=pending,
        waitlisted_registrations=waitlisted,
        attendance_marked_count=attendance_marked,
        present_count=present,
        absent_count=absent,
        certificates_issued=certificates_issued,
        timeline=timeline,
    )


async def _validate_status_transition(
    *,
    club_id: str,
    current_status: str,
    next_status: str,
    coordinator_id: str | None,
    registration_open: bool,
    current_user: dict[str, Any],
) -> None:
    if current_status == next_status:
        return

    allowed = STATE_TRANSITIONS.get(current_status, set())
    if next_status not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition: {current_status} -> {next_status}",
        )

    if next_status == "active" and not coordinator_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coordinator is required before activation")

    if next_status in {"suspended", "archived"} and not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Only admin can set club status to {next_status}",
        )

    if registration_open and next_status not in ACTIVE_STATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration can be open only when club is active",
        )

    if next_status == "archived":
        has_active_events = await db.club_events.count_documents(
            {"club_id": club_id, "status": {"$in": ["draft", "open", "closed"]}}
        )
        if has_active_events:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archive blocked: club has active events")

    if next_status == "suspended":
        has_open_events = await db.club_events.count_documents(
            {"club_id": club_id, "status": {"$in": ["open"]}}
        )
        if has_open_events:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Suspend blocked: club has ongoing events")


async def _enrich_club_document(document: dict[str, Any]) -> dict[str, Any]:
    row = dict(document)
    coordinator = await _resolve_user(row.get("coordinator_user_id"))
    president = await _resolve_user(row.get("president_user_id"))
    row["coordinator_name"] = coordinator.get("full_name") if coordinator else None
    row["coordinator_email"] = coordinator.get("email") if coordinator else None
    row["president_name"] = president.get("full_name") if president else None
    row["president_email"] = president.get("email") if president else None
    try:
        row["member_count"] = await db.club_members.count_documents(
            {"club_id": str(row.get("_id")), "status": "active"}
        )
    except Exception:
        row["member_count"] = 0
    return row


async def _batch_enrich_club_documents(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not documents:
        return []

    rows = [dict(item) for item in documents]
    club_ids = [str(item.get("_id")) for item in rows if item.get("_id")]

    user_ids: set[str] = set()
    for row in rows:
        coordinator_user_id = row.get("coordinator_user_id")
        president_user_id = row.get("president_user_id")
        if coordinator_user_id and ObjectId.is_valid(coordinator_user_id):
            user_ids.add(coordinator_user_id)
        if president_user_id and ObjectId.is_valid(president_user_id):
            user_ids.add(president_user_id)

    users_by_id: dict[str, dict[str, Any]] = {}
    if user_ids:
        user_docs = await db.users.find(
            {"_id": {"$in": [ObjectId(user_id) for user_id in user_ids]}},
            {"full_name": 1, "email": 1},
        ).to_list(length=len(user_ids))
        users_by_id = {str(item["_id"]): item for item in user_docs}

    member_count_by_club_id: dict[str, int] = {}
    if club_ids:
        member_docs = await db.club_members.find(
            {"club_id": {"$in": club_ids}, "status": "active"},
            {"club_id": 1},
        ).to_list(length=5000)
        for item in member_docs:
            club_id = str(item.get("club_id") or "")
            if not club_id:
                continue
            member_count_by_club_id[club_id] = member_count_by_club_id.get(club_id, 0) + 1

    enriched: list[dict[str, Any]] = []
    for row in rows:
        coordinator = users_by_id.get(str(row.get("coordinator_user_id") or ""))
        president = users_by_id.get(str(row.get("president_user_id") or ""))
        row["coordinator_name"] = coordinator.get("full_name") if coordinator else None
        row["coordinator_email"] = coordinator.get("email") if coordinator else None
        row["president_name"] = president.get("full_name") if president else None
        row["president_email"] = president.get("email") if president else None
        row["member_count"] = member_count_by_club_id.get(str(row.get("_id")), 0)
        enriched.append(row)

    return enriched


async def _reactivate_club_membership(
    member: dict[str, Any],
    *,
    student_name: str | None,
    student_email: str | None,
    joined_at: datetime,
) -> str:
    update_data = {
        "student_name": student_name,
        "student_email": student_email,
        "role": "member",
        "status": "active",
        "joined_at": joined_at,
        "left_at": None,
        "schema_version": CLUB_MEMBER_SCHEMA_VERSION,
    }
    persist_public_id_update(member, update_data, kind="club_member")
    await db.club_members.update_one(
        {"_id": member["_id"]},
        {"$set": update_data},
    )
    return str(member["_id"])


async def _count_active_members(club_id: str) -> int:
    return await db.club_members.count_documents({"club_id": club_id, "status": "active"})


async def _club_has_capacity(club: dict[str, Any]) -> bool:
    max_members = club.get("max_members")
    if not max_members:
        return True
    active_member_count = await _count_active_members(str(club["_id"]))
    return active_member_count < int(max_members)


async def _create_club_application(
    *,
    club_id: str,
    student_user_id: str,
    student_name: str | None,
    student_email: str | None,
    status: str,
) -> str:
    result = await db.club_applications.insert_one(
        persist_public_id(
            {
                "club_id": club_id,
                "student_user_id": student_user_id,
                "student_name": student_name,
                "student_email": student_email,
                "status": status,
                "applied_at": datetime.now(timezone.utc),
                "reviewed_by": None,
                "reviewed_at": None,
                "schema_version": CLUB_APPLICATION_SCHEMA_VERSION,
            },
            kind="club_application",
        )
    )
    public_id = build_public_id("club_application", {"club_id": club_id, "_id": result.inserted_id}, prefer_existing=False)
    if public_id:
        await db.club_applications.update_one({"_id": result.inserted_id}, {"$set": {"public_id": public_id}})
    return str(result.inserted_id)


async def _activate_membership_from_application(
    *,
    club_id: str,
    application: dict[str, Any],
    joined_at: datetime,
) -> None:
    exists = await db.club_members.find_one(
        {
            "club_id": club_id,
            "student_user_id": application.get("student_user_id"),
            "status": {"$in": ["active", "inactive", "removed"]},
        }
    )
    if exists and exists.get("status") in {"inactive", "removed"}:
        await _reactivate_club_membership(
            exists,
            student_name=application.get("student_name"),
            student_email=application.get("student_email"),
            joined_at=joined_at,
        )
    elif not exists:
        membership_result = await db.club_members.insert_one(
            persist_public_id(
                {
                    "club_id": club_id,
                    "student_user_id": application.get("student_user_id"),
                    "student_name": application.get("student_name"),
                    "student_email": application.get("student_email"),
                    "role": "member",
                    "status": "active",
                    "joined_at": joined_at,
                    "left_at": None,
                    "schema_version": CLUB_MEMBER_SCHEMA_VERSION,
                },
                kind="club_member",
            )
        )
        public_id = build_public_id(
            "club_member",
            {"club_id": club_id, "_id": membership_result.inserted_id},
            prefer_existing=False,
        )
        if public_id:
            await db.club_members.update_one(
                {"_id": membership_result.inserted_id},
                {"$set": {"public_id": public_id}},
            )


async def _promote_waitlisted_club_applications(club_id: str) -> None:
    club = await _ensure_club(club_id)
    if club.get("status") not in ACTIVE_STATES or not club.get("registration_open", False):
        return
    while await _club_has_capacity(club):
        waitlisted = await db.club_applications.find_one(
            {"club_id": club_id, "status": "waitlisted"},
            sort=[("applied_at", 1)],
        )
        if not waitlisted:
            return

        now = datetime.now(timezone.utc)
        if club.get("membership_type") == "open":
            await _activate_membership_from_application(club_id=club_id, application=waitlisted, joined_at=now)
            await db.club_applications.update_one(
                {"_id": waitlisted["_id"]},
                {
                    "$set": {
                        "status": "approved",
                        "reviewed_by": None,
                        "reviewed_at": now,
                        "schema_version": CLUB_APPLICATION_SCHEMA_VERSION,
                    }
                },
            )
            await log_audit_event(
                actor_user_id=None,
                action="promote_waitlisted_club_application",
                entity_type="club_application",
                entity_id=str(waitlisted["_id"]),
                detail="Promoted waitlisted club application into active membership",
                old_value={"status": "waitlisted"},
                new_value={"status": "approved"},
                severity="low",
            )
            await record_membership_queue_snapshot(
                club_id=club_id,
                changed_by_user_id=None,
                source_action="promote_waitlisted_club_application",
            )
        else:
            await db.club_applications.update_one(
                {"_id": waitlisted["_id"]},
                {
                    "$set": {
                        "status": "pending",
                        "reviewed_by": None,
                        "reviewed_at": None,
                        "schema_version": CLUB_APPLICATION_SCHEMA_VERSION,
                    }
                },
            )
            await log_audit_event(
                actor_user_id=None,
                action="promote_waitlisted_club_application",
                entity_type="club_application",
                entity_id=str(waitlisted["_id"]),
                detail="Promoted waitlisted club application back into the review queue",
                old_value={"status": "waitlisted"},
                new_value={"status": "pending"},
                severity="low",
            )
            await record_membership_queue_snapshot(
                club_id=club_id,
                changed_by_user_id=None,
                source_action="promote_waitlisted_club_application",
            )


async def _review_application_document(
    *,
    club_id: str,
    club: dict[str, Any],
    application: dict[str, Any],
    next_status: str | None,
    extra_updates: dict[str, Any],
    current_user: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    current_status = application.get("status", "pending")
    update_fields = dict(extra_updates)

    if next_status is not None:
        if application.get("status") in {"approved", "rejected"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Application already reviewed")

        allowed_transitions = {
            "pending": {"approved", "rejected", "waitlisted"},
            "waitlisted": {"pending", "approved", "rejected"},
        }
        if next_status not in allowed_transitions.get(current_status, set()):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid application status transition: {current_status} -> {next_status}",
            )

        if next_status == "pending" and club.get("membership_type") == "open":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Open clubs should promote waitlisted applications directly to approved",
            )

        if next_status in {"approved", "pending"} and current_status == "waitlisted" and not await _club_has_capacity(club):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Club membership capacity reached",
            )

        if next_status == "approved" and not await _club_has_capacity(club):
            existing_member = await db.club_members.find_one(
                {
                    "club_id": club_id,
                    "student_user_id": application.get("student_user_id"),
                    "status": "active",
                }
            )
            if not existing_member:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Club membership capacity reached",
                )

        review_identity = (
            _current_user_identity_fields(current_user, prefix="reviewed_by")
            if next_status in {"approved", "rejected"}
            else {"reviewed_by": None, "reviewed_by_name": None, "reviewed_by_email": None}
        )
        update_fields.update(review_identity)
        update_fields["status"] = next_status
        update_fields["reviewed_at"] = now if next_status in {"approved", "rejected"} else None

    if not update_fields:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    await db.club_applications.update_one(
        {"_id": application["_id"]},
        {
            "$set": {
                **update_fields,
                "schema_version": CLUB_APPLICATION_SCHEMA_VERSION,
            }
        },
    )

    if next_status == "approved":
        await _activate_membership_from_application(club_id=club_id, application=application, joined_at=now)

    return await db.club_applications.find_one({"_id": application["_id"]})


@router.get("/", response_model=List[ClubOut])
async def list_clubs(
    status_filter: str | None = Query(default=None, alias="status"),
    is_active: bool | None = Query(default=None),
    registration_open: bool | None = Query(default=None),
    academic_year: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[ClubOut]:
    query: dict[str, Any] = {}

    if status_filter:
        query["status"] = status_filter
    if academic_year:
        query["academic_year"] = academic_year
    if registration_open is not None:
        query["registration_open"] = registration_open

    if is_active is not None:
        if is_active:
            query["status"] = {"$in": list(ACTIVE_STATES)}
        else:
            query["status"] = {"$nin": list(ACTIVE_STATES)}

    if current_user.get("role") == "student":
        query.setdefault("status", {"$nin": list(NON_DISCOVERABLE_STATES_FOR_STUDENT)})

    items = await db.clubs.find(query).sort("updated_at", -1).skip(skip).limit(limit).to_list(length=limit)

    enriched = await _batch_enrich_club_documents(items)
    return [ClubOut(**club_public(item)) for item in enriched]


@router.post("/", response_model=ClubOut, status_code=status.HTTP_201_CREATED)
async def create_club(
    payload: ClubCreate,
    current_user=Depends(require_permission("club:create")),
) -> ClubOut:
    if payload.coordinator_user_id:
        teacher = await _resolve_user(payload.coordinator_user_id)
        if not teacher:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coordinator not found")
        if teacher.get("role") != "teacher":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coordinator must be a teacher")

    if payload.president_user_id:
        president = await _resolve_user(payload.president_user_id)
        if not president:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="President not found")
        if president.get("role") != "student":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="President must be a student")

    slug = (payload.slug or payload.name).strip().lower().replace(" ", "-")
    duplicate_slug = await db.clubs.find_one({"slug": slug, "academic_year": payload.academic_year})
    if duplicate_slug:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Club slug already exists for this academic year")

    now = datetime.now(timezone.utc)
    document = {
        "name": payload.name.strip(),
        "slug": slug,
        "description": payload.description,
        "category": payload.category,
        "department_id": payload.department_id,
        "academic_year": payload.academic_year,
        "coordinator_user_id": payload.coordinator_user_id,
        "president_user_id": payload.president_user_id,
        "status": payload.status,
        "registration_open": bool(payload.registration_open),
        "membership_type": payload.membership_type,
        "max_members": payload.max_members,
        "logo_url": payload.logo_url,
        "banner_url": payload.banner_url,
        "tagline": payload.tagline,
        "achievement_highlights": payload.achievement_highlights,
        "recruitment_headline": payload.recruitment_headline,
        "recruitment_cta_label": payload.recruitment_cta_label,
        "public_contact_url": payload.public_contact_url,
        "sponsorship_target_amount": payload.sponsorship_target_amount,
        "sponsorship_committed_amount": payload.sponsorship_committed_amount,
        "sponsorship_notes": payload.sponsorship_notes,
        "created_by": str(current_user["_id"]),
        "created_at": now,
        "updated_at": now,
        "schema_version": CLUB_SCHEMA_VERSION,
        # Legacy compatibility
        "is_active": payload.status in ACTIVE_STATES,
    }

    document["status"] = _normalize_status(document["status"])

    if document["status"] == "active" and not document.get("coordinator_user_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coordinator is required before activation")
    if document["status"] == "registration_closed":
        if not document.get("coordinator_user_id"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coordinator is required before activation")
        document["registration_open"] = False

    persist_public_id(document, kind="club")
    result = await db.clubs.insert_one(document)
    created = await db.clubs.find_one({"_id": result.inserted_id})
    enriched = await _enrich_club_document(created)

    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="create",
        entity_type="club",
        entity_id=str(result.inserted_id),
        detail="Created club",
    )
    return ClubOut(**club_public(enriched))


@router.patch("/{club_id}", response_model=ClubOut)
async def update_club(
    club_id: str,
    payload: ClubUpdate,
    current_user=Depends(require_permission("club:update")),
) -> ClubOut:
    club = await _ensure_club(club_id)
    if not await _can_manage_club(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to manage this club")

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if "coordinator_user_id" in update_data and update_data["coordinator_user_id"]:
        teacher = await _resolve_user(update_data["coordinator_user_id"])
        if not teacher or teacher.get("role") != "teacher":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coordinator must be a teacher")

    if "president_user_id" in update_data and update_data["president_user_id"]:
        president = await _resolve_user(update_data["president_user_id"])
        if not president or president.get("role") != "student":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="President must be a student")

    current_status = _normalize_status(club.get("status", "draft"))
    next_status = _normalize_status(update_data.get("status", current_status))
    coordinator_id = update_data.get("coordinator_user_id", club.get("coordinator_user_id"))
    registration_open = update_data.get("registration_open", club.get("registration_open", False))

    await _validate_status_transition(
        club_id=club_id,
        current_status=current_status,
        next_status=next_status,
        coordinator_id=coordinator_id,
        registration_open=bool(registration_open),
        current_user=current_user,
    )

    if bool(registration_open) and next_status not in ACTIVE_STATES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration can be opened only when club is active",
        )

    if next_status in {"archived", "registration_closed", "closed", "suspended", "dormant"}:
        update_data["registration_open"] = False
    if next_status == "archived":
        update_data["archived_at"] = datetime.now(timezone.utc)
    if next_status == "active" and "registration_open" not in update_data:
        update_data["registration_open"] = bool(club.get("registration_open", False))

    update_data["updated_at"] = datetime.now(timezone.utc)
    update_data["status"] = next_status
    update_data["is_active"] = next_status in ACTIVE_STATES
    persist_public_id_update(club, update_data, kind="club")

    await db.clubs.update_one(
        {"_id": parse_object_id(club_id)},
        {"$set": {**update_data, "schema_version": CLUB_SCHEMA_VERSION}},
    )
    updated = await db.clubs.find_one({"_id": parse_object_id(club_id)})
    enriched = await _enrich_club_document(updated)

    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="update",
        entity_type="club",
        entity_id=club_id,
        action_type="admin_action" if current_user.get("role") == "admin" else "update",
        detail=(
            f"Club status changed {current_status} -> {next_status}"
            if current_status != next_status
            else "Updated club settings"
        ),
        old_value={"status": current_status, "registration_open": club.get("registration_open")},
        new_value={"status": next_status, "registration_open": update_data.get("registration_open", club.get("registration_open"))},
        severity="medium" if current_status != next_status else "low",
    )
    await _promote_waitlisted_club_applications(club_id)
    return ClubOut(**club_public(enriched))


@router.post("/{club_id}/join")
async def join_club(
    club_id: str,
    current_user=Depends(require_roles(["student"])),
) -> dict[str, Any]:
    club = await _ensure_club(club_id)
    if club.get("status") not in ACTIVE_STATES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Club is not active")
    if not club.get("registration_open", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Club registration is closed")

    student_user_id = str(current_user["_id"])

    existing_member = await db.club_members.find_one(
        {"club_id": club_id, "student_user_id": student_user_id}
    )
    if existing_member and existing_member.get("status") == "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already a club member")

    pending_or_waitlisted = await db.club_applications.find_one(
        {"club_id": club_id, "student_user_id": student_user_id, "status": {"$in": ["pending", "waitlisted"]}}
    )
    if pending_or_waitlisted:
        detail = "Already in membership waitlist" if pending_or_waitlisted.get("status") == "waitlisted" else "Application already pending"
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

    has_capacity = await _club_has_capacity(club)

    if club.get("membership_type") == "open":
        if not has_capacity:
            application_id = await _create_club_application(
                club_id=club_id,
                student_user_id=student_user_id,
                student_name=current_user.get("full_name"),
                student_email=current_user.get("email"),
                status="waitlisted",
            )
            await record_membership_queue_snapshot(
                club_id=club_id,
                changed_by_user_id=student_user_id,
                source_action="join_waitlist",
            )
            return {
                "status": "waitlisted",
                "application_id": application_id,
                "message": "Club is full right now. You have been added to the membership waitlist",
            }
        now = datetime.now(timezone.utc)
        if existing_member and existing_member.get("status") in {"inactive", "removed"}:
            membership_id = await _reactivate_club_membership(
                existing_member,
                student_name=current_user.get("full_name"),
                student_email=current_user.get("email"),
                joined_at=now,
            )
        else:
            result = await db.club_members.insert_one(
                persist_public_id(
                {
                    "club_id": club_id,
                    "student_user_id": student_user_id,
                    "student_name": current_user.get("full_name"),
                    "student_email": current_user.get("email"),
                    "role": "member",
                    "status": "active",
                    "joined_at": now,
                    "left_at": None,
                    "schema_version": CLUB_MEMBER_SCHEMA_VERSION,
                },
                kind="club_member",
                )
            )
            public_id = build_public_id("club_member", {"club_id": club_id, "_id": result.inserted_id}, prefer_existing=False)
            if public_id:
                await db.club_members.update_one({"_id": result.inserted_id}, {"$set": {"public_id": public_id}})
            membership_id = str(result.inserted_id)
        return {
            "status": "approved",
            "membership_id": membership_id,
            "message": "Joined club successfully",
        }

    application_status = "pending" if has_capacity else "waitlisted"
    application_id = await _create_club_application(
        club_id=club_id,
        student_user_id=student_user_id,
        student_name=current_user.get("full_name"),
        student_email=current_user.get("email"),
        status=application_status,
    )
    await record_membership_queue_snapshot(
        club_id=club_id,
        changed_by_user_id=student_user_id,
        source_action="join_request",
    )
    return {
        "status": application_status,
        "application_id": application_id,
        "message": (
            "Application submitted for coordinator approval"
            if application_status == "pending"
            else "Club is full right now. You have been added to the membership waitlist"
        ),
    }


@router.get("/{club_id}/members", response_model=List[ClubMembershipOut])
async def list_members(
    club_id: str,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[ClubMembershipOut]:
    club = await _ensure_club(club_id)

    query: dict[str, Any] = {"club_id": club_id}
    if not await _can_view_members(current_user, club):
        if current_user.get("role") != "student":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view members")
        query["student_user_id"] = str(current_user["_id"])

    items = await db.club_members.find(query).sort("joined_at", -1).to_list(length=1000)
    return [ClubMembershipOut(**club_member_public(item)) for item in items]


@router.patch("/{club_id}/members/{member_id}", response_model=ClubMembershipOut)
async def update_member(
    club_id: str,
    member_id: str,
    payload: ClubMembershipUpdate,
    current_user=Depends(require_permission("club:update")),
) -> ClubMembershipOut:
    club = await _ensure_club(club_id)
    if not await _can_manage_club(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to manage this club")

    member_obj_id = parse_object_id(member_id)
    member = await db.club_members.find_one({"_id": member_obj_id, "club_id": club_id})
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    effective_status = update_data.get("status", member.get("status"))
    if update_data.get("role") == "president":
        if effective_status != "active":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="President must be an active member")
        existing_president = await db.club_members.find_one(
            {
                "club_id": club_id,
                "role": "president",
                "status": "active",
                "_id": {"$ne": member_obj_id},
            }
        )
        if existing_president:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only one president is allowed per club")
        await assign_student_as_club_president(str(member.get("student_user_id")), club_id)

    is_current_president = member.get("role") == "president" or club.get("president_user_id") == member.get("student_user_id")
    if is_current_president and (
        update_data.get("role") in {"member", "core_member", "vice_president"}
        or update_data.get("status") in {"inactive", "removed"}
    ):
        await clear_student_club_president(str(member.get("student_user_id")), club_id)

    if update_data.get("status") in {"inactive", "removed"}:
        update_data["left_at"] = datetime.now(timezone.utc)
    was_active_member = member.get("status") == "active"
    persist_public_id_update(member, update_data, kind="club_member")

    await db.club_members.update_one(
        {"_id": member_obj_id},
        {"$set": {**update_data, "schema_version": CLUB_MEMBER_SCHEMA_VERSION}},
    )
    updated = await db.club_members.find_one({"_id": member_obj_id})
    if was_active_member and update_data.get("status") in {"inactive", "removed"}:
        await _promote_waitlisted_club_applications(club_id)
    return ClubMembershipOut(**club_member_public(updated))


@router.get("/{club_id}/applications", response_model=List[ClubApplicationOut])
async def list_applications(
    club_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[ClubApplicationOut]:
    club = await _ensure_club(club_id)

    query: dict[str, Any] = {"club_id": club_id}
    if status_filter:
        query["status"] = status_filter

    if await _can_view_members(current_user, club):
        pass
    elif current_user.get("role") == "student":
        query["student_user_id"] = str(current_user["_id"])
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view applications")

    items = await db.club_applications.find(query).sort("applied_at", -1).to_list(length=1000)
    return [ClubApplicationOut(**club_application_public(item)) for item in items]


@router.patch("/{club_id}/applications/{application_id}", response_model=ClubApplicationOut)
async def review_application(
    club_id: str,
    application_id: str,
    payload: ClubApplicationReview,
    current_user=Depends(require_permission("club:update")),
) -> ClubApplicationOut:
    club = await _ensure_club(club_id)
    if not await _can_manage_club(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to review applications")

    application_obj_id = parse_object_id(application_id)
    application = await db.club_applications.find_one({"_id": application_obj_id, "club_id": club_id})
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    payload_data = payload.model_dump(exclude_unset=True)
    if not payload_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    extra_updates = await _prepare_club_application_context_updates(
        club=club,
        payload_data=payload_data,
        current_user=current_user,
        now=datetime.now(timezone.utc),
    )
    updated = await _review_application_document(
        club_id=club_id,
        club=club,
        application=application,
        next_status=payload_data.get("status"),
        extra_updates=extra_updates,
        current_user=current_user,
    )
    await record_membership_queue_snapshot(
        club_id=club_id,
        changed_by_user_id=str(current_user["_id"]),
        source_action="review_application" if payload_data.get("status") else "update_application_context",
    )
    return ClubApplicationOut(**club_application_public(updated))


@router.post("/{club_id}/applications/bulk-review")
async def bulk_review_applications(
    club_id: str,
    payload: ClubApplicationBulkReview,
    current_user=Depends(require_permission("club:update")),
) -> dict[str, Any]:
    club = await _ensure_club(club_id)
    if not await _can_manage_club(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to review applications")

    updated_ids: list[str] = []
    for application_id in payload.application_ids:
        application = await db.club_applications.find_one({"_id": parse_object_id(application_id), "club_id": club_id})
        if not application:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
        updated = await _review_application_document(
            club_id=club_id,
            club=club,
            application=application,
            next_status=payload.status,
            extra_updates={},
            current_user=current_user,
        )
        updated_ids.append(str(updated["_id"]))

    await record_membership_queue_snapshot(
        club_id=club_id,
        changed_by_user_id=str(current_user["_id"]),
        source_action="bulk_review_applications",
    )

    return {
        "updated_count": len(updated_ids),
        "updated_ids": updated_ids,
        "status": payload.status,
    }


@router.post("/{club_id}/applications/remind")
async def remind_applications(
    club_id: str,
    payload: ClubApplicationReminder,
    current_user=Depends(require_permission("club:update")),
) -> dict[str, Any]:
    club = await _ensure_club(club_id)
    if not await _can_manage_club(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to review applications")

    query: dict[str, Any] = {"club_id": club_id}
    if payload.application_ids:
        query["_id"] = {"$in": [parse_object_id(item) for item in payload.application_ids]}
    elif payload.status_filter:
        query["status"] = payload.status_filter
    else:
        query["status"] = {"$in": ["pending", "waitlisted"]}

    applications = await db.club_applications.find(query).to_list(length=1000)
    if not applications:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No matching applications found")

    target_user_ids = [str(item.get("student_user_id")) for item in applications if item.get("student_user_id")]
    if not target_user_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No notification recipients found")

    status_label = payload.status_filter or (
        "selected queue"
        if payload.application_ids
        else "membership queue"
    )
    message = payload.message or (
        f"{club.get('name', 'This club')} still has your membership request in the {status_label}. "
        "Open the clubs workspace to review the latest status."
    )
    title = f"{club.get('name', 'Club')} membership update"
    inserted = await create_notifications_bulk(
        title=title,
        message=message,
        priority="normal",
        scope="club",
        target_user_ids=target_user_ids,
        created_by=str(current_user["_id"]),
    )
    return {
        "reminded_count": inserted,
        "target_count": len(target_user_ids),
        "club_id": club_id,
    }


@router.get("/{club_id}/applications/views", response_model=List[SharedQueueViewOut])
async def list_application_queue_views(
    club_id: str,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[SharedQueueViewOut]:
    club = await _ensure_club(club_id)
    if not await _can_manage_club(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view shared queue views")
    rows = await list_shared_queue_views(scope_type="club", scope_id=club_id, queue_type="membership")
    return [SharedQueueViewOut(**row) for row in rows]


@router.post("/{club_id}/applications/views", response_model=SharedQueueViewOut, status_code=status.HTTP_201_CREATED)
async def create_application_queue_view(
    club_id: str,
    payload: SharedQueueViewCreate,
    current_user=Depends(require_permission("club:update")),
) -> SharedQueueViewOut:
    club = await _ensure_club(club_id)
    if not await _can_manage_club(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to save shared queue views")
    created = await save_shared_queue_view(
        scope_type="club",
        scope_id=club_id,
        queue_type="membership",
        name=payload.name,
        filters=payload.filters.model_dump(),
        current_user_id=str(current_user["_id"]),
    )
    return SharedQueueViewOut(**created)


@router.delete("/{club_id}/applications/views/{view_id}")
async def delete_application_queue_view(
    club_id: str,
    view_id: str,
    current_user=Depends(require_permission("club:update")),
) -> dict[str, Any]:
    club = await _ensure_club(club_id)
    if not await _can_manage_club(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete shared queue views")
    deleted = await delete_shared_queue_view(
        view_id=view_id,
        scope_type="club",
        scope_id=club_id,
        queue_type="membership",
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shared queue view not found")
    return {"deleted": True, "view_id": view_id}


@router.get("/{club_id}/applications/history", response_model=List[SharedQueueSnapshotOut])
async def list_application_queue_history(
    club_id: str,
    limit: int = Query(default=12, ge=1, le=24),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[SharedQueueSnapshotOut]:
    club = await _ensure_club(club_id)
    if not await _can_manage_club(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view queue history")
    rows = await list_shared_queue_snapshots(scope_type="club", scope_id=club_id, queue_type="membership", limit=limit)
    return [SharedQueueSnapshotOut(**row) for row in rows]


@router.get("/{club_id}/events/{event_id}/history", response_model=ClubEventHistoryOut)
async def get_club_event_history(
    club_id: str,
    event_id: str,
    limit: int = Query(default=20, ge=5, le=40),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> ClubEventHistoryOut:
    club = await _ensure_club(club_id)
    await _authorize_club_analytics_access(current_user, club)
    event = await db.club_events.find_one({"_id": parse_object_id(event_id), "club_id": club_id})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club event not found")
    return await _build_club_event_history(club, event, limit=limit)


@router.get("/{club_id}/analytics", response_model=ClubAnalyticsOut)
async def get_club_analytics(
    club_id: str,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> ClubAnalyticsOut:
    club = await _ensure_club(club_id)
    await _authorize_club_analytics_access(current_user, club)
    analytics, _, _, _ = await _build_club_analytics_payload(club_id)
    return analytics


@router.get("/{club_id}/analytics/export")
async def export_club_analytics(
    club_id: str,
    report: Literal["event_performance", "attendance_certificate"] = Query(default="event_performance"),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> Response:
    club = await _ensure_club(club_id)
    await _authorize_club_analytics_access(current_user, club)
    analytics, event_performance, registration_docs, event_docs_by_id = await _build_club_analytics_payload(club_id)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    club_slug = _slugify_filename_part(club.get("name"), fallback=club_id)

    if report == "event_performance":
        rows = [
            {
                "club_id": club_id,
                "club_name": club.get("name"),
                "event_id": row.event_id,
                "event_title": row.title,
                "event_status": row.status,
                "event_date": row.event_date,
                "capacity": row.capacity,
                "confirmed_registrations": row.confirmed_registrations,
                "pending_registrations": row.pending_registrations,
                "waitlisted_registrations": row.waitlisted_registrations,
                "fill_pct": row.fill_pct,
                "attendance_marked_count": row.attendance_marked_count,
                "attendance_marked_pct": row.attendance_marked_pct,
                "present_count": row.present_count,
                "absent_count": row.absent_count,
                "no_show_rate_pct": row.no_show_rate_pct,
                "certificate_enabled": row.certificate_enabled,
                "certificate_eligible_count": row.certificate_eligible_count,
                "certificate_issued_count": row.certificate_issued_count,
                "certificate_issuance_pct": row.certificate_issuance_pct,
                "health_summary": row.health_summary,
                "club_attendance_marked_pct": analytics.attendance_marked_pct,
                "club_no_show_rate_pct": analytics.no_show_rate_pct,
                "club_certificate_issuance_pct": analytics.certificate_issuance_pct,
                "club_waitlist_pressure_events": analytics.waitlist_pressure_events,
            }
            for row in event_performance
        ]
        return _build_csv_response(
            rows=rows,
            fieldnames=[
                "club_id",
                "club_name",
                "event_id",
                "event_title",
                "event_status",
                "event_date",
                "capacity",
                "confirmed_registrations",
                "pending_registrations",
                "waitlisted_registrations",
                "fill_pct",
                "attendance_marked_count",
                "attendance_marked_pct",
                "present_count",
                "absent_count",
                "no_show_rate_pct",
                "certificate_enabled",
                "certificate_eligible_count",
                "certificate_issued_count",
                "certificate_issuance_pct",
                "health_summary",
                "club_attendance_marked_pct",
                "club_no_show_rate_pct",
                "club_certificate_issuance_pct",
                "club_waitlist_pressure_events",
            ],
            filename=f"{club_slug}-event-performance-report-{timestamp}.csv",
        )

    performance_by_event = {row.event_id: row for row in event_performance}
    fallback_user_ids = sorted(
        {
            str(row.get("student_user_id"))
            for row in registration_docs
            if row.get("student_user_id")
            and not (row.get("student_name") or row.get("full_name"))
            and not (row.get("student_email") or row.get("email"))
            and ObjectId.is_valid(str(row.get("student_user_id")))
        }
    )
    fallback_users_by_id: dict[str, dict[str, Any]] = {}
    if fallback_user_ids:
        fallback_user_docs = await db.users.find(
            {"_id": {"$in": [ObjectId(user_id) for user_id in fallback_user_ids]}},
            {"full_name": 1, "email": 1},
        ).to_list(length=len(fallback_user_ids))
        fallback_users_by_id = {str(row["_id"]): row for row in fallback_user_docs}

    rows = []
    for registration in sorted(
        registration_docs,
        key=lambda row: (
            str(event_docs_by_id.get(str(row.get("event_id")), {}).get("event_date") or ""),
            str(event_docs_by_id.get(str(row.get("event_id")), {}).get("title") or ""),
            str(row.get("student_name") or row.get("full_name") or row.get("student_email") or row.get("email") or ""),
        ),
    ):
        event_id = str(registration.get("event_id") or "")
        event_doc = event_docs_by_id.get(event_id, {})
        performance = performance_by_event.get(event_id)
        attendance_status = registration.get("attendance_status")
        certificate_enabled = bool(event_doc.get("certificate_enabled", False))
        fallback_user = fallback_users_by_id.get(str(registration.get("student_user_id")))
        student_name = registration.get("student_name") or registration.get("full_name") or (fallback_user or {}).get("full_name")
        student_email = registration.get("student_email") or registration.get("email") or (fallback_user or {}).get("email")
        rows.append(
            {
                "club_id": club_id,
                "club_name": club.get("name"),
                "event_id": event_id,
                "event_title": event_doc.get("title") or "Untitled event",
                "event_status": event_doc.get("status") or "draft",
                "event_date": event_doc.get("event_date"),
                "event_health_summary": performance.health_summary if performance else "",
                "event_fill_pct": performance.fill_pct if performance else "",
                "event_pending_registrations": performance.pending_registrations if performance else "",
                "event_waitlisted_registrations": performance.waitlisted_registrations if performance else "",
                "student_user_id": registration.get("student_user_id"),
                "student_name": student_name,
                "student_email": student_email,
                "registration_status": registration.get("status"),
                "attendance_status": attendance_status or "pending",
                "certificate_enabled": certificate_enabled,
                "certificate_eligible": certificate_enabled and attendance_status == "present",
                "certificate_issued": bool(registration.get("certificate_issued", False)),
                "created_at": registration.get("created_at"),
            }
        )
    return _build_csv_response(
        rows=rows,
        fieldnames=[
            "club_id",
            "club_name",
            "event_id",
            "event_title",
            "event_status",
            "event_date",
            "event_health_summary",
            "event_fill_pct",
            "event_pending_registrations",
            "event_waitlisted_registrations",
            "student_user_id",
            "student_name",
            "student_email",
            "registration_status",
            "attendance_status",
            "certificate_enabled",
            "certificate_eligible",
            "certificate_issued",
            "created_at",
        ],
        filename=f"{club_slug}-attendance-certificate-report-{timestamp}.csv",
    )
