from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from starlette.concurrency import run_in_threadpool

from app.core.database import db
from app.core.mongo import parse_object_id
from app.services.ai_runtime import AI_SIMILARITY_ENGINE_VERSION
from app.services.notifications import create_notification
from app.services.similarity_engine import compute_similarity_scores


async def _notify_similarity_alert(
    *,
    source_submission: dict[str, Any],
    source_assignment: dict[str, Any] | None,
    matched_submission_id: str,
    score: float,
    threshold: float,
    created_by: str,
) -> None:
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

    title = "Similarity Alert"
    message = (
        f"Submission {str(source_submission.get('_id'))} matched {matched_submission_id} "
        f"with score {round(score, 3)} (threshold {round(threshold, 3)})."
    )
    for user_id in recipients:
        await create_notification(
            title=title,
            message=message,
            priority="urgent",
            scope="similarity",
            target_user_id=user_id,
            created_by=created_by,
        )


async def run_similarity_pipeline(
    *,
    submission_id: str,
    source: dict[str, Any],
    source_assignment: dict[str, Any] | None,
    active_threshold: float,
    actor_user_id: str,
) -> dict[str, Any]:
    source_text = source.get("extracted_text") or ""
    source_assignment_id = source.get("assignment_id")

    candidate_cursor = db.submissions.find({"assignment_id": source_assignment_id})
    candidates = await candidate_cursor.to_list(length=1000)

    candidate_texts: list[tuple[str, str]] = []
    id_to_submission: dict[str, dict[str, Any]] = {}
    for item in candidates:
        item_id = str(item.get("_id"))
        if item_id == submission_id:
            continue
        candidate_texts.append((item_id, item.get("extracted_text", "")))
        id_to_submission[item_id] = item

    scores = await run_in_threadpool(compute_similarity_scores, source_text, candidate_texts)

    created_items: list[dict[str, Any]] = []
    max_score = 0.0
    created_count = 0
    updated_count = 0
    flagged_count = 0
    threshold_value = round(float(active_threshold), 4)

    for matched_submission_id, score in scores:
        numeric_score = round(float(score), 4)
        max_score = max(max_score, numeric_score)
        matched_submission = id_to_submission.get(matched_submission_id)
        matched_assignment_id = matched_submission.get("assignment_id") if matched_submission else None
        matched_assignment = None
        if matched_assignment_id:
            matched_assignment = await db.assignments.find_one({"_id": parse_object_id(matched_assignment_id)})

        is_flagged = numeric_score >= threshold_value
        if is_flagged:
            flagged_count += 1

        lookup_query = {
            "source_submission_id": submission_id,
            "matched_submission_id": matched_submission_id,
            "threshold": threshold_value,
            "engine_version": AI_SIMILARITY_ENGINE_VERSION,
        }
        existing = await db.similarity_logs.find_one(lookup_query)
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
            "engine_version": AI_SIMILARITY_ENGINE_VERSION,
            "updated_at": datetime.now(timezone.utc),
        }

        if existing:
            await db.similarity_logs.update_one({"_id": existing["_id"]}, {"$set": document})
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
                source_submission=source,
                source_assignment=source_assignment,
                matched_submission_id=matched_submission_id,
                score=numeric_score,
                threshold=threshold_value,
                created_by=actor_user_id,
            )

    await db.submissions.update_one(
        {"_id": parse_object_id(submission_id)},
        {"$set": {"similarity_score": round(max_score, 4)}},
    )
    return {
        "items": created_items,
        "max_score": round(max_score, 4),
        "created_count": created_count,
        "updated_count": updated_count,
        "flagged_count": flagged_count,
        "engine_version": AI_SIMILARITY_ENGINE_VERSION,
        "threshold": threshold_value,
    }
