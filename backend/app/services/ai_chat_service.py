from __future__ import annotations

import json
import re

from openai import OpenAI

from app.core.config import settings


def _fallback_response(question_text: str | None, rubric: str | None, student_answer: str | None) -> str:
    answer = (student_answer or "").strip()
    if not answer:
        return (
            "Suggested Marks: 0/10\n"
            "Explanation: Student answer is empty or unavailable.\n"
            "Constructive Feedback: Ask the student to address the question directly with key concepts.\n"
            "Improvement Suggestions: Include definitions, examples, and a clear structure."
        )
    return (
        "Suggested Marks: 5/10\n"
        "Explanation: Preliminary fallback assessment generated because AI provider was unavailable.\n"
        "Constructive Feedback: Answer covers some points but needs depth and stronger alignment to rubric.\n"
        "Improvement Suggestions: Add precise terminology, examples, and clearer stepwise explanation."
    )


def generate_evaluation_chat_reply(
    *,
    teacher_message: str,
    question_text: str | None,
    student_answer: str | None,
    rubric: str | None,
) -> tuple[str, str | None]:
    """Return (ai_response, provider_error)."""
    try:
        if not settings.openai_api_key:
            return _fallback_response(question_text, rubric, student_answer), "OpenAI key not configured"

        system_prompt = (
            "You are an academic evaluation assistant helping teachers grade answers fairly and consistently. "
            "Return concise plain text with sections: Suggested Marks (optional), Explanation, "
            "Constructive Feedback, Improvement Suggestions."
        )
        context_blob = {
            "question_text": question_text or "",
            "rubric": rubric or "",
            "student_answer": student_answer or "",
            "teacher_instruction": teacher_message,
        }
        user_prompt = (
            "Use this context to help teacher evaluate the answer:\n"
            f"{json.dumps(context_blob, ensure_ascii=True)}"
        )

        client = OpenAI(api_key=settings.openai_api_key, timeout=float(settings.openai_timeout_seconds))
        raw = ""
        if hasattr(client, "responses"):
            response = client.responses.create(
                model=settings.openai_model,
                temperature=0.2,
                max_output_tokens=settings.openai_max_output_tokens,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = (getattr(response, "output_text", "") or "").strip()
        else:
            response = client.chat.completions.create(
                model=settings.openai_model,
                temperature=0.2,
                max_tokens=settings.openai_max_output_tokens,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = ((response.choices[0].message.content or "") if response.choices else "").strip()

        if not raw:
            raise ValueError("Empty AI response text")
        # Remove accidental fenced blocks to keep UI clean.
        raw = re.sub(r"^```[a-zA-Z]*\n|\n```$", "", raw).strip()
        return raw[:4000], None
    except Exception as exc:
        return _fallback_response(question_text, rubric, student_answer), str(exc)[:300]
