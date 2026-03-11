from datetime import datetime, timezone
from typing import Any


def normalize_chat_result(ai_result: Any) -> tuple[str, str | None, dict[str, Any]]:
    if isinstance(ai_result, tuple):
        if len(ai_result) == 3:
            ai_response, ai_error, ai_metadata = ai_result
            return str(ai_response), ai_error, ai_metadata or {}
        if len(ai_result) == 2:
            ai_response, ai_error = ai_result
            return str(ai_response), ai_error, {}
        raise ValueError("generate_evaluation_chat_reply returned an unexpected tuple shape")
    return str(ai_result), None, {}


async def upsert_evaluation_chat_thread(
    *,
    database: Any,
    teacher_id: str,
    student_id: str,
    exam_id: str,
    question_id: str | None,
    teacher_message: str,
    ai_response: str,
    ai_error: str | None,
    ai_metadata: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    thread = await database.ai_evaluation_chats.find_one({"student_id": student_id, "exam_id": exam_id})
    teacher_message_doc = {
        "role": "teacher",
        "content": teacher_message.strip(),
        "timestamp": now,
        "question_id": question_id,
    }
    ai_message_doc = {
        "role": "ai",
        "content": ai_response,
        "timestamp": now,
        "question_id": question_id,
        "provider_error": ai_error,
        "provider": ai_metadata.get("provider"),
        "prompt_version": ai_metadata.get("prompt_version"),
        "runtime_snapshot": ai_metadata.get("runtime_snapshot"),
    }

    if thread:
        messages = list(thread.get("messages", []))
        messages.extend([teacher_message_doc, ai_message_doc])
        await database.ai_evaluation_chats.update_one(
            {"_id": thread["_id"]},
            {
                "$set": {
                    "messages": messages,
                    "question_id": question_id,
                    "updated_at": now,
                }
            },
        )
        return await database.ai_evaluation_chats.find_one({"_id": thread["_id"]})

    document = {
        "teacher_id": teacher_id,
        "student_id": student_id,
        "exam_id": exam_id,
        "question_id": question_id,
        "messages": [teacher_message_doc, ai_message_doc],
        "created_at": now,
        "updated_at": now,
    }
    result = await database.ai_evaluation_chats.insert_one(document)
    return await database.ai_evaluation_chats.find_one({"_id": result.inserted_id})
