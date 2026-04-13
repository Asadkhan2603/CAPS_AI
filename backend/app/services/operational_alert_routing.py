from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.core.database import db
from app.core.schema_versions import OPERATIONAL_ALERT_ROUTE_SCHEMA_VERSION
from app.services.notifications import create_notifications_bulk

ALERT_NOTIFICATION_SCOPE = "system"
SYSTEM_READ_ADMIN_TYPES = {"super_admin", "admin", "compliance_admin"}
MAX_ROUTE_HISTORY_ENTRIES = 12


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


def _serialize_route_timestamp(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def _append_route_history(
    current: list[dict[str, Any]] | None,
    *,
    timestamp: datetime,
    action: str,
    level: str,
    message: str,
    notifications_created: int,
    target_user_count: int,
) -> list[dict[str, Any]]:
    next_history = list(current or [])
    next_history.append(
        {
            "timestamp": _serialize_route_timestamp(timestamp),
            "action": action,
            "level": level,
            "message": message,
            "notifications_created": int(notifications_created),
            "target_user_count": int(target_user_count),
        }
    )
    return next_history[-MAX_ROUTE_HISTORY_ENTRIES:]


def _alert_route_public(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "alert_code": document.get("alert_code"),
        "level": document.get("level"),
        "message": document.get("message"),
        "is_active": bool(document.get("is_active")),
        "first_seen_at": document.get("first_seen_at"),
        "last_seen_at": document.get("last_seen_at"),
        "last_sent_at": document.get("last_sent_at"),
        "resolved_at": document.get("resolved_at"),
        "last_routing_outcome": document.get("last_routing_outcome"),
        "last_routing_outcome_at": document.get("last_routing_outcome_at"),
        "routed_count": int(document.get("routed_count") or 0),
        "resolved_count": int(document.get("resolved_count") or 0),
        "cooldown_suppressed_count": int(document.get("cooldown_suppressed_count") or 0),
        "notifications_sent_total": int(document.get("notifications_sent_total") or 0),
        "history": list(document.get("history") or []),
        "schema_version": document.get("schema_version") or OPERATIONAL_ALERT_ROUTE_SCHEMA_VERSION,
    }


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
        routed_count = int(state.get("routed_count") or 0) if state else 0
        resolved_count = int(state.get("resolved_count") or 0) if state else 0
        cooldown_suppressed_count = int(state.get("cooldown_suppressed_count") or 0) if state else 0
        notifications_sent_total = int(state.get("notifications_sent_total") or 0) if state else 0
        history = list(state.get("history") or []) if state else []
        sent_count = 0

        if should_send:
            sent_count = await create_notifications_bulk(
                title=_notification_title(level=level, resolved=False),
                message=_notification_message(code=code, message=message, resolved=False),
                priority=_priority_for_level(level),
                scope=ALERT_NOTIFICATION_SCOPE,
                target_user_ids=target_user_ids,
                created_by=None,
                track_delivery=False,
                send_email=False,
            )
            notifications_created += sent_count
            routed_alert_codes.append(code)
            routed_count += 1
            notifications_sent_total += sent_count
            history = _append_route_history(
                history,
                timestamp=timestamp,
                action="routed",
                level=level,
                message=message,
                notifications_created=sent_count,
                target_user_count=len(target_user_ids),
            )
        else:
            cooldown_suppressed_count += 1

        first_seen_at = state.get("first_seen_at") if state and state.get("first_seen_at") else timestamp
        update_fields = {
            "alert_code": code,
            "level": level,
            "message": message,
            "is_active": True,
            "first_seen_at": first_seen_at,
            "last_seen_at": timestamp,
            "resolved_at": None,
            "routed_count": routed_count,
            "resolved_count": resolved_count,
            "cooldown_suppressed_count": cooldown_suppressed_count,
            "notifications_sent_total": notifications_sent_total,
            "history": history,
            "last_routing_outcome": "notification_sent" if should_send else "cooldown_suppressed",
            "last_routing_outcome_at": timestamp,
            "schema_version": OPERATIONAL_ALERT_ROUTE_SCHEMA_VERSION,
        }
        if should_send:
            update_fields["last_sent_at"] = timestamp
        elif state and state.get("last_sent_at"):
            update_fields["last_sent_at"] = state.get("last_sent_at")
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
        sent_count = await create_notifications_bulk(
            title=_notification_title(level=str(state.get("level") or "medium"), resolved=True),
            message=_notification_message(code=code, message=message, resolved=True),
            priority="info",
            scope=ALERT_NOTIFICATION_SCOPE,
            target_user_ids=target_user_ids,
            created_by=None,
            track_delivery=False,
            send_email=False,
        )
        notifications_created += sent_count
        resolved_alert_codes.append(code)
        resolved_count = int(state.get("resolved_count") or 0) + 1
        notifications_sent_total = int(state.get("notifications_sent_total") or 0) + sent_count
        history = _append_route_history(
            list(state.get("history") or []),
            timestamp=timestamp,
            action="resolved",
            level=str(state.get("level") or "medium"),
            message=message,
            notifications_created=sent_count,
            target_user_count=len(target_user_ids),
        )
        await database.operational_alert_routes.update_one(
            {"alert_code": code},
            {
                "$set": {
                    "is_active": False,
                    "last_seen_at": timestamp,
                    "resolved_at": timestamp,
                    "last_sent_at": timestamp,
                    "resolved_count": resolved_count,
                    "notifications_sent_total": notifications_sent_total,
                    "history": history,
                    "last_routing_outcome": "resolved",
                    "last_routing_outcome_at": timestamp,
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
        "active_alert_count": len(active_codes),
        "notifications_created": notifications_created,
    }


async def list_operational_alert_route_history(
    *,
    limit: int = 25,
    database: Any = db,
) -> list[dict[str, Any]]:
    scoped_limit = max(1, min(100, int(limit)))
    rows = await database.operational_alert_routes.find({}).sort("last_seen_at", -1).limit(scoped_limit).to_list(length=scoped_limit)
    return [_alert_route_public(row) for row in rows]
