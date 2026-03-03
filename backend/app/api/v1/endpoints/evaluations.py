from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from starlette.concurrency import run_in_threadpool

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.evaluations import evaluation_public
from app.schemas.evaluation import (
    EvaluationAIPreviewOut,
    EvaluationAIPreviewRequest,
    EvaluationCreate,
    EvaluationOut,
    EvaluationUpdate,
)
from app.schemas.review_ticket import ReviewTicketDecision
from app.services.audit import log_audit_event
from app.services.evaluation_ai_module import build_ai_insight
from app.services.grading import grade_from_total, grand_total, internal_total

router = APIRouter()


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


def _compute_totals(payload: dict) -> tuple[float, float, str]:
    internal = internal_total(
        payload["attendance_percent"],
        payload["skill"],
        payload["behavior"],
        payload["report"],
        payload["viva"],
    )
    total = grand_total(
        payload["attendance_percent"],
        payload["skill"],
        payload["behavior"],
        payload["report"],
        payload["viva"],
        payload["final_exam"],
    )
    grade = grade_from_total(total)
    return float(internal), float(total), grade


async def _build_ai_insight_async(
    *,
    submission_text: str,
    attendance_percent: int,
    internal_total: float,
    grand_total: float,
    grade: str,
) -> dict:
    return await run_in_threadpool(
        build_ai_insight,
        submission_text=submission_text,
        attendance_percent=attendance_percent,
        internal_total=internal_total,
        grand_total=grand_total,
        grade=grade,
    )


def _ensure_teacher_owns_evaluation(current_user: dict, evaluation: dict) -> None:
    if current_user.get("role") == "teacher" and evaluation.get("teacher_user_id") != str(current_user["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this evaluation")


async def _ensure_teacher_can_evaluate_submission(current_user: dict, submission: dict) -> None:
    if current_user.get("role") != "teacher":
        return
    assignment_id = submission.get("assignment_id")
    if not assignment_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submission has no assignment mapping")
    allowed = await _teacher_can_access_assignment(str(current_user["_id"]), assignment_id)
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to evaluate this submission")


async def _persist_ai_trace(
    *,
    evaluation_id: str | None,
    submission_id: str,
    actor_user_id: str,
    ai_payload: dict,
    totals_payload: dict,
) -> None:
    document = {
        "evaluation_id": evaluation_id,
        "submission_id": submission_id,
        "actor_user_id": actor_user_id,
        "ai_score": ai_payload.get("ai_score"),
        "ai_feedback": ai_payload.get("ai_feedback"),
        "ai_status": ai_payload.get("ai_status"),
        "ai_provider": ai_payload.get("ai_provider"),
        "ai_confidence": ai_payload.get("ai_confidence"),
        "ai_strengths": ai_payload.get("ai_strengths") or [],
        "ai_gaps": ai_payload.get("ai_gaps") or [],
        "ai_suggestions": ai_payload.get("ai_suggestions") or [],
        "ai_risk_flags": ai_payload.get("ai_risk_flags") or [],
        "grade": totals_payload.get("grade"),
        "internal_total": totals_payload.get("internal_total"),
        "grand_total": totals_payload.get("grand_total"),
        "created_at": datetime.now(timezone.utc),
    }
    await db.ai_evaluation_runs.insert_one(document)


@router.get("/", response_model=List[EvaluationOut])
async def list_evaluations(
    submission_id: str | None = Query(default=None),
    student_user_id: str | None = Query(default=None),
    teacher_user_id: str | None = Query(default=None),
    is_finalized: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[EvaluationOut]:
    query = {}
    if submission_id:
        query["submission_id"] = submission_id
    if student_user_id:
        query["student_user_id"] = student_user_id
    if teacher_user_id:
        query["teacher_user_id"] = teacher_user_id
    if is_finalized is not None:
        query["is_finalized"] = is_finalized

    if current_user.get("role") == "student":
        query["student_user_id"] = str(current_user["_id"])
    if current_user.get("role") == "teacher":
        query["teacher_user_id"] = str(current_user["_id"])

    cursor = db.evaluations.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [EvaluationOut(**evaluation_public(item)) for item in items]


@router.get("/{evaluation_id}", response_model=EvaluationOut)
async def get_evaluation(
    evaluation_id: str,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> EvaluationOut:
    item = await db.evaluations.find_one({"_id": parse_object_id(evaluation_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    if current_user.get("role") == "student" and item.get("student_user_id") != str(current_user["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this evaluation")
    _ensure_teacher_owns_evaluation(current_user, item)
    return EvaluationOut(**evaluation_public(item))


@router.get("/{evaluation_id}/trace")
async def get_evaluation_trace(
    evaluation_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> dict:
    item = await db.evaluations.find_one({"_id": parse_object_id(evaluation_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    _ensure_teacher_owns_evaluation(current_user, item)

    rows = await db.ai_evaluation_runs.find({"evaluation_id": evaluation_id}).sort("created_at", -1).limit(limit).to_list(length=limit)
    return {
        "evaluation_id": evaluation_id,
        "submission_id": item.get("submission_id"),
        "count": len(rows),
        "items": [
            {
                "id": str(row.get("_id")),
                "ai_score": row.get("ai_score"),
                "ai_status": row.get("ai_status"),
                "ai_provider": row.get("ai_provider"),
                "ai_confidence": row.get("ai_confidence"),
                "ai_risk_flags": row.get("ai_risk_flags") or [],
                "grade": row.get("grade"),
                "internal_total": row.get("internal_total"),
                "grand_total": row.get("grand_total"),
                "created_at": row.get("created_at"),
            }
            for row in rows
        ],
    }


@router.post("/ai-preview", response_model=EvaluationAIPreviewOut)
async def preview_evaluation_ai(
    payload: EvaluationAIPreviewRequest,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> EvaluationAIPreviewOut:
    submission = await db.submissions.find_one({"_id": parse_object_id(payload.submission_id)})
    if not submission:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submission not found for provided submission_id")
    await _ensure_teacher_can_evaluate_submission(current_user, submission)

    payload_data = payload.model_dump()
    internal, total, grade = _compute_totals(payload_data)
    # Reuse submission-level AI output when available to keep evaluation traces deterministic.
    if submission.get("ai_score") is not None and submission.get("ai_feedback"):
        ai_payload = {
            "ai_score": submission.get("ai_score"),
            "ai_feedback": submission.get("ai_feedback"),
            "ai_status": submission.get("ai_status"),
            "ai_provider": submission.get("ai_provider"),
            "ai_confidence": None,
            "ai_risk_flags": [],
            "ai_strengths": [],
            "ai_gaps": [],
            "ai_suggestions": [],
        }
    else:
        ai_payload = await _build_ai_insight_async(
            submission_text=submission.get("extracted_text") or "",
            attendance_percent=payload.attendance_percent,
            internal_total=internal,
            grand_total=total,
            grade=grade,
        )

    return EvaluationAIPreviewOut(
        submission_id=payload.submission_id,
        internal_total=internal,
        grand_total=total,
        grade=grade,
        ai_score=ai_payload.get("ai_score"),
        ai_feedback=ai_payload.get("ai_feedback"),
        ai_insight=ai_payload.get("insight"),
    )


@router.post("/", response_model=EvaluationOut, status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    payload: EvaluationCreate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> EvaluationOut:
    submission = await db.submissions.find_one({"_id": parse_object_id(payload.submission_id)})
    if not submission:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submission not found for provided submission_id")
    await _ensure_teacher_can_evaluate_submission(current_user, submission)

    existing = await db.evaluations.find_one({"submission_id": payload.submission_id})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evaluation already exists for submission")

    payload_data = payload.model_dump()
    internal, total, grade = _compute_totals(payload_data)
    if submission.get("ai_score") is not None and submission.get("ai_feedback"):
        ai_payload = {
            "ai_score": submission.get("ai_score"),
            "ai_feedback": submission.get("ai_feedback"),
            "ai_status": submission.get("ai_status"),
            "ai_provider": submission.get("ai_provider"),
            "ai_confidence": None,
            "ai_risk_flags": [],
            "ai_strengths": [],
            "ai_gaps": [],
            "ai_suggestions": [],
        }
    else:
        ai_payload = await _build_ai_insight_async(
            submission_text=submission.get("extracted_text") or "",
            attendance_percent=payload.attendance_percent,
            internal_total=internal,
            grand_total=total,
            grade=grade,
        )
    now = datetime.now(timezone.utc)

    document = {
        "submission_id": payload.submission_id,
        "student_user_id": submission.get("student_user_id"),
        "teacher_user_id": str(current_user["_id"]),
        "attendance_percent": payload.attendance_percent,
        "skill": payload.skill,
        "behavior": payload.behavior,
        "report": payload.report,
        "viva": payload.viva,
        "final_exam": payload.final_exam,
        "internal_total": internal,
        "grand_total": total,
        "grade": grade,
        "ai_score": ai_payload.get("ai_score"),
        "ai_feedback": ai_payload.get("ai_feedback"),
        "ai_status": ai_payload.get("ai_status"),
        "ai_provider": ai_payload.get("ai_provider"),
        "ai_confidence": ai_payload.get("ai_confidence"),
        "ai_risk_flags": ai_payload.get("ai_risk_flags") or [],
        "ai_strengths": ai_payload.get("ai_strengths") or [],
        "ai_gaps": ai_payload.get("ai_gaps") or [],
        "ai_suggestions": ai_payload.get("ai_suggestions") or [],
        "remarks": payload.remarks,
        "is_finalized": payload.is_finalized,
        "finalized_at": now if payload.is_finalized else None,
        "finalized_by_user_id": str(current_user["_id"]) if payload.is_finalized else None,
        "created_at": now,
        "updated_at": now,
    }

    result = await db.evaluations.insert_one(document)
    created = await db.evaluations.find_one({"_id": result.inserted_id})

    await _persist_ai_trace(
        evaluation_id=str(result.inserted_id),
        submission_id=payload.submission_id,
        actor_user_id=str(current_user["_id"]),
        ai_payload=ai_payload,
        totals_payload={"internal_total": internal, "grand_total": total, "grade": grade},
    )

    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="create",
        entity_type="evaluation",
        entity_id=str(result.inserted_id),
        detail=f"Created evaluation for submission {payload.submission_id}",
    )

    return EvaluationOut(**evaluation_public(created))


@router.post("/{evaluation_id}/ai-refresh", response_model=EvaluationOut)
async def refresh_evaluation_ai(
    evaluation_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> EvaluationOut:
    evaluation_obj_id = parse_object_id(evaluation_id)
    item = await db.evaluations.find_one({"_id": evaluation_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    _ensure_teacher_owns_evaluation(current_user, item)

    submission = await db.submissions.find_one({"_id": parse_object_id(item.get("submission_id"))})
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapped submission not found")

    ai_payload = await _build_ai_insight_async(
        submission_text=submission.get("extracted_text") or "",
        attendance_percent=int(item.get("attendance_percent") or 0),
        internal_total=float(item.get("internal_total") or 0),
        grand_total=float(item.get("grand_total") or 0),
        grade=str(item.get("grade") or "Needs Improvement"),
    )

    await db.evaluations.update_one(
        {"_id": evaluation_obj_id},
        {
            "$set": {
                "ai_score": ai_payload.get("ai_score"),
                "ai_feedback": ai_payload.get("ai_feedback"),
                "ai_status": ai_payload.get("ai_status"),
                "ai_provider": ai_payload.get("ai_provider"),
                "ai_confidence": ai_payload.get("ai_confidence"),
                "ai_risk_flags": ai_payload.get("ai_risk_flags") or [],
                "ai_strengths": ai_payload.get("ai_strengths") or [],
                "ai_gaps": ai_payload.get("ai_gaps") or [],
                "ai_suggestions": ai_payload.get("ai_suggestions") or [],
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )

    await _persist_ai_trace(
        evaluation_id=evaluation_id,
        submission_id=item.get("submission_id"),
        actor_user_id=str(current_user["_id"]),
        ai_payload=ai_payload,
        totals_payload={
            "internal_total": item.get("internal_total"),
            "grand_total": item.get("grand_total"),
            "grade": item.get("grade"),
        },
    )

    updated = await db.evaluations.find_one({"_id": evaluation_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="refresh_ai",
        entity_type="evaluation",
        entity_id=evaluation_id,
        detail="Refreshed AI insight for evaluation",
    )

    return EvaluationOut(**evaluation_public(updated))


@router.put("/{evaluation_id}", response_model=EvaluationOut)
async def update_evaluation(
    evaluation_id: str,
    payload: EvaluationUpdate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> EvaluationOut:
    evaluation_obj_id = parse_object_id(evaluation_id)
    item = await db.evaluations.find_one({"_id": evaluation_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    _ensure_teacher_owns_evaluation(current_user, item)

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if item.get("is_finalized") and current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finalized evaluation can only be modified by admin")

    merged = {
        "attendance_percent": update_data.get("attendance_percent", item.get("attendance_percent", 0)),
        "skill": update_data.get("skill", item.get("skill", 0.0)),
        "behavior": update_data.get("behavior", item.get("behavior", 0.0)),
        "report": update_data.get("report", item.get("report", 0.0)),
        "viva": update_data.get("viva", item.get("viva", 0.0)),
        "final_exam": update_data.get("final_exam", item.get("final_exam", 0)),
    }
    internal, total, grade = _compute_totals(merged)
    update_data["internal_total"] = internal
    update_data["grand_total"] = total
    update_data["grade"] = grade

    if any(
        key in update_data
        for key in ["attendance_percent", "skill", "behavior", "report", "viva", "final_exam"]
    ):
        submission = await db.submissions.find_one({"_id": parse_object_id(item.get("submission_id"))})
        submission_text = submission.get("extracted_text") if submission else ""
        ai_payload = await _build_ai_insight_async(
            submission_text=submission_text or "",
            attendance_percent=int(merged["attendance_percent"]),
            internal_total=internal,
            grand_total=total,
            grade=grade,
        )
        update_data.update(
            {
                "ai_score": ai_payload.get("ai_score"),
                "ai_feedback": ai_payload.get("ai_feedback"),
                "ai_status": ai_payload.get("ai_status"),
                "ai_provider": ai_payload.get("ai_provider"),
                "ai_confidence": ai_payload.get("ai_confidence"),
                "ai_risk_flags": ai_payload.get("ai_risk_flags") or [],
                "ai_strengths": ai_payload.get("ai_strengths") or [],
                "ai_gaps": ai_payload.get("ai_gaps") or [],
                "ai_suggestions": ai_payload.get("ai_suggestions") or [],
            }
        )
        await _persist_ai_trace(
            evaluation_id=evaluation_id,
            submission_id=item.get("submission_id"),
            actor_user_id=str(current_user["_id"]),
            ai_payload=ai_payload,
            totals_payload={"internal_total": internal, "grand_total": total, "grade": grade},
        )

    update_data["updated_at"] = datetime.now(timezone.utc)
    await db.evaluations.update_one({"_id": evaluation_obj_id}, {"$set": update_data})
    updated = await db.evaluations.find_one({"_id": evaluation_obj_id})

    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="update",
        entity_type="evaluation",
        entity_id=evaluation_id,
        detail="Updated evaluation fields",
    )

    return EvaluationOut(**evaluation_public(updated))


@router.patch("/{evaluation_id}/finalize", response_model=EvaluationOut)
async def finalize_evaluation(
    evaluation_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> EvaluationOut:
    evaluation_obj_id = parse_object_id(evaluation_id)
    item = await db.evaluations.find_one({"_id": evaluation_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    _ensure_teacher_owns_evaluation(current_user, item)

    await db.evaluations.update_one(
        {"_id": evaluation_obj_id},
        {
            "$set": {
                "is_finalized": True,
                "finalized_at": datetime.now(timezone.utc),
                "finalized_by_user_id": str(current_user["_id"]),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    updated = await db.evaluations.find_one({"_id": evaluation_obj_id})
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

    evaluation_obj_id = parse_object_id(evaluation_id)
    item = await db.evaluations.find_one({"_id": evaluation_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    await db.evaluations.update_one(
        {"_id": evaluation_obj_id},
        {
            "$set": {
                "is_finalized": False,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    updated = await db.evaluations.find_one({"_id": evaluation_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="override_unfinalize",
        entity_type="evaluation",
        entity_id=evaluation_id,
        detail=f"Admin override unfinalized evaluation. Reason: {payload.reason.strip()}",
    )
    return EvaluationOut(**evaluation_public(updated))
