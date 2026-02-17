from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import db
from app.core.config import settings
from app.core.mongo import parse_object_id
from app.core.security import require_roles

router = APIRouter()


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
        my_assignment_docs = await db.assignments.find({'created_by': user_id}).to_list(length=1000)
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
            'sections': await db.sections.count_documents({}),
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


@router.get('/teacher/classes')
async def teacher_section_tiles(
    current_user=Depends(require_roles(['teacher'])),
) -> dict:
    user_id = str(current_user.get('_id'))
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid user context')

    mappings = await db.section_subjects.find({'teacher_user_id': user_id, 'is_active': True}).to_list(length=1000)
    tiles = []
    now = datetime.now(timezone.utc)

    for mapping in mappings:
        section_id = mapping.get('section_id')
        subject_id = mapping.get('subject_id')
        if not section_id or not subject_id:
            continue

        section = await db.sections.find_one({'_id': parse_object_id(section_id)})
        subject = await db.subjects.find_one({'_id': parse_object_id(subject_id)})

        total_students = await db.students.count_documents({'section_id': section_id})
        active_assignments = await db.assignments.count_documents(
            {'section_id': section_id, 'subject_id': subject_id, 'status': 'open'}
        )

        assignment_docs = await db.assignments.find({'section_id': section_id, 'subject_id': subject_id}).to_list(length=1000)
        assignment_ids = [str(item.get('_id')) for item in assignment_docs]

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
            submission_docs = await db.submissions.find({'assignment_id': {'$in': assignment_ids}}).to_list(length=2000)
            submission_ids = [str(item.get('_id')) for item in submission_docs]
            if submission_ids:
                risky = await db.evaluations.find(
                    {
                        'submission_id': {'$in': submission_ids},
                        '$or': [{'grand_total': {'$lt': 40}}, {'attendance_percent': {'$lt': 70}}],
                    }
                ).to_list(length=2000)
                risk_student_count = len({item.get('student_user_id') for item in risky if item.get('student_user_id')})

        if risk_student_count >= 3 or similarity_alert_count >= 3 or late_submissions_count >= 5:
            health_status = 'risk'
        elif risk_student_count >= 1 or similarity_alert_count >= 1 or late_submissions_count >= 1:
            health_status = 'attention'
        else:
            health_status = 'healthy'

        tiles.append(
            {
                'section_id': section_id,
                'subject_name': (subject or {}).get('name', 'Unknown Subject'),
                'year': (section or {}).get('academic_year'),
                'class_name': (section or {}).get('program'),
                'section_name': (section or {}).get('name', section_id),
                'total_students': total_students,
                'active_assignments': active_assignments,
                'late_submissions_count': late_submissions_count,
                'similarity_alert_count': similarity_alert_count,
                'risk_student_count': risk_student_count,
                'health_status': health_status,
            }
        )

    return {'items': tiles}


@router.get('/academic-structure')
async def academic_structure(
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    role = current_user.get('role')
    user_id = str(current_user.get('_id'))
    user_email = str(current_user.get('email') or '').lower()

    courses = await db.courses.find({'is_active': True}).to_list(length=2000)
    years = await db.years.find({'is_active': True}).to_list(length=4000)
    classes = await db.classes.find({'is_active': True}).to_list(length=8000)
    enrollments = await db.enrollments.find({}).to_list(length=20000)
    students = await db.students.find({'is_active': True}).to_list(length=20000)
    users = await db.users.find({}).to_list(length=4000)

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
        teacher_class_ids = {
            str(item.get('_id'))
            for item in classes
            if item.get('class_coordinator_user_id') == user_id
        }
        classes = [item for item in classes if str(item.get('_id')) in teacher_class_ids] if teacher_class_ids else []

    course_by_id = {str(item.get('_id')): item for item in courses}
    years_by_course_id: dict[str, list[dict]] = {}
    for year in years:
        years_by_course_id.setdefault(year.get('course_id'), []).append(year)
    users_by_id = {str(item.get('_id')): item for item in users}

    students_by_id = {str(item.get('_id')): item for item in students}
    students_by_section_key: dict[str, list[dict]] = {}
    for student in students:
        section_key = str(student.get('section_id') or '')
        if section_key:
            students_by_section_key.setdefault(section_key, []).append(student)

    enrollments_by_class_id: dict[str, list[dict]] = {}
    for enrollment in enrollments:
        enrollments_by_class_id.setdefault(enrollment.get('class_id'), []).append(enrollment)

    candidate_student_user_ids: set[str] = set()
    student_user_id_by_student_id: dict[str, str] = {}
    users_by_email = {str(item.get('email') or '').lower(): str(item.get('_id')) for item in users if item.get('email')}
    for student in students:
        student_id = str(student.get('_id'))
        email = str(student.get('email') or '').lower()
        mapped_user_id = users_by_email.get(email)
        if mapped_user_id:
            student_user_id_by_student_id[student_id] = mapped_user_id
            candidate_student_user_ids.add(mapped_user_id)

    submissions = await db.submissions.find({'student_user_id': {'$in': list(candidate_student_user_ids)}}).to_list(length=50000)
    event_regs = await db.event_registrations.find({'student_user_id': {'$in': list(candidate_student_user_ids)}}).to_list(length=50000)
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

    faculty_groups: dict[str, dict] = {}
    for class_doc in classes:
        class_id = str(class_doc.get('_id'))
        course_id = class_doc.get('course_id')
        year_id = class_doc.get('year_id')
        if not course_id or not year_id:
            continue

        course = course_by_id.get(course_id)
        if not course:
            continue
        year = next((item for item in years_by_course_id.get(course_id, []) if str(item.get('_id')) == year_id), None)
        if not year:
            continue

        faculty_name = class_doc.get('faculty_name') or 'Faculty of Engineering'
        branch_name = class_doc.get('branch_name') or class_doc.get('name') or 'General Branch'
        section_name = class_doc.get('section') or class_doc.get('name') or f'Section-{class_id[:6]}'
        teacher_name = 'Unassigned'
        teacher_user_id = class_doc.get('class_coordinator_user_id')
        if teacher_user_id and teacher_user_id in users_by_id:
            teacher_name = users_by_id[teacher_user_id].get('full_name') or 'Unassigned'

        class_enrollments = enrollments_by_class_id.get(class_id, [])
        section_students = [students_by_id[item.get('student_id')] for item in class_enrollments if item.get('student_id') in students_by_id]
        if not section_students:
            section_students = students_by_section_key.get(section_name, [])

        student_items = []
        for student in section_students:
            student_id = str(student.get('_id'))
            mapped_user_id = student_user_id_by_student_id.get(student_id)
            student_items.append(
                {
                    'id': student_id,
                    'name': student.get('full_name'),
                    'rollNo': student.get('roll_number'),
                    'logs': {
                        'assignment_submissions': submissions_count_by_user.get(mapped_user_id or '', 0),
                        'event_registrations': regs_count_by_user.get(mapped_user_id or '', 0),
                    },
                }
            )

        faculty_node = faculty_groups.setdefault(
            faculty_name,
            {
                'id': f"FAC-{abs(hash(faculty_name)) % 100000:05d}",
                'name': faculty_name,
                'courses': {},
            },
        )
        course_key = str(course.get('_id'))
        course_node = faculty_node['courses'].setdefault(
            course_key,
            {
                'id': course_key,
                'name': course.get('name') or 'Course',
                'years': {},
            },
        )
        year_key = str(year.get('_id'))
        year_node = course_node['years'].setdefault(
            year_key,
            {
                'id': year_key,
                'name': year.get('label') or f"Year {year.get('year_number')}",
                'branches': {},
            },
        )
        branch_key = branch_name.lower()
        branch_node = year_node['branches'].setdefault(
            branch_key,
            {
                'id': f"BR-{abs(hash(branch_name + year_key)) % 100000:05d}",
                'name': branch_name,
                'sections': [],
            },
        )
        branch_node['sections'].append(
            {
                'id': class_id,
                'name': section_name,
                'teacher': teacher_name,
                'students': student_items,
            }
        )

    faculty_items = []
    for faculty in faculty_groups.values():
        course_items = []
        for course in faculty['courses'].values():
            year_items = []
            for year in course['years'].values():
                branch_items = []
                for branch in year['branches'].values():
                    branch_items.append(
                        {
                            'id': branch['id'],
                            'name': branch['name'],
                            'sections': branch['sections'],
                        }
                    )
                year_items.append(
                    {
                        'id': year['id'],
                        'name': year['name'],
                        'branches': branch_items,
                    }
                )
            course_items.append(
                {
                    'id': course['id'],
                    'name': course['name'],
                    'years': year_items,
                }
            )
        faculty_items.append({'id': faculty['id'], 'name': faculty['name'], 'courses': course_items})

    return {
        'university': {
            'id': 'UNI001',
            'name': settings.app_name,
            'location': 'Indore, India',
        },
        'faculties': faculty_items,
    }
