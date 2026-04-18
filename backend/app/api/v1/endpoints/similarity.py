from datetime import datetime, timezone
from typing import Any, List

from bson import ObjectId
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
from app.services.public_ids import build_display_label, build_public_id, build_user_label
from app.services.semantic_rollout_readiness import calibration_eligible as is_calibration_eligible
from app.services.semantic_rollout_readiness import language_bucket_for_row, normalize_match_scope
from app.services.similarity_access_policy import (
    can_view_similarity_log,
    filter_similarity_logs_for_user,
    teacher_can_run_similarity_for_assignment,
)
from app.services.similarity_pipeline import run_similarity_pipeline

router = APIRouter()
_REVIEW_STATUSES = {"open", "in_progress", "fixed", "reopened"}
_REVIEW_REASON_CODES = {
    "low_evidence",
    "extraction_quality",
    "common_prompt_language",
    "allowed_collaboration",
    "multilingual_mismatch",
    "assignment_context_mismatch",
    "other",
}
_DECISION_MODES = {"flagged", "assist_only", "suppressed"}
_MATCH_SCOPES = {"same_assignment_lexical", "same_assignment_shadow", "cross_assignment_shadow"}
_LANGUAGE_BUCKETS = {"latin_only", "mixed_transliterated", "non_latin"}
_STALE_OPEN_HOURS = 48
_STALE_IN_PROGRESS_HOURS = 72


def _normalize_object_id_value(value: Any) -> str | None:
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, str) and ObjectId.is_valid(value):
        return value
    return None


def _has_low_extraction_quality(item: dict) -> bool:
    extraction_quality = item.get("extraction_quality")
    if not isinstance(extraction_quality, dict):
        return False
    values = []
    for key in ("source", "matched"):
        value = extraction_quality.get(key)
        if isinstance(value, (int, float)):
            values.append(float(value))
    return any(value < 0.5 for value in values)


def _has_semantic_drift(item: dict) -> bool:
    lexical_score = item.get("score")
    semantic_score = item.get("semantic_shadow_score")
    if not isinstance(lexical_score, (int, float)) or not isinstance(semantic_score, (int, float)):
        return False
    return float(semantic_score) - float(lexical_score) >= float(settings.semantic_shadow_calibration_paraphrase_advantage_min)


def _review_updated_timestamp(item: dict) -> datetime | None:
    value = item.get("review_updated_at") or item.get("reviewed_at") or item.get("created_at")
    return value if isinstance(value, datetime) else None


def _is_stale_review(item: dict) -> bool:
    updated_at = _review_updated_timestamp(item)
    if updated_at is None:
        return False
    review_status = str(item.get("review_status") or "").strip().lower()
    age_hours = max(0.0, (datetime.now(timezone.utc) - updated_at).total_seconds() / 3600.0)
    if review_status == "open":
        return age_hours >= _STALE_OPEN_HOURS
    if review_status == "in_progress":
        return age_hours >= _STALE_IN_PROGRESS_HOURS
    return False


def _counts_toward_calibration(item: dict) -> bool:
    return is_calibration_eligible(item)


def _matches_similarity_search(item: dict, search: str) -> bool:
    normalized = search.strip().lower()
    if not normalized:
        return True
    haystack = " ".join(
        str(value or "")
        for value in (
            item.get("source_submission_id"),
            item.get("matched_submission_id"),
            item.get("source_submission_public_id"),
            item.get("matched_submission_public_id"),
            item.get("source_assignment_id"),
            item.get("matched_assignment_id"),
            item.get("source_assignment_label"),
            item.get("matched_assignment_label"),
            ((item.get("source_submission_summary") or {}).get("student_label") if isinstance(item.get("source_submission_summary"), dict) else None),
            ((item.get("matched_submission_summary") or {}).get("student_label") if isinstance(item.get("matched_submission_summary"), dict) else None),
            ((item.get("source_submission_summary") or {}).get("file_name") if isinstance(item.get("source_submission_summary"), dict) else None),
            ((item.get("matched_submission_summary") or {}).get("file_name") if isinstance(item.get("matched_submission_summary"), dict) else None),
            item.get("review_notes"),
        )
    ).lower()
    return normalized in haystack


def _derive_submission_public_id(
    submission_doc: dict | None,
    fallback_submission_id: str | None,
) -> str | None:
    if isinstance(submission_doc, dict):
        public_id = submission_doc.get("public_id") or build_public_id("submission", submission_doc)
        if public_id:
            return str(public_id)
    if isinstance(fallback_submission_id, str) and fallback_submission_id.strip():
        if ObjectId.is_valid(fallback_submission_id):
            derived = build_public_id("submission", {"_id": fallback_submission_id})
            if derived:
                return str(derived)
        return fallback_submission_id
    return None


def _derive_assignment_label(
    assignment_doc: dict | None,
    fallback_assignment_id: str | None,
) -> str | None:
    if isinstance(assignment_doc, dict):
        public_id = assignment_doc.get("public_id") or build_public_id("assignment", assignment_doc)
        label = build_display_label(
            "assignment",
            assignment_doc,
            public_id=public_id,
            display_name=assignment_doc.get("title"),
        )
        if label:
            return str(label)
    if isinstance(fallback_assignment_id, str) and fallback_assignment_id.strip():
        if ObjectId.is_valid(fallback_assignment_id):
            derived_public_id = build_public_id("assignment", {"_id": fallback_assignment_id})
            if derived_public_id:
                return str(derived_public_id)
        return fallback_assignment_id
    return None


def _build_similarity_text_preview(text: str | None, *, max_length: int = 240) -> str | None:
    value = " ".join(str(text or "").split())
    if not value:
        return None
    if len(value) <= max_length:
        return value
    return f"{value[: max_length - 3].rstrip()}..."


def _build_submission_summary(
    submission_doc: dict | None,
    *,
    submission_public_id: str | None,
    assignment_label: str | None,
    student_doc: dict | None,
) -> dict[str, Any] | None:
    if not isinstance(submission_doc, dict) and not submission_public_id:
        return None
    original_filename = submission_doc.get("original_filename") if isinstance(submission_doc, dict) else None
    submission_label = None
    if isinstance(submission_doc, dict):
        submission_label = build_display_label(
            "submission",
            submission_doc,
            public_id=submission_public_id,
            display_name=original_filename,
        )
    if not submission_label:
        submission_label = submission_public_id
    return {
        "submission_public_id": submission_public_id,
        "submission_label": submission_label,
        "student_label": build_user_label(
            submission_doc.get("student_user_id") if isinstance(submission_doc, dict) else None,
            full_name=(student_doc or {}).get("full_name"),
            email=(student_doc or {}).get("email"),
        ) if isinstance(submission_doc, dict) or student_doc else None,
        "assignment_label": assignment_label,
        "file_name": original_filename or "-",
        "uploaded_at": submission_doc.get("created_at") if isinstance(submission_doc, dict) else None,
        "text_preview": _build_similarity_text_preview(
            submission_doc.get("extracted_text") if isinstance(submission_doc, dict) else None
        ),
        "text_length": len(str(submission_doc.get("extracted_text") or "")) if isinstance(submission_doc, dict) else None,
    }


async def _attach_submission_public_ids(items: list[dict]) -> list[dict]:
    if not items:
        return items

    submission_ids = {
        value
        for item in items
        for value in (
            _normalize_object_id_value(item.get("source_submission_id")),
            _normalize_object_id_value(item.get("matched_submission_id")),
        )
        if value
    }
    submission_docs_by_id: dict[str, dict] = {}
    if submission_ids:
        submission_docs = await db.submissions.find(
            {"_id": {"$in": [ObjectId(value) for value in submission_ids]}},
            {
                "_id": 1,
                "public_id": 1,
                "student_user_id": 1,
            },
        ).to_list(length=len(submission_ids))
        submission_docs_by_id = {
            str(item.get("_id")): item
            for item in submission_docs
            if item.get("_id")
        }

    enriched: list[dict] = []
    for item in items:
        source_submission_id = item.get("source_submission_id")
        matched_submission_id = item.get("matched_submission_id")
        source_submission_id_key = _normalize_object_id_value(source_submission_id)
        matched_submission_id_key = _normalize_object_id_value(matched_submission_id)
        enriched.append(
            {
                **item,
                "source_submission_public_id": _derive_submission_public_id(
                    submission_docs_by_id.get(source_submission_id_key),
                    str(source_submission_id) if source_submission_id is not None else None,
                ),
                "matched_submission_public_id": _derive_submission_public_id(
                    submission_docs_by_id.get(matched_submission_id_key),
                    str(matched_submission_id) if matched_submission_id is not None else None,
                ),
            }
        )
    return enriched


async def _attach_assignment_labels(items: list[dict]) -> list[dict]:
    if not items:
        return items

    assignment_ids = {
        value
        for item in items
        for value in (
            _normalize_object_id_value(item.get("source_assignment_id")),
            _normalize_object_id_value(item.get("matched_assignment_id")),
        )
        if value
    }
    assignment_docs_by_id: dict[str, dict] = {}
    if assignment_ids:
        assignment_docs = await db.assignments.find(
            {"_id": {"$in": [ObjectId(value) for value in assignment_ids]}},
            {
                "_id": 1,
                "title": 1,
                "public_id": 1,
            },
        ).to_list(length=len(assignment_ids))
        assignment_docs_by_id = {
            str(item.get("_id")): item
            for item in assignment_docs
            if item.get("_id")
        }

    enriched: list[dict] = []
    for item in items:
        source_assignment_id = item.get("source_assignment_id")
        matched_assignment_id = item.get("matched_assignment_id")
        source_assignment_id_key = _normalize_object_id_value(source_assignment_id)
        matched_assignment_id_key = _normalize_object_id_value(matched_assignment_id)
        enriched.append(
            {
                **item,
                "source_assignment_label": _derive_assignment_label(
                    assignment_docs_by_id.get(source_assignment_id_key),
                    str(source_assignment_id) if source_assignment_id is not None else None,
                ),
                "matched_assignment_label": _derive_assignment_label(
                    assignment_docs_by_id.get(matched_assignment_id_key),
                    str(matched_assignment_id) if matched_assignment_id is not None else None,
                ),
            }
        )
    return enriched


async def _attach_submission_summaries(items: list[dict]) -> list[dict]:
    if not items:
        return items

    submission_ids = {
        value
        for item in items
        for value in (
            _normalize_object_id_value(item.get("source_submission_id")),
            _normalize_object_id_value(item.get("matched_submission_id")),
        )
        if value
    }
    if not submission_ids:
        return items

    submission_docs = await db.submissions.find(
        {"_id": {"$in": [ObjectId(value) for value in submission_ids]}},
        {
            "_id": 1,
            "public_id": 1,
            "original_filename": 1,
            "student_user_id": 1,
            "assignment_id": 1,
            "created_at": 1,
            "extracted_text": 1,
        },
    ).to_list(length=len(submission_ids))
    submission_docs_by_id = {
        str(item.get("_id")): item
        for item in submission_docs
        if item.get("_id")
    }

    assignment_ids = {
        value
        for item in submission_docs
        for value in (_normalize_object_id_value(item.get("assignment_id")),)
        if value
    }
    assignment_docs_by_id: dict[str, dict] = {}
    if assignment_ids:
        assignment_docs = await db.assignments.find(
            {"_id": {"$in": [ObjectId(value) for value in assignment_ids]}},
            {
                "_id": 1,
                "title": 1,
                "public_id": 1,
            },
        ).to_list(length=len(assignment_ids))
        assignment_docs_by_id = {
            str(item.get("_id")): item
            for item in assignment_docs
            if item.get("_id")
        }

    student_user_ids = {
        value
        for item in submission_docs
        for value in (_normalize_object_id_value(item.get("student_user_id")),)
        if value
    }
    student_docs_by_id: dict[str, dict] = {}
    if student_user_ids:
        student_docs = await db.users.find(
            {"_id": {"$in": [ObjectId(value) for value in student_user_ids]}},
            {
                "_id": 1,
                "full_name": 1,
                "email": 1,
            },
        ).to_list(length=len(student_user_ids))
        student_docs_by_id = {
            str(item.get("_id")): item
            for item in student_docs
            if item.get("_id")
        }

    enriched: list[dict] = []
    for item in items:
        source_submission_id = item.get("source_submission_id")
        matched_submission_id = item.get("matched_submission_id")
        source_submission_doc = submission_docs_by_id.get(_normalize_object_id_value(source_submission_id))
        matched_submission_doc = submission_docs_by_id.get(_normalize_object_id_value(matched_submission_id))
        source_assignment_label = item.get("source_assignment_label") or _derive_assignment_label(
            assignment_docs_by_id.get(_normalize_object_id_value(source_submission_doc.get("assignment_id"))) if isinstance(source_submission_doc, dict) else None,
            str(source_submission_doc.get("assignment_id")) if isinstance(source_submission_doc, dict) and source_submission_doc.get("assignment_id") is not None else None,
        )
        matched_assignment_label = item.get("matched_assignment_label") or _derive_assignment_label(
            assignment_docs_by_id.get(_normalize_object_id_value(matched_submission_doc.get("assignment_id"))) if isinstance(matched_submission_doc, dict) else None,
            str(matched_submission_doc.get("assignment_id")) if isinstance(matched_submission_doc, dict) and matched_submission_doc.get("assignment_id") is not None else None,
        )
        source_submission_public_id = item.get("source_submission_public_id") or _derive_submission_public_id(
            source_submission_doc,
            str(source_submission_id) if source_submission_id is not None else None,
        )
        matched_submission_public_id = item.get("matched_submission_public_id") or _derive_submission_public_id(
            matched_submission_doc,
            str(matched_submission_id) if matched_submission_id is not None else None,
        )
        enriched.append(
            {
                **item,
                "source_submission_summary": _build_submission_summary(
                    source_submission_doc,
                    submission_public_id=source_submission_public_id,
                    assignment_label=source_assignment_label,
                    student_doc=student_docs_by_id.get(_normalize_object_id_value(source_submission_doc.get("student_user_id"))) if isinstance(source_submission_doc, dict) else None,
                ),
                "matched_submission_summary": _build_submission_summary(
                    matched_submission_doc,
                    submission_public_id=matched_submission_public_id,
                    assignment_label=matched_assignment_label,
                    student_doc=student_docs_by_id.get(_normalize_object_id_value(matched_submission_doc.get("student_user_id"))) if isinstance(matched_submission_doc, dict) else None,
                ),
            }
        )
    return enriched


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
    review_status: str | None = Query(default=None),
    decision_mode: str | None = Query(default=None),
    awaiting_final_decision: bool | None = Query(default=None),
    stale_review: bool | None = Query(default=None),
    counts_toward_calibration: bool | None = Query(default=None),
    calibration_eligible: bool | None = Query(default=None),
    semantic_review_candidate: bool | None = Query(default=None),
    match_scope: str | None = Query(default=None),
    language_bucket: str | None = Query(default=None),
    semantic_drift_present: bool | None = Query(default=None),
    cap_reached: bool | None = Query(default=None),
    low_extraction_quality: bool | None = Query(default=None),
    min_score: float | None = Query(default=None, ge=0, le=1),
    max_score: float | None = Query(default=None, ge=0, le=1),
    search: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[SimilarityLogOut]:
    query = {}
    if source_submission_id:
        query['source_submission_id'] = source_submission_id
    if is_flagged is not None:
        query['is_flagged'] = is_flagged
    if review_status:
        normalized_review_status = str(review_status).strip().lower()
        if normalized_review_status not in _REVIEW_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid review_status filter')
        query['review_status'] = normalized_review_status
    if decision_mode:
        normalized_decision_mode = str(decision_mode).strip().lower()
        if normalized_decision_mode not in _DECISION_MODES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid decision_mode filter')
        query['decision_mode'] = normalized_decision_mode
    normalized_match_scope = None
    if match_scope:
        normalized_match_scope = str(match_scope).strip().lower()
        if normalized_match_scope not in _MATCH_SCOPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid match_scope filter')
    normalized_language_bucket = None
    if language_bucket:
        normalized_language_bucket = str(language_bucket).strip().lower()
        if normalized_language_bucket not in _LANGUAGE_BUCKETS:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid language_bucket filter')
    if cap_reached is not None:
        query['cap_reached'] = cap_reached

    candidate_limit = max(limit + skip, 200)
    items = await db.similarity_logs.find(query).sort("created_at", -1).limit(candidate_limit).to_list(length=candidate_limit)

    items = await filter_similarity_logs_for_user(current_user, items, database=db)
    items = await _attach_submission_public_ids(items)
    items = await _attach_assignment_labels(items)
    items = await _attach_submission_summaries(items)
    filtered_items = []
    for item in items:
        numeric_score = item.get("score")
        if min_score is not None and (not isinstance(numeric_score, (int, float)) or float(numeric_score) < float(min_score)):
            continue
        if max_score is not None and (not isinstance(numeric_score, (int, float)) or float(numeric_score) > float(max_score)):
            continue
        if awaiting_final_decision is not None and (
            str(item.get("review_status") or "").strip().lower() in {"open", "in_progress"}
        ) is not awaiting_final_decision:
            continue
        if stale_review is not None and _is_stale_review(item) is not stale_review:
            continue
        if counts_toward_calibration is not None and _counts_toward_calibration(item) is not counts_toward_calibration:
            continue
        if calibration_eligible is not None and is_calibration_eligible(item) is not calibration_eligible:
            continue
        if semantic_review_candidate is not None and bool(item.get("semantic_review_candidate")) is not semantic_review_candidate:
            continue
        if normalized_match_scope is not None and normalize_match_scope(item) != normalized_match_scope:
            continue
        if normalized_language_bucket is not None and language_bucket_for_row(item) != normalized_language_bucket:
            continue
        if semantic_drift_present is not None and _has_semantic_drift(item) is not semantic_drift_present:
            continue
        if low_extraction_quality is not None and _has_low_extraction_quality(item) is not low_extraction_quality:
            continue
        if search and not _matches_similarity_search(item, search):
            continue
        filtered_items.append(item)

    sliced_items = filtered_items[skip: skip + limit]
    return [SimilarityLogOut(**similarity_log_public(item)) for item in sliced_items]


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
    item = (await _attach_submission_public_ids([item]))[0]
    item = (await _attach_assignment_labels([item]))[0]
    item = (await _attach_submission_summaries([item]))[0]
    payload = similarity_log_public(item, include_evidence=True)
    related_shadow_rows = await db.similarity_logs.find(
        {
            "source_submission_id": item.get("source_submission_id"),
            "match_scope": "cross_assignment_shadow",
        }
    ).sort("semantic_shadow_score", -1).limit(5).to_list(length=5)
    related_shadow_rows = await filter_similarity_logs_for_user(current_user, related_shadow_rows, database=db)
    related_shadow_rows = await _attach_submission_public_ids(related_shadow_rows)
    related_shadow_rows = await _attach_assignment_labels(related_shadow_rows)
    related_shadow_rows = await _attach_submission_summaries(related_shadow_rows)
    payload["related_shadow_candidates"] = [
        similarity_log_public(row, include_evidence=True)
        for row in related_shadow_rows
        if str(row.get("_id")) != log_id
    ]
    return SimilarityLogOut(**payload)


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
    review_reason_code = payload.get("review_reason_code")
    review_notes = payload.get("review_notes")
    update_data = {}
    normalized_status = None
    now = datetime.now(timezone.utc)
    if review_status is not None:
        status_value = str(review_status).strip().lower()
        if status_value not in _REVIEW_STATUSES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid review_status value')
        update_data["review_status"] = status_value
        normalized_status = status_value
    else:
        normalized_status = str(item.get("review_status") or "open").strip().lower()
    if review_reason_code is not None:
        if review_reason_code in {"", None}:
            update_data["review_reason_code"] = None
        else:
            reason_value = str(review_reason_code).strip().lower()
            if reason_value not in _REVIEW_REASON_CODES:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid review_reason_code value')
            update_data["review_reason_code"] = reason_value
    if review_notes is not None:
        update_data["review_notes"] = str(review_notes).strip()[:2000]

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No review fields provided')

    if normalized_status != "reopened" and "review_reason_code" not in update_data:
        update_data["review_reason_code"] = None
    if normalized_status != "reopened" and review_reason_code is None and item.get("review_reason_code"):
        update_data["review_reason_code"] = None

    update_data["reviewed_by_user_id"] = str(current_user.get("_id"))
    update_data["reviewed_at"] = now
    update_data["review_updated_at"] = now
    if normalized_status in {"fixed", "reopened"}:
        update_data["review_finalized_at"] = now
        update_data["review_finalized_by_user_id"] = str(current_user.get("_id"))
    else:
        update_data["review_finalized_at"] = None
        update_data["review_finalized_by_user_id"] = None

    await db.similarity_logs.update_one({"_id": parse_object_id(log_id)}, {"$set": update_data})
    updated = await db.similarity_logs.find_one({"_id": parse_object_id(log_id)})
    updated = (await _attach_submission_public_ids([updated]))[0]
    updated = (await _attach_assignment_labels([updated]))[0]
    updated = (await _attach_submission_summaries([updated]))[0]
    payload = similarity_log_public(updated, include_evidence=True)
    payload["related_shadow_candidates"] = []
    return SimilarityLogOut(**payload)


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
    created_items = await _attach_submission_public_ids(created_items)
    created_items = await _attach_assignment_labels(created_items)
    created_items = await _attach_submission_summaries(created_items)

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
