from copy import deepcopy
from typing import Any, Dict

from app.core.schema_versions import USER_SCHEMA_VERSION, normalize_schema_version


DEFAULT_COMMUNICATION_PREFERENCES = {
    "announcement_email": True,
    "club_announcement_email": True,
    "notification_email": True,
    "notification_in_app": True,
    "notification_email_mode": "instant",
    "notification_scope_preferences": {
        "global_scope": {"in_app": None, "email_mode": "inherit"},
        "notice": {"in_app": None, "email_mode": "inherit"},
        "similarity": {"in_app": None, "email_mode": "inherit"},
        "ai": {"in_app": None, "email_mode": "inherit"},
        "system": {"in_app": None, "email_mode": "inherit"},
    },
    "digest_preferences": {
        "daily_digest_hour_utc": 8,
        "weekly_digest_day_of_week": 0,
    },
}

_VALID_NOTIFICATION_EMAIL_MODES = {"off", "instant", "daily_digest", "weekly_digest"}
_VALID_SCOPE_EMAIL_MODES = {"inherit", *tuple(_VALID_NOTIFICATION_EMAIL_MODES)}
_KNOWN_NOTIFICATION_SCOPE_KEYS = tuple(DEFAULT_COMMUNICATION_PREFERENCES["notification_scope_preferences"].keys())


def _normalize_notification_email_mode(value: Any, *, fallback: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in _VALID_NOTIFICATION_EMAIL_MODES else fallback


def _normalize_scope_email_mode(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in _VALID_SCOPE_EMAIL_MODES else "inherit"


def _normalize_digest_preferences(raw: Any) -> Dict[str, int]:
    defaults = deepcopy(DEFAULT_COMMUNICATION_PREFERENCES["digest_preferences"])
    source = raw if isinstance(raw, dict) else {}
    try:
        daily_hour = int(source.get("daily_digest_hour_utc", defaults["daily_digest_hour_utc"]))
    except (TypeError, ValueError):
        daily_hour = defaults["daily_digest_hour_utc"]
    try:
        weekly_day = int(source.get("weekly_digest_day_of_week", defaults["weekly_digest_day_of_week"]))
    except (TypeError, ValueError):
        weekly_day = defaults["weekly_digest_day_of_week"]
    defaults["daily_digest_hour_utc"] = min(max(daily_hour, 0), 23)
    defaults["weekly_digest_day_of_week"] = min(max(weekly_day, 0), 6)
    return defaults


def _normalize_notification_scope_preferences(raw: Any) -> Dict[str, Dict[str, Any]]:
    normalized = deepcopy(DEFAULT_COMMUNICATION_PREFERENCES["notification_scope_preferences"])
    source = raw if isinstance(raw, dict) else {}
    for key in _KNOWN_NOTIFICATION_SCOPE_KEYS:
        current = source.get(key)
        if not isinstance(current, dict):
            continue
        in_app = current.get("in_app")
        normalized[key]["in_app"] = None if in_app is None else bool(in_app)
        normalized[key]["email_mode"] = _normalize_scope_email_mode(current.get("email_mode"))
    return normalized


def normalize_communication_preferences(document: Dict[str, Any] | None) -> Dict[str, Any]:
    raw = document if isinstance(document, dict) else {}
    normalized = deepcopy(DEFAULT_COMMUNICATION_PREFERENCES)
    normalized["announcement_email"] = bool(raw.get("announcement_email", normalized["announcement_email"]))
    normalized["club_announcement_email"] = bool(raw.get("club_announcement_email", normalized["club_announcement_email"]))
    normalized["notification_in_app"] = bool(raw.get("notification_in_app", normalized["notification_in_app"]))

    legacy_notification_email = raw.get("notification_email")
    fallback_mode = "instant" if legacy_notification_email is not False else "off"
    normalized["notification_email_mode"] = _normalize_notification_email_mode(
        raw.get("notification_email_mode"),
        fallback=fallback_mode,
    )
    normalized["notification_email"] = bool(
        legacy_notification_email if legacy_notification_email is not None else normalized["notification_email_mode"] != "off"
    )
    normalized["notification_scope_preferences"] = _normalize_notification_scope_preferences(
        raw.get("notification_scope_preferences")
    )
    normalized["digest_preferences"] = _normalize_digest_preferences(raw.get("digest_preferences"))
    return normalized


def user_public(document: Dict[str, Any]) -> Dict[str, Any]:
    user_id = str(document["_id"])
    return {
        "id": user_id,
        "full_name": document.get("full_name", ""),
        "email": document.get("email", ""),
        "role": document.get("role", ""),
        "admin_type": document.get("admin_type", "admin" if document.get("role") == "admin" else None),
        "extended_roles": document.get("extended_roles", []),
        "role_scope": document.get("role_scope", {}) or {},
        "is_active": document.get("is_active", True),
        "must_change_password": document.get("must_change_password", False),
        "profile": document.get("profile", {}) or {},
        "communication_preferences": normalize_communication_preferences(document.get("communication_preferences")),
        "avatar_url": f"/api/v1/auth/profile/avatar/{user_id}" if document.get("avatar_filename") else None,
        "avatar_updated_at": document.get("avatar_updated_at"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=USER_SCHEMA_VERSION,
        ),
    }
