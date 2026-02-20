from datetime import datetime, timezone
from pathlib import Path
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.submissions import submission_public
from app.schemas.submission import SubmissionOut, SubmissionUpdate
from app.services.ai_evaluation import generate_ai_feedback
from app.services.audit import log_audit_event
from app.services.file_parser import parse_file_content

router = APIRouter()

UPLOAD_DIR = Path('uploads/submissions')
MAX_UPLOAD_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md'}


async def _teacher_can_access_assignment(teacher_user_id: str, assignment_id: str) -> bool:
    assignment = await db.assignments.find_one({'_id': parse_object_id(assignment_id)})
    if not assignment:
        return False
    if assignment.get('created_by') == teacher_user_id:
        return True

    class_id = assignment.get('class_id')
    if not class_id:
        return False

    class_doc = await db.classes.find_one({'_id': parse_object_id(class_id)})
    if not class_doc:
        return False
    return class_doc.get('class_coordinator_user_id') == teacher_user_id


async def _teacher_can_access_submission(teacher_user_id: str, submission: dict) -> bool:
    assignment_id = submission.get('assignment_id')
    if not assignment_id:
        return False
    return await _teacher_can_access_assignment(teacher_user_id, assignment_id)


async def _evaluate_submission_and_save(submission_obj_id, item: dict) -> dict:
    extracted_text = item.get('extracted_text', '')
    feedback = generate_ai_feedback(extracted_text, max_score=10.0)
    ai_status = str(feedback.get('status') or 'failed')
    update_data = {
        'ai_status': ai_status,
        'ai_score': feedback.get('score'),
        'ai_feedback': feedback.get('summary'),
        'ai_provider': feedback.get('provider'),
        'ai_error': feedback.get('error'),
    }
    await db.submissions.update_one({'_id': submission_obj_id}, {'$set': update_data})
    updated = await db.submissions.find_one({'_id': submission_obj_id})
    return updated or item


@router.get('/', response_model=List[SubmissionOut])
async def list_submissions(
    assignment_id: str | None = Query(default=None),
    student_user_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias='status'),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> List[SubmissionOut]:
    query = {}
    if assignment_id:
        query['assignment_id'] = assignment_id
    if student_user_id:
        query['student_user_id'] = student_user_id
    if status_filter:
        query['status'] = status_filter

    if current_user.get('role') == 'student':
        query['student_user_id'] = str(current_user['_id'])
    cursor = db.submissions.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    if current_user.get('role') == 'teacher':
        teacher_user_id = str(current_user['_id'])
        scoped_items = []
        for item in items:
            assignment_id = item.get('assignment_id')
            if not assignment_id:
                continue
            if await _teacher_can_access_assignment(teacher_user_id, assignment_id):
                scoped_items.append(item)
        items = scoped_items
    return [SubmissionOut(**submission_public(item)) for item in items]


@router.get('/{submission_id}', response_model=SubmissionOut)
async def get_submission(
    submission_id: str,
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> SubmissionOut:
    item = await db.submissions.find_one({'_id': parse_object_id(submission_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Submission not found')

    if current_user.get('role') == 'student' and item.get('student_user_id') != str(current_user['_id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to view this submission')
    if current_user.get('role') == 'teacher':
        allowed = await _teacher_can_access_submission(str(current_user['_id']), item)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to view this submission')

    return SubmissionOut(**submission_public(item))


@router.post('/upload', response_model=SubmissionOut, status_code=status.HTTP_201_CREATED)
async def upload_submission(
    assignment_id: str = Form(...),
    notes: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> SubmissionOut:
    if current_user.get('role') != 'student':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Only students can upload submissions')

    assignment = await db.assignments.find_one({'_id': parse_object_id(assignment_id)})
    if not assignment:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Assignment not found for provided assignment_id')
    if assignment.get('status', 'open') == 'closed':
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Assignment is closed')

    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported file type')

    content = await file.read()
    size = len(content)
    if size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Uploaded file is empty')
    if size > MAX_UPLOAD_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='File exceeds 10MB limit')

    extracted_text = parse_file_content(file.filename or 'submission', content)

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid4().hex}{suffix}"
    saved_path = UPLOAD_DIR / stored_name
    saved_path.write_bytes(content)

    document = {
        'assignment_id': assignment_id,
        'student_user_id': str(current_user['_id']),
        'original_filename': file.filename or 'submission',
        'stored_filename': stored_name,
        'file_mime_type': file.content_type,
        'file_size_bytes': size,
        'notes': notes,
        'status': 'submitted',
        'ai_status': 'pending',
        'ai_score': None,
        'ai_feedback': None,
        'ai_provider': None,
        'ai_error': None,
        'similarity_score': None,
        'extracted_text': extracted_text,
        'created_at': datetime.now(timezone.utc),
    }

    result = await db.submissions.insert_one(document)
    created = await db.submissions.find_one({'_id': result.inserted_id})
    return SubmissionOut(**submission_public(created))


@router.post('/{submission_id}/ai-evaluate', response_model=SubmissionOut)
async def ai_evaluate_submission(
    submission_id: str,
    force: bool = Query(default=False),
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> SubmissionOut:
    submission_obj_id = parse_object_id(submission_id)
    item = await db.submissions.find_one({'_id': submission_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Submission not found')

    if current_user.get('role') == 'teacher':
        allowed = await _teacher_can_access_submission(str(current_user['_id']), item)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to evaluate this submission')

    if item.get('ai_status') == 'completed' and not force:
        return SubmissionOut(**submission_public(item))

    await db.submissions.update_one({'_id': submission_obj_id}, {'$set': {'ai_status': 'running'}})
    updated = await _evaluate_submission_and_save(submission_obj_id, item)
    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='ai_evaluate',
        entity_type='submission',
        entity_id=submission_id,
        detail=f"AI evaluation status={updated.get('ai_status')}",
    )
    return SubmissionOut(**submission_public(updated))


@router.post('/ai-evaluate/pending')
async def ai_evaluate_pending_submissions(
    assignment_id: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> dict:
    query = {'ai_status': {'$in': ['pending', 'failed', None]}}
    if assignment_id:
        query['assignment_id'] = assignment_id

    items = await db.submissions.find(query).limit(limit).to_list(length=limit)
    evaluated = []
    teacher_user_id = str(current_user['_id'])

    for item in items:
        if current_user.get('role') == 'teacher':
            allowed = await _teacher_can_access_submission(teacher_user_id, item)
            if not allowed:
                continue
        submission_id = str(item.get('_id'))
        submission_obj_id = parse_object_id(submission_id)
        await db.submissions.update_one({'_id': submission_obj_id}, {'$set': {'ai_status': 'running'}})
        updated = await _evaluate_submission_and_save(submission_obj_id, item)
        await log_audit_event(
            actor_user_id=str(current_user['_id']),
            action='ai_evaluate',
            entity_type='submission',
            entity_id=submission_id,
            detail=f"Bulk AI evaluation status={updated.get('ai_status')}",
        )
        evaluated.append(
            {
                'submission_id': submission_id,
                'ai_status': updated.get('ai_status'),
                'ai_score': updated.get('ai_score'),
            }
        )

    return {
        'count': len(evaluated),
        'items': evaluated,
    }


@router.put('/{submission_id}', response_model=SubmissionOut)
async def update_submission(
    submission_id: str,
    payload: SubmissionUpdate,
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> SubmissionOut:
    item = await db.submissions.find_one({'_id': parse_object_id(submission_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Submission not found')

    if current_user.get('role') == 'student' and item.get('student_user_id') != str(current_user['_id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to update this submission')
    if current_user.get('role') == 'teacher':
        allowed = await _teacher_can_access_submission(str(current_user['_id']), item)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to update this submission')

    update_data = payload.model_dump(exclude_none=True)
    if current_user.get('role') == 'student':
        update_data = {
            key: value for key, value in update_data.items() if key in {'notes'}
        }
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')

    await db.submissions.update_one({'_id': parse_object_id(submission_id)}, {'$set': update_data})
    updated = await db.submissions.find_one({'_id': parse_object_id(submission_id)})
    return SubmissionOut(**submission_public(updated))


@router.delete('/{submission_id}')
async def delete_submission(
    submission_id: str,
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    item = await db.submissions.find_one({'_id': parse_object_id(submission_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Submission not found')

    if current_user.get('role') == 'student' and item.get('student_user_id') != str(current_user['_id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to delete this submission')
    if current_user.get('role') == 'teacher':
        allowed = await _teacher_can_access_submission(str(current_user['_id']), item)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to delete this submission')

    result = await db.submissions.delete_one({'_id': parse_object_id(submission_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Submission not found')

    saved_name = item.get('stored_filename')
    if saved_name:
        saved_path = UPLOAD_DIR / saved_name
        if saved_path.exists():
            saved_path.unlink()

    return {'message': 'Submission deleted'}
