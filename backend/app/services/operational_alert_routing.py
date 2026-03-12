from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.core.database import db
from app.core.schema_versions import OPERATIONAL_ALERT_ROUTE_SCHEMA_VERSION
from app.services.notifications import create_notifications_bulk

ALERT_NOTIFICATION_SCOPE = "system"
SYSTEM_READ_ADMIN_TYPES = {"super_admin", "admin", "compliance_admin"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _priority_for_level(level: str | None) -> str:
    normalized = str(level or "").lower()
    if normalized in {"critical", "high"}:
        return "urgent"
    if normalized == "medium":
        return "normal"
    return "info"


def _notification_title(*, level: str, resolved: bool) -> str:
    if resolved:
        return "System alert resolved"
    return f"System alert: {level.title()}"


def _notification_message(*, code: str, message: str, resolved: bool) -> str:
    prefix = "Resolved" if resolved else "Active"
    return f"{prefix} system alert [{code}]: {message}"


async def _system_read_admin_user_ids(*, database: Any) -> list[str]:
    rows = await database.users.find(
        {
            "role": "admin",
            "is_active": {"$ne": False},
            "$or": [
                {"admin_type": {"$in": sorted(SYSTEM_READ_ADMIN_TYPES)}},
                {"admin_type": {"$exists": False}},
                {"admin_type": None},
            ],
        },
        {"_id": 1},
    ).to_list(length=500)
    return [str(row["_id"]) for row in rows if row.get("_id")]


async def route_operational_alert_notifications(
    *,
    alerts: list[dict[str, Any]],
    database: Any = db,
    now: datetime | None = None,
) -> dict[str, Any]:
    timestamp = now or _now()
    routed_alert_codes: list[str] = []
    resolved_alert_codes: list[str] = []
    notifications_created = 0

    if not settings.operational_alert_notifications_enabled:
        return {
            "enabled": False,
            "cooldown_minutes": settings.operational_alert_notification_cooldown_minutes,
            "routed_alert_codes": routed_alert_codes,
            "resolved_alert_codes": resolved_alert_codes,
            "notifications_created": notifications_created,
        }

    target_user_ids = await _system_read_admin_user_ids(database=database)
    if not target_user_ids:
        return {
            "enabled": True,
            "cooldown_minutes": settings.operational_alert_notification_cooldown_minutes,
            "routed_alert_codes": routed_alert_codes,
            "resolved_alert_codes": resolved_alert_codes,
            "notifications_created": notifications_created,
        }

    cooldown = timedelta(minutes=max(1, settings.operational_alert_notification_cooldown_minutes))
    active_codes: set[str] = set()

    for alert in alerts:
        code = str(alert.get("code") or "").strip()
        if not code:
            continue
        active_codes.add(code)
        level = str(alert.get("level") or "medium").lower()
        message = str(alert.get("message") or "").strip()
        state = await database.operational_alert_routes.find_one({"alert_code": code})
        last_sent_at = state.get("last_sent_at") if state else None
        should_send = (
            state is None
            or not bool(state.get("is_active"))
            or state.get("level") != level
            or not isinstance(last_sent_at, datetime)
            or (timestamp - last_sent_at) >= cooldown
        )

        if should_send:
            notifications_created += await create_notifications_bulk(
                title=_notification_title(level=level, resolved=False),
                message=_notification_message(code=code, message=message, resolved=False),
                priority=_priority_for_level(level),
                scope=ALERT_NOTIFICATION_SCOPE,
                target_user_ids=target_user_ids,
                created_by=None,
            )
            routed_alert_codes.append(code)

        first_seen_at = state.get("first_seen_at") if state and state.get("first_seen_at") else timestamp
        update_fields = {
            "alert_code": code,
            "level": level,
            "message": message,
            "is_active": True,
            "first_seen_at": first_seen_at,
            "last_seen_at": timestamp,
            "resolved_at": None,
            "schema_version": OPERATIONAL_ALERT_ROUTE_SCHEMA_VERSION,
        }
        if should_send:
            update_fields["last_sent_at"] = timestamp
        await database.operational_alert_routes.update_one(
            {"alert_code": code},
            {"$set": update_fields},
            upsert=True,
        )

    active_states = await database.operational_alert_routes.find({"is_active": True}).to_list(length=200)
    for state in active_states:
        code = str(state.get("alert_code") or "").strip()
        if not code or code in active_codes:
            continue
        message = str(state.get("message") or "").strip()
        notifications_created += await create_notifications_bulk(
            title=_notification_title(level=str(state.get("level") or "medium"), resolved=True),
            message=_notification_message(code=code, message=message, resolved=True),
            priority="info",
            scope=ALERT_NOTIFICATION_SCOPE,
            target_user_ids=target_user_ids,
            created_by=None,
        )
        resolved_alert_codes.append(code)
        await database.operational_alert_routes.update_one(
            {"alert_code": code},
            {
                "$set": {
                    "is_active": False,
                    "last_seen_at": timestamp,
                    "resolved_at": timestamp,
                    "last_sent_at": timestamp,
                    "schema_version": OPERATIONAL_ALERT_ROUTE_SCHEMA_VERSION,
                }
            },
            upsert=False,
        )

    return {
        "enabled": True,
        "cooldown_minutes": settings.operational_alert_notification_cooldown_minutes,
        "target_user_count": len(target_user_ids),
        "routed_alert_codes": routed_alert_codes,
        "resolved_alert_codes": resolved_alert_codes,
        "notifications_created": notifications_created,
    }
