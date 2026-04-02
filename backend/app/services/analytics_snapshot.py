from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.core.database import db
from app.core.redis_store import redis_store
from app.core.schema_versions import ANALYTICS_SNAPSHOT_SCHEMA_VERSION
from app.models.analytics_snapshots import analytics_snapshot_public


def _today_key() -> str:
    return date.today().isoformat()


def _as_utc_datetime(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def _average_review_ticket_sla_hours(*, day_ago: datetime) -> float:
    rows = await db.review_tickets.find(
        {
            "resolved_at": {"$gte": day_ago},
            "created_at": {"$exists": True},
        },
        {"created_at": 1, "resolved_at": 1},
    ).to_list(length=5000)
    durations: list[float] = []
    for row in rows:
        created_at = _as_utc_datetime(row.get("created_at"))
        resolved_at = _as_utc_datetime(row.get("resolved_at"))
        if not created_at or not resolved_at or resolved_at < created_at:
            continue
        durations.append((resolved_at - created_at).total_seconds() / 3600)
    if not durations:
        return 0.0
    return round(sum(durations) / len(durations), 2)


async def _active_club_members_count() -> int:
    club_members = getattr(db, "club_members", None)
    if club_members is None:
        return 0
    return int(await club_members.count_documents({"status": "active"}))


def _snapshot_age_hours(snapshot: dict[str, Any]) -> int | None:
    updated_at = _as_utc_datetime(snapshot.get("updated_at"))
    if not updated_at:
        return None
    return max(0, int((datetime.now(timezone.utc) - updated_at).total_seconds() // 3600))


def build_admin_analytics_overview(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "total_users": int(snapshot.get("users_total") or 0),
        "active_students": int(snapshot.get("active_students") or 0),
        "active_clubs": int(snapshot.get("active_clubs") or 0),
        "pending_review_tickets": int(snapshot.get("pending_review_tickets") or 0),
        "assignments_total": int(snapshot.get("assignments_total") or 0),
        "submissions_total": int(snapshot.get("submissions_total") or 0),
        "events_this_week": int(snapshot.get("events_this_week") or 0),
        "system_errors_24h": int(snapshot.get("system_errors_24h") or 0),
    }


async def compute_platform_snapshot(*, snapshot_date: str | None = None) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    key = snapshot_date or _today_key()
    day_ago = now - timedelta(hours=24)
    week_ahead = now + timedelta(days=7)

    users_total = await db.users.count_documents({})
    active_students = await db.students.count_documents({"is_active": True})
    assignments_total = await db.assignments.count_documents({})
    submissions_total = await db.submissions.count_documents({})
    assignment_completion_pct = round((submissions_total / assignments_total) * 100, 2) if assignments_total else 0.0

    clubs_total = await db.clubs.count_documents({"status": {"$in": ["active", "registration_closed"]}})
    active_club_members = await _active_club_members_count()
    club_participation_pct = round((active_club_members / active_students) * 100, 2) if active_students else 0.0

    events_total = await db.club_events.count_documents({})
    event_registrations = await db.event_registrations.count_documents({"status": {"$in": ["registered", "approved"]}})
    event_attendance_pct = round((event_registrations / events_total) * 100, 2) if events_total else 0.0

    pending_tickets = await db.review_tickets.count_documents({"status": {"$in": ["pending", "open"]}})
    login_count_24h = await db.audit_logs.count_documents(
        {"action_type": "login", "created_at": {"$gte": day_ago}, "actor_user_id": {"$ne": None}}
    )
    daily_active_user_ids = await db.audit_logs.distinct(
        "actor_user_id",
        {"action_type": "login", "created_at": {"$gte": day_ago}, "actor_user_id": {"$ne": None}},
    )
    daily_active_users = len(daily_active_user_ids)
    system_errors_24h = await db.audit_logs.count_documents(
        {
            "created_at": {"$gte": day_ago},
            "$or": [
                {"action": {"$in": ["error", "exception"]}},
                {"severity": "high"},
            ],
        }
    )
    review_ticket_sla_hours = await _average_review_ticket_sla_hours(day_ago=day_ago)

    snapshot = {
        "date": key,
        "users_total": users_total,
        "active_students": active_students,
        "assignments_total": assignments_total,
        "submissions_total": submissions_total,
        "daily_active_users": daily_active_users,
        "login_count_24h": login_count_24h,
        "assignment_completion_pct": assignment_completion_pct,
        "club_participation_pct": club_participation_pct,
        "event_attendance_pct": event_attendance_pct,
        "pending_review_tickets": pending_tickets,
        "system_errors_24h": system_errors_24h,
        "review_ticket_sla_hours": review_ticket_sla_hours,
        "active_clubs": clubs_total,
        "events_this_week": await db.club_events.count_documents({"event_date": {"$gte": now, "$lte": week_ahead}}),
        "updated_at": now,
        "schema_version": ANALYTICS_SNAPSHOT_SCHEMA_VERSION,
    }

    await db.analytics_snapshots.update_one({"date": key}, {"$set": snapshot}, upsert=True)
    public_snapshot = analytics_snapshot_public(snapshot)
    await redis_store.set_json(
        f"analytics:snapshot:{key}",
        public_snapshot,
        ttl_seconds=settings.analytics_cache_ttl_seconds,
    )
    return public_snapshot


async def get_daily_snapshot(*, snapshot_date: str | None = None) -> dict[str, Any] | None:
    key = snapshot_date or _today_key()
    cached = await redis_store.get_json(f"analytics:snapshot:{key}")
    if cached:
        return analytics_snapshot_public(cached)
    doc = await db.analytics_snapshots.find_one({"date": key})
    if doc:
        public_doc = analytics_snapshot_public(doc)
        await redis_store.set_json(
            f"analytics:snapshot:{key}",
            public_doc,
            ttl_seconds=settings.analytics_cache_ttl_seconds,
        )
        return public_doc
    return None


async def get_snapshot_history(*, limit: int = 30) -> list[dict[str, Any]]:
    rows = await db.analytics_snapshots.find({}).sort("date", -1).limit(limit).to_list(length=limit)
    return [analytics_snapshot_public(row) for row in rows]


async def get_latest_snapshot(
    *,
    max_age_hours: int | None = None,
) -> tuple[dict[str, Any] | None, int | None]:
    doc = await db.analytics_snapshots.find_one({}, sort=[("updated_at", -1)])
    if not doc:
        return None, None
    public_doc = analytics_snapshot_public(doc)
    age_hours = _snapshot_age_hours(public_doc)
    freshness_hours = max(1, int(max_age_hours or settings.analytics_snapshot_freshness_hours))
    if age_hours is not None and age_hours > freshness_hours:
        return None, age_hours
    return public_doc, age_hours
