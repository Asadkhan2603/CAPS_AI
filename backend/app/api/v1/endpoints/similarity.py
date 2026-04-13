from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status

from app.core.config import settings
from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.similarity_logs import similarity_log_public
from app.schemas.similarity_log import SimilarityLogOut, SimilarityRunQueuedResponse
from app.services.ai_jobs import AI_JOB_TYPE_SIMILARITY, queue_ai_job, schedule_ai_job_processing, serialize_ai_job
from app.services.ai_runtime import get_ai_runtime_settings
from app.services.audit import log_audit_event
from app.services.similarity_access_policy import (
    can_view_similarity_log,
    filter_similarity_logs_for_user,
    teacher_can_run_similarity_for_assignment,
)
from app.services.similarity_pipeline import run_similarity_pipeline

router = APIRouter()
_REVIEW_STATUSES = {"open", "in_progress", "fixed", "reopened"}


async def _load_similarity_run_context(
    submission_id: str,
    current_user: dict,
) -> tuple[dict, str, dict | None]:
    source_obj_id = parse_object_id(submission_id)
    source = await db.submissions.find_one({'_id': source_obj_id})
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Submission not found')

    source_text = source.get('extracted_text')
    if not source_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Submission has no extracted text')

    source_assignment_id = source.get('assignment_id')
    if not source_assignment_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Submission has no assignment mapping')

    if current_user.get('role') == 'teacher':
        allowed = await teacher_can_run_similarity_for_assignment(
            str(current_user['_id']),
            source_assignment_id,
            database=db,
        )
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to run similarity on this submission')

    source_assignment = await db.assignments.find_one({'_id': parse_object_id(source_assignment_id)})
    if source_assignment and source_assignment.get('plagiarism_enabled', True) is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Plagiarism detection is disabled for this assignment',
        )
    return source, source_assignment_id, source_assignment


async def _queue_similarity_job_response(
    *,
    submission_id: str,
    active_threshold: float,
    current_user: dict,
    candidate_count: int,
    detail: str,
) -> SimilarityRunQueuedResponse:
    job, created = await queue_ai_job(
        job_type=AI_JOB_TYPE_SIMILARITY,
        requested_by_user_id=str(current_user['_id']),
        requested_by_role=str(current_user.get('role') or ''),
        params={
            'submission_id': submission_id,
            'threshold': active_threshold,
        },
        idempotency_key=f"similarity:{current_user.get('role')}:{current_user.get('_id')}:{submission_id}:{round(active_threshold, 4)}",
    )
    schedule_ai_job_processing(max_jobs=1)
    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='run_similarity_async',
        entity_type='ai_job',
        entity_id=str(job.get('_id')),
        detail=detail,
    )
    return SimilarityRunQueuedResponse(
        success=True,
        status='queued',
        queued=created,
        submission_id=submission_id,
        candidate_count=candidate_count,
        async_only_threshold=max(1, int(settings.similarity_sync_inline_candidate_limit)),
        detail=detail,
        job=serialize_ai_job(job),
    )


@router.get('/checks', response_model=List[SimilarityLogOut])
async def similarity_checks(
    source_submission_id: str | None = Query(default=None),
    is_flagged: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[SimilarityLogOut]:
    query = {}
    if source_submission_id:
        query['source_submission_id'] = source_submission_id
    if is_flagged is not None:
        query['is_flagged'] = is_flagged

    cursor = db.similarity_logs.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)

    items = await filter_similarity_logs_for_user(current_user, items, database=db)

    return [SimilarityLogOut(**similarity_log_public(item)) for item in items]


@router.get('/checks/{log_id}', response_model=SimilarityLogOut)
async def get_similarity_check(
    log_id: str,
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> SimilarityLogOut:
    item = await db.similarity_logs.find_one({"_id": parse_object_id(log_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Similarity log not found')
    allowed = await can_view_similarity_log(current_user, item, database=db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to view this similarity log')
    return SimilarityLogOut(**similarity_log_public(item, include_evidence=True))


@router.patch('/checks/{log_id}', response_model=SimilarityLogOut)
async def update_similarity_check(
    log_id: str,
    payload: dict,
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> SimilarityLogOut:
    item = await db.similarity_logs.find_one({"_id": parse_object_id(log_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Similarity log not found')
    allowed = await can_view_similarity_log(current_user, item, database=db)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to update this similarity log')

    review_status = payload.get("review_status")
    review_notes = payload.get("review_notes")
    update_data = {}
    if review_status is not None:
        status_value = str(review_status).strip().lower()
        if status_value not in _REVIEW_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid review_status value')
        update_data["review_status"] = status_value
    if review_notes is not None:
        update_data["review_notes"] = str(review_notes).strip()[:2000]

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No review fields provided')

    update_data["reviewed_by_user_id"] = str(current_user.get("_id"))
    update_data["reviewed_at"] = datetime.now(timezone.utc)

    await db.similarity_logs.update_one({"_id": parse_object_id(log_id)}, {"$set": update_data})
    updated = await db.similarity_logs.find_one({"_id": parse_object_id(log_id)})
    return SimilarityLogOut(**similarity_log_public(updated, include_evidence=True))


@router.post('/checks/run/{submission_id}', response_model=List[SimilarityLogOut] | SimilarityRunQueuedResponse)
async def run_similarity_check(
    submission_id: str,
    response: Response,
    threshold: float | None = Query(default=None, ge=0, le=1),
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[SimilarityLogOut] | SimilarityRunQueuedResponse:
    source, source_assignment_id, source_assignment = await _load_similarity_run_context(submission_id, current_user)

    runtime_settings = await get_ai_runtime_settings()
    active_threshold = threshold if threshold is not None else float(runtime_settings.get('similarity_threshold') or 0.8)
    candidate_count = max(0, (await db.submissions.count_documents({"assignment_id": source_assignment_id})) - 1)
    if candidate_count > max(1, int(settings.similarity_sync_inline_candidate_limit)):
        queued_response = await _queue_similarity_job_response(
            submission_id=submission_id,
            active_threshold=active_threshold,
            current_user=current_user,
            candidate_count=candidate_count,
            detail=(
                f"Similarity run deferred to async job because candidate count {candidate_count} exceeds "
                f"inline limit {max(1, int(settings.similarity_sync_inline_candidate_limit))}"
            ),
        )
        response.status_code = status.HTTP_202_ACCEPTED
        return queued_response

    result = await run_similarity_pipeline(
        submission_id=submission_id,
        source=source,
        source_assignment=source_assignment,
        active_threshold=active_threshold,
        actor_user_id=str(current_user['_id']),
    )

    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='run_similarity',
        entity_type='submission',
        entity_id=submission_id,
        detail=f"Generated {result.get('created_count', 0)} similarity checks",
    )

    created_items = list(result.get('items') or [])
    created_items = await filter_similarity_logs_for_user(current_user, created_items, database=db)

    return [SimilarityLogOut(**similarity_log_public(item)) for item in created_items]


@router.post('/checks/run-async/{submission_id}')
async def run_similarity_check_async(
    submission_id: str,
    threshold: float | None = Query(default=None, ge=0, le=1),
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> dict:
    _source, source_assignment_id, _source_assignment = await _load_similarity_run_context(submission_id, current_user)

    runtime_settings = await get_ai_runtime_settings()
    active_threshold = threshold if threshold is not None else float(runtime_settings.get('similarity_threshold') or 0.8)
    candidate_count = max(0, (await db.submissions.count_documents({"assignment_id": source_assignment_id})) - 1)
    queued_response = await _queue_similarity_job_response(
        submission_id=submission_id,
        active_threshold=active_threshold,
        current_user=current_user,
        candidate_count=candidate_count,
        detail='Queued durable similarity computation',
    )
    return queued_response.model_dump()
