from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.mongo import parse_object_id
from app.core.schema_versions import EVALUATION_SCHEMA_VERSION
from app.core.security import require_roles
from app.models.evaluations import evaluation_public
from app.schemas.evaluation import EvaluationOut, EvaluationUpdate
from app.schemas.review_ticket import ReviewTicketDecision
from app.services.ai_runtime import get_ai_runtime_settings
from app.services.audit import log_audit_event
from app.services.evaluation_access_policy import ensure_teacher_owns_evaluation
from app.services.evaluation_workflow import (
    ai_payload_update_fields,
    build_ai_insight_async,
    compute_evaluation_totals,
    persist_ai_trace,
)
from app.services.official_results import request_semester_result_correction

from .evaluations_common import get_evaluations_db

router = APIRouter()


@router.put("/{evaluation_id}", response_model=EvaluationOut)
async def update_evaluation(
    evaluation_id: str,
    payload: EvaluationUpdate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> EvaluationOut:
    database = get_evaluations_db()
    evaluation_obj_id = parse_object_id(evaluation_id)
    item = await database.evaluations.find_one({"_id": evaluation_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    ensure_teacher_owns_evaluation(current_user, item)

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if item.get("is_finalized") and current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finalized evaluation can only be modified by admin")

    was_released = item.get("result_status") == "released"
    merged = {
        "attendance_percent": update_data.get("attendance_percent", item.get("attendance_percent", 0)),
        "skill": update_data.get("skill", item.get("skill", 0.0)),
        "behavior": update_data.get("behavior", item.get("behavior", 0.0)),
        "report": update_data.get("report", item.get("report", 0.0)),
        "viva": update_data.get("viva", item.get("viva", 0.0)),
        "final_exam": update_data.get("final_exam", item.get("final_exam", 0)),
    }
    internal, total, grade = compute_evaluation_totals(merged)
    update_data["internal_total"] = internal
    update_data["grand_total"] = total
    update_data["grade"] = grade
    if "rubric_criteria" in update_data and update_data["rubric_criteria"] is None:
        update_data["rubric_criteria"] = []

    if any(
        key in update_data
        for key in ["attendance_percent", "skill", "behavior", "report", "viva", "final_exam", "rubric_criteria"]
    ):
        submission = await database.submissions.find_one({"_id": parse_object_id(item.get("submission_id"))})
        submission_text = submission.get("extracted_text") if submission else ""
        rubric_criteria = update_data.get("rubric_criteria", item.get("rubric_criteria") or [])
        ai_payload = await build_ai_insight_async(
            submission_text=submission_text or "",
            attendance_percent=int(merged["attendance_percent"]),
            internal_total_value=internal,
            grand_total_value=total,
            grade=grade,
            rubric_criteria=rubric_criteria,
            runtime_settings=await get_ai_runtime_settings(),
        )
        update_data.update(ai_payload_update_fields(ai_payload))
        await persist_ai_trace(
            database=database,
            evaluation_id=evaluation_id,
            submission_id=item.get("submission_id"),
            actor_user_id=str(current_user["_id"]),
            ai_payload=ai_payload,
            totals_payload={"internal_total": internal, "grand_total": total, "grade": grade},
        )
        if was_released:
            update_data["result_status"] = "finalized_unreleased" if item.get("is_finalized") else "draft"
            update_data["released_at"] = None
            update_data["released_by_user_id"] = None

    update_data["schema_version"] = EVALUATION_SCHEMA_VERSION
    update_data["updated_at"] = datetime.now(timezone.utc)
    await database.evaluations.update_one({"_id": evaluation_obj_id}, {"$set": update_data})
    updated = await database.evaluations.find_one({"_id": evaluation_obj_id})

    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="update",
        entity_type="evaluation",
        entity_id=evaluation_id,
        detail="Updated evaluation fields",
    )
    if was_released:
        await request_semester_result_correction(
            trigger_evaluation=updated,
            actor_user_id=str(current_user.get("_id") or ""),
            reason="Underlying released evaluation changed and requires semester result review.",
            database=database,
        )

    return EvaluationOut(**evaluation_public(updated))


@router.patch("/{evaluation_id}/finalize", response_model=EvaluationOut)
async def finalize_evaluation(
    evaluation_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> EvaluationOut:
    database = get_evaluations_db()
    evaluation_obj_id = parse_object_id(evaluation_id)
    item = await database.evaluations.find_one({"_id": evaluation_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    ensure_teacher_owns_evaluation(current_user, item)

    await database.evaluations.update_one(
        {"_id": evaluation_obj_id},
        {
            "$set": {
                "is_finalized": True,
                "result_status": "finalized_unreleased",
                "finalized_at": datetime.now(timezone.utc),
                "finalized_by_user_id": str(current_user["_id"]),
                "schema_version": EVALUATION_SCHEMA_VERSION,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    updated = await database.evaluations.find_one({"_id": evaluation_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="finalize",
        entity_type="evaluation",
        entity_id=evaluation_id,
        detail="Finalized evaluation",
    )
    return EvaluationOut(**evaluation_public(updated))


@router.patch("/{evaluation_id}/override-unfinalize", response_model=EvaluationOut)
async def override_unfinalize_evaluation(
    evaluation_id: str,
    payload: ReviewTicketDecision,
    current_user=Depends(require_roles(["admin"])),
) -> EvaluationOut:
    if not payload.reason or len(payload.reason.strip()) < 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reason is required for override")

    database = get_evaluations_db()
    evaluation_obj_id = parse_object_id(evaluation_id)
    item = await database.evaluations.find_one({"_id": evaluation_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    was_released = item.get("result_status") == "released"
    await database.evaluations.update_one(
        {"_id": evaluation_obj_id},
        {
            "$set": {
                "is_finalized": False,
                "result_status": "draft",
                "schema_version": EVALUATION_SCHEMA_VERSION,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    updated = await database.evaluations.find_one({"_id": evaluation_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="override_unfinalize",
        entity_type="evaluation",
        entity_id=evaluation_id,
        detail=f"Admin override unfinalized evaluation. Reason: {payload.reason.strip()}",
    )
    if was_released:
        await request_semester_result_correction(
            trigger_evaluation=updated,
            actor_user_id=str(current_user.get("_id") or ""),
            reason=f"Released evaluation was unfinalized by admin override. Reason: {payload.reason.strip()}",
            database=database,
        )
    return EvaluationOut(**evaluation_public(updated))


@router.patch("/{evaluation_id}/release", response_model=EvaluationOut)
async def release_evaluation_result(
    evaluation_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> EvaluationOut:
    database = get_evaluations_db()
    evaluation_obj_id = parse_object_id(evaluation_id)
    item = await database.evaluations.find_one({"_id": evaluation_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    ensure_teacher_owns_evaluation(current_user, item)
    if not item.get("is_finalized"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only finalized evaluation can be released")

    next_version = int(item.get("result_version") or 1)
    if item.get("result_status") != "released":
        next_version += 1

    await database.evaluations.update_one(
        {"_id": evaluation_obj_id},
        {
            "$set": {
                "result_status": "released",
                "released_at": datetime.now(timezone.utc),
                "released_by_user_id": str(current_user["_id"]),
                "result_version": next_version,
                "schema_version": EVALUATION_SCHEMA_VERSION,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    updated = await database.evaluations.find_one({"_id": evaluation_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="release_result",
        entity_type="evaluation",
        entity_id=evaluation_id,
        detail=f"Released official result version {next_version}",
    )
    return EvaluationOut(**evaluation_public(updated))
