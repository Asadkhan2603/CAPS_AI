from __future__ import annotations

from pymongo import ASCENDING
from pymongo.errors import OperationFailure

from app.core.database import db

_indexes_ensured = False


async def _safe_create_index(collection, keys, **kwargs) -> None:
    try:
        await collection.create_index(keys, **kwargs)
    except OperationFailure as exc:
        # Accept existing index with different generated name/options to keep startup resilient.
        if getattr(exc, "code", None) in {85, 86}:
            return
        raise


async def ensure_indexes() -> None:
    global _indexes_ensured
    if _indexes_ensured:
        return

    await _safe_create_index(db.users, [('email', ASCENDING)], unique=True)
    await _safe_create_index(db.notices, [('is_active', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.notices, [('scope', ASCENDING), ('scope_ref_id', ASCENDING)])
    await _safe_create_index(db.assignments, [('created_by', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.submissions, [('assignment_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.evaluations, [('student_user_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.evaluations, [('teacher_user_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.notifications, [('target_user_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.audit_logs, [('created_at', ASCENDING)])
    await _safe_create_index(db.clubs, [('slug', ASCENDING), ('academic_year', ASCENDING)], unique=True)
    await _safe_create_index(db.clubs, [('status', ASCENDING), ('updated_at', ASCENDING)])
    await _safe_create_index(db.clubs, [('coordinator_user_id', ASCENDING)])
    await _safe_create_index(db.club_members, [('club_id', ASCENDING), ('student_user_id', ASCENDING)], unique=True)
    await _safe_create_index(db.club_members, [('club_id', ASCENDING), ('status', ASCENDING)])
    await _safe_create_index(db.club_applications, [('club_id', ASCENDING), ('student_user_id', ASCENDING), ('status', ASCENDING)])
    await _safe_create_index(db.club_events, [('club_id', ASCENDING), ('status', ASCENDING), ('event_date', ASCENDING)])
    await _safe_create_index(db.event_registrations, [('event_id', ASCENDING), ('student_user_id', ASCENDING)])

    _indexes_ensured = True
