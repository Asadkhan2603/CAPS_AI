from typing import Any, Dict

from app.core.schema_versions import ANALYTICS_SNAPSHOT_SCHEMA_VERSION, normalize_schema_version


def analytics_snapshot_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "date": document.get("date"),
        "users_total": int(document.get("users_total") or 0),
        "active_students": int(document.get("active_students") or 0),
        "daily_active_users": int(document.get("daily_active_users") or 0),
        "login_count_24h": int(document.get("login_count_24h") or 0),
        "assignment_completion_pct": float(document.get("assignment_completion_pct") or 0.0),
        "club_participation_pct": float(document.get("club_participation_pct") or 0.0),
        "event_attendance_pct": float(document.get("event_attendance_pct") or 0.0),
        "pending_review_tickets": int(document.get("pending_review_tickets") or 0),
        "active_clubs": int(document.get("active_clubs") or 0),
        "events_this_week": int(document.get("events_this_week") or 0),
        "updated_at": document.get("updated_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=ANALYTICS_SNAPSHOT_SCHEMA_VERSION,
        ),
    }
