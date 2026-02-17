from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import settings
from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.similarity_logs import similarity_log_public
from app.schemas.similarity_log import SimilarityLogOut
from app.services.audit import log_audit_event
from app.services.similarity_engine import compute_similarity_scores

router = APIRouter()


@router.get('/checks', response_model=List[SimilarityLogOut])
async def similarity_checks(
    source_submission_id: str | None = Query(default=None),
    is_flagged: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[SimilarityLogOut]:
    query = {}
    if source_submission_id:
        query['source_submission_id'] = source_submission_id
    if is_flagged is not None:
        query['is_flagged'] = is_flagged

    cursor = db.similarity_logs.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [SimilarityLogOut(**similarity_log_public(item)) for item in items]


@router.post('/checks/run/{submission_id}', response_model=List[SimilarityLogOut])
async def run_similarity_check(
    submission_id: str,
    threshold: float | None = Query(default=None, ge=0, le=1),
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[SimilarityLogOut]:
    source_obj_id = parse_object_id(submission_id)
    source = await db.submissions.find_one({'_id': source_obj_id})
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Submission not found')

    source_text = source.get('extracted_text')
    if not source_text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Submission has no extracted text')

    source_assignment_id = source.get('assignment_id')
    candidate_cursor = db.submissions.find({'assignment_id': source_assignment_id})
    candidates = await candidate_cursor.to_list(length=1000)

    candidate_texts = []
    for item in candidates:
        item_id = str(item.get('_id'))
        if item_id == submission_id:
            continue
        candidate_texts.append((item_id, item.get('extracted_text', '')))

    scores = compute_similarity_scores(source_text, candidate_texts)
    active_threshold = threshold if threshold is not None else settings.similarity_threshold

    created_items = []
    max_score = 0.0
    for matched_submission_id, score in scores:
        max_score = max(max_score, score)
        document = {
            'source_submission_id': submission_id,
            'matched_submission_id': matched_submission_id,
            'score': score,
            'threshold': active_threshold,
            'is_flagged': score >= active_threshold,
            'created_at': datetime.now(timezone.utc),
        }
        result = await db.similarity_logs.insert_one(document)
        created = await db.similarity_logs.find_one({'_id': result.inserted_id})
        if created:
            created_items.append(created)

    await db.submissions.update_one(
        {'_id': source_obj_id},
        {'$set': {'similarity_score': round(max_score, 4)}},
    )

    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='run_similarity',
        entity_type='submission',
        entity_id=submission_id,
        detail=f'Generated {len(created_items)} similarity checks',
    )

    return [SimilarityLogOut(**similarity_log_public(item)) for item in created_items]
