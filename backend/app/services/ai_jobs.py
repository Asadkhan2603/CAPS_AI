from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone
from typing import Any

from pymongo import ReturnDocument

from app.core.database import db
from app.core.mongo import parse_object_id
from app.services.ai_runtime import get_ai_runtime_settings
from app.services.audit import log_audit_event
from app.services.similarity_pipeline import run_similarity_pipeline
from app.services.submission_ai import evaluate_submission_and_save

AI_JOB_TYPE_BULK_SUBMISSION = "bulk_submission_ai"
AI_JOB_TYPE_SIMILARITY = "similarity_check"

AI_JOB_STATUS_QUEUED = "queued"
AI_JOB_STATUS_RUNNING = "running"
AI_JOB_STATUS_COMPLETED = "completed"
AI_JOB_STATUS_FAILED = "failed"

_worker_id = (os.getenv("HOSTNAME") or "").strip() or f"ai-jobs-{os.getpid()}"


def serialize_ai_job(document: dict[str, Any]) -> dict[str, Any]:
    def _serialize_dt(value: Any) -> str | None:
        if not isinstance(value, datetime):
            return None
        if value.tzinfo:
            return value.isoformat()
        return value.replace(tzinfo=timezone.utc).isoformat()

    return {
        "id": str(document.get("_id")),
        "job_type": document.get("job_type"),
        "status": document.get("status"),
        "requested_by_user_id": document.get("requested_by_user_id"),
        "requested_by_role": document.get("requested_by_role"),
        "idempotency_key": document.get("idempotency_key"),
        "params": document.get("params") or {},
        "progress": document.get("progress") or {},
        "summary": document.get("summary") or {},
        "error": document.get("error"),
        "requested_at": _serialize_dt(document.get("requested_at")),
        "started_at": _serialize_dt(document.get("started_at")),
        "completed_at": _serialize_dt(document.get("completed_at")),
        "worker_id": document.get("worker_id"),
    }


async def queue_ai_job(
    *,
    job_type: str,
    requested_by_user_id: str,
    requested_by_role: str,
    params: dict[str, Any],
    idempotency_key: str,
) -> tuple[dict[str, Any], bool]:
    existing = await db.ai_jobs.find_one(
        {
            "job_type": job_type,
            "idempotency_key": idempotency_key,
            "status": {"$in": [AI_JOB_STATUS_QUEUED, AI_JOB_STATUS_RUNNING]},
        }
    )
    if existing:
        return existing, False

    now = datetime.now(timezone.utc)
    document = {
        "job_type": job_type,
        "status": AI_JOB_STATUS_QUEUED,
        "requested_by_user_id": requested_by_user_id,
        "requested_by_role": requested_by_role,
        "idempotency_key": idempotency_key,
        "params": params,
        "progress": {
            "total": len(params.get("submission_ids") or []) or (1 if params.get("submission_id") else 0),
            "completed": 0,
            "failed": 0,
            "skipped": 0,
        },
        "summary": {},
        "error": None,
        "requested_at": now,
        "started_at": None,
        "completed_at": None,
        "worker_id": None,
    }
    result = await db.ai_jobs.insert_one(document)
    created = await db.ai_jobs.find_one({"_id": result.inserted_id})
    return created, True


async def get_ai_job(job_id: str) -> dict[str, Any] | None:
    return await db.ai_jobs.find_one({"_id": parse_object_id(job_id)})


def schedule_ai_job_processing(*, max_jobs: int = 1) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        return
    loop.create_task(process_ai_jobs_once(max_jobs=max_jobs))


async def process_ai_jobs_once(*, max_jobs: int = 2) -> int:
    processed = 0
    for _ in range(max(1, max_jobs)):
        job = await db.ai_jobs.find_one_and_update(
            {"status": AI_JOB_STATUS_QUEUED},
            {
                "$set": {
                    "status": AI_JOB_STATUS_RUNNING,
                    "started_at": datetime.now(timezone.utc),
                    "worker_id": _worker_id,
                    "error": None,
                }
            },
            sort=[("requested_at", 1)],
            return_document=ReturnDocument.AFTER,
        )
        if not job:
            break
        try:
            await _run_job(job)
        except Exception as exc:
            await db.ai_jobs.update_one(
                {"_id": job["_id"]},
                {
                    "$set": {
                        "status": AI_JOB_STATUS_FAILED,
                        "completed_at": datetime.now(timezone.utc),
                        "progress": {
                            **(job.get("progress") or {}),
                            "failed": max(1, int((job.get("progress") or {}).get("failed") or 0)),
                        },
                        "error": str(exc)[:500],
                    }
                },
            )
        processed += 1
    return processed


async def _run_job(job: dict[str, Any]) -> None:
    if job.get("job_type") == AI_JOB_TYPE_BULK_SUBMISSION:
        summary = await _run_bulk_submission_job(job)
        progress = {
            "total": summary.get("submission_count", 0),
            "completed": summary.get("completed", 0),
            "failed": summary.get("failed", 0),
            "skipped": summary.get("skipped", 0),
            "fallback": summary.get("fallback", 0),
        }
    elif job.get("job_type") == AI_JOB_TYPE_SIMILARITY:
        summary = await _run_similarity_job(job)
        progress = {
            "total": 1,
            "completed": 1,
            "failed": 0,
            "skipped": 0,
            "fallback": 0,
        }
    else:
        raise ValueError(f"Unsupported AI job type: {job.get('job_type')}")

    await db.ai_jobs.update_one(
        {"_id": job["_id"]},
        {
            "$set": {
                "status": AI_JOB_STATUS_COMPLETED,
                "completed_at": datetime.now(timezone.utc),
                "summary": summary,
                "progress": progress,
                "error": None,
            }
        },
    )


async def _run_bulk_submission_job(job: dict[str, Any]) -> dict[str, Any]:
    params = job.get("params") or {}
    submission_ids = [str(item) for item in params.get("submission_ids") or [] if item]
    runtime_settings = await get_ai_runtime_settings()
    force = bool(params.get("force"))
    completed = 0
    failed = 0
    skipped = 0
    fallback = 0
    results: list[dict[str, Any]] = []

    for submission_id in submission_ids:
        item = await db.submissions.find_one({"_id": parse_object_id(submission_id)})
        if not item:
            failed += 1
            results.append({"submission_id": submission_id, "status": "missing"})
            continue
        if item.get("ai_status") == "completed" and not force:
            skipped += 1
            results.append({"submission_id": submission_id, "status": "skipped"})
            continue

        await db.submissions.update_one(
            {"_id": item["_id"]},
            {"$set": {"ai_status": "running", "ai_error": None}},
        )
        updated = await evaluate_submission_and_save(
            item["_id"],
            item,
            runtime_settings=runtime_settings,
        )
        ai_status = str(updated.get("ai_status") or "failed")
        if ai_status == "completed":
            completed += 1
        elif ai_status == "fallback":
            fallback += 1
        else:
            failed += 1

        results.append(
            {
                "submission_id": submission_id,
                "status": ai_status,
                "ai_score": updated.get("ai_score"),
                "ai_provider": updated.get("ai_provider"),
            }
        )
        await db.ai_jobs.update_one(
            {"_id": job["_id"]},
            {
                "$set": {
                    "progress": {
                        "total": len(submission_ids),
                        "completed": completed,
                        "failed": failed,
                        "skipped": skipped,
                        "fallback": fallback,
                    }
                }
            },
        )

    await log_audit_event(
        actor_user_id=str(job.get("requested_by_user_id") or ""),
        action="ai_bulk_job_completed",
        entity_type="ai_job",
        entity_id=str(job["_id"]),
        detail=f"Bulk submission AI completed for {len(submission_ids)} submissions",
    )
    return {
        "submission_count": len(submission_ids),
        "completed": completed,
        "fallback": fallback,
        "failed": failed,
        "skipped": skipped,
        "results": results[:50],
    }


async def _run_similarity_job(job: dict[str, Any]) -> dict[str, Any]:
    params = job.get("params") or {}
    submission_id = str(params.get("submission_id") or "")
    threshold = float(params.get("threshold") or 0)
    source = await db.submissions.find_one({"_id": parse_object_id(submission_id)})
    if not source:
        raise ValueError("Submission not found for similarity job")
    source_assignment = None
    if source.get("assignment_id"):
        source_assignment = await db.assignments.find_one({"_id": parse_object_id(source.get("assignment_id"))})

    result = await run_similarity_pipeline(
        submission_id=submission_id,
        source=source,
        source_assignment=source_assignment,
        active_threshold=threshold,
        actor_user_id=str(job.get("requested_by_user_id") or ""),
    )
    await log_audit_event(
        actor_user_id=str(job.get("requested_by_user_id") or ""),
        action="similarity_job_completed",
        entity_type="ai_job",
        entity_id=str(job["_id"]),
        detail=f"Similarity job completed for submission {submission_id}",
    )
    return {
        "submission_id": submission_id,
        "threshold": result.get("threshold"),
        "engine_version": result.get("engine_version"),
        "created_count": result.get("created_count"),
        "updated_count": result.get("updated_count"),
        "flagged_count": result.get("flagged_count"),
        "max_score": result.get("max_score"),
    }
