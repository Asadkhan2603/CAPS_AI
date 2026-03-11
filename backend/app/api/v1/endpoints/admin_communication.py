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

    if scope == 'batch':
        class_ids = [str(item) for item in await db.classes.distinct('_id', {'batch_id': scope_ref_id, 'is_active': True}) if item]
        student_ids: set[str] = set()
        if class_ids:
            student_ids = {
                value
                for value in await db.enrollments.distinct('student_id', {'class_id': {'$in': class_ids}})
                if isinstance(value, str) and value
            }
        return {'scope': 'batch', 'matched_users': len(student_ids), 'estimated_reach': len(student_ids)}

    if scope == 'class':
        parse_object_id(scope_ref_id)
        student_ids = {
            value
            for value in await db.enrollments.distinct('student_id', {'class_id': scope_ref_id})
            if isinstance(value, str) and value
        }
        return {'scope': 'class', 'matched_users': len(student_ids), 'estimated_reach': len(student_ids)}

    if scope == 'subject':
        parse_object_id(scope_ref_id)
        class_ids = {
            value
            for value in await db.assignments.distinct('class_id', {'subject_id': scope_ref_id})
            if isinstance(value, str) and value
        }
        student_ids: set[str] = set()
        if class_ids:
            student_ids = {
                value
                for value in await db.enrollments.distinct('student_id', {'class_id': {'$in': list(class_ids)}})
                if isinstance(value, str) and value
            }
        return {'scope': 'subject', 'matched_users': len(student_ids), 'estimated_reach': len(student_ids)}

    raise HTTPException(status_code=400, detail='Unsupported scope')
