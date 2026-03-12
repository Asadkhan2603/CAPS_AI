from __future__ import annotations

from typing import Any

from starlette.concurrency import run_in_threadpool

from app.core.database import db
from app.core.schema_versions import SUBMISSION_SCHEMA_VERSION
from app.services.ai_evaluation import generate_ai_feedback


async def evaluate_submission_and_save(
    submission_obj_id,
    item: dict[str, Any],
    *,
    runtime_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    extracted_text = item.get("extracted_text", "")
    feedback = await run_in_threadpool(
        generate_ai_feedback,
        extracted_text,
        max_score=10.0,
        runtime_settings=runtime_settings,
    )
    ai_status = str(feedback.get("status") or "failed")
    update_data = {
        "ai_status": ai_status,
        "ai_score": feedback.get("score"),
        "ai_feedback": feedback.get("summary"),
        "ai_provider": feedback.get("provider"),
        "ai_prompt_version": feedback.get("prompt_version"),
        "ai_runtime_snapshot": feedback.get("runtime_snapshot"),
        "ai_error": feedback.get("error"),
        "schema_version": SUBMISSION_SCHEMA_VERSION,
    }
    await db.submissions.update_one({"_id": submission_obj_id}, {"$set": update_data})
    updated = await db.submissions.find_one({"_id": submission_obj_id})
    return updated or item
