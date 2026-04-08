from __future__ import annotations

from pymongo import ASCENDING
from pymongo.errors import OperationFailure

from app.core.database import db

_indexes_ensured = False
LEGACY_COMPATIBILITY_INDEX_COLLECTIONS = ("courses", "branches", "years")


async def _safe_create_index(collection, keys, **kwargs) -> None:
    try:
        await collection.create_index(keys, **kwargs)
    except OperationFailure as exc:
        # Accept existing index with different generated name/options to keep startup resilient.
        if getattr(exc, "code", None) in {85, 86, 11000}:
            return
        raise


async def _collection_exists(name: str) -> bool:
    try:
        existing = await db.list_collection_names()
    except Exception:
        return True
    return name in set(existing)


async def _ensure_legacy_compatibility_indexes() -> None:
    # Legacy academic collections stay indexable only for explicit recovery/translation flows.
    # Do not add new collections here unless they are already retired from the active router.
    for name in LEGACY_COMPATIBILITY_INDEX_COLLECTIONS:
        if not await _collection_exists(name):
            continue
        await _safe_create_index(getattr(db, name), [('is_active', ASCENDING), ('deleted_at', ASCENDING)])


async def ensure_indexes() -> None:
    global _indexes_ensured
    if _indexes_ensured:
        return

    await _safe_create_index(db.users, [('email', ASCENDING)], unique=True)
    await _safe_create_index(db.notices, [('is_active', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.notices, [('scope', ASCENDING), ('scope_ref_id', ASCENDING)])
    await _safe_create_index(
        db.notices,
        [('is_active', ASCENDING), ('scheduled_at', ASCENDING), ('fanout_dispatched_at', ASCENDING), ('fanout_next_retry_at', ASCENDING)],
    )
    await _safe_create_index(
        db.notices,
        [('fanout_status', ASCENDING), ('fanout_processing_expires_at', ASCENDING), ('scheduled_at', ASCENDING)],
    )
    await _safe_create_index(db.assignments, [('created_by', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.submissions, [('assignment_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.evaluations, [('student_user_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.evaluations, [('teacher_user_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.notifications, [('target_user_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.grievances, [('student_user_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.grievances, [('section_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.grievances, [('department_id', ASCENDING), ('current_stage', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.grievances, [('assigned_resolver_user_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.grievances, [('status', ASCENDING), ('stage_due_at', ASCENDING)])
    await _safe_create_index(db.communication_deliveries, [('source_kind', ASCENDING), ('source_id', ASCENDING), ('channel', ASCENDING), ('target_user_id', ASCENDING)])
    await _safe_create_index(db.communication_deliveries, [('source_kind', ASCENDING), ('source_id', ASCENDING), ('channel', ASCENDING), ('target_email', ASCENDING)])
    await _safe_create_index(db.communication_deliveries, [('target_user_id', ASCENDING), ('channel', ASCENDING), ('status', ASCENDING), ('updated_at', ASCENDING)])
    await _safe_create_index(
        db.communication_digests,
        [('status', ASCENDING), ('scheduled_for', ASCENDING), ('digest_frequency', ASCENDING)],
    )
    await _safe_create_index(
        db.communication_digests,
        [('source_kind', ASCENDING), ('source_id', ASCENDING), ('target_user_id', ASCENDING), ('digest_frequency', ASCENDING)],
    )
    await _safe_create_index(db.audit_logs, [('created_at', ASCENDING)])
    await _safe_create_index(db.audit_logs, [('resource_type', ASCENDING), ('severity', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.clubs, [('slug', ASCENDING), ('academic_year', ASCENDING)], unique=True)
    await _safe_create_index(db.clubs, [('status', ASCENDING), ('updated_at', ASCENDING)])
    await _safe_create_index(db.clubs, [('academic_year', ASCENDING), ('updated_at', ASCENDING)])
    await _safe_create_index(db.clubs, [('registration_open', ASCENDING), ('updated_at', ASCENDING)])
    await _safe_create_index(db.clubs, [('coordinator_user_id', ASCENDING)])
    await _safe_create_index(db.clubs, [('president_user_id', ASCENDING)])
    await _safe_create_index(db.club_members, [('club_id', ASCENDING), ('student_user_id', ASCENDING)], unique=True)
    await _safe_create_index(db.club_members, [('club_id', ASCENDING), ('status', ASCENDING)])
    await _safe_create_index(db.club_members, [('club_id', ASCENDING), ('joined_at', ASCENDING)])
    await _safe_create_index(db.club_members, [('student_user_id', ASCENDING), ('status', ASCENDING), ('club_id', ASCENDING)])
    await _safe_create_index(db.club_applications, [('club_id', ASCENDING), ('student_user_id', ASCENDING), ('status', ASCENDING)])
    await _safe_create_index(db.club_applications, [('club_id', ASCENDING), ('status', ASCENDING), ('applied_at', ASCENDING)])
    await _safe_create_index(db.club_events, [('club_id', ASCENDING), ('status', ASCENDING), ('event_date', ASCENDING)])
    await _safe_create_index(db.club_events, [('is_deleted', ASCENDING), ('club_id', ASCENDING), ('status', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.club_events, [('is_deleted', ASCENDING), ('visibility', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.event_registrations, [('event_id', ASCENDING), ('student_user_id', ASCENDING)])
    await _safe_create_index(db.event_registrations, [('event_id', ASCENDING), ('status', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.event_registrations, [('student_user_id', ASCENDING), ('created_at', ASCENDING)])
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
    await _safe_create_index(db.notices, [('is_deleted', ASCENDING), ('deleted_at', ASCENDING)])
    await _safe_create_index(db.universities, [('is_active', ASCENDING), ('deleted_at', ASCENDING)])
    await _safe_create_index(
        db.universities,
        [('university_id', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(db.faculties, [('is_active', ASCENDING), ('deleted_at', ASCENDING)])
    await _safe_create_index(
        db.faculties,
        [('faculty_id', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(
        db.faculties,
        [('faculty_code', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(
        db.faculties,
        [('university_id', ASCENDING), ('faculty_name', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(db.faculties, [('university_id', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.departments, [('is_active', ASCENDING), ('deleted_at', ASCENDING)])
    await _safe_create_index(
        db.departments,
        [('department_id', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(
        db.departments,
        [('faculty_id', ASCENDING), ('department_code', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(
        db.departments,
        [('faculty_id', ASCENDING), ('department_name', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(db.departments, [('faculty_id', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.programs, [('is_active', ASCENDING), ('deleted_at', ASCENDING)])
    await _safe_create_index(
        db.programs,
        [('program_id', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(
        db.programs,
        [('department_id', ASCENDING), ('program_code', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(
        db.programs,
        [('department_id', ASCENDING), ('program_name', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(db.programs, [('department_id', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.specializations, [('is_active', ASCENDING), ('deleted_at', ASCENDING)])
    await _safe_create_index(
        db.specializations,
        [('specialization_id', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(
        db.specializations,
        [('program_id', ASCENDING), ('specialization_code', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(
        db.specializations,
        [('program_id', ASCENDING), ('specialization_name', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(db.specializations, [('program_id', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.batches, [('is_active', ASCENDING), ('deleted_at', ASCENDING)])
    await _safe_create_index(db.semesters, [('is_active', ASCENDING), ('deleted_at', ASCENDING)])
    await _safe_create_index(db.batch_read_models, [('is_active', ASCENDING), ('deleted_at', ASCENDING)])
    await _safe_create_index(db.batch_read_models, [('program_id', ASCENDING), ('specialization_id', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.semester_read_models, [('is_active', ASCENDING), ('deleted_at', ASCENDING)])
    await _safe_create_index(db.semester_read_models, [('batch_id', ASCENDING), ('semester_number', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.semester_read_models, [('program_id', ASCENDING), ('specialization_id', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(
        db.semesters,
        [('batch_id', ASCENDING), ('semester_number', ASCENDING)],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(db.classes, [('is_active', ASCENDING), ('deleted_at', ASCENDING)])
    await _safe_create_index(db.section_read_models, [('is_active', ASCENDING), ('deleted_at', ASCENDING)])
    await _safe_create_index(db.section_read_models, [('department_id', ASCENDING), ('batch_id', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.section_read_models, [('semester_id', ASCENDING), ('class_coordinator_user_id', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.course_offering_read_models, [('is_active', ASCENDING), ('section_id', ASCENDING), ('group_id', ASCENDING)])
    await _safe_create_index(db.course_offering_read_models, [('teacher_user_id', ASCENDING), ('subject_id', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.class_slot_read_models, [('is_active', ASCENDING), ('section_id', ASCENDING), ('group_id', ASCENDING), ('day', ASCENDING)])
    await _safe_create_index(db.class_slot_read_models, [('course_offering_id', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.timetables, [('class_id', ASCENDING), ('semester', ASCENDING), ('status', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.timetables, [('entries.teacher_user_id', ASCENDING), ('status', ASCENDING)])
    await _safe_create_index(db.timetables, [('entries.room_code', ASCENDING), ('status', ASCENDING)])
    await _safe_create_index(db.timetable_subject_teacher_maps, [('class_id', ASCENDING), ('subject_id', ASCENDING)], unique=True)
    await _safe_create_index(db.groups, [('section_id', ASCENDING), ('code', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.groups, [('section_id', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.course_offerings, [('section_id', ASCENDING), ('semester_id', ASCENDING), ('academic_year', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(
        db.course_offerings,
        [
            ('subject_id', ASCENDING),
            ('teacher_user_id', ASCENDING),
            ('batch_id', ASCENDING),
            ('semester_id', ASCENDING),
            ('section_id', ASCENDING),
            ('group_id', ASCENDING),
            ('academic_year', ASCENDING),
            ('offering_type', ASCENDING),
        ],
        unique=True,
        partialFilterExpression={'is_active': True},
    )
    await _safe_create_index(db.course_offerings, [('teacher_user_id', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.class_slots, [('course_offering_id', ASCENDING), ('day', ASCENDING), ('start_time', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.class_slots, [('day', ASCENDING), ('room_code', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.attendance_records, [('class_slot_id', ASCENDING), ('student_id', ASCENDING)], unique=True)
    await _safe_create_index(db.attendance_records, [('student_id', ASCENDING), ('marked_at', ASCENDING)])
    await _safe_create_index(db.students, [('class_id', ASCENDING), ('group_id', ASCENDING), ('is_active', ASCENDING)])
    await _safe_create_index(db.internship_sessions, [('student_user_id', ASCENDING), ('clock_in_at', ASCENDING)])
    await _safe_create_index(db.internship_sessions, [('status', ASCENDING), ('clock_in_at', ASCENDING)])
    await _safe_create_index(db.ai_evaluation_runs, [('evaluation_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.ai_evaluation_runs, [('submission_id', ASCENDING), ('created_at', ASCENDING)])
    await _safe_create_index(db.ai_evaluation_chats, [('student_id', ASCENDING), ('exam_id', ASCENDING)], unique=True)
    await _safe_create_index(db.ai_evaluation_chats, [('teacher_id', ASCENDING)])
    await _safe_create_index(db.ai_evaluation_chats, [('exam_id', ASCENDING)])
    await _safe_create_index(db.ai_jobs, [('status', ASCENDING), ('requested_at', ASCENDING)])
    await _safe_create_index(db.ai_jobs, [('job_type', ASCENDING), ('requested_by_user_id', ASCENDING), ('requested_at', ASCENDING)])
    await _safe_create_index(db.ai_jobs, [('job_type', ASCENDING), ('idempotency_key', ASCENDING), ('status', ASCENDING)])
    await _safe_create_index(db.club_queue_views, [('scope_type', ASCENDING), ('scope_id', ASCENDING), ('queue_type', ASCENDING), ('updated_at', ASCENDING)])
    await _safe_create_index(db.club_queue_snapshots, [('scope_type', ASCENDING), ('scope_id', ASCENDING), ('queue_type', ASCENDING), ('captured_at', ASCENDING)])
    await _safe_create_index(db.system_health_snapshots, [('bucket_minute', ASCENDING)], unique=True)
    await _safe_create_index(db.system_health_snapshots, [('recorded_at', ASCENDING)])
    await _safe_create_index(db.operational_alert_routes, [('alert_code', ASCENDING)], unique=True)
    await _safe_create_index(db.operational_alert_routes, [('is_active', ASCENDING), ('last_seen_at', ASCENDING)])
    await _safe_create_index(
        db.similarity_logs,
        [('source_submission_id', ASCENDING), ('matched_submission_id', ASCENDING), ('threshold', ASCENDING), ('engine_version', ASCENDING)],
        unique=True,
    )
    await _ensure_legacy_compatibility_indexes()

    _indexes_ensured = True
