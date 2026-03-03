from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.ai_chat import ai_chat_public
from app.schemas.ai_chat import AIChatEvaluateRequest, AIChatEvaluateResponse, AIChatThreadOut
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


async def _resolve_submission(student_id: str, exam_id: str, submission_id: Optional[str]) -> Optional[dict]:
    if submission_id:
        submission = await db.submissions.find_one({"_id": parse_object_id(submission_id)})
        return submission
    return await db.submissions.find_one({"student_user_id": student_id, "assignment_id": exam_id})


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

    ai_response, ai_error = await run_in_threadpool(
        generate_evaluation_chat_reply,
        teacher_message=payload.teacher_message,
        question_text=payload.question_text,
        student_answer=student_answer,
        rubric=payload.rubric,
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
