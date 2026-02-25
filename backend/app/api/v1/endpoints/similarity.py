from datetime import datetime, timezone
from typing import List, Set

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from app.core.config import settings
from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.similarity_logs import similarity_log_public
from app.schemas.similarity_log import SimilarityLogOut
from app.services.audit import log_audit_event
from app.services.notifications import create_notification
from app.services.similarity_engine import compute_similarity_scores

router = APIRouter()


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


async def _class_coordinator_class_ids(user_id: str) -> Set[str]:
    classes = await db.classes.find({'class_coordinator_user_id': user_id}).to_list(length=1000)
    return {str(item.get('_id')) for item in classes if item.get('_id')}


async def _can_view_similarity_log(current_user: dict, item: dict) -> bool:
    if current_user.get('role') == 'admin':
        return True
    if current_user.get('role') != 'teacher':
        return False

    user_id = str(current_user['_id'])
    extensions = current_user.get('extended_roles', [])
    if 'year_head' in extensions:
        return True

    if 'class_coordinator' in extensions:
        coordinator_classes = await _class_coordinator_class_ids(user_id)
        if item.get('source_class_id') in coordinator_classes or item.get('matched_class_id') in coordinator_classes:
            return True

    source_assignment_id = item.get('source_assignment_id')
    matched_assignment_id = item.get('matched_assignment_id')
    if source_assignment_id and await _teacher_can_access_assignment(user_id, source_assignment_id):
        return True
    if matched_assignment_id and await _teacher_can_access_assignment(user_id, matched_assignment_id):
        return True
    return False


async def _notify_similarity_alert(
    *,
    source_submission: dict,
    source_assignment: dict | None,
    matched_submission_id: str,
    score: float,
    threshold: float,
    created_by: str,
) -> None:
    recipients: Set[str] = set()

    if source_assignment and source_assignment.get('created_by'):
        recipients.add(str(source_assignment.get('created_by')))

    source_class_id = source_assignment.get('class_id') if source_assignment else None
    if source_class_id:
        class_doc = await db.classes.find_one({'_id': parse_object_id(source_class_id)})
        if class_doc and class_doc.get('class_coordinator_user_id'):
            recipients.add(str(class_doc.get('class_coordinator_user_id')))

    year_heads = await db.users.find(
        {'role': 'teacher', 'extended_roles': {'$in': ['year_head']}}
    ).to_list(length=1000)
    for user in year_heads:
        recipients.add(str(user.get('_id')))

    title = 'Similarity Alert'
    message = (
        f"Submission {str(source_submission.get('_id'))} matched {matched_submission_id} "
        f"with score {round(score, 3)} (threshold {round(threshold, 3)})."
    )
    for user_id in recipients:
        await create_notification(
            title=title,
            message=message,
            priority='urgent',
            scope='similarity',
            target_user_id=user_id,
            created_by=created_by,
        )


async def _run_similarity_pipeline(
    *,
    submission_id: str,
    source: dict,
    source_assignment: dict | None,
    active_threshold: float,
    actor_user_id: str,
) -> list[dict]:
    source_text = source.get('extracted_text') or ''
    source_assignment_id = source.get('assignment_id')

    candidate_cursor = db.submissions.find({'assignment_id': source_assignment_id})
    candidates = await candidate_cursor.to_list(length=1000)

    candidate_texts = []
    id_to_submission = {}
    for item in candidates:
        item_id = str(item.get('_id'))
        if item_id == submission_id:
            continue
        candidate_texts.append((item_id, item.get('extracted_text', '')))
        id_to_submission[item_id] = item

    scores = compute_similarity_scores(source_text, candidate_texts)

    created_items = []
    max_score = 0.0
    for matched_submission_id, score in scores:
        max_score = max(max_score, score)
        matched_submission = id_to_submission.get(matched_submission_id)
        matched_assignment_id = matched_submission.get('assignment_id') if matched_submission else None
        matched_assignment = None
        if matched_assignment_id:
            matched_assignment = await db.assignments.find_one({'_id': parse_object_id(matched_assignment_id)})

        is_flagged = score >= active_threshold
        document = {
            'source_submission_id': submission_id,
            'matched_submission_id': matched_submission_id,
            'source_assignment_id': source_assignment_id,
            'matched_assignment_id': matched_assignment_id,
            'source_class_id': source_assignment.get('class_id') if source_assignment else None,
            'matched_class_id': matched_assignment.get('class_id') if matched_assignment else None,
            'visible_to_extensions': ['year_head', 'class_coordinator'],
            'score': score,
            'threshold': active_threshold,
            'is_flagged': is_flagged,
            'created_at': datetime.now(timezone.utc),
        }
        result = await db.similarity_logs.insert_one(document)
        created = await db.similarity_logs.find_one({'_id': result.inserted_id})
        if created:
            created_items.append(created)

        if is_flagged:
            await _notify_similarity_alert(
                source_submission=source,
                source_assignment=source_assignment,
                matched_submission_id=matched_submission_id,
                score=score,
                threshold=active_threshold,
                created_by=actor_user_id,
            )

    await db.submissions.update_one(
        {'_id': parse_object_id(submission_id)},
        {'$set': {'similarity_score': round(max_score, 4)}},
    )
    return created_items


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

    if current_user.get('role') == 'teacher':
        scoped = []
        for item in items:
            if await _can_view_similarity_log(current_user, item):
                scoped.append(item)
        items = scoped

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
    if not source_assignment_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Submission has no assignment mapping')

    if current_user.get('role') == 'teacher':
        allowed = await _teacher_can_access_assignment(str(current_user['_id']), source_assignment_id)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to run similarity on this submission')

    source_assignment = await db.assignments.find_one({'_id': parse_object_id(source_assignment_id)})
    if source_assignment and source_assignment.get('plagiarism_enabled', True) is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Plagiarism detection is disabled for this assignment',
        )

    active_threshold = threshold if threshold is not None else settings.similarity_threshold
    created_items = await _run_similarity_pipeline(
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
        detail=f'Generated {len(created_items)} similarity checks',
    )

    if current_user.get('role') == 'teacher':
        scoped = []
        for item in created_items:
            if await _can_view_similarity_log(current_user, item):
                scoped.append(item)
        created_items = scoped

    return [SimilarityLogOut(**similarity_log_public(item)) for item in created_items]


@router.post('/checks/run-async/{submission_id}')
async def run_similarity_check_async(
    submission_id: str,
    background_tasks: BackgroundTasks,
    threshold: float | None = Query(default=None, ge=0, le=1),
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> dict:
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
        allowed = await _teacher_can_access_assignment(str(current_user['_id']), source_assignment_id)
        if not allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to run similarity on this submission')

    source_assignment = await db.assignments.find_one({'_id': parse_object_id(source_assignment_id)})
    if source_assignment and source_assignment.get('plagiarism_enabled', True) is False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Plagiarism detection is disabled for this assignment',
        )

    active_threshold = threshold if threshold is not None else settings.similarity_threshold

    async def _task() -> None:
        await _run_similarity_pipeline(
            submission_id=submission_id,
            source=source,
            source_assignment=source_assignment,
            active_threshold=active_threshold,
            actor_user_id=str(current_user['_id']),
        )
        await log_audit_event(
            actor_user_id=str(current_user['_id']),
            action='run_similarity_async',
            entity_type='submission',
            entity_id=submission_id,
            detail='Queued asynchronous similarity computation',
        )

    background_tasks.add_task(_task)
    return {'success': True, 'status': 'queued', 'submission_id': submission_id}
