from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles

router = APIRouter()


async def _student_ids_for_class(class_id: str) -> set[str]:
    enrollment_rows = await db.enrollments.find({'class_id': class_id}).to_list(length=10000)
    student_ids = {row.get('student_id') for row in enrollment_rows if row.get('student_id')}
    direct_student_rows = await db.students.find({'class_id': class_id, 'is_active': True}).to_list(length=10000)
    student_ids.update(str(row.get('_id')) for row in direct_student_rows if row.get('_id'))
    return {sid for sid in student_ids if sid}


@router.get('/summary')
async def analytics_summary(
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    role = current_user.get('role')
    user_id = str(current_user.get('_id'))

    if role == 'student':
        total_submissions = await db.submissions.count_documents({'student_user_id': user_id})
        total_evaluations = await db.evaluations.count_documents({'student_user_id': user_id})
        pending = await db.submissions.count_documents({'student_user_id': user_id, 'status': 'submitted'})
        return {
            'role': role,
            'summary': {
                'total_submissions': total_submissions,
                'total_evaluations': total_evaluations,
                'pending_reviews': pending,
            },
        }

    if role == 'teacher':
        my_assignments = await db.assignments.count_documents({'created_by': user_id})
        my_assignment_docs = await db.assignments.find({'created_by': user_id}).to_list(length=2000)
        my_assignment_ids = [str(item.get('_id')) for item in my_assignment_docs]
        my_submissions = await db.submissions.count_documents({'assignment_id': {'$in': my_assignment_ids}})
        my_evaluations = await db.evaluations.count_documents({'teacher_user_id': user_id})
        my_similarity_flags = await db.similarity_logs.count_documents(
            {'is_flagged': True, 'source_assignment_id': {'$in': my_assignment_ids}}
        )
        my_notices = await db.notices.count_documents({'is_active': True})
        return {
            'role': role,
            'summary': {
                'my_assignments': my_assignments,
                'my_submissions': my_submissions,
                'my_evaluations': my_evaluations,
                'my_similarity_flags': my_similarity_flags,
                'my_notices': my_notices,
            },
        }

    return {
        'role': role,
        'summary': {
            'users': await db.users.count_documents({}),
            'courses': await db.courses.count_documents({}),
            'years': await db.years.count_documents({}),
            'classes': await db.classes.count_documents({}),
            'subjects': await db.subjects.count_documents({}),
            'students': await db.students.count_documents({}),
            'assignments': await db.assignments.count_documents({}),
            'submissions': await db.submissions.count_documents({}),
            'evaluations': await db.evaluations.count_documents({}),
            'similarity_flags': await db.similarity_logs.count_documents({'is_flagged': True}),
            'notices': await db.notices.count_documents({'is_active': True}),
            'clubs': await db.clubs.count_documents({'is_active': True}),
            'club_events': await db.club_events.count_documents({}),
        },
    }


async def _teacher_section_tiles(
    current_user=Depends(require_roles(['teacher'])),
) -> dict:
    user_id = str(current_user.get('_id'))
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid user context')

    now = datetime.now(timezone.utc)
    classes = await db.classes.find({'class_coordinator_user_id': user_id, 'is_active': True}).to_list(length=2000)
    teacher_assignment_classes = await db.assignments.distinct('class_id', {'created_by': user_id})
    extra_classes = await db.classes.find({'_id': {'$in': [parse_object_id(cid) for cid in teacher_assignment_classes if cid]}}).to_list(length=2000)

    class_by_id = {str(item.get('_id')): item for item in classes}
    for class_doc in extra_classes:
        class_by_id[str(class_doc.get('_id'))] = class_doc

    subject_by_id = {str(item.get('_id')): item for item in await db.subjects.find({'is_active': True}).to_list(length=5000)}
    items = []
    for class_id, class_doc in class_by_id.items():
        assignment_docs = await db.assignments.find({'class_id': class_id}).to_list(length=5000)
        assignment_ids = [str(item.get('_id')) for item in assignment_docs]

        student_ids = await _student_ids_for_class(class_id)
        total_students = len(student_ids)
        active_assignments = len([item for item in assignment_docs if item.get('status') == 'open'])

        late_submissions_count = 0
        for assignment in assignment_docs:
            due = assignment.get('due_date')
            if due and due < now:
                submitted = await db.submissions.count_documents({'assignment_id': str(assignment.get('_id'))})
                late_submissions_count += max(0, total_students - submitted)

        similarity_alert_count = 0
        if assignment_ids:
            similarity_alert_count = await db.similarity_logs.count_documents(
                {'source_assignment_id': {'$in': assignment_ids}, 'is_flagged': True}
            )

        risk_student_count = 0
        if assignment_ids:
            submission_docs = await db.submissions.find({'assignment_id': {'$in': assignment_ids}}).to_list(length=20000)
            submission_ids = [str(item.get('_id')) for item in submission_docs]
            if submission_ids:
                risky = await db.evaluations.find(
                    {
                        'submission_id': {'$in': submission_ids},
                        '$or': [{'grand_total': {'$lt': 40}}, {'attendance_percent': {'$lt': 70}}],
                    }
                ).to_list(length=20000)
                risk_student_count = len({item.get('student_user_id') for item in risky if item.get('student_user_id')})

        if risk_student_count >= 3 or similarity_alert_count >= 3 or late_submissions_count >= 5:
            health_status = 'risk'
        elif risk_student_count >= 1 or similarity_alert_count >= 1 or late_submissions_count >= 1:
            health_status = 'attention'
        else:
            health_status = 'healthy'

        class_subject_ids = sorted({item.get('subject_id') for item in assignment_docs if item.get('subject_id')})
        class_subject_names = [subject_by_id.get(subject_id, {}).get('name', subject_id) for subject_id in class_subject_ids]

        items.append(
            {
                'class_id': class_id,
                'class_name': class_doc.get('name', class_id),
                'year_id': class_doc.get('year_id'),
                'total_students': total_students,
                'active_assignments': active_assignments,
                'late_submissions_count': late_submissions_count,
                'similarity_alert_count': similarity_alert_count,
                'risk_student_count': risk_student_count,
                'health_status': health_status,
                'subjects': class_subject_names,
            }
        )

    return {'items': items}


@router.get('/teacher/classes')
async def teacher_class_tiles(
    current_user=Depends(require_roles(['teacher'])),
) -> dict:
    # Legacy compatibility alias; canonical path is /teacher/sections.
    return await _teacher_section_tiles(current_user=current_user)


@router.get('/teacher/sections')
async def teacher_section_tiles(
    current_user=Depends(require_roles(['teacher'])),
) -> dict:
    return await _teacher_section_tiles(current_user=current_user)


@router.get('/academic-structure')
async def academic_structure(
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    role = current_user.get('role')
    user_id = str(current_user.get('_id'))
    user_email = str(current_user.get('email') or '').lower()

    courses = await db.courses.find({'is_active': True}).to_list(length=2000)
    years = await db.years.find({'is_active': True}).to_list(length=5000)
    classes = await db.classes.find({'is_active': True}).to_list(length=20000)
    enrollments = await db.enrollments.find({}).to_list(length=50000)
    students = await db.students.find({'is_active': True}).to_list(length=50000)
    subjects = await db.subjects.find({'is_active': True}).to_list(length=5000)
    assignments = await db.assignments.find({}).to_list(length=50000)
    users = await db.users.find({}).to_list(length=5000)

    if role == 'student':
        student_ids_by_email = {
            str(item.get('_id'))
            for item in students
            if str(item.get('email') or '').lower() == user_email
        }
        allowed_class_ids = {
            item.get('class_id')
            for item in enrollments
            if item.get('student_id') in student_ids_by_email
        }
        classes = [item for item in classes if str(item.get('_id')) in allowed_class_ids]
    elif role == 'teacher':
        allowed_class_ids = {
            str(item.get('_id'))
            for item in classes
            if item.get('class_coordinator_user_id') == user_id
        }
        classes = [item for item in classes if str(item.get('_id')) in allowed_class_ids] if allowed_class_ids else []

    course_by_id = {str(item.get('_id')): item for item in courses}
    year_by_id = {str(item.get('_id')): item for item in years}
    subject_by_id = {str(item.get('_id')): item for item in subjects}
    users_by_id = {str(item.get('_id')): item for item in users}
    students_by_id = {str(item.get('_id')): item for item in students}

    class_student_ids: dict[str, set[str]] = {}
    for row in enrollments:
        class_id = row.get('class_id')
        student_id = row.get('student_id')
        if class_id and student_id:
            class_student_ids.setdefault(class_id, set()).add(student_id)
    for row in students:
        class_id = row.get('class_id')
        if class_id and row.get('_id'):
            class_student_ids.setdefault(class_id, set()).add(str(row.get('_id')))

    class_subject_ids: dict[str, set[str]] = {}
    for row in assignments:
        class_id = row.get('class_id')
        subject_id = row.get('subject_id')
        if class_id and subject_id:
            class_subject_ids.setdefault(class_id, set()).add(subject_id)

    candidate_user_ids: set[str] = set()
    student_user_by_student_id: dict[str, str] = {}
    users_by_email = {str(item.get('email') or '').lower(): str(item.get('_id')) for item in users if item.get('email')}
    for student in students:
        student_id = str(student.get('_id'))
        email = str(student.get('email') or '').lower()
        mapped_user_id = users_by_email.get(email)
        if mapped_user_id:
            student_user_by_student_id[student_id] = mapped_user_id
            candidate_user_ids.add(mapped_user_id)

    submissions = await db.submissions.find({'student_user_id': {'$in': list(candidate_user_ids)}}).to_list(length=50000)
    event_regs = await db.event_registrations.find({'student_user_id': {'$in': list(candidate_user_ids)}}).to_list(length=50000)
    submissions_count_by_user: dict[str, int] = {}
    regs_count_by_user: dict[str, int] = {}
    for row in submissions:
        key = row.get('student_user_id')
        if key:
            submissions_count_by_user[key] = submissions_count_by_user.get(key, 0) + 1
    for row in event_regs:
        key = row.get('student_user_id')
        if key:
            regs_count_by_user[key] = regs_count_by_user.get(key, 0) + 1

    tree: dict[str, dict] = {}
    for class_doc in classes:
        class_id = str(class_doc.get('_id'))
        course_id = class_doc.get('course_id')
        year_id = class_doc.get('year_id')
        if not course_id or not year_id:
            continue

        course = course_by_id.get(course_id)
        year = year_by_id.get(year_id)
        if not course or not year:
            continue

        course_node = tree.setdefault(
            course_id,
            {
                'id': course_id,
                'name': course.get('name') or 'Course',
                'years': {},
            },
        )
        year_node = course_node['years'].setdefault(
            year_id,
            {
                'id': year_id,
                'name': year.get('label') or f"Year {year.get('year_number')}",
                'classes': [],
            },
        )

        teacher_name = 'Unassigned'
        coordinator_id = class_doc.get('class_coordinator_user_id')
        if coordinator_id and coordinator_id in users_by_id:
            teacher_name = users_by_id[coordinator_id].get('full_name') or 'Unassigned'

        student_items = []
        for student_id in sorted(class_student_ids.get(class_id, set())):
            student = students_by_id.get(student_id)
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

        year_node['classes'].append(
            {
                'id': class_id,
                'name': class_doc.get('name') or class_id,
                'coordinator': teacher_name,
                'students': student_items,
                'subjects': subject_items,
            }
        )

    course_items = []
    for course in tree.values():
        year_items = []
        for year in course['years'].values():
            year_items.append(
                {
                    'id': year['id'],
                    'name': year['name'],
                    'classes': year['classes'],
                }
            )
        course_items.append(
            {
                'id': course['id'],
                'name': course['name'],
                'years': year_items,
            }
        )

    return {
        'university': {
            'id': 'UNI001',
            'name': settings.app_name,
            'location': 'Indore, India',
        },
        'courses': course_items,
    }
