from collections import defaultdict
from datetime import datetime, timezone
from math import ceil
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import settings
from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.redis_store import redis_store
from app.core.security import require_roles
from app.models.notices import notice_public
from app.api.v1.endpoints.notices import _filter_visible_notices, _notice_is_expired
from app.services.analytics_snapshot import compute_platform_snapshot, get_latest_snapshot

router = APIRouter()

ANALYTICS_DEFAULT_PAGE_SIZE = 200
ANALYTICS_MAX_PAGE_SIZE = 500
ANALYTICS_SMALL_SCAN_CAP = 5_000
ANALYTICS_MEDIUM_SCAN_CAP = 25_000
ANALYTICS_LARGE_SCAN_CAP = 100_000
ACTIVE_CLUB_STATUSES = ('active', 'registration_closed')
ADMIN_SNAPSHOT_SUMMARY_FIELDS = (
    'users_total',
    'students_total',
    'programs_total',
    'batches_total',
    'semesters_total',
    'classes_total',
    'subjects_total',
    'assignments_total',
    'submissions_total',
    'evaluations_total',
    'similarity_flags_total',
    'notices_total',
    'clubs_total',
    'club_events_total',
)


def _bounded_cap(*, minimum: int, estimate: int, maximum: int) -> int:
    return min(maximum, max(minimum, estimate))


def _safe_object_ids(raw_ids: list[Any]) -> list[Any]:
    object_ids: list[Any] = []
    for raw in raw_ids:
        if raw is None:
            continue
        try:
            object_ids.append(parse_object_id(str(raw)))
        except HTTPException:
            continue
    return object_ids


def _to_utc_datetime(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def _get_cached_json(key: str):
    return await redis_store.get_json(key)


async def _set_cached_json(key: str, payload: dict):
    await redis_store.set_json(
        key,
        payload,
        ttl_seconds=max(30, settings.analytics_cache_ttl_seconds),
    )


async def _distinct_values(
    collection,
    field: str,
    query: dict[str, Any],
    *,
    fallback_cap: int = ANALYTICS_MEDIUM_SCAN_CAP,
) -> list[Any]:
    distinct = getattr(collection, 'distinct', None)
    if callable(distinct):
        try:
            values = await distinct(field, query)
            return [value for value in values if value is not None]
        except Exception:
            pass

    rows = await collection.find(query, {field: 1}).to_list(length=max(1, fallback_cap))
    values: list[Any] = []
    seen: set[str] = set()
    for row in rows:
        value = row.get(field)
        if isinstance(value, list):
            for nested in value:
                if nested is None:
                    continue
                marker = str(nested)
                if marker not in seen:
                    seen.add(marker)
                    values.append(nested)
            continue
        if value is None:
            continue
        marker = str(value)
        if marker not in seen:
            seen.add(marker)
            values.append(value)
    return values


async def _student_profiles_and_class_ids(current_user: dict) -> tuple[list[dict[str, Any]], set[str]]:
    user_id = str(current_user.get('_id'))
    user_email = (current_user.get('email') or '').strip().lower()

    student_profiles = await db.students.find(
        {'$or': [{'email': user_email}, {'user_id': user_id}], 'is_active': True}
    ).to_list(length=ANALYTICS_SMALL_SCAN_CAP)
    student_ids = [str(item.get('_id')) for item in student_profiles if item.get('_id')]

    class_ids = {
        str(item.get('class_id'))
        for item in student_profiles
        if item.get('class_id')
    }
    if student_ids:
        enrolled_class_ids = await _distinct_values(
            db.enrollments,
            'class_id',
            {'student_id': {'$in': student_ids}},
            fallback_cap=ANALYTICS_MEDIUM_SCAN_CAP,
        )
        class_ids.update(str(value) for value in enrolled_class_ids if value)

    return student_profiles, class_ids


def _snapshot_supports_admin_dashboard(snapshot: dict[str, Any] | None) -> bool:
    if not snapshot:
        return False
    return all(field in snapshot for field in ADMIN_SNAPSHOT_SUMMARY_FIELDS)


async def _get_admin_platform_snapshot() -> tuple[dict[str, Any], str, int]:
    snapshot, snapshot_age_hours = await get_latest_snapshot(
        max_age_hours=max(1, int(settings.analytics_snapshot_freshness_hours))
    )
    if not _snapshot_supports_admin_dashboard(snapshot):
        snapshot = await compute_platform_snapshot()
        return snapshot, 'live', 0
    return snapshot, 'snapshot', int(snapshot_age_hours or 0)


def _admin_summary_from_snapshot(snapshot: dict[str, Any]) -> dict[str, int]:
    return {
        'users': int(snapshot.get('users_total') or 0),
        'programs': int(snapshot.get('programs_total') or 0),
        'batches': int(snapshot.get('batches_total') or 0),
        'semesters': int(snapshot.get('semesters_total') or 0),
        'classes': int(snapshot.get('classes_total') or 0),
        'subjects': int(snapshot.get('subjects_total') or 0),
        'students': int(snapshot.get('students_total') or snapshot.get('active_students') or 0),
        'assignments': int(snapshot.get('assignments_total') or 0),
        'submissions': int(snapshot.get('submissions_total') or 0),
        'evaluations': int(snapshot.get('evaluations_total') or 0),
        'similarity_flags': int(snapshot.get('similarity_flags_total') or 0),
        'notices': int(snapshot.get('notices_total') or 0),
        'clubs': int(snapshot.get('clubs_total') or snapshot.get('active_clubs') or 0),
        'club_events': int(snapshot.get('club_events_total') or 0),
    }


async def _build_summary_payload(current_user: dict) -> dict[str, Any]:
    role = current_user.get('role')
    user_id = str(current_user.get('_id'))

    if role == 'student':
        total_submissions = await db.submissions.count_documents({'student_user_id': user_id})
        total_evaluations = await db.evaluations.count_documents({'student_user_id': user_id})
        pending = await db.submissions.count_documents({'student_user_id': user_id, 'status': 'submitted'})
        return {
            'total_submissions': total_submissions,
            'total_evaluations': total_evaluations,
            'pending_reviews': pending,
        }

    if role == 'teacher':
        my_assignments = await db.assignments.count_documents({'created_by': user_id})
        my_assignment_ids = [str(item) for item in await _distinct_values(db.assignments, '_id', {'created_by': user_id})]
        my_submissions = 0
        my_similarity_flags = 0
        if my_assignment_ids:
            my_submissions = await db.submissions.count_documents({'assignment_id': {'$in': my_assignment_ids}})
            my_similarity_flags = await db.similarity_logs.count_documents(
                {'is_flagged': True, 'source_assignment_id': {'$in': my_assignment_ids}}
            )
        my_evaluations = await db.evaluations.count_documents({'teacher_user_id': user_id})
        my_notices = await db.notices.count_documents({'is_active': True})
        return {
            'my_assignments': my_assignments,
            'my_submissions': my_submissions,
            'my_evaluations': my_evaluations,
            'my_similarity_flags': my_similarity_flags,
            'my_notices': my_notices,
        }

    return {
        'users': await db.users.count_documents({}),
        'programs': await db.programs.count_documents({}),
        'batches': await db.batches.count_documents({}),
        'semesters': await db.semesters.count_documents({}),
        'classes': await db.classes.count_documents({}),
        'subjects': await db.subjects.count_documents({}),
        'students': await db.students.count_documents({}),
        'assignments': await db.assignments.count_documents({}),
        'submissions': await db.submissions.count_documents({}),
        'evaluations': await db.evaluations.count_documents({}),
        'similarity_flags': await db.similarity_logs.count_documents({'is_flagged': True}),
        'notices': await db.notices.count_documents({'is_active': True}),
        'clubs': await db.clubs.count_documents({'status': {'$in': list(ACTIVE_CLUB_STATUSES)}}),
        'club_events': await db.club_events.count_documents({}),
    }


async def _build_urgent_notices_payload(current_user: dict, *, limit: int = 3) -> list[dict[str, Any]]:
    now = datetime.now(timezone.utc)
    items = await db.notices.find(
        {
            'is_active': True,
            'priority': 'urgent',
            '$or': [{'scheduled_at': None}, {'scheduled_at': {'$lte': now}}],
        }
    ).to_list(length=max(limit * 10, 20))
    items = sorted(
        items,
        key=lambda item: item.get('created_at') or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )
    items = [item for item in items if not _notice_is_expired(item, now)]
    items = await _filter_visible_notices(items, current_user)
    return [
        notice_public(item, current_user_id=str(current_user.get('_id')))
        for item in items[:limit]
    ]


async def _build_student_dashboard_payload(current_user: dict) -> dict[str, Any]:
    student_profiles, class_ids = await _student_profiles_and_class_ids(current_user)
    primary_student = student_profiles[0] if student_profiles else None
    if not class_ids or not primary_student:
        return {
            'deadlines': [],
            'timetable': [],
            'internship_status': None,
        }

    now = datetime.now(timezone.utc)
    assignment_rows = await db.assignments.find(
        {
            'is_deleted': {'$in': [False, None]},
            'class_id': {'$in': list(class_ids)},
        },
        {'_id': 1, 'title': 1, 'due_date': 1},
    ).to_list(length=ANALYTICS_MEDIUM_SCAN_CAP)

    deadlines = []
    for item in assignment_rows:
        due_date = _to_utc_datetime(item.get('due_date'))
        if not due_date:
            continue
        hours_left = int((due_date - now).total_seconds() // 3600)
        urgency = 'normal'
        if hours_left < 0:
            urgency = 'overdue'
        elif hours_left <= 24:
            urgency = 'high'
        elif hours_left <= 72:
            urgency = 'medium'
        deadlines.append(
            {
                'id': str(item.get('_id')),
                'title': item.get('title') or 'Assignment',
                'dueDate': due_date,
                'urgency': urgency,
                'hoursLeft': hours_left,
            }
        )
    deadlines.sort(key=lambda item: item.get('dueDate') or now)
    deadlines = deadlines[:8]

    offering_query: dict[str, Any] = {
        'section_id': primary_student.get('class_id'),
        'is_active': True,
    }
    if primary_student.get('group_id'):
        offering_query['$or'] = [{'group_id': None}, {'group_id': primary_student.get('group_id')}]
    offering_rows = await db.course_offerings.find(
        offering_query,
        {
            '_id': 1,
            'subject_id': 1,
            'teacher_user_id': 1,
            'offering_type': 1,
            'group_id': 1,
            'group_name': 1,
        },
    ).to_list(length=ANALYTICS_SMALL_SCAN_CAP)

    offering_ids = [str(item.get('_id')) for item in offering_rows if item.get('_id')]
    subject_ids = {str(item.get('subject_id')) for item in offering_rows if item.get('subject_id')}
    teacher_ids = {str(item.get('teacher_user_id')) for item in offering_rows if item.get('teacher_user_id')}

    subject_map: dict[str, dict[str, Any]] = {}
    if subject_ids:
        subject_rows = await db.subjects.find(
            {'_id': {'$in': _safe_object_ids(list(subject_ids))}, 'is_active': True},
            {'name': 1, 'code': 1},
        ).to_list(length=ANALYTICS_SMALL_SCAN_CAP)
        subject_map = {str(item.get('_id')): item for item in subject_rows if item.get('_id')}

    teacher_map: dict[str, dict[str, Any]] = {}
    if teacher_ids:
        teacher_rows = await db.users.find(
            {'_id': {'$in': _safe_object_ids(list(teacher_ids))}},
            {'full_name': 1},
        ).to_list(length=ANALYTICS_SMALL_SCAN_CAP)
        teacher_map = {str(item.get('_id')): item for item in teacher_rows if item.get('_id')}

    group_map: dict[str, dict[str, Any]] = {}
    group_ids = {str(item.get('group_id')) for item in offering_rows if item.get('group_id')}
    if group_ids and hasattr(db, 'groups'):
        group_rows = await db.groups.find(
            {'_id': {'$in': _safe_object_ids(list(group_ids))}, 'is_active': True},
            {'name': 1},
        ).to_list(length=ANALYTICS_SMALL_SCAN_CAP)
        group_map = {str(item.get('_id')): item for item in group_rows if item.get('_id')}

    offering_map = {}
    for item in offering_rows:
        offering_id = str(item.get('_id'))
        subject = subject_map.get(str(item.get('subject_id')), {})
        teacher = teacher_map.get(str(item.get('teacher_user_id')), {})
        group = group_map.get(str(item.get('group_id')), {})
        offering_map[offering_id] = {
            'subject': subject.get('name') or subject.get('code') or item.get('subject_id') or 'Subject',
            'teacher': teacher.get('full_name') or item.get('teacher_user_id') or 'Teacher',
            'type': item.get('offering_type') or '-',
            'group': item.get('group_name') or group.get('name') or '',
        }

    timetable_rows = []
    if offering_ids:
        timetable_rows = await db.class_slots.find(
            {'course_offering_id': {'$in': offering_ids}, 'is_active': True},
            {'course_offering_id': 1, 'day': 1, 'start_time': 1, 'end_time': 1, 'room_code': 1},
        ).to_list(length=ANALYTICS_MEDIUM_SCAN_CAP)

    grouped_timetable: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for slot in timetable_rows:
        day = slot.get('day') or 'Unknown'
        offering = offering_map.get(str(slot.get('course_offering_id')), {})
        grouped_timetable[day].append(
            {
                'time': f"{slot.get('start_time')}-{slot.get('end_time')}",
                'subject': offering.get('subject') or 'Subject',
                'teacher': offering.get('teacher') or 'Teacher',
                'room': slot.get('room_code') or '-',
                'type': offering.get('type') or '-',
                'group': offering.get('group') or '',
            }
        )

    timetable = []
    for day, sessions in grouped_timetable.items():
        timetable.append(
            {
                'day': day,
                'sessions': sorted(sessions, key=lambda item: str(item.get('time') or '')),
            }
        )
    timetable.sort(key=lambda item: str(item.get('day') or ''))

    internship_status = None
    if hasattr(db, 'internship_sessions'):
        internship_status = await db.internship_sessions.find_one(
            {'student_user_id': str(current_user.get('_id'))},
            sort=[('clock_in_at', -1)],
        )
        if internship_status:
            internship_status = {
                'id': str(internship_status.get('_id')),
                'student_user_id': internship_status.get('student_user_id'),
                'student_id': internship_status.get('student_id'),
                'status': internship_status.get('status'),
                'clock_in_at': internship_status.get('clock_in_at'),
                'clock_out_at': internship_status.get('clock_out_at'),
                'total_minutes': internship_status.get('total_minutes'),
                'auto_closed': bool(internship_status.get('auto_closed', False)),
                'note': internship_status.get('note'),
                'created_at': internship_status.get('created_at'),
                'updated_at': internship_status.get('updated_at'),
                'schema_version': internship_status.get('schema_version'),
            }

    return {
        'deadlines': deadlines,
        'timetable': timetable,
        'internship_status': internship_status,
    }


async def _count_by_field(
    collection,
    *,
    query: dict[str, Any],
    field: str,
    fallback_cap: int = ANALYTICS_LARGE_SCAN_CAP,
) -> dict[str, int]:
    aggregate = getattr(collection, 'aggregate', None)
    if callable(aggregate):
        try:
            pipeline = [
                {'$match': query},
                {'$group': {'_id': f'${field}', 'count': {'$sum': 1}}},
            ]
            rows = await aggregate(pipeline).to_list(length=fallback_cap)
            grouped: dict[str, int] = {}
            for row in rows:
                key = row.get('_id')
                if key is not None:
                    grouped[str(key)] = int(row.get('count') or 0)
            return grouped
        except Exception:
            pass

    rows = await collection.find(query, {field: 1}).to_list(length=max(1, fallback_cap))
    grouped: dict[str, int] = {}
    for row in rows:
        key = row.get(field)
        if key is None:
            continue
        key_text = str(key)
        grouped[key_text] = grouped.get(key_text, 0) + 1
    return grouped


def _empty_academic_structure_payload(*, page: int, page_size: int, total_classes: int = 0) -> dict:
    total_pages = max(1, ceil(total_classes / page_size)) if page_size else 1
    return {
        'university': {
            'id': 'UNI001',
            'name': settings.app_name,
            'location': 'Indore, India',
        },
        'programs': [],
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_classes': total_classes,
            'total_pages': total_pages,
        },
    }


@router.get('/summary')
async def analytics_summary(
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    role = current_user.get('role')
    user_id = str(current_user.get('_id'))
    if role == 'admin':
        snapshot, snapshot_served_from, snapshot_age_hours = await _get_admin_platform_snapshot()
        return {
            'role': role,
            'summary': _admin_summary_from_snapshot(snapshot),
            'snapshot_served_from': snapshot_served_from,
            'snapshot_age_hours': snapshot_age_hours,
        }

    cache_key = f'analytics:summary:{role}:{user_id}'
    cached = await _get_cached_json(cache_key)
    if cached:
        return cached

    payload = {
        'role': role,
        'summary': await _build_summary_payload(current_user),
    }
    await _set_cached_json(cache_key, payload)
    return payload


@router.get('/dashboard')
async def analytics_dashboard(
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    role = current_user.get('role')
    user_id = str(current_user.get('_id'))
    if role == 'admin':
        snapshot, snapshot_served_from, snapshot_age_hours = await _get_admin_platform_snapshot()
        return {
            'role': role,
            'summary': _admin_summary_from_snapshot(snapshot),
            'urgent_notices': await _build_urgent_notices_payload(current_user, limit=3),
            'teacher_sections': [],
            'student_dashboard': {
                'deadlines': [],
                'timetable': [],
                'internship_status': None,
            },
            'generated_at': snapshot.get('updated_at') or datetime.now(timezone.utc),
            'snapshot_served_from': snapshot_served_from,
            'snapshot_age_hours': snapshot_age_hours,
        }

    cache_key = f'analytics:dashboard:{role}:{user_id}'
    cached = await _get_cached_json(cache_key)
    if cached:
        return cached

    payload = {
        'role': role,
        'summary': await _build_summary_payload(current_user),
        'urgent_notices': await _build_urgent_notices_payload(current_user, limit=3),
        'teacher_sections': [],
        'student_dashboard': {
            'deadlines': [],
            'timetable': [],
            'internship_status': None,
        },
        'generated_at': datetime.now(timezone.utc),
    }

    if role == 'teacher':
        payload['teacher_sections'] = (await _teacher_section_tiles(current_user=current_user)).get('items', [])
    if role == 'student':
        payload['student_dashboard'] = await _build_student_dashboard_payload(current_user)

    await _set_cached_json(cache_key, payload)
    return payload


async def _teacher_section_tiles(
    current_user=Depends(require_roles(['teacher'])),
) -> dict:
    user_id = str(current_user.get('_id'))
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid user context')

    now = datetime.now(timezone.utc)
    classes = await db.classes.find(
        {'class_coordinator_user_id': user_id, 'is_active': True},
        {'name': 1, 'program_id': 1, 'batch_id': 1, 'semester_id': 1},
    ).to_list(length=ANALYTICS_SMALL_SCAN_CAP)
    teacher_assignment_classes = await _distinct_values(
        db.assignments,
        'class_id',
        {'created_by': user_id},
        fallback_cap=ANALYTICS_MEDIUM_SCAN_CAP,
    )
    extra_class_object_ids = _safe_object_ids([str(value) for value in teacher_assignment_classes if value])
    extra_classes = []
    if extra_class_object_ids:
        extra_classes = await db.classes.find(
            {'_id': {'$in': extra_class_object_ids}, 'is_active': True},
            {'name': 1, 'program_id': 1, 'batch_id': 1, 'semester_id': 1},
        ).to_list(length=ANALYTICS_SMALL_SCAN_CAP)

    class_by_id = {str(item.get('_id')): item for item in classes}
    for class_doc in extra_classes:
        class_by_id[str(class_doc.get('_id'))] = class_doc

    class_ids = sorted([class_id for class_id in class_by_id.keys() if class_id])
    if not class_ids:
        return {'items': []}

    assignments_cap = _bounded_cap(
        minimum=ANALYTICS_SMALL_SCAN_CAP,
        estimate=len(class_ids) * 600,
        maximum=ANALYTICS_LARGE_SCAN_CAP,
    )
    assignment_docs = await db.assignments.find(
        {'class_id': {'$in': class_ids}},
        {'_id': 1, 'class_id': 1, 'status': 1, 'due_date': 1, 'subject_id': 1},
    ).to_list(length=assignments_cap)

    assignments_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    assignment_to_class: dict[str, str] = {}
    subject_ids: set[str] = set()
    for row in assignment_docs:
        class_id = row.get('class_id')
        assignment_obj_id = row.get('_id')
        if not class_id or assignment_obj_id is None:
            continue
        class_id_text = str(class_id)
        assignment_id = str(assignment_obj_id)
        assignments_by_class[class_id_text].append(row)
        assignment_to_class[assignment_id] = class_id_text
        subject_id = row.get('subject_id')
        if subject_id:
            subject_ids.add(str(subject_id))

    subject_by_id: dict[str, dict[str, Any]] = {}
    subject_object_ids = _safe_object_ids(list(subject_ids))
    if subject_object_ids:
        subject_docs = await db.subjects.find(
            {'_id': {'$in': subject_object_ids}, 'is_active': True},
            {'name': 1},
        ).to_list(length=_bounded_cap(minimum=1_000, estimate=len(subject_object_ids) * 2, maximum=ANALYTICS_SMALL_SCAN_CAP))
        subject_by_id = {str(item.get('_id')): item for item in subject_docs if item.get('_id')}

    enrollment_cap = _bounded_cap(
        minimum=ANALYTICS_SMALL_SCAN_CAP,
        estimate=len(class_ids) * 400,
        maximum=ANALYTICS_LARGE_SCAN_CAP,
    )
    enrollment_rows = await db.enrollments.find(
        {'class_id': {'$in': class_ids}},
        {'class_id': 1, 'student_id': 1},
    ).to_list(length=enrollment_cap)
    direct_student_rows = await db.students.find(
        {'class_id': {'$in': class_ids}, 'is_active': True},
        {'class_id': 1, '_id': 1},
    ).to_list(length=enrollment_cap)

    class_student_ids: dict[str, set[str]] = defaultdict(set)
    for row in enrollment_rows:
        class_id = row.get('class_id')
        student_id = row.get('student_id')
        if class_id and student_id:
            class_student_ids[str(class_id)].add(str(student_id))
    for row in direct_student_rows:
        class_id = row.get('class_id')
        student_id = row.get('_id')
        if class_id and student_id:
            class_student_ids[str(class_id)].add(str(student_id))

    assignment_ids = sorted(assignment_to_class.keys())
    submission_to_class: dict[str, str] = {}
    submissions_count_by_assignment: dict[str, int] = {}
    similarity_count_by_assignment: dict[str, int] = {}
    risk_students_by_class: dict[str, set[str]] = defaultdict(set)

    if assignment_ids:
        submissions_cap = _bounded_cap(
            minimum=ANALYTICS_MEDIUM_SCAN_CAP,
            estimate=len(assignment_ids) * 250,
            maximum=ANALYTICS_LARGE_SCAN_CAP,
        )
        submission_rows = await db.submissions.find(
            {'assignment_id': {'$in': assignment_ids}},
            {'_id': 1, 'assignment_id': 1},
        ).to_list(length=submissions_cap)
        for row in submission_rows:
            assignment_id = row.get('assignment_id')
            submission_obj_id = row.get('_id')
            if not assignment_id:
                continue
            assignment_key = str(assignment_id)
            submissions_count_by_assignment[assignment_key] = submissions_count_by_assignment.get(assignment_key, 0) + 1
            if submission_obj_id is not None:
                class_id = assignment_to_class.get(assignment_key)
                if class_id:
                    submission_to_class[str(submission_obj_id)] = class_id

        similarity_count_by_assignment = await _count_by_field(
            db.similarity_logs,
            query={'is_flagged': True, 'source_assignment_id': {'$in': assignment_ids}},
            field='source_assignment_id',
            fallback_cap=_bounded_cap(
                minimum=ANALYTICS_SMALL_SCAN_CAP,
                estimate=len(assignment_ids) * 50,
                maximum=ANALYTICS_LARGE_SCAN_CAP,
            ),
        )

        submission_ids = list(submission_to_class.keys())
        if submission_ids:
            risky_cap = _bounded_cap(
                minimum=ANALYTICS_SMALL_SCAN_CAP,
                estimate=len(submission_ids) * 2,
                maximum=ANALYTICS_LARGE_SCAN_CAP,
            )
            risky_rows = await db.evaluations.find(
                {
                    'submission_id': {'$in': submission_ids},
                    '$or': [{'grand_total': {'$lt': 40}}, {'attendance_percent': {'$lt': 70}}],
                },
                {'submission_id': 1, 'student_user_id': 1},
            ).to_list(length=risky_cap)
            for row in risky_rows:
                submission_id = row.get('submission_id')
                student_user_id = row.get('student_user_id')
                class_id = submission_to_class.get(str(submission_id)) if submission_id else None
                if class_id and student_user_id:
                    risk_students_by_class[class_id].add(str(student_user_id))

    items = []
    for class_id, class_doc in class_by_id.items():
        assignment_docs_for_class = assignments_by_class.get(class_id, [])
        assignment_ids_for_class = [str(item.get('_id')) for item in assignment_docs_for_class if item.get('_id')]
        total_students = len(class_student_ids.get(class_id, set()))
        active_assignments = sum(1 for item in assignment_docs_for_class if item.get('status') == 'open')

        late_submissions_count = 0
        for assignment in assignment_docs_for_class:
            assignment_id_obj = assignment.get('_id')
            assignment_id = str(assignment_id_obj) if assignment_id_obj is not None else ''
            due = _to_utc_datetime(assignment.get('due_date'))
            if due and due < now and assignment_id:
                submitted = submissions_count_by_assignment.get(assignment_id, 0)
                late_submissions_count += max(0, total_students - submitted)

        similarity_alert_count = sum(similarity_count_by_assignment.get(assignment_id, 0) for assignment_id in assignment_ids_for_class)
        risk_student_count = len(risk_students_by_class.get(class_id, set()))

        if risk_student_count >= 3 or similarity_alert_count >= 3 or late_submissions_count >= 5:
            health_status = 'risk'
        elif risk_student_count >= 1 or similarity_alert_count >= 1 or late_submissions_count >= 1:
            health_status = 'attention'
        else:
            health_status = 'healthy'

        class_subject_ids = sorted({str(item.get('subject_id')) for item in assignment_docs_for_class if item.get('subject_id')})
        class_subject_names = [subject_by_id.get(subject_id, {}).get('name', subject_id) for subject_id in class_subject_ids]

        items.append(
            {
                'class_id': class_id,
                'class_name': class_doc.get('name', class_id),
                'program_id': class_doc.get('program_id'),
                'batch_id': class_doc.get('batch_id'),
                'semester_id': class_doc.get('semester_id'),
                'total_students': total_students,
                'active_assignments': active_assignments,
                'late_submissions_count': late_submissions_count,
                'similarity_alert_count': similarity_alert_count,
                'risk_student_count': risk_student_count,
                'health_status': health_status,
                'subjects': class_subject_names,
            }
        )

    items.sort(key=lambda row: str(row.get('class_name') or ''))
    return {'items': items}


@router.get('/teacher/sections')
async def teacher_section_tiles(
    current_user=Depends(require_roles(['teacher'])),
) -> dict:
    return await _teacher_section_tiles(current_user=current_user)


@router.get('/academic-structure')
async def academic_structure(
    page: int = Query(1, ge=1),
    page_size: int = Query(ANALYTICS_DEFAULT_PAGE_SIZE, ge=1, le=ANALYTICS_MAX_PAGE_SIZE),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    role = current_user.get('role')
    user_id = str(current_user.get('_id'))
    cache_key = f'analytics:academic-structure:{role}:{user_id}:{page}:{page_size}'
    cached = await _get_cached_json(cache_key)
    if cached:
        return cached

    user_email = str(current_user.get('email') or '').lower()
    class_query: dict[str, Any] = {'is_active': True}

    if role == 'teacher':
        class_query['class_coordinator_user_id'] = user_id

    if role == 'student':
        student_docs_for_email = await db.students.find(
            {'is_active': True, 'email': user_email},
            {'_id': 1, 'class_id': 1},
        ).to_list(length=ANALYTICS_SMALL_SCAN_CAP)
        student_ids = {str(row.get('_id')) for row in student_docs_for_email if row.get('_id')}
        allowed_class_ids = {str(row.get('class_id')) for row in student_docs_for_email if row.get('class_id')}
        if student_ids:
            enrolled_class_ids = await _distinct_values(
                db.enrollments,
                'class_id',
                {'student_id': {'$in': list(student_ids)}},
                fallback_cap=ANALYTICS_MEDIUM_SCAN_CAP,
            )
            allowed_class_ids.update(str(value) for value in enrolled_class_ids if value)

        allowed_class_object_ids = _safe_object_ids(list(allowed_class_ids))
        if not allowed_class_object_ids:
            payload = _empty_academic_structure_payload(page=page, page_size=page_size, total_classes=0)
            await _set_cached_json(cache_key, payload)
            return payload
        class_query['_id'] = {'$in': allowed_class_object_ids}

    total_classes = await db.classes.count_documents(class_query)
    if total_classes == 0:
        payload = _empty_academic_structure_payload(page=page, page_size=page_size, total_classes=0)
        await _set_cached_json(cache_key, payload)
        return payload

    skip = (page - 1) * page_size
    class_cursor = db.classes.find(
        class_query,
        {
            'name': 1,
            'program_id': 1,
            'batch_id': 1,
            'semester_id': 1,
            'class_coordinator_user_id': 1,
        },
    )
    if hasattr(class_cursor, 'sort'):
        class_cursor = class_cursor.sort('name', 1)
    if hasattr(class_cursor, 'skip'):
        class_cursor = class_cursor.skip(skip)
    if hasattr(class_cursor, 'limit'):
        class_cursor = class_cursor.limit(page_size)
    classes = await class_cursor.to_list(length=page_size)
    if not classes:
        payload = _empty_academic_structure_payload(page=page, page_size=page_size, total_classes=total_classes)
        await _set_cached_json(cache_key, payload)
        return payload

    class_ids = [str(item.get('_id')) for item in classes if item.get('_id')]
    enrollment_cap = _bounded_cap(
        minimum=ANALYTICS_SMALL_SCAN_CAP,
        estimate=page_size * 400,
        maximum=ANALYTICS_LARGE_SCAN_CAP,
    )
    enrollments = await db.enrollments.find(
        {'class_id': {'$in': class_ids}},
        {'class_id': 1, 'student_id': 1},
    ).to_list(length=enrollment_cap)

    students = await db.students.find(
        {'class_id': {'$in': class_ids}, 'is_active': True},
        {'_id': 1, 'full_name': 1, 'roll_number': 1, 'email': 1, 'class_id': 1},
    ).to_list(length=enrollment_cap)

    students_by_id = {str(item.get('_id')): item for item in students if item.get('_id')}
    enrolled_student_ids = {str(item.get('student_id')) for item in enrollments if item.get('student_id')}
    missing_student_ids = enrolled_student_ids - set(students_by_id.keys())
    missing_student_object_ids = _safe_object_ids(list(missing_student_ids))
    if missing_student_object_ids:
        extra_students = await db.students.find(
            {'_id': {'$in': missing_student_object_ids}, 'is_active': True},
            {'_id': 1, 'full_name': 1, 'roll_number': 1, 'email': 1, 'class_id': 1},
        ).to_list(length=enrollment_cap)
        for row in extra_students:
            row_id = row.get('_id')
            if row_id is not None:
                students_by_id[str(row_id)] = row

    class_student_ids: dict[str, set[str]] = defaultdict(set)
    for row in enrollments:
        class_id = row.get('class_id')
        student_id = row.get('student_id')
        if class_id and student_id:
            class_student_ids[str(class_id)].add(str(student_id))
    for row in students_by_id.values():
        class_id = row.get('class_id')
        row_id = row.get('_id')
        if class_id and row_id:
            class_student_ids[str(class_id)].add(str(row_id))

    assignments = await db.assignments.find(
        {'class_id': {'$in': class_ids}},
        {'class_id': 1, 'subject_id': 1},
    ).to_list(
        length=_bounded_cap(
            minimum=ANALYTICS_SMALL_SCAN_CAP,
            estimate=page_size * 400,
            maximum=ANALYTICS_LARGE_SCAN_CAP,
        )
    )
    class_subject_ids: dict[str, set[str]] = defaultdict(set)
    for row in assignments:
        class_id = row.get('class_id')
        subject_id = row.get('subject_id')
        if class_id and subject_id:
            class_subject_ids[str(class_id)].add(str(subject_id))

    subject_ids = {subject_id for values in class_subject_ids.values() for subject_id in values}
    subject_by_id: dict[str, dict[str, Any]] = {}
    subject_object_ids = _safe_object_ids(list(subject_ids))
    if subject_object_ids:
        subjects = await db.subjects.find(
            {'_id': {'$in': subject_object_ids}, 'is_active': True},
            {'name': 1, 'code': 1},
        ).to_list(length=_bounded_cap(minimum=ANALYTICS_SMALL_SCAN_CAP, estimate=len(subject_object_ids) * 2, maximum=ANALYTICS_MEDIUM_SCAN_CAP))
        subject_by_id = {str(item.get('_id')): item for item in subjects if item.get('_id')}

    program_ids = {str(item.get('program_id')) for item in classes if item.get('program_id')}
    batch_ids = {str(item.get('batch_id')) for item in classes if item.get('batch_id')}
    semester_ids = {str(item.get('semester_id')) for item in classes if item.get('semester_id')}
    programs_collection = getattr(db, 'programs', None)
    batches_collection = getattr(db, 'batches', None)
    semesters_collection = getattr(db, 'semesters', None)

    program_object_ids = _safe_object_ids(list(program_ids))
    programs = []
    if programs_collection is not None and program_object_ids:
        programs = await programs_collection.find({'_id': {'$in': program_object_ids}, 'is_active': True}).to_list(
            length=_bounded_cap(minimum=ANALYTICS_SMALL_SCAN_CAP, estimate=len(program_object_ids) * 2, maximum=ANALYTICS_MEDIUM_SCAN_CAP)
        )

    batch_object_ids = _safe_object_ids(list(batch_ids))
    batches = []
    if batches_collection is not None and batch_object_ids:
        batches = await batches_collection.find({'_id': {'$in': batch_object_ids}, 'is_active': True}).to_list(
            length=_bounded_cap(minimum=ANALYTICS_SMALL_SCAN_CAP, estimate=len(batch_object_ids) * 2, maximum=ANALYTICS_MEDIUM_SCAN_CAP)
        )

    semester_object_ids = _safe_object_ids(list(semester_ids))
    semesters = []
    if semesters_collection is not None and semester_object_ids:
        semesters = await semesters_collection.find({'_id': {'$in': semester_object_ids}, 'is_active': True}).to_list(
            length=_bounded_cap(minimum=ANALYTICS_SMALL_SCAN_CAP, estimate=len(semester_object_ids) * 2, maximum=ANALYTICS_MEDIUM_SCAN_CAP)
        )

    coordinator_ids = {str(item.get('class_coordinator_user_id')) for item in classes if item.get('class_coordinator_user_id')}
    coordinator_object_ids = _safe_object_ids(list(coordinator_ids))
    coordinator_users = await db.users.find(
        {'_id': {'$in': coordinator_object_ids}},
        {'full_name': 1},
    ).to_list(length=_bounded_cap(minimum=ANALYTICS_SMALL_SCAN_CAP, estimate=len(coordinator_object_ids) * 2, maximum=ANALYTICS_MEDIUM_SCAN_CAP)) if coordinator_object_ids else []

    student_emails = {str(item.get('email') or '').lower() for item in students_by_id.values() if item.get('email')}
    users_by_email: dict[str, str] = {}
    if student_emails:
        user_rows = await db.users.find(
            {'email': {'$in': list(student_emails)}},
            {'_id': 1, 'email': 1},
        ).to_list(length=_bounded_cap(minimum=ANALYTICS_SMALL_SCAN_CAP, estimate=len(student_emails) * 2, maximum=ANALYTICS_MEDIUM_SCAN_CAP))
        users_by_email = {
            str(item.get('email') or '').lower(): str(item.get('_id'))
            for item in user_rows
            if item.get('_id') and item.get('email')
        }

    users_by_id = {str(item.get('_id')): item for item in coordinator_users if item.get('_id')}
    students_by_student_id = {str(item.get('_id')): item for item in students_by_id.values() if item.get('_id')}

    student_user_by_student_id: dict[str, str] = {}
    candidate_user_ids: set[str] = set()
    for student in students_by_student_id.values():
        student_id = str(student.get('_id'))
        email = str(student.get('email') or '').lower()
        mapped_user_id = users_by_email.get(email)
        if mapped_user_id:
            student_user_by_student_id[student_id] = mapped_user_id
            candidate_user_ids.add(mapped_user_id)

    submissions_count_by_user: dict[str, int] = {}
    regs_count_by_user: dict[str, int] = {}
    if candidate_user_ids:
        query = {'student_user_id': {'$in': list(candidate_user_ids)}}
        submissions_count_by_user = await _count_by_field(
            db.submissions,
            query=query,
            field='student_user_id',
            fallback_cap=_bounded_cap(
                minimum=ANALYTICS_MEDIUM_SCAN_CAP,
                estimate=len(candidate_user_ids) * 200,
                maximum=ANALYTICS_LARGE_SCAN_CAP,
            ),
        )
        regs_count_by_user = await _count_by_field(
            db.event_registrations,
            query=query,
            field='student_user_id',
            fallback_cap=_bounded_cap(
                minimum=ANALYTICS_MEDIUM_SCAN_CAP,
                estimate=len(candidate_user_ids) * 100,
                maximum=ANALYTICS_LARGE_SCAN_CAP,
            ),
        )

    program_by_id = {str(item.get('_id')): item for item in programs if item.get('_id')}
    batch_by_id = {str(item.get('_id')): item for item in batches if item.get('_id')}
    semester_by_id = {str(item.get('_id')): item for item in semesters if item.get('_id')}

    tree: dict[str, dict[str, Any]] = {}
    for class_doc in classes:
        class_id = str(class_doc.get('_id'))
        if not class_id:
            continue

        raw_program_id = str(class_doc.get('program_id') or '')
        raw_batch_id = str(class_doc.get('batch_id') or '')
        raw_semester_id = str(class_doc.get('semester_id') or '')

        program_doc = program_by_id.get(raw_program_id) if raw_program_id else None
        if program_doc:
            program_key = raw_program_id
            program_name = program_doc.get('name') or 'Program'
            program_legacy = False
        else:
            program_key = f'unassigned-program:{class_id}'
            program_name = 'Unassigned Program'
            program_legacy = True

        program_node = tree.setdefault(
            program_key,
            {
                'id': raw_program_id or program_key,
                'name': program_name,
                'is_legacy': program_legacy,
                'batches': {},
            },
        )

        batch_doc = batch_by_id.get(raw_batch_id) if raw_batch_id else None
        if batch_doc:
            batch_key = raw_batch_id
            batch_name = batch_doc.get('name') or batch_doc.get('academic_span_label') or batch_doc.get('code') or 'Batch'
            batch_legacy = False
        else:
            batch_key = f'unassigned-batch:{class_id}'
            batch_name = 'Unassigned Batch'
            batch_legacy = True

        batch_node = program_node['batches'].setdefault(
            batch_key,
            {
                'id': raw_batch_id or batch_key,
                'name': batch_name,
                'is_legacy': batch_legacy,
                'semesters': {},
                'classes': [],
            },
        )

        semester_doc = semester_by_id.get(raw_semester_id) if raw_semester_id else None
        if semester_doc:
            semester_key = raw_semester_id
            semester_name = semester_doc.get('label') or f"Semester {semester_doc.get('semester_number')}"
            semester_legacy = False
        else:
            semester_key = f'unassigned-semester:{batch_key}'
            semester_name = 'Sections'
            semester_legacy = True

        semester_node = batch_node['semesters'].setdefault(
            semester_key,
            {
                'id': raw_semester_id or semester_key,
                'name': semester_name,
                'is_legacy': semester_legacy,
                'classes': [],
            },
        )

        teacher_name = 'Unassigned'
        coordinator_id = str(class_doc.get('class_coordinator_user_id') or '')
        if coordinator_id and coordinator_id in users_by_id:
            teacher_name = users_by_id[coordinator_id].get('full_name') or 'Unassigned'

        student_items = []
        for student_id in sorted(class_student_ids.get(class_id, set())):
            student = students_by_student_id.get(student_id)
            if not student:
                continue
            mapped_user_id = student_user_by_student_id.get(student_id, '')
            student_items.append(
                {
                    'id': student_id,
                    'name': student.get('full_name'),
                    'rollNo': student.get('roll_number'),
                    'logs': {
                        'assignment_submissions': submissions_count_by_user.get(mapped_user_id, 0),
                        'event_registrations': regs_count_by_user.get(mapped_user_id, 0),
                    },
                }
            )

        subject_items = []
        for subject_id in sorted(class_subject_ids.get(class_id, set())):
            subject_doc = subject_by_id.get(subject_id)
            if subject_doc:
                subject_items.append(
                    {
                        'id': subject_id,
                        'name': subject_doc.get('name') or subject_id,
                        'code': subject_doc.get('code'),
                    }
                )

        class_item = {
            'id': class_id,
            'name': class_doc.get('name') or class_id,
            'coordinator': teacher_name,
            'students': student_items,
            'subjects': subject_items,
        }
        semester_node['classes'].append(class_item)
        batch_node['classes'].append(class_item)

    program_items = []
    for program in tree.values():
        batch_items = []
        for batch in program['batches'].values():
            semester_items = []
            for semester in batch['semesters'].values():
                semester_items.append(
                    {
                        'id': semester['id'],
                        'name': semester['name'],
                        'is_legacy': semester['is_legacy'],
                        'classes': semester['classes'],
                    }
                )
            semester_items.sort(key=lambda item: str(item.get('name') or ''))
            batch_items.append(
                {
                    'id': batch['id'],
                    'name': batch['name'],
                    'is_legacy': batch['is_legacy'],
                    'classes': batch['classes'],
                    'semesters': semester_items,
                }
            )
        batch_items.sort(key=lambda item: str(item.get('name') or ''))
        program_items.append(
            {
                'id': program['id'],
                'name': program['name'],
                'is_legacy': program['is_legacy'],
                'batches': batch_items,
            }
        )
    program_items.sort(key=lambda item: str(item.get('name') or ''))

    payload = {
        'university': {
            'id': 'UNI001',
            'name': settings.app_name,
            'location': 'Indore, India',
        },
        'programs': program_items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_classes': total_classes,
            'total_pages': max(1, ceil(total_classes / page_size)),
        },
    }
    await _set_cached_json(cache_key, payload)
    return payload
