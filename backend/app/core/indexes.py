from __future__ import annotations

from pymongo import ASCENDING

from app.core.database import db

_indexes_ensured = False


async def ensure_indexes() -> None:
    global _indexes_ensured
    if _indexes_ensured:
        return

    await db.users.create_index([('email', ASCENDING)], unique=True, name='uniq_users_email')
    await db.notices.create_index([('is_active', ASCENDING), ('created_at', ASCENDING)], name='idx_notices_active_created')
    await db.notices.create_index([('scope', ASCENDING), ('scope_ref_id', ASCENDING)], name='idx_notices_scope_ref')
    await db.assignments.create_index([('created_by', ASCENDING), ('created_at', ASCENDING)], name='idx_assignments_creator_created')
    await db.submissions.create_index([('assignment_id', ASCENDING), ('created_at', ASCENDING)], name='idx_submissions_assignment_created')
    await db.evaluations.create_index([('student_user_id', ASCENDING), ('created_at', ASCENDING)], name='idx_eval_student_created')
    await db.evaluations.create_index([('teacher_user_id', ASCENDING), ('created_at', ASCENDING)], name='idx_eval_teacher_created')
    await db.notifications.create_index([('target_user_id', ASCENDING), ('created_at', ASCENDING)], name='idx_notifications_target_created')
    await db.audit_logs.create_index([('created_at', ASCENDING)], name='idx_audit_created')

    _indexes_ensured = True
