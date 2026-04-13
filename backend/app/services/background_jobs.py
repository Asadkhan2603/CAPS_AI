from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from bson import ObjectId

from app.core.config import settings
from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import NOTICE_SCHEMA_VERSION
from app.api.v1.endpoints.admin_communication import get_delivery_anomaly_alerts
from app.services.audit import log_audit_event
from app.services.analytics_snapshot import compute_platform_snapshot
from app.services.communication_email_content import build_notice_email_body, build_notice_email_subject
from app.services.grievances import escalate_due_grievances
from app.services.operational_alert_routing import route_operational_alert_notifications
from app.services.communication_deliveries import (
    resolve_all_active_user_recipients,
    resolve_user_recipients,
    upsert_email_deliveries,
    upsert_in_app_deliveries,
)
from app.services.communication_preferences import partition_email_recipients_by_preference
from app.services.notifications import create_notifications_bulk
from app.services.outbound_email import send_outbound_email_batch


def _to_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _retry_limit() -> int:
    return max(1, int(settings.scheduled_notice_retry_limit))


def _dispatch_lease_seconds() -> int:
    return max(30, int(settings.scheduled_notice_dispatch_lease_seconds))


def _retry_backoff_seconds(attempt_number: int) -> int:
    base = max(30, int(settings.scheduled_notice_retry_backoff_seconds))
    exponent = max(0, int(attempt_number) - 1)
    return min(base * (2 ** exponent), 3600)


def _retry_at(*, attempt_number: int, now: datetime | None = None) -> datetime:
    anchor = _to_aware_utc(now) or _utcnow()
    return anchor + timedelta(seconds=_retry_backoff_seconds(attempt_number))


def _notice_is_due_for_dispatch(notice: dict[str, Any], *, now: datetime) -> bool:
    scheduled_at = _to_aware_utc(notice.get("scheduled_at"))
    if not scheduled_at or scheduled_at > now:
        return False
    if notice.get("fanout_dispatched_at"):
        return False
    processing_expires_at = _to_aware_utc(notice.get("fanout_processing_expires_at"))
    if processing_expires_at and processing_expires_at > now:
        return False
    next_retry_at = _to_aware_utc(notice.get("fanout_next_retry_at"))
    if next_retry_at and next_retry_at > now:
        return False
    attempts = max(0, int(notice.get("fanout_attempts") or 0))
    status = str(notice.get("fanout_status") or "queued").strip().lower()
    if status == "failed" and attempts >= _retry_limit():
        return False
    return True


def _notice_has_terminal_failure(notice: dict[str, Any], *, now: datetime) -> bool:
    if notice.get("fanout_dispatched_at"):
        return False
    if str(notice.get("fanout_status") or "").strip().lower() != "failed":
        return False
    next_retry_at = _to_aware_utc(notice.get("fanout_next_retry_at"))
    attempts = max(0, int(notice.get("fanout_attempts") or 0))
    return (not next_retry_at or next_retry_at <= now) and attempts >= _retry_limit()


async def _class_ids_for_batch(batch_id: str) -> list[str]:
    class_object_ids = await db.classes.distinct("_id", {"batch_id": batch_id, "is_active": True})
    return [str(item) for item in class_object_ids if item]


async def _student_user_ids_for_class_ids(class_ids: Iterable[str]) -> list[str]:
    class_ids = [class_id for class_id in class_ids if class_id]
    if not class_ids:
        return []
    student_ids = sorted(
        {
            value
            for value in await db.enrollments.distinct("student_id", {"class_id": {"$in": class_ids}})
            if isinstance(value, str) and value
        }
    )
    if not student_ids:
        return []
    student_object_ids = [parse_object_id(sid) for sid in student_ids if ObjectId.is_valid(sid)]
    if not student_object_ids:
        return []
    emails = sorted(
        {
            value.strip().lower()
            for value in await db.students.distinct("email", {"_id": {"$in": student_object_ids}})
            if isinstance(value, str) and value.strip()
        }
    )
    if not emails:
        return []
    user_object_ids = await db.users.distinct("_id", {"email": {"$in": emails}, "is_active": True})
    return [str(item) for item in user_object_ids if item]


async def _student_user_ids_for_subject(subject_id: str) -> list[str]:
    class_ids = sorted(
        {
            value
            for value in await db.assignments.distinct("class_id", {"subject_id": subject_id})
            if isinstance(value, str) and value
        }
    )
    return await _student_user_ids_for_class_ids(class_ids)


async def _student_user_ids_for_club(club_id: str) -> list[str]:
    if not club_id or not ObjectId.is_valid(club_id):
        return []
    member_ids = sorted(
        {
            value
            for value in await db.club_members.distinct(
                "student_user_id",
                {"club_id": club_id, "status": "active"},
            )
            if isinstance(value, str) and value
        }
    )
    club = await db.clubs.find_one({"_id": parse_object_id(club_id)})
    president_user_id = str(club.get("president_user_id")) if club and club.get("president_user_id") else None
    user_ids = set(member_ids)
    if president_user_id:
        user_ids.add(president_user_id)
    return sorted(user_ids)


async def _target_user_ids_for_notice(notice: dict[str, Any]) -> list[str]:
    scope = notice.get("scope")
    scope_ref_id = notice.get("scope_ref_id")
    if scope == "class" and scope_ref_id:
        return await _student_user_ids_for_class_ids([scope_ref_id])
    if scope == "batch" and scope_ref_id:
        class_ids = await _class_ids_for_batch(scope_ref_id)
        return await _student_user_ids_for_class_ids(class_ids)
    if scope == "subject" and scope_ref_id:
        return await _student_user_ids_for_subject(scope_ref_id)
    if scope == "club" and scope_ref_id:
        return await _student_user_ids_for_club(scope_ref_id)
    return []


async def _claim_notice_for_dispatch(notice: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
    now = _utcnow()
    if not notice or not notice.get("_id") or notice.get("is_active") is False:
        return None, 0

    scheduled_at = _to_aware_utc(notice.get("scheduled_at"))
    if scheduled_at and scheduled_at > now:
        return None, 0

    if notice.get("fanout_dispatched_at"):
        return None, 0

    processing_expires_at = _to_aware_utc(notice.get("fanout_processing_expires_at"))
    if processing_expires_at and processing_expires_at > now:
        return None, 0

    attempts = max(0, int(notice.get("fanout_attempts") or 0))
    next_retry_at = _to_aware_utc(notice.get("fanout_next_retry_at"))
    if next_retry_at and next_retry_at > now:
        return None, 0

    status = str(notice.get("fanout_status") or "queued").strip().lower()
    if status == "failed" and attempts >= _retry_limit():
        return None, 0

    claimed_attempt = attempts + 1
    lease_expires_at = now + timedelta(seconds=_dispatch_lease_seconds())
    update_result = await db.notices.update_one(
        {
            "_id": notice["_id"],
            "is_active": True,
            "fanout_dispatched_at": notice.get("fanout_dispatched_at"),
            "fanout_status": notice.get("fanout_status"),
            "fanout_attempts": attempts,
            "fanout_processing_expires_at": notice.get("fanout_processing_expires_at"),
            "fanout_next_retry_at": notice.get("fanout_next_retry_at"),
        },
        {
            "$set": {
                "fanout_status": "dispatching",
                "fanout_attempts": claimed_attempt,
                "fanout_last_attempt_at": now,
                "fanout_processing_started_at": now,
                "fanout_processing_expires_at": lease_expires_at,
                "fanout_next_retry_at": None,
                "schema_version": NOTICE_SCHEMA_VERSION,
            }
        },
    )
    if getattr(update_result, "matched_count", 0) == 0:
        return None, 0
    claimed_notice = await db.notices.find_one({"_id": notice["_id"]})
    return claimed_notice, claimed_attempt


async def fanout_notice_notifications(notice_id: str) -> bool:
    claimed_attempt = 0
    notice_object_id = parse_object_id(notice_id)
    try:
        notice = await db.notices.find_one({"_id": notice_object_id, "is_active": True})
        claimed_notice, claimed_attempt = await _claim_notice_for_dispatch(notice or {})
        if not claimed_notice:
            return False
        notice = claimed_notice
        scope = notice.get("scope")
        recipients: list[dict[str, Any]] = []

        if scope == "college":
            recipients = await resolve_all_active_user_recipients()
        else:
            target_user_ids = await _target_user_ids_for_notice(notice)
            recipients = await resolve_user_recipients(target_user_ids)

        resolved_target_user_ids = [
            str(recipient.get("user_id"))
            for recipient in recipients
            if recipient.get("user_id")
        ]

        await upsert_in_app_deliveries(
            source_kind="notice",
            source_id=str(notice["_id"]),
            source_public_id=notice.get("public_id"),
            recipients=recipients,
            metadata={"scope": scope, "priority": notice.get("priority")},
        )
        email_preference_key = "club_announcement_email" if scope == "club" else "announcement_email"
        email_recipients, preference_skips = await partition_email_recipients_by_preference(
            recipients=recipients,
            preference_key=email_preference_key,
            disabled_reason="Recipient disabled announcement email",
        )
        email_results = list(preference_skips)
        if email_recipients:
            email_results.extend(
                await send_outbound_email_batch(
                    subject=build_notice_email_subject(notice),
                    body=build_notice_email_body(notice),
                    recipients=email_recipients,
                )
            )
        await upsert_email_deliveries(
            source_kind="notice",
            source_id=str(notice["_id"]),
            source_public_id=notice.get("public_id"),
            recipients=recipients,
            results=email_results,
            metadata={"scope": scope, "priority": notice.get("priority")},
        )

        if resolved_target_user_ids:
            await create_notifications_bulk(
                title=notice.get("title") or "Announcement",
                message=notice.get("message") or "",
                priority=notice.get("priority") or "normal",
                scope="notice",
                target_user_ids=resolved_target_user_ids,
                created_by=notice.get("created_by"),
                batch_size=1000,
                track_delivery=False,
                send_email=False,
            )
        fanout_count = len(resolved_target_user_ids)
        await db.notices.update_one(
            {"_id": notice["_id"]},
            {
                "$set": {
                    "fanout_status": "dispatched",
                    "fanout_last_attempt_at": _utcnow(),
                    "fanout_next_retry_at": None,
                    "fanout_dispatched_at": datetime.now(timezone.utc),
                    "fanout_count": fanout_count,
                    "fanout_failed_at": None,
                    "fanout_error": None,
                    "fanout_processing_started_at": None,
                    "fanout_processing_expires_at": None,
                    "schema_version": NOTICE_SCHEMA_VERSION,
                }
            },
        )
        return True
    except Exception as exc:
        now = _utcnow()
        should_retry = 0 < claimed_attempt < _retry_limit()
        next_retry_at = _retry_at(attempt_number=claimed_attempt, now=now) if should_retry else None
        await db.notices.update_one(
            {"_id": notice_object_id},
            {
                "$set": {
                    "fanout_status": "retry_scheduled" if should_retry else "failed",
                    "fanout_failed_at": now,
                    "fanout_error": str(exc)[:500],
                    "fanout_next_retry_at": next_retry_at,
                    "fanout_processing_started_at": None,
                    "fanout_processing_expires_at": None,
                    "schema_version": NOTICE_SCHEMA_VERSION,
                }
            },
        )
        # Background jobs must never break request flow.
        return False


async def run_daily_analytics_snapshot_job() -> None:
    try:
        await compute_platform_snapshot()
    except Exception:
        return


async def dispatch_scheduled_notice_notifications(*, limit: int = 200) -> int:
    try:
        now = _utcnow()
        rows = await db.notices.find(
            {
                "is_active": True,
                "scheduled_at": {"$lte": now},
                "$or": [
                    {"fanout_dispatched_at": {"$exists": False}},
                    {"fanout_dispatched_at": None},
                ],
            },
        ).sort("scheduled_at", 1).to_list(length=max(limit * 5, 5000))
        dispatched = 0
        for row in rows:
            if dispatched >= limit:
                break
            if not _notice_is_due_for_dispatch(row, now=now):
                continue
            notice_id = row.get("_id")
            if not notice_id:
                continue
            if await fanout_notice_notifications(str(notice_id)):
                dispatched += 1
        return dispatched
    except Exception:
        return 0


async def get_scheduled_notice_dispatch_health() -> dict[str, Any]:
    now = _utcnow()
    rows = await db.notices.find(
        {
            "is_active": True,
            "scheduled_at": {"$ne": None},
            "$or": [
                {"fanout_dispatched_at": {"$exists": False}},
                {"fanout_dispatched_at": None},
            ],
        }
    ).to_list(length=5000)

    pending_total = len(rows)
    due_rows = [row for row in rows if _notice_is_due_for_dispatch(row, now=now)]
    due_now_total = len(due_rows)
    retry_pending_total = len(
        [
            row
            for row in rows
            if (_to_aware_utc(row.get("fanout_next_retry_at")) or now) > now
        ]
    )
    in_progress_total = len(
        [
            row
            for row in rows
            if str(row.get("fanout_status") or "").strip().lower() == "dispatching"
            and (_to_aware_utc(row.get("fanout_processing_expires_at")) or now) > now
        ]
    )
    terminal_failed_total = len([row for row in rows if _notice_has_terminal_failure(row, now=now)])
    oldest_due_at = min((_to_aware_utc(row.get("scheduled_at")) for row in due_rows), default=None)
    oldest_due_age_seconds = int((now - oldest_due_at).total_seconds()) if oldest_due_at else None

    return {
        "pending_total": pending_total,
        "due_now_total": due_now_total,
        "retry_pending_total": retry_pending_total,
        "in_progress_total": in_progress_total,
        "terminal_failed_total": terminal_failed_total,
        "oldest_due_at": oldest_due_at,
        "oldest_due_age_seconds": oldest_due_age_seconds,
        "retry_limit": _retry_limit(),
        "retry_backoff_seconds": max(30, int(settings.scheduled_notice_retry_backoff_seconds)),
        "dispatch_lease_seconds": _dispatch_lease_seconds(),
    }


async def dispatch_due_grievance_escalations(*, limit: int = 200) -> int:
    try:
        return await escalate_due_grievances(limit=limit)
    except Exception:
        return 0


async def dispatch_delivery_anomaly_escalations(*, days: int = 3) -> int:
    try:
        alerts = await get_delivery_anomaly_alerts(days=max(1, min(days, 365)))
        routing_result = await route_operational_alert_notifications(alerts=alerts, database=db)
        if routing_result.get("routed_alert_codes") or routing_result.get("resolved_alert_codes"):
            severity = "high" if routing_result.get("routed_alert_codes") else "low"
            detail = (
                f"Routed delivery alerts: {', '.join(routing_result.get('routed_alert_codes') or []) or 'none'}; "
                f"resolved delivery alerts: {', '.join(routing_result.get('resolved_alert_codes') or []) or 'none'}; "
                f"notifications_created={int(routing_result.get('notifications_created') or 0)}"
            )
            await log_audit_event(
                actor_user_id=None,
                action="communication_delivery_anomaly_escalation",
                action_type="communication_delivery_anomaly_escalation",
                entity_type="communication_delivery",
                detail=detail,
                new_value=routing_result,
                severity=severity,
            )
        return int(routing_result.get("notifications_created") or 0)
    except Exception:
        return 0
