from __future__ import annotations

from pymongo import ASCENDING
from pymongo.errors import DuplicateKeyError, OperationFailure

from app.core.database import db

_indexes_ensured = False


async def _safe_create_index(collection, keys, **kwargs) -> None:
    try:
        await collection.create_index(keys, **kwargs)
    except OperationFailure as exc:
        # Accept existing index with different generated name/options to keep startup resilient.
        if getattr(exc, "code", None) in {85, 86, 11000}:
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
    await _safe_create_index(db.audit_logs, [('resource_type', ASCENDING), ('severity', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.clubs, [('slug', ASCENDING), ('academic_year', ASCENDING)], unique=True)
    await _safe_create_index(db.clubs, [('status', ASCENDING), ('updated_at', ASCENDING)])
    await _safe_create_index(db.clubs, [('coordinator_user_id', ASCENDING)])
    await _safe_create_index(db.club_members, [('club_id', ASCENDING), ('student_user_id', ASCENDING)], unique=True)
    await _safe_create_index(db.club_members, [('club_id', ASCENDING), ('status', ASCENDING)])
    await _safe_create_index(db.club_applications, [('club_id', ASCENDING), ('student_user_id', ASCENDING), ('status', ASCENDING)])
    await _safe_create_index(db.club_events, [('club_id', ASCENDING), ('status', ASCENDING), ('event_date', ASCENDING)])
    await _safe_create_index(db.event_registrations, [('event_id', ASCENDING), ('student_user_id', ASCENDING)])
    await _safe_create_index(db.token_blacklist, [('jti', ASCENDING)], unique=True)
    await _safe_create_index(db.token_blacklist, [('expires_at', ASCENDING)], expireAfterSeconds=0)
    await _safe_create_index(db.user_sessions, [('user_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.user_sessions, [('refresh_jti', ASCENDING)], unique=True)
    await _safe_create_index(db.user_sessions, [('revoked_at', ASCENDING)])
    await _safe_create_index(db.audit_logs_immutable, [('created_at', ASCENDING)])
    await _safe_create_index(db.audit_logs_immutable, [('integrity_hash', ASCENDING)], unique=True)
    await _safe_create_index(db.admin_action_reviews, [('status', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.admin_action_reviews, [('entity_type', ASCENDING), ('entity_id', ASCENDING)])
    await _safe_create_index(db.recovery_logs, [('created_at', ASCENDING)])
    await _safe_create_index(db.assignments, [('is_deleted', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.club_events, [('is_deleted', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.courses, [('is_deleted', ASCENDING)])
    await _safe_create_index(db.departments, [('is_deleted', ASCENDING)])
    await _safe_create_index(db.branches, [('is_deleted', ASCENDING)])
    await _safe_create_index(db.years, [('is_deleted', ASCENDING)])
    await _safe_create_index(db.classes, [('is_deleted', ASCENDING)])
    await _safe_create_index(db.notices, [('is_deleted', ASCENDING), ('deleted_at', ASCENDING)])

    _indexes_ensured = True
