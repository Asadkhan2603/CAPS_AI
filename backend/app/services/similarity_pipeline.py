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
from app.services.public_ids import build_public_id
from app.services.ai_runtime import AI_SIMILARITY_ENGINE_VERSION
from app.services.notifications import create_notifications_bulk
from app.services.similarity_engine import (
    build_similarity_risk_signals,
    build_similarity_retrieval_artifact,
    classify_similarity_decision,
    compute_similarity_scores,
    compute_overlap_stats,
    compute_semantic_shadow_score,
    ensure_similarity_retrieval_artifact,
    extract_top_sentence_overlaps,
    extraction_quality_score,
    shortlist_similarity_candidate_ids,
    tokenize_text,
)
from app.services.similarity_rollout import (
    detect_language_profile,
    resolve_tokenizer_mode_for_texts,
    should_capture_semantic_shadow,
)


async def _notify_similarity_alert(
    *,
    recipient_user_ids: list[str],
    source_submission: dict[str, Any],
    matched_submission: dict[str, Any] | None,
    score: float,
    threshold: float,
    created_by: str,
) -> None:
    if not recipient_user_ids:
        return

    source_submission_label = _submission_alert_label(source_submission)
    matched_submission_label = _submission_alert_label(matched_submission)
    title = "Similarity Alert"
    message = (
        f"Submission {source_submission_label} matched {matched_submission_label} "
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


def _submission_alert_label(submission: dict[str, Any] | None) -> str:
    if not isinstance(submission, dict):
        return "submission record"
    public_id = submission.get("public_id") or build_public_id("submission", submission)
    if public_id:
        return str(public_id)
    return "submission record"


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


async def _load_cross_assignment_similarity_candidates(
    *,
    source: dict[str, Any],
    source_submission_id: str,
    source_assignment_id: str,
    source_text: str,
) -> tuple[list[str], int]:
    if not settings.similarity_cross_assignment_enabled:
        return [], 0

    query = {
        "_id": {"$ne": parse_object_id(source_submission_id)},
        "assignment_id": {"$ne": source_assignment_id},
    }
    total_candidates = await db.submissions.count_documents(query)
    if total_candidates <= 0:
        return [], 0

    candidate_rows = await db.submissions.find(
        query,
        {
            "_id": 1,
            "similarity_retrieval_artifact": 1,
            "extracted_text": 1,
        },
    ).to_list(length=max(1, total_candidates))
    candidate_artifacts = [
        (
            str(item["_id"]),
            ensure_similarity_retrieval_artifact(
                item.get("extracted_text", ""),
                item.get("similarity_retrieval_artifact"),
            ),
        )
        for item in candidate_rows
        if item.get("_id")
    ]
    cross_limit = max(3, min(int(settings.semantic_shadow_capture_top_n), 12))
    ranked_candidates = await run_in_threadpool(
        lambda: shortlist_similarity_candidate_ids(source_text, candidate_artifacts, limit=cross_limit),
    )
    ranked_candidate_ids = [submission_id for submission_id, _score in ranked_candidates]
    return ranked_candidate_ids, max(0, total_candidates)


def _review_status_for_similarity_case(*, decision_mode: str, suppression_reason: str | None, semantic_review_candidate: bool) -> str | None:
    if decision_mode in {"flagged", "assist_only"}:
        return "open"
    if suppression_reason in {
        "low_extraction_hold",
        "short_generic_overlap",
        "insufficient_non_prompt_overlap",
    }:
        return "open"
    if semantic_review_candidate:
        return "open"
    return None


def _build_language_profile(source_text: str, matched_text: str) -> dict[str, Any]:
    source_profile = detect_language_profile(source_text)
    matched_profile = detect_language_profile(matched_text)
    return {
        "source": source_profile,
        "matched": matched_profile,
        "mixed_or_non_latin": bool(
            source_profile.get("mixed_script")
            or source_profile.get("mixed_language_hint")
            or matched_profile.get("mixed_script")
            or matched_profile.get("mixed_language_hint")
            or source_profile.get("primary_script") != "latin"
            or matched_profile.get("primary_script") != "latin"
        ),
    }


def _build_submission_extraction_diagnostics(submission: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(submission, dict):
        return None
    return {
        "ocr_attempted": submission.get("ocr_attempted"),
        "ocr_provider": submission.get("ocr_provider"),
        "ocr_chars_added": submission.get("ocr_chars_added"),
        "page_count": submission.get("page_count"),
        "extraction_confidence": submission.get("extraction_confidence"),
        "low_text_reason": submission.get("low_text_reason"),
        "ocr_result_state": submission.get("ocr_result_state"),
        "ocr_retry_count": submission.get("ocr_retry_count"),
        "ocr_timeout_seconds": submission.get("ocr_timeout_seconds"),
        "ocr_error": submission.get("ocr_error"),
        "ocr_retry_guidance": submission.get("ocr_retry_guidance"),
    }


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
                "ocr_attempted": 1,
                "ocr_provider": 1,
                "ocr_chars_added": 1,
                "page_count": 1,
                "extraction_confidence": 1,
                "low_text_reason": 1,
                "ocr_result_state": 1,
                "ocr_retry_count": 1,
                "ocr_timeout_seconds": 1,
                "ocr_error": 1,
                "ocr_retry_guidance": 1,
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
    source_language_profile = detect_language_profile(source_text)
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

        matched_text = matched_submission.get("extracted_text", "") if matched_submission else ""
        matched_extraction_quality = extraction_quality_score(matched_text)
        tokenization_mode_applied = resolve_tokenizer_mode_for_texts([source_text, matched_text])
        overlap_stats = compute_overlap_stats(
            source_text,
            matched_text,
            prompt_terms=prompt_terms,
            tokenizer_mode=tokenization_mode_applied,
        )
        evidence_excerpts = extract_top_sentence_overlaps(
            source_text,
            matched_text,
            prompt_terms=prompt_terms,
            max_pairs=3,
            tokenizer_mode=tokenization_mode_applied,
        )
        semantic_shadow_score = None
        capture_semantic_shadow = should_capture_semantic_shadow(
            rank=rank,
            lexical_score=numeric_score,
            threshold=threshold_value,
            raw_candidate_count=raw_candidate_count,
        )
        if capture_semantic_shadow:
            semantic_shadow_score = compute_semantic_shadow_score(source_text, matched_text)
        language_profile = _build_language_profile(source_text, matched_text)
        extraction_diagnostics = {
            "source": _build_submission_extraction_diagnostics(source),
            "matched": _build_submission_extraction_diagnostics(matched_submission),
        }
        risk_signals = build_similarity_risk_signals(
            source_text,
            matched_text,
            prompt_terms=prompt_terms,
            overlap_stats=overlap_stats,
            evidence_excerpts=evidence_excerpts,
            extraction_diagnostics=extraction_diagnostics,
            language_profile=language_profile,
            tokenizer_mode=tokenization_mode_applied,
        )
        decision = classify_similarity_decision(
            lexical_score=numeric_score,
            threshold=threshold_value,
            semantic_shadow_score=semantic_shadow_score,
            overlap_stats=overlap_stats,
            risk_signals=risk_signals,
            language_profile=language_profile,
        )
        decision_mode = str(decision.get("decision_mode") or "suppressed")
        suppression_reason = decision.get("suppression_reason")
        semantic_review_candidate = bool(decision.get("semantic_review_candidate"))
        if decision_mode == "suppressed" and suppression_reason == "below_threshold" and not semantic_review_candidate:
            continue
        is_flagged = decision_mode == "flagged"
        if is_flagged:
            flagged_count += 1
        match_scope = "same_assignment_lexical" if is_flagged else "same_assignment_shadow"
        review_status = _review_status_for_similarity_case(
            decision_mode=decision_mode,
            suppression_reason=suppression_reason,
            semantic_review_candidate=semantic_review_candidate,
        )

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
            "extraction_diagnostics": extraction_diagnostics,
            "semantic_shadow_score": semantic_shadow_score,
            "decision_mode": decision_mode,
            "suppression_reason": suppression_reason,
            "risk_signals": risk_signals,
            "tokenization_mode_applied": tokenization_mode_applied,
            "semantic_review_candidate": semantic_review_candidate,
            "match_scope": match_scope,
            "language_profile": language_profile,
            "candidate_count": candidate_count,
            "cap_reached": cap_reached,
            "review_status": review_status,
            "review_notes": None,
            "reviewed_by_user_id": None,
            "reviewed_at": None,
            "review_updated_at": None,
            "review_finalized_at": None,
            "review_finalized_by_user_id": None,
            "engine_version": AI_SIMILARITY_ENGINE_VERSION,
            "updated_at": datetime.now(timezone.utc),
            "schema_version": SIMILARITY_LOG_SCHEMA_VERSION,
        }

        if existing:
            existing_review_fields = {
                "review_status": existing.get("review_status"),
                "review_reason_code": existing.get("review_reason_code"),
                "review_notes": existing.get("review_notes"),
                "reviewed_by_user_id": existing.get("reviewed_by_user_id"),
                "reviewed_at": existing.get("reviewed_at"),
                "review_updated_at": existing.get("review_updated_at"),
                "review_finalized_at": existing.get("review_finalized_at"),
                "review_finalized_by_user_id": existing.get("review_finalized_by_user_id"),
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
                matched_submission=matched_submission,
                score=numeric_score,
                threshold=threshold_value,
                created_by=actor_user_id,
            )

    cross_assignment_candidate_ids, cross_assignment_candidate_count = await _load_cross_assignment_similarity_candidates(
        source=source,
        source_submission_id=submission_id,
        source_assignment_id=source_assignment_id,
        source_text=source_text,
    )
    if cross_assignment_candidate_ids:
        cross_assignment_candidates = await db.submissions.find(
            {"_id": {"$in": [parse_object_id(item) for item in cross_assignment_candidate_ids]}},
            {
                "_id": 1,
                "assignment_id": 1,
                "extracted_text": 1,
                "ocr_attempted": 1,
                "ocr_provider": 1,
                "ocr_chars_added": 1,
                "page_count": 1,
                "extraction_confidence": 1,
                "low_text_reason": 1,
                "ocr_result_state": 1,
                "ocr_retry_count": 1,
                "ocr_timeout_seconds": 1,
                "ocr_error": 1,
                "ocr_retry_guidance": 1,
            },
        ).to_list(length=len(cross_assignment_candidate_ids))
        cross_by_id = {
            str(item.get("_id")): item
            for item in cross_assignment_candidates
            if item.get("_id")
        }
        cross_texts = [
            (candidate_id, cross_by_id[candidate_id].get("extracted_text", ""))
            for candidate_id in cross_assignment_candidate_ids
            if candidate_id in cross_by_id
        ]
        cross_scores = await run_in_threadpool(compute_similarity_scores, source_text, cross_texts)
        existing_cross_logs = await db.similarity_logs.find(
            {
                "source_submission_id": submission_id,
                "matched_submission_id": {"$in": [candidate_id for candidate_id, _score in cross_scores]},
                "match_scope": "cross_assignment_shadow",
                "engine_version": AI_SIMILARITY_ENGINE_VERSION,
            }
        ).to_list(length=len(cross_scores))
        existing_cross_by_match = {
            str(item.get("matched_submission_id")): item
            for item in existing_cross_logs
            if item.get("matched_submission_id")
        }
        for rank, (matched_submission_id, lexical_score) in enumerate(cross_scores, start=1):
            matched_submission = cross_by_id.get(matched_submission_id)
            if not matched_submission:
                continue
            matched_text = matched_submission.get("extracted_text", "")
            tokenization_mode_applied = resolve_tokenizer_mode_for_texts([source_text, matched_text])
            semantic_shadow_score = compute_semantic_shadow_score(source_text, matched_text)
            if semantic_shadow_score is None:
                continue
            numeric_lexical = round(float(lexical_score), 4)
            matched_extraction_quality = extraction_quality_score(matched_text)
            prompt_terms = set(
                tokenize_text(f"{source_assignment.get('title', '')} {source_assignment.get('description', '')}")
                if source_assignment
                else []
            )
            evidence_excerpts = extract_top_sentence_overlaps(
                source_text,
                matched_text,
                prompt_terms=prompt_terms,
                max_pairs=2,
                tokenizer_mode=tokenization_mode_applied,
            )
            overlap_stats = compute_overlap_stats(
                source_text,
                matched_text,
                prompt_terms=prompt_terms,
                tokenizer_mode=tokenization_mode_applied,
            )
            language_profile = _build_language_profile(source_text, matched_text)
            extraction_diagnostics = {
                "source": _build_submission_extraction_diagnostics(source),
                "matched": _build_submission_extraction_diagnostics(matched_submission),
            }
            risk_signals = build_similarity_risk_signals(
                source_text,
                matched_text,
                prompt_terms=prompt_terms,
                overlap_stats=overlap_stats,
                evidence_excerpts=evidence_excerpts,
                extraction_diagnostics=extraction_diagnostics,
                language_profile=language_profile,
                tokenizer_mode=tokenization_mode_applied,
            )
            document = {
                "source_submission_id": submission_id,
                "matched_submission_id": matched_submission_id,
                "source_assignment_id": source_assignment_id,
                "matched_assignment_id": matched_submission.get("assignment_id"),
                "source_class_id": source_assignment.get("class_id") if source_assignment else None,
                "matched_class_id": None,
                "visible_to_extensions": ["year_head", "class_coordinator"],
                "score": numeric_lexical,
                "threshold": threshold_value,
                "is_flagged": False,
                "evidence_excerpts": evidence_excerpts,
                "overlap_stats": overlap_stats,
                "extraction_quality": {
                    "source": source_extraction_quality,
                    "matched": matched_extraction_quality,
                },
                "extraction_diagnostics": extraction_diagnostics,
                "semantic_shadow_score": semantic_shadow_score,
                "decision_mode": "assist_only",
                "suppression_reason": "cross_assignment_shadow_only",
                "risk_signals": risk_signals,
                "tokenization_mode_applied": tokenization_mode_applied,
                "semantic_review_candidate": True,
                "match_scope": "cross_assignment_shadow",
                "language_profile": language_profile,
                "candidate_count": len(cross_texts),
                "cap_reached": cross_assignment_candidate_count > len(cross_assignment_candidate_ids),
                "review_status": "open",
                "review_notes": None,
                "reviewed_by_user_id": None,
                "reviewed_at": None,
                "review_updated_at": None,
                "review_finalized_at": None,
                "review_finalized_by_user_id": None,
                "engine_version": AI_SIMILARITY_ENGINE_VERSION,
                "updated_at": datetime.now(timezone.utc),
                "schema_version": SIMILARITY_LOG_SCHEMA_VERSION,
            }
            existing = existing_cross_by_match.get(matched_submission_id)
            if existing:
                await db.similarity_logs.update_one(
                    {"_id": existing["_id"]},
                    {"$set": document},
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
