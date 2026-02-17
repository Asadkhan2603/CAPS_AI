from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.evaluations import evaluation_public
from app.schemas.evaluation import EvaluationCreate, EvaluationOut, EvaluationUpdate
from app.services.ai_evaluation import generate_ai_feedback
from app.services.audit import log_audit_event
from app.services.grading import grade_from_total, grand_total, internal_total

router = APIRouter()


def _compute_totals(payload: dict) -> tuple[float, float, str]:
    internal = internal_total(
        payload["attendance_percent"],
        payload["skill"],
        payload["behavior"],
        payload["report"],
        payload["viva"],
    )
    total = grand_total(
        payload["attendance_percent"],
        payload["skill"],
        payload["behavior"],
        payload["report"],
        payload["viva"],
        payload["final_exam"],
    )
    grade = grade_from_total(total)
    return float(internal), float(total), grade


@router.get('/', response_model=List[EvaluationOut])
async def list_evaluations(
    submission_id: str | None = Query(default=None),
    student_user_id: str | None = Query(default=None),
    teacher_user_id: str | None = Query(default=None),
    is_finalized: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> List[EvaluationOut]:
    query = {}
    if submission_id:
        query['submission_id'] = submission_id
    if student_user_id:
        query['student_user_id'] = student_user_id
    if teacher_user_id:
        query['teacher_user_id'] = teacher_user_id
    if is_finalized is not None:
        query['is_finalized'] = is_finalized

    if current_user.get('role') == 'student':
        query['student_user_id'] = str(current_user['_id'])

    cursor = db.evaluations.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [EvaluationOut(**evaluation_public(item)) for item in items]


@router.get('/{evaluation_id}', response_model=EvaluationOut)
async def get_evaluation(
    evaluation_id: str,
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> EvaluationOut:
    item = await db.evaluations.find_one({'_id': parse_object_id(evaluation_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found')
    if current_user.get('role') == 'student' and item.get('student_user_id') != str(current_user['_id']):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to view this evaluation')
    return EvaluationOut(**evaluation_public(item))


@router.post('/', response_model=EvaluationOut, status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    payload: EvaluationCreate,
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> EvaluationOut:
    submission = await db.submissions.find_one({'_id': parse_object_id(payload.submission_id)})
    if not submission:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Submission not found for provided submission_id')

    existing = await db.evaluations.find_one({'submission_id': payload.submission_id})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Evaluation already exists for submission')

    payload_data = payload.model_dump()
    internal, total, grade = _compute_totals(payload_data)
    ai_feedback = generate_ai_feedback(submission.get('extracted_text', ''), max_score=10.0)

    document = {
        'submission_id': payload.submission_id,
        'student_user_id': submission.get('student_user_id'),
        'teacher_user_id': str(current_user['_id']),
        'attendance_percent': payload.attendance_percent,
        'skill': payload.skill,
        'behavior': payload.behavior,
        'report': payload.report,
        'viva': payload.viva,
        'final_exam': payload.final_exam,
        'internal_total': internal,
        'grand_total': total,
        'grade': grade,
        'ai_score': ai_feedback.get('score'),
        'ai_feedback': ai_feedback.get('summary'),
        'remarks': payload.remarks,
        'is_finalized': payload.is_finalized,
        'created_at': datetime.now(timezone.utc),
    }

    result = await db.evaluations.insert_one(document)
    created = await db.evaluations.find_one({'_id': result.inserted_id})

    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='create',
        entity_type='evaluation',
        entity_id=str(result.inserted_id),
        detail=f"Created evaluation for submission {payload.submission_id}",
    )

    return EvaluationOut(**evaluation_public(created))


@router.put('/{evaluation_id}', response_model=EvaluationOut)
async def update_evaluation(
    evaluation_id: str,
    payload: EvaluationUpdate,
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> EvaluationOut:
    evaluation_obj_id = parse_object_id(evaluation_id)
    item = await db.evaluations.find_one({'_id': evaluation_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Evaluation not found')

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')

    if item.get('is_finalized') and current_user.get('role') != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Finalized evaluation can only be modified by admin')

    merged = {
        'attendance_percent': update_data.get('attendance_percent', item.get('attendance_percent', 0)),
        'skill': update_data.get('skill', item.get('skill', 0.0)),
        'behavior': update_data.get('behavior', item.get('behavior', 0.0)),
        'report': update_data.get('report', item.get('report', 0.0)),
        'viva': update_data.get('viva', item.get('viva', 0.0)),
        'final_exam': update_data.get('final_exam', item.get('final_exam', 0)),
    }
    internal, total, grade = _compute_totals(merged)
    update_data['internal_total'] = internal
    update_data['grand_total'] = total
    update_data['grade'] = grade

    await db.evaluations.update_one({'_id': evaluation_obj_id}, {'$set': update_data})
    updated = await db.evaluations.find_one({'_id': evaluation_obj_id})

    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='update',
        entity_type='evaluation',
        entity_id=evaluation_id,
        detail='Updated evaluation fields',
    )

    return EvaluationOut(**evaluation_public(updated))
