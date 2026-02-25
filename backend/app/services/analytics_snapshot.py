from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.core.database import db
from app.core.redis_store import redis_store


def _today_key() -> str:
    return date.today().isoformat()


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
    active_club_members = await db.club_members.count_documents({"status": "active"})
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

    snapshot = {
        "date": key,
        "users_total": users_total,
        "active_students": active_students,
        "daily_active_users": daily_active_users,
        "login_count_24h": login_count_24h,
        "assignment_completion_pct": assignment_completion_pct,
        "club_participation_pct": club_participation_pct,
        "event_attendance_pct": event_attendance_pct,
        "pending_review_tickets": pending_tickets,
        "active_clubs": clubs_total,
        "events_this_week": await db.club_events.count_documents({"event_date": {"$gte": now, "$lte": week_ahead}}),
        "updated_at": now,
    }

    await db.analytics_snapshots.update_one({"date": key}, {"$set": snapshot}, upsert=True)
    await redis_store.set_json(f"analytics:snapshot:{key}", snapshot, ttl_seconds=settings.analytics_cache_ttl_seconds)
    return snapshot


async def get_daily_snapshot(*, snapshot_date: str | None = None) -> dict[str, Any] | None:
    key = snapshot_date or _today_key()
    cached = await redis_store.get_json(f"analytics:snapshot:{key}")
    if cached:
        return cached
    doc = await db.analytics_snapshots.find_one({"date": key})
    if doc:
        await redis_store.set_json(f"analytics:snapshot:{key}", doc, ttl_seconds=settings.analytics_cache_ttl_seconds)
    return doc


async def get_snapshot_history(*, limit: int = 30) -> list[dict[str, Any]]:
    rows = await db.analytics_snapshots.find({}).sort("date", -1).limit(limit).to_list(length=limit)
    return rows
