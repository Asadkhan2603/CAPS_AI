from fastapi import APIRouter, Depends

from app.core.database import db
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

    summary = {
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
        'notifications': await db.notifications.count_documents({}),
    }

    if role == 'teacher':
        summary['my_assignments'] = await db.assignments.count_documents({'created_by': user_id})
        summary['my_evaluations'] = await db.evaluations.count_documents({'teacher_user_id': user_id})

    return {'role': role, 'summary': summary}
