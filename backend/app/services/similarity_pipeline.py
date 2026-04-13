from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from starlette.concurrency import run_in_threadpool

from app.core.ai_capacity import SIMILARITY_CANDIDATE_CAP
from app.core.config import settings
from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.observability import observability_state
from app.core.schema_versions import SIMILARITY_LOG_SCHEMA_VERSION, SUBMISSION_SCHEMA_VERSION
from app.services.ai_runtime import AI_SIMILARITY_ENGINE_VERSION
from app.services.notifications import create_notifications_bulk
from app.services.similarity_engine import (
    build_similarity_retrieval_artifact,
    compute_similarity_scores,
    compute_overlap_stats,
    compute_semantic_shadow_score,
    ensure_similarity_retrieval_artifact,
    extract_top_sentence_overlaps,
    extraction_quality_score,
    shortlist_similarity_candidate_ids,
    tokenize_text,
)
from app.services.similarity_rollout import should_capture_semantic_shadow


async def _notify_similarity_alert(
    *,
    recipient_user_ids: list[str],
    source_submission: dict[str, Any],
    matched_submission_id: str,
    score: float,
    threshold: float,
    created_by: str,
) -> None:
    if not recipient_user_ids:
        return

    title = "Similarity Alert"
    message = (
        f"Submission {str(source_submission.get('_id'))} matched {matched_submission_id} "
        f"with lexical similarity {round(score, 3)} (threshold {round(threshold, 3)})."
    )
    await create_notifications_bulk(
        title=title,
        message=message,
        priority="urgent",
        scope="similarity",
        target_user_ids=recipient_user_ids,
        created_by=created_by,
        track_delivery=False,
        send_email=False,
    )


async def _resolve_similarity_alert_recipients(
    source_assignment: dict[str, Any] | None,
) -> list[str]:
    recipients: set[str] = set()

    if source_assignment and source_assignment.get("created_by"):
        recipients.add(str(source_assignment.get("created_by")))

    source_class_id = source_assignment.get("class_id") if source_assignment else None
    if source_class_id:
        class_doc = await db.classes.find_one({"_id": parse_object_id(source_class_id)})
        if class_doc and class_doc.get("class_coordinator_user_id"):
            recipients.add(str(class_doc.get("class_coordinator_user_id")))

    year_heads = await db.users.find(
        {"role": "teacher", "extended_roles": {"$in": ["year_head"]}}
    ).to_list(length=1000)
    for user in year_heads:
        if user.get("_id"):
            recipients.add(str(user.get("_id")))

    return sorted(recipients)


async def _persist_similarity_retrieval_artifacts(
    artifact_updates: list[tuple[Any, dict]],
) -> None:
    for submission_obj_id, artifact in artifact_updates:
        await db.submissions.update_one(
            {"_id": submission_obj_id},
            {"$set": {"similarity_retrieval_artifact": artifact, "schema_version": SUBMISSION_SCHEMA_VERSION}},
        )


async def _load_assignment_similarity_candidates(
    *,
    source: dict[str, Any],
    source_submission_id: str,
    source_assignment_id: str,
    source_text: str,
) -> tuple[list[str], dict[str, dict[str, Any]], int]:
    total_candidates = await db.submissions.count_documents({"assignment_id": source_assignment_id})
    candidate_rows = await db.submissions.find(
        {"assignment_id": source_assignment_id},
        {
            "_id": 1,
            "similarity_retrieval_artifact": 1,
        },
    ).to_list(length=max(1, total_candidates))

    artifact_updates: list[tuple[Any, dict]] = []
    missing_artifact_ids: list[Any] = []
    artifact_by_id: dict[str, dict[str, Any]] = {}

    for item in candidate_rows:
        item_id = item.get("_id")
        if not item_id:
            continue
        submission_id = str(item_id)
        stored_artifact = item.get("similarity_retrieval_artifact")
        if stored_artifact:
            artifact_by_id[submission_id] = ensure_similarity_retrieval_artifact("", stored_artifact)
            continue
        missing_artifact_ids.append(item_id)

    if missing_artifact_ids:
        missing_rows = await db.submissions.find(
            {"_id": {"$in": missing_artifact_ids}},
            {
                "_id": 1,
                "extracted_text": 1,
                "similarity_retrieval_artifact": 1,
            },
        ).to_list(length=len(missing_artifact_ids))
        for item in missing_rows:
            item_id = item.get("_id")
            if not item_id:
                continue
            artifact = ensure_similarity_retrieval_artifact(
                item.get("extracted_text", ""),
                item.get("similarity_retrieval_artifact"),
            )
            artifact_by_id[str(item_id)] = artifact
            artifact_updates.append((item_id, artifact))

    if artifact_updates:
        await _persist_similarity_retrieval_artifacts(artifact_updates)

    source_artifact = ensure_similarity_retrieval_artifact(
        source_text,
        source.get("similarity_retrieval_artifact") if isinstance(source, dict) else None,
    )
    if source.get("similarity_retrieval_artifact") != source_artifact:
        await db.submissions.update_one(
            {"_id": parse_object_id(source_submission_id)},
            {"$set": {"similarity_retrieval_artifact": source_artifact, "schema_version": SUBMISSION_SCHEMA_VERSION}},
        )
        source["similarity_retrieval_artifact"] = source_artifact

    candidate_artifacts = [
        (submission_id, artifact)
        for submission_id, artifact in artifact_by_id.items()
        if submission_id != source_submission_id
    ]
    ranked_candidates = await run_in_threadpool(
        lambda: shortlist_similarity_candidate_ids(source_text, candidate_artifacts, limit=None),
    )
    ranked_candidate_ids = [submission_id for submission_id, _score in ranked_candidates]
    candidate_pool_ids = ranked_candidate_ids[:SIMILARITY_CANDIDATE_CAP]
    if settings.similarity_prefilter_enabled:
        filtered_candidate_ids = candidate_pool_ids[: max(1, int(settings.similarity_prefilter_top_k))]
    else:
        filtered_candidate_ids = candidate_pool_ids
    return filtered_candidate_ids, artifact_by_id, max(0, total_candidates - 1)


async def run_similarity_pipeline(
    *,
    submission_id: str,
    source: dict[str, Any],
    source_assignment: dict[str, Any] | None,
    active_threshold: float,
    actor_user_id: str,
) -> dict[str, Any]:
    started = datetime.now(timezone.utc)
    source_text = source.get("extracted_text") or ""
    source_assignment_id = source.get("assignment_id")

    filtered_candidate_ids, _artifact_by_id, raw_candidate_count = await _load_assignment_similarity_candidates(
        source=source,
        source_submission_id=submission_id,
        source_assignment_id=source_assignment_id,
        source_text=source_text,
    )
    shortlisted_candidates: list[dict[str, Any]] = []
    if filtered_candidate_ids:
        shortlisted_candidates = await db.submissions.find(
            {"_id": {"$in": [parse_object_id(item) for item in filtered_candidate_ids]}},
            {
                "_id": 1,
                "extracted_text": 1,
                "assignment_id": 1,
                "schema_version": 1,
            },
        ).to_list(length=len(filtered_candidate_ids))
    id_to_submission = {str(item.get("_id")): item for item in shortlisted_candidates if item.get("_id")}
    filtered_candidate_texts = [
        (candidate_id, id_to_submission[candidate_id].get("extracted_text", ""))
        for candidate_id in filtered_candidate_ids
        if candidate_id in id_to_submission
    ]
    scores = await run_in_threadpool(compute_similarity_scores, source_text, filtered_candidate_texts)

    created_items: list[dict[str, Any]] = []
    max_score = 0.0
    created_count = 0
    updated_count = 0
    flagged_count = 0
    threshold_value = round(float(active_threshold), 4)
    candidate_count = len(filtered_candidate_texts)
    cap_reached = raw_candidate_count > SIMILARITY_CANDIDATE_CAP
    prompt_terms = set(
        tokenize_text(f"{source_assignment.get('title', '')} {source_assignment.get('description', '')}")
        if source_assignment
        else []
    )
    source_extraction_quality = extraction_quality_score(source_text)
    similarity_alert_recipient_user_ids = await _resolve_similarity_alert_recipients(source_assignment)
    existing_logs = []
    if filtered_candidate_ids:
        existing_logs = await db.similarity_logs.find(
            {
                "source_submission_id": submission_id,
                "matched_submission_id": {"$in": filtered_candidate_ids},
                "threshold": threshold_value,
                "engine_version": AI_SIMILARITY_ENGINE_VERSION,
            }
        ).to_list(length=len(filtered_candidate_ids))
    existing_by_matched_submission_id = {
        str(item.get("matched_submission_id")): item for item in existing_logs if item.get("matched_submission_id")
    }

    for rank, (matched_submission_id, score) in enumerate(scores, start=1):
        numeric_score = round(float(score), 4)
        max_score = max(max_score, numeric_score)
        matched_submission = id_to_submission.get(matched_submission_id)
        matched_assignment_id = source_assignment_id if matched_submission else None
        matched_assignment = source_assignment

        is_flagged = numeric_score >= threshold_value
        matched_text = matched_submission.get("extracted_text", "") if matched_submission else ""
        matched_extraction_quality = extraction_quality_score(matched_text)
        overlap_stats = None
        evidence_excerpts: list[dict] = []
        semantic_shadow_score = None
        capture_semantic_shadow = should_capture_semantic_shadow(
            rank=rank,
            lexical_score=numeric_score,
            threshold=threshold_value,
            raw_candidate_count=raw_candidate_count,
        )
        if is_flagged:
            overlap_stats = compute_overlap_stats(source_text, matched_text, prompt_terms=prompt_terms)
            evidence_excerpts = extract_top_sentence_overlaps(
                source_text,
                matched_text,
                prompt_terms=prompt_terms,
                max_pairs=3,
            )
        if capture_semantic_shadow:
            semantic_shadow_score = compute_semantic_shadow_score(source_text, matched_text)
        if is_flagged:
            flagged_count += 1

        existing = existing_by_matched_submission_id.get(matched_submission_id)
        document = {
            "source_submission_id": submission_id,
            "matched_submission_id": matched_submission_id,
            "source_assignment_id": source_assignment_id,
            "matched_assignment_id": matched_assignment_id,
            "source_class_id": source_assignment.get("class_id") if source_assignment else None,
            "matched_class_id": matched_assignment.get("class_id") if matched_assignment else None,
            "visible_to_extensions": ["year_head", "class_coordinator"],
            "score": numeric_score,
            "threshold": threshold_value,
            "is_flagged": is_flagged,
            "evidence_excerpts": evidence_excerpts,
            "overlap_stats": overlap_stats,
            "extraction_quality": {
                "source": source_extraction_quality,
                "matched": matched_extraction_quality,
            },
            "semantic_shadow_score": semantic_shadow_score,
            "candidate_count": candidate_count,
            "cap_reached": cap_reached,
            "review_status": "open" if is_flagged else None,
            "review_notes": None,
            "reviewed_by_user_id": None,
            "reviewed_at": None,
            "engine_version": AI_SIMILARITY_ENGINE_VERSION,
            "updated_at": datetime.now(timezone.utc),
            "schema_version": SIMILARITY_LOG_SCHEMA_VERSION,
        }

        if existing:
            existing_review_fields = {
                "review_status": existing.get("review_status"),
                "review_notes": existing.get("review_notes"),
                "reviewed_by_user_id": existing.get("reviewed_by_user_id"),
                "reviewed_at": existing.get("reviewed_at"),
            }
            await db.similarity_logs.update_one(
                {"_id": existing["_id"]},
                {"$set": {**document, **{k: v for k, v in existing_review_fields.items() if v is not None}}},
            )
            created = await db.similarity_logs.find_one({"_id": existing["_id"]})
            updated_count += 1
        else:
            payload = {**document, "created_at": datetime.now(timezone.utc)}
            result = await db.similarity_logs.insert_one(payload)
            created = await db.similarity_logs.find_one({"_id": result.inserted_id})
            created_count += 1

        if created:
            created_items.append(created)

        should_notify = is_flagged and (not existing or not bool(existing.get("is_flagged")))
        if should_notify:
            await _notify_similarity_alert(
                recipient_user_ids=similarity_alert_recipient_user_ids,
                source_submission=source,
                matched_submission_id=matched_submission_id,
                score=numeric_score,
                threshold=threshold_value,
                created_by=actor_user_id,
            )

    await db.submissions.update_one(
        {"_id": parse_object_id(submission_id)},
        {"$set": {"similarity_score": round(max_score, 4), "schema_version": SUBMISSION_SCHEMA_VERSION}},
    )
    observability_state.record_similarity_run(
        candidate_count=raw_candidate_count,
        duration_ms=int((datetime.now(timezone.utc) - started).total_seconds() * 1000),
        flagged_count=flagged_count,
        max_score=round(max_score, 4),
    )
    return {
        "items": created_items,
        "max_score": round(max_score, 4),
        "created_count": created_count,
        "updated_count": updated_count,
        "flagged_count": flagged_count,
        "engine_version": AI_SIMILARITY_ENGINE_VERSION,
        "threshold": threshold_value,
        "candidate_count": candidate_count,
        "raw_candidate_count": raw_candidate_count,
    }
