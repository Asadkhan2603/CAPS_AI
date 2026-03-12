from typing import Any

from app.models.ai_evaluation_runs import ai_evaluation_run_public
from app.services.ai_jobs import serialize_ai_job


def _and_query(*parts: dict[str, Any]) -> dict[str, Any]:
    filtered = [part for part in parts if part]
    if not filtered:
        return {}
    if len(filtered) == 1:
        return filtered[0]
    return {"$and": filtered}


def _serialize_empty_scope_response(
    *,
    role: str,
    provider_payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "scope": {
            "role": role,
            "assignments_count": 0,
            "submissions_count": 0,
            "label": "No accessible assignments",
        },
        "provider": provider_payload,
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


async def build_ai_operations_overview_payload(
    *,
    database: Any,
    actor_id: str,
    role: str,
    assignment_scope_ids: list[str],
    limit: int,
    runtime_settings: dict[str, Any],
    provider_payload: dict[str, Any],
    serialize_dt,
    distinct_strings,
) -> dict[str, Any]:
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
        return _serialize_empty_scope_response(role=role, provider_payload=provider_payload)

    submission_ids = await distinct_strings(database.submissions, "_id", submission_scope_query) if role == "teacher" else []
    evaluation_scope_query = {"submission_id": {"$in": submission_ids}} if role == "teacher" else {}
    evaluation_ai_query = _and_query(
        evaluation_scope_query,
        {"$or": [{"ai_score": {"$ne": None}}, {"ai_feedback": {"$nin": [None, ""]}}]},
    )
    trace_scope_query = {"submission_id": {"$in": submission_ids}} if role == "teacher" else {}
    job_scope_query = {"requested_by_user_id": actor_id} if role == "teacher" else {}

    summary = {
        "submissions_total": await database.submissions.count_documents(submission_count_query),
        "submissions_pending": await database.submissions.count_documents(submission_pending_query),
        "submissions_running": await database.submissions.count_documents(submission_running_query),
        "submissions_completed": await database.submissions.count_documents(submission_completed_query),
        "submissions_fallback": await database.submissions.count_documents(_and_query(submission_scope_query, {"ai_status": "fallback"})),
        "submissions_failed": await database.submissions.count_documents(submission_failed_query),
        "evaluations_total": await database.evaluations.count_documents(evaluation_scope_query),
        "evaluations_with_ai": await database.evaluations.count_documents(evaluation_ai_query),
        "trace_runs_total": await database.ai_evaluation_runs.count_documents(trace_scope_query),
        "similarity_flags_total": await database.similarity_logs.count_documents(
            _and_query(similarity_scope_query, {"is_flagged": True})
        ),
        "chat_threads_total": await database.ai_evaluation_chats.count_documents(chat_scope_query),
        "jobs_total": await database.ai_jobs.count_documents(job_scope_query),
        "jobs_queued": await database.ai_jobs.count_documents(_and_query(job_scope_query, {"status": "queued"})),
        "jobs_running": await database.ai_jobs.count_documents(_and_query(job_scope_query, {"status": "running"})),
        "jobs_failed": await database.ai_jobs.count_documents(_and_query(job_scope_query, {"status": "failed"})),
        "jobs_completed": await database.ai_jobs.count_documents(_and_query(job_scope_query, {"status": "completed"})),
    }

    recent_evaluation_runs = await database.ai_evaluation_runs.find(trace_scope_query).sort("created_at", -1).limit(limit).to_list(length=limit)
    recent_similarity_flags = await database.similarity_logs.find(
        _and_query(similarity_scope_query, {"is_flagged": True})
    ).sort("created_at", -1).limit(limit).to_list(length=limit)
    recent_chat_threads = await database.ai_evaluation_chats.find(chat_scope_query).sort("updated_at", -1).limit(limit).to_list(length=limit)
    recent_jobs = await database.ai_jobs.find(job_scope_query).sort("requested_at", -1).limit(limit).to_list(length=limit)

    return {
        "scope": {
            "role": role,
            "assignments_count": len(assignment_scope_ids) if role == "teacher" else await database.assignments.count_documents({"is_deleted": {"$in": [False, None]}}),
            "submissions_count": summary["submissions_total"],
            "label": "Accessible teacher scope" if role == "teacher" else "Global admin scope",
        },
        "provider": provider_payload,
        "runtime_config": runtime_settings,
        "summary": summary,
        "recent_evaluation_runs": [
            {
                **ai_evaluation_run_public(item),
                "created_at": serialize_dt(item.get("created_at")),
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
                "created_at": serialize_dt(item.get("created_at")),
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
                "updated_at": serialize_dt(item.get("updated_at")),
            }
            for item in recent_chat_threads
        ],
        "recent_jobs": [serialize_ai_job(item) for item in recent_jobs],
    }


async def list_ai_jobs_payload(
    *,
    database: Any,
    actor_id: str,
    role: str,
    limit: int,
    status_filter: str | None,
    job_type: str | None,
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if role == "teacher":
        query["requested_by_user_id"] = actor_id
    if status_filter:
        query["status"] = status_filter
    if job_type:
        query["job_type"] = job_type

    items = await database.ai_jobs.find(query).sort("requested_at", -1).limit(limit).to_list(length=limit)
    return {
        "count": len(items),
        "items": [serialize_ai_job(item) for item in items],
    }


async def get_ai_job_detail_payload(
    *,
    job_id: str,
    actor_id: str,
    role: str,
    fetch_ai_job,
) -> dict[str, Any]:
    job = await fetch_ai_job(job_id)
    if not job:
        raise LookupError("AI job not found")
    if role == "teacher" and job.get("requested_by_user_id") != actor_id:
        raise PermissionError("Not allowed to access this AI job")
    return serialize_ai_job(job)
