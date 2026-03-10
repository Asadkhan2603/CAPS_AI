from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.concurrency import run_in_threadpool

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.ai_chat import ai_chat_public
from app.schemas.ai_chat import AIChatEvaluateRequest, AIChatEvaluateResponse, AIChatThreadOut
from app.services.ai_jobs import get_ai_job, serialize_ai_job
from app.services.ai_runtime import get_ai_runtime_settings, save_ai_runtime_settings
from app.services.ai_chat_service import generate_evaluation_chat_reply
from app.services.audit import log_audit_event

router = APIRouter()

_indexes_ensured = False


async def _ensure_indexes() -> None:
    global _indexes_ensured
    if _indexes_ensured:
        return
    await db.ai_evaluation_chats.create_index([("student_id", 1), ("exam_id", 1)], unique=True)
    await db.ai_evaluation_chats.create_index("teacher_id")
    await db.ai_evaluation_chats.create_index("exam_id")
    _indexes_ensured = True


async def _teacher_can_access_assignment(teacher_user_id: str, assignment_id: str) -> bool:
    assignment = await db.assignments.find_one({"_id": parse_object_id(assignment_id)})
    if not assignment:
        return False
    if assignment.get("created_by") == teacher_user_id:
        return True
    class_id = assignment.get("class_id")
    if not class_id:
        return False
    class_doc = await db.classes.find_one({"_id": parse_object_id(class_id)})
    if not class_doc:
        return False
    return class_doc.get("class_coordinator_user_id") == teacher_user_id


def _and_query(*parts: dict[str, Any]) -> dict[str, Any]:
    filtered = [part for part in parts if part]
    if not filtered:
        return {}
    if len(filtered) == 1:
        return filtered[0]
    return {"$and": filtered}


async def _distinct_strings(collection, field: str, query: dict[str, Any]) -> list[str]:
    distinct = getattr(collection, "distinct", None)
    if callable(distinct):
        try:
            values = await distinct(field, query)
            return sorted({str(value) for value in values if value is not None})
        except Exception:
            pass

    rows = await collection.find(query, {field: 1}).to_list(length=5000)
    return sorted({str(row.get(field)) for row in rows if row.get(field) is not None})


async def _teacher_assignment_scope_ids(teacher_user_id: str) -> list[str]:
    created_assignment_ids = await _distinct_strings(
        db.assignments,
        "_id",
        {"created_by": teacher_user_id, "is_deleted": {"$in": [False, None]}},
    )
    coordinated_class_ids = await _distinct_strings(
        db.classes,
        "_id",
        {"class_coordinator_user_id": teacher_user_id},
    )

    coordinated_assignment_ids: list[str] = []
    if coordinated_class_ids:
        coordinated_assignment_ids = await _distinct_strings(
            db.assignments,
            "_id",
            {"class_id": {"$in": coordinated_class_ids}, "is_deleted": {"$in": [False, None]}},
        )

    return sorted(set(created_assignment_ids + coordinated_assignment_ids))


def _provider_mode_payload(runtime_settings: dict[str, Any]) -> dict[str, Any]:
    openai_configured = bool(runtime_settings.get("openai_configured"))
    effective_provider_enabled = bool(runtime_settings.get("effective_provider_enabled"))
    return {
        "openai_configured": openai_configured,
        "provider_enabled": bool(runtime_settings.get("provider_enabled")),
        "mode": "openai+fallback" if effective_provider_enabled else "fallback-only",
        "model": runtime_settings.get("openai_model") if openai_configured else None,
        "timeout_seconds": runtime_settings.get("openai_timeout_seconds"),
        "max_output_tokens": runtime_settings.get("openai_max_output_tokens"),
        "similarity_threshold": runtime_settings.get("similarity_threshold"),
    }


def _serialize_dt(value: Any) -> str | None:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo:
        return value.isoformat()
    return value.replace(tzinfo=timezone.utc).isoformat()


async def _resolve_submission(student_id: str, exam_id: str, submission_id: Optional[str]) -> Optional[dict]:
    if submission_id:
        submission = await db.submissions.find_one({"_id": parse_object_id(submission_id)})
        return submission
    return await db.submissions.find_one({"student_user_id": student_id, "assignment_id": exam_id})


@router.get("/admin/runtime-config")
async def get_ai_runtime_config(
    current_user=Depends(require_roles(["admin"])),
) -> dict[str, Any]:
    runtime_settings = await get_ai_runtime_settings()
    return {
        "effective": runtime_settings,
        "provider": _provider_mode_payload(runtime_settings),
    }


@router.put("/admin/runtime-config")
async def update_ai_runtime_config(
    payload: dict[str, Any],
    current_user=Depends(require_roles(["admin"])),
) -> dict[str, Any]:
    runtime_settings = await save_ai_runtime_settings(payload, actor_user_id=str(current_user["_id"]))
    return {
        "effective": runtime_settings,
        "provider": _provider_mode_payload(runtime_settings),
    }


@router.get("/ops/overview")
async def get_ai_operations_overview(
    limit: int = Query(default=8, ge=1, le=25),
    current_user=Depends(require_roles(["teacher", "admin"])),
) -> dict[str, Any]:
    actor_id = str(current_user["_id"])
    role = str(current_user.get("role") or "")

    assignment_scope_ids: list[str] = []
    if role == "teacher":
        assignment_scope_ids = await _teacher_assignment_scope_ids(actor_id)
    runtime_settings = await get_ai_runtime_settings()
    assignment_scope_query = {"assignment_id": {"$in": assignment_scope_ids}} if assignment_scope_ids else {}
    similarity_scope_query = (
        {
            "$or": [
                {"source_assignment_id": {"$in": assignment_scope_ids}},
                {"matched_assignment_id": {"$in": assignment_scope_ids}},
            ]
        }
        if assignment_scope_ids
        else {}
    )
    chat_scope_query = {"exam_id": {"$in": assignment_scope_ids}} if assignment_scope_ids else {}

    submission_scope_query = assignment_scope_query if role == "teacher" else {}
    submission_count_query = submission_scope_query
    submission_pending_query = _and_query(
        submission_scope_query,
        {"$or": [{"ai_status": "pending"}, {"ai_status": None}]},
    )
    submission_running_query = _and_query(submission_scope_query, {"ai_status": "running"})
    submission_completed_query = _and_query(submission_scope_query, {"ai_status": "completed"})
    submission_failed_query = _and_query(submission_scope_query, {"ai_status": "failed"})

    if role == "teacher" and not assignment_scope_ids:
        return {
            "scope": {
                "role": role,
                "assignments_count": 0,
                "submissions_count": 0,
                "label": "No accessible assignments",
            },
            "provider": _provider_mode_payload(runtime_settings),
            "summary": {
                "submissions_total": 0,
                "submissions_pending": 0,
                "submissions_running": 0,
                "submissions_completed": 0,
                "submissions_fallback": 0,
                "submissions_failed": 0,
                "evaluations_total": 0,
                "evaluations_with_ai": 0,
                "trace_runs_total": 0,
                "similarity_flags_total": 0,
                "chat_threads_total": 0,
                "jobs_total": 0,
                "jobs_queued": 0,
                "jobs_running": 0,
                "jobs_failed": 0,
                "jobs_completed": 0,
            },
            "recent_evaluation_runs": [],
            "recent_similarity_flags": [],
            "recent_chat_threads": [],
            "recent_jobs": [],
        }

    submission_ids = await _distinct_strings(db.submissions, "_id", submission_scope_query) if role == "teacher" else []
    evaluation_scope_query = {"submission_id": {"$in": submission_ids}} if role == "teacher" else {}
    evaluation_ai_query = _and_query(
        evaluation_scope_query,
        {"$or": [{"ai_score": {"$ne": None}}, {"ai_feedback": {"$nin": [None, ""]}}]},
    )
    trace_scope_query = {"submission_id": {"$in": submission_ids}} if role == "teacher" else {}
    job_scope_query = {"requested_by_user_id": actor_id} if role == "teacher" else {}

    summary = {
        "submissions_total": await db.submissions.count_documents(submission_count_query),
        "submissions_pending": await db.submissions.count_documents(submission_pending_query),
        "submissions_running": await db.submissions.count_documents(submission_running_query),
        "submissions_completed": await db.submissions.count_documents(submission_completed_query),
        "submissions_fallback": await db.submissions.count_documents(_and_query(submission_scope_query, {"ai_status": "fallback"})),
        "submissions_failed": await db.submissions.count_documents(submission_failed_query),
        "evaluations_total": await db.evaluations.count_documents(evaluation_scope_query),
        "evaluations_with_ai": await db.evaluations.count_documents(evaluation_ai_query),
        "trace_runs_total": await db.ai_evaluation_runs.count_documents(trace_scope_query),
        "similarity_flags_total": await db.similarity_logs.count_documents(
            _and_query(similarity_scope_query, {"is_flagged": True})
        ),
        "chat_threads_total": await db.ai_evaluation_chats.count_documents(chat_scope_query),
        "jobs_total": await db.ai_jobs.count_documents(job_scope_query),
        "jobs_queued": await db.ai_jobs.count_documents(_and_query(job_scope_query, {"status": "queued"})),
        "jobs_running": await db.ai_jobs.count_documents(_and_query(job_scope_query, {"status": "running"})),
        "jobs_failed": await db.ai_jobs.count_documents(_and_query(job_scope_query, {"status": "failed"})),
        "jobs_completed": await db.ai_jobs.count_documents(_and_query(job_scope_query, {"status": "completed"})),
    }

    recent_evaluation_runs = await db.ai_evaluation_runs.find(trace_scope_query).sort("created_at", -1).limit(limit).to_list(length=limit)
    recent_similarity_flags = await db.similarity_logs.find(
        _and_query(similarity_scope_query, {"is_flagged": True})
    ).sort("created_at", -1).limit(limit).to_list(length=limit)
    recent_chat_threads = await db.ai_evaluation_chats.find(chat_scope_query).sort("updated_at", -1).limit(limit).to_list(length=limit)
    recent_jobs = await db.ai_jobs.find(job_scope_query).sort("requested_at", -1).limit(limit).to_list(length=limit)

    return {
        "scope": {
            "role": role,
            "assignments_count": len(assignment_scope_ids) if role == "teacher" else await db.assignments.count_documents({"is_deleted": {"$in": [False, None]}}),
            "submissions_count": summary["submissions_total"],
            "label": "Accessible teacher scope" if role == "teacher" else "Global admin scope",
        },
        "provider": _provider_mode_payload(runtime_settings),
        "runtime_config": runtime_settings,
        "summary": summary,
        "recent_evaluation_runs": [
            {
                "id": str(item.get("_id")),
                "evaluation_id": item.get("evaluation_id"),
                "submission_id": item.get("submission_id"),
                "actor_user_id": item.get("actor_user_id"),
                "ai_status": item.get("ai_status"),
                "ai_provider": item.get("ai_provider"),
                "ai_score": item.get("ai_score"),
                "grade": item.get("grade"),
                "grand_total": item.get("grand_total"),
                "created_at": _serialize_dt(item.get("created_at")),
            }
            for item in recent_evaluation_runs
        ],
        "recent_similarity_flags": [
            {
                "id": str(item.get("_id")),
                "source_submission_id": item.get("source_submission_id"),
                "matched_submission_id": item.get("matched_submission_id"),
                "source_assignment_id": item.get("source_assignment_id"),
                "matched_assignment_id": item.get("matched_assignment_id"),
                "score": item.get("score"),
                "threshold": item.get("threshold"),
                "created_at": _serialize_dt(item.get("created_at")),
            }
            for item in recent_similarity_flags
        ],
        "recent_chat_threads": [
            {
                "id": str(item.get("_id")),
                "teacher_id": item.get("teacher_id"),
                "student_id": item.get("student_id"),
                "exam_id": item.get("exam_id"),
                "question_id": item.get("question_id"),
                "message_count": len(item.get("messages") or []),
                "last_role": (item.get("messages") or [{}])[-1].get("role"),
                "updated_at": _serialize_dt(item.get("updated_at")),
            }
            for item in recent_chat_threads
        ],
        "recent_jobs": [serialize_ai_job(item) for item in recent_jobs],
    }


@router.get("/jobs")
async def list_ai_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    job_type: str | None = Query(default=None),
    current_user=Depends(require_roles(["teacher", "admin"])),
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if current_user.get("role") == "teacher":
        query["requested_by_user_id"] = str(current_user["_id"])
    if status_filter:
        query["status"] = status_filter
    if job_type:
        query["job_type"] = job_type

    items = await db.ai_jobs.find(query).sort("requested_at", -1).limit(limit).to_list(length=limit)
    return {
        "count": len(items),
        "items": [serialize_ai_job(item) for item in items],
    }


@router.get("/jobs/{job_id}")
async def get_ai_job_detail(
    job_id: str,
    current_user=Depends(require_roles(["teacher", "admin"])),
) -> dict[str, Any]:
    job = await get_ai_job(job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI job not found")
    if current_user.get("role") == "teacher" and job.get("requested_by_user_id") != str(current_user["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this AI job")
    return serialize_ai_job(job)


@router.post("/evaluate", response_model=AIChatEvaluateResponse)
async def evaluate_with_ai(
    payload: AIChatEvaluateRequest,
    current_user=Depends(require_roles(["teacher", "admin"])),
) -> AIChatEvaluateResponse:
    await _ensure_indexes()
    actor_id = str(current_user["_id"])
    teacher_id = actor_id if current_user.get("role") == "teacher" else (payload.teacher_id or actor_id)
    student_id = payload.student_id
    exam_id = payload.exam_id

    submission = await _resolve_submission(student_id, exam_id, payload.submission_id)
    if current_user.get("role") == "teacher":
        if not await _teacher_can_access_assignment(actor_id, exam_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this exam")
        if submission and submission.get("student_user_id") != student_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="submission_id does not match student_id")
    elif current_user.get("role") == "admin":
        # Admin may audit; still validate if submission belongs to same exam when supplied.
        if submission and submission.get("assignment_id") != exam_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="submission_id does not match exam_id")

    student_answer = payload.student_answer
    if not student_answer and submission:
        student_answer = submission.get("extracted_text") or submission.get("notes") or ""

    runtime_settings = await get_ai_runtime_settings()
    ai_response, ai_error, ai_metadata = await run_in_threadpool(
        generate_evaluation_chat_reply,
        teacher_message=payload.teacher_message,
        question_text=payload.question_text,
        student_answer=student_answer,
        rubric=payload.rubric,
        runtime_settings=runtime_settings,
    )
    now = datetime.now(timezone.utc)
    thread = await db.ai_evaluation_chats.find_one({"student_id": student_id, "exam_id": exam_id})
    teacher_message_doc = {
        "role": "teacher",
        "content": payload.teacher_message.strip(),
        "timestamp": now,
        "question_id": payload.question_id,
    }
    ai_message_doc = {
        "role": "ai",
        "content": ai_response,
        "timestamp": now,
        "question_id": payload.question_id,
        "provider_error": ai_error,
        "provider": ai_metadata.get("provider"),
        "prompt_version": ai_metadata.get("prompt_version"),
        "runtime_snapshot": ai_metadata.get("runtime_snapshot"),
    }

    if thread:
        messages = list(thread.get("messages", []))
        messages.extend([teacher_message_doc, ai_message_doc])
        await db.ai_evaluation_chats.update_one(
            {"_id": thread["_id"]},
            {
                "$set": {
                    "messages": messages,
                    "question_id": payload.question_id,
                    "updated_at": now,
                }
            },
        )
        updated = await db.ai_evaluation_chats.find_one({"_id": thread["_id"]})
    else:
        document = {
            "teacher_id": teacher_id,
            "student_id": student_id,
            "exam_id": exam_id,
            "question_id": payload.question_id,
            "messages": [teacher_message_doc, ai_message_doc],
            "created_at": now,
            "updated_at": now,
        }
        result = await db.ai_evaluation_chats.insert_one(document)
        updated = await db.ai_evaluation_chats.find_one({"_id": result.inserted_id})

    await log_audit_event(
        actor_user_id=actor_id,
        action="ai_chat_evaluate",
        entity_type="ai_evaluation_chat",
        entity_id=str(updated["_id"]),
        detail=f"AI chat evaluate exam_id={exam_id} student_id={student_id}",
    )

    return AIChatEvaluateResponse(
        thread=AIChatThreadOut(**ai_chat_public(updated)),
        ai_response=ai_response,
    )


@router.get("/history/{student_id}/{exam_id}", response_model=AIChatThreadOut)
async def get_ai_chat_history(
    student_id: str,
    exam_id: str,
    current_user=Depends(require_roles(["teacher", "admin"])),
) -> AIChatThreadOut:
    await _ensure_indexes()
    actor_id = str(current_user["_id"])

    if current_user.get("role") == "teacher":
        if not await _teacher_can_access_assignment(actor_id, exam_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this exam")

    thread = await db.ai_evaluation_chats.find_one({"student_id": student_id, "exam_id": exam_id})
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI chat history not found")
    return AIChatThreadOut(**ai_chat_public(thread))
