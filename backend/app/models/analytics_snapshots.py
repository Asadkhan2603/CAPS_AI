from typing import Any, Dict

from app.core.schema_versions import ANALYTICS_SNAPSHOT_SCHEMA_VERSION, normalize_schema_version


def analytics_snapshot_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "date": document.get("date"),
        "users_total": int(document.get("users_total") or 0),
        "students_total": int(document.get("students_total") or 0),
        "programs_total": int(document.get("programs_total") or 0),
        "batches_total": int(document.get("batches_total") or 0),
        "semesters_total": int(document.get("semesters_total") or 0),
        "classes_total": int(document.get("classes_total") or 0),
        "subjects_total": int(document.get("subjects_total") or 0),
        "active_students": int(document.get("active_students") or 0),
        "assignments_total": int(document.get("assignments_total") or 0),
        "submissions_total": int(document.get("submissions_total") or 0),
        "evaluations_total": int(document.get("evaluations_total") or 0),
        "similarity_flags_total": int(document.get("similarity_flags_total") or 0),
        "notices_total": int(document.get("notices_total") or 0),
        "clubs_total": int(document.get("clubs_total") or 0),
        "club_events_total": int(document.get("club_events_total") or 0),
        "daily_active_users": int(document.get("daily_active_users") or 0),
        "login_count_24h": int(document.get("login_count_24h") or 0),
        "assignment_completion_pct": float(document.get("assignment_completion_pct") or 0.0),
        "club_participation_pct": float(document.get("club_participation_pct") or 0.0),
        "event_attendance_pct": float(document.get("event_attendance_pct") or 0.0),
        "pending_review_tickets": int(document.get("pending_review_tickets") or 0),
        "system_errors_24h": int(document.get("system_errors_24h") or 0),
        "review_ticket_sla_hours": float(document.get("review_ticket_sla_hours") or 0.0),
        "active_clubs": int(document.get("active_clubs") or 0),
        "events_this_week": int(document.get("events_this_week") or 0),
        "updated_at": document.get("updated_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=ANALYTICS_SNAPSHOT_SCHEMA_VERSION,
        ),
    }
