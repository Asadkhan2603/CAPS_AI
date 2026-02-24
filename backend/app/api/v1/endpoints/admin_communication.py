from fastapi import APIRouter, Depends, HTTPException

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission

router = APIRouter()


@router.post('/preview-target')
async def preview_target(
    payload: dict,
    _current_user=Depends(require_permission('announcements.publish')),
) -> dict:
    scope = (payload.get('scope') or 'college').strip().lower()
    scope_ref_id = payload.get('scope_ref_id')

    if scope in {'section', 'class'}:
        scope = 'class'

    if scope == 'college':
        matched_users = await db.users.count_documents({'is_active': True})
        return {'scope': 'college', 'matched_users': matched_users, 'estimated_reach': matched_users}

    if not scope_ref_id:
        raise HTTPException(status_code=400, detail='scope_ref_id is required for selected scope')

    if scope == 'year':
        class_rows = await db.classes.find({'year_id': scope_ref_id}).to_list(length=5000)
        class_ids = [str(item.get('_id')) for item in class_rows if item.get('_id')]
        student_ids = set()
        if class_ids:
            enrollment_rows = await db.enrollments.find({'class_id': {'$in': class_ids}}).to_list(length=20000)
            for row in enrollment_rows:
                if row.get('student_id'):
                    student_ids.add(row.get('student_id'))
        return {'scope': 'year', 'matched_users': len(student_ids), 'estimated_reach': len(student_ids)}

    if scope == 'class':
        parse_object_id(scope_ref_id)
        enrollment_rows = await db.enrollments.find({'class_id': scope_ref_id}).to_list(length=10000)
        student_ids = {row.get('student_id') for row in enrollment_rows if row.get('student_id')}
        return {'scope': 'class', 'matched_users': len(student_ids), 'estimated_reach': len(student_ids)}

    if scope == 'subject':
        parse_object_id(scope_ref_id)
        assignment_rows = await db.assignments.find({'subject_id': scope_ref_id}).to_list(length=5000)
        class_ids = {row.get('class_id') for row in assignment_rows if row.get('class_id')}
        student_ids = set()
        if class_ids:
            enrollment_rows = await db.enrollments.find({'class_id': {'$in': list(class_ids)}}).to_list(length=20000)
            for row in enrollment_rows:
                if row.get('student_id'):
                    student_ids.add(row.get('student_id'))
        return {'scope': 'subject', 'matched_users': len(student_ids), 'estimated_reach': len(student_ids)}

    raise HTTPException(status_code=400, detail='Unsupported scope')
