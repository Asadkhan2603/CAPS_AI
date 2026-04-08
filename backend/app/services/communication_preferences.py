from __future__ import annotations

from typing import Any, Iterable

from bson import ObjectId

from app.core.database import db
from app.models.users import normalize_communication_preferences

_SCOPE_KEY_MAP = {
    "global": "global_scope",
    "notice": "notice",
    "similarity": "similarity",
    "ai": "ai",
    "system": "system",
}


def _scope_key(scope: str | None) -> str:
    normalized = str(scope or "global").strip().lower()
    return _SCOPE_KEY_MAP.get(normalized, "global_scope")


def resolve_notification_delivery_preferences(user_doc: dict[str, Any] | None, *, scope: str) -> dict[str, Any]:
    preferences = normalize_communication_preferences((user_doc or {}).get("communication_preferences"))
    scope_preferences = preferences.get("notification_scope_preferences") or {}
    scoped = scope_preferences.get(_scope_key(scope), {}) or {}

    in_app_override = scoped.get("in_app")
    in_app_enabled = bool(preferences.get("notification_in_app", True)) if in_app_override is None else bool(in_app_override)

    base_email_mode = str(preferences.get("notification_email_mode") or "instant").strip().lower()
    if preferences.get("notification_email") is False:
        base_email_mode = "off"
    scope_email_mode = str(scoped.get("email_mode") or "inherit").strip().lower()
    effective_email_mode = base_email_mode if scope_email_mode == "inherit" else scope_email_mode

    return {
        "in_app": in_app_enabled,
        "email_mode": effective_email_mode,
        "digest_preferences": preferences.get("digest_preferences") or {},
        "preferences": preferences,
    }


async def _users_by_recipient_ids(recipients: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    user_ids = [
        ObjectId(str(recipient.get("user_id")))
        for recipient in recipients
        if recipient.get("user_id") and ObjectId.is_valid(str(recipient.get("user_id")))
    ]
    if not user_ids:
        return {}
    rows = await db.users.find({"_id": {"$in": user_ids}}).to_list(length=max(len(user_ids), 1))
    return {str(row.get("_id")): row for row in rows if row.get("_id")}


async def partition_email_recipients_by_preference(
    *,
    recipients: Iterable[dict[str, Any]],
    preference_key: str,
    disabled_reason: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    recipient_list = [dict(recipient) for recipient in recipients]
    users_by_id = await _users_by_recipient_ids(recipient_list)

    allowed: list[dict[str, Any]] = []
    skipped_results: list[dict[str, Any]] = []
    for recipient in recipient_list:
        user_id = str(recipient.get("user_id") or "").strip()
        user_doc = users_by_id.get(user_id)
        if user_doc is None:
            allowed.append(recipient)
            continue

        preferences = normalize_communication_preferences(user_doc.get("communication_preferences"))
        if preferences.get(preference_key, True):
            allowed.append(recipient)
            continue

        skipped_results.append(
            {
                "user_id": user_id or None,
                "email": recipient.get("email"),
                "status": "skipped",
                "error": disabled_reason,
                "sent_at": None,
                "metadata": {"preference_key": preference_key},
            }
        )

    return allowed, skipped_results


async def partition_notification_recipients_by_preferences(
    *,
    recipients: Iterable[dict[str, Any]],
    scope: str,
) -> dict[str, Any]:
    recipient_list = [dict(recipient) for recipient in recipients]
    users_by_id = await _users_by_recipient_ids(recipient_list)

    result = {
        "in_app_recipients": [],
        "instant_email_recipients": [],
        "digest_recipients": {"daily_digest": [], "weekly_digest": []},
        "in_app_skips": [],
        "email_skips": [],
    }

    for recipient in recipient_list:
        user_id = str(recipient.get("user_id") or "").strip()
        user_doc = users_by_id.get(user_id)
        effective = resolve_notification_delivery_preferences(user_doc, scope=scope)
        digest_preferences = effective.get("digest_preferences") or {}

        if effective.get("in_app", True):
            result["in_app_recipients"].append(recipient)
        else:
            result["in_app_skips"].append(
                {
                    "user_id": user_id or None,
                    "email": recipient.get("email"),
                    "status": "skipped",
                    "error": f"Recipient disabled in-app notifications for {scope or 'global'} scope",
                    "sent_at": None,
                    "metadata": {"scope": scope, "channel": "in_app"},
                }
            )

        email_mode = str(effective.get("email_mode") or "instant").strip().lower()
        if email_mode == "off":
            result["email_skips"].append(
                {
                    "user_id": user_id or None,
                    "email": recipient.get("email"),
                    "status": "skipped",
                    "error": f"Recipient disabled email notifications for {scope or 'global'} scope",
                    "sent_at": None,
                    "metadata": {"scope": scope, "email_mode": "off"},
                }
            )
        elif email_mode in {"daily_digest", "weekly_digest"}:
            result["digest_recipients"][email_mode].append(
                {
                    **recipient,
                    "digest_preferences": digest_preferences,
                }
            )
        else:
            result["instant_email_recipients"].append(recipient)

    return result
