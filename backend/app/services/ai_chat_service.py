from __future__ import annotations

import json
import re

from openai import OpenAI

from app.core.config import settings
from app.core.observability import observability_state
from app.services.ai_runtime import AI_CHAT_PROMPT_VERSION, build_runtime_snapshot


def _coverage_band(coverage_ratio: float) -> str:
    if coverage_ratio >= 0.7:
        return "strong"
    if coverage_ratio >= 0.4:
        return "moderate"
    return "limited"


def _answer_depth_band(answer_tokens: list[str]) -> str:
    if len(answer_tokens) >= 180:
        return "detailed"
    if len(answer_tokens) >= 70:
        return "moderate"
    return "brief"


def _fallback_response(question_text: str | None, rubric: str | None, student_answer: str | None) -> str:
    answer = (student_answer or "").strip()
    answer_tokens = re.findall(r"[a-zA-Z0-9]+", answer.lower())
    question_tokens = re.findall(r"[a-zA-Z0-9]+", (question_text or "").lower())
    rubric_tokens = re.findall(r"[a-zA-Z0-9]+", (rubric or "").lower())
    reference_terms = set(question_tokens + rubric_tokens)
    overlap = len([token for token in answer_tokens if token in reference_terms])
    coverage_ratio = (overlap / max(len(reference_terms), 1)) if reference_terms else 0.0
    coverage_band = _coverage_band(coverage_ratio)
    answer_depth = _answer_depth_band(answer_tokens)

    if not answer:
        return (
            "Fallback Review Hint: No answer text available.\n"
            "Explanation: Deterministic backup guidance was used because answer text is empty or unavailable.\n"
            "Teacher Action: Do not rely on this fallback alone for grading.\n"
            "Constructive Feedback: Ask the student to address the question directly with key concepts.\n"
            "Improvement Suggestions: Include definitions, examples, and a clear structure."
        )
    return (
        f"Fallback Review Hint: {coverage_band.title()} rubric-term coverage in a {answer_depth} response.\n"
        "Explanation: Deterministic backup guidance was generated because the primary AI provider was unavailable. "
        "This summary is based on term overlap and answer structure only.\n"
        "Teacher Action: Treat this as assistive review context, not a grading decision.\n"
        "Constructive Feedback: Improve direct alignment to rubric checkpoints and ensure each key term is explained.\n"
        "Improvement Suggestions: Use structured points, add evidence/examples, and close with a concise summary statement."
    )


def generate_evaluation_chat_reply(
    *,
    teacher_message: str,
    question_text: str | None,
    student_answer: str | None,
    rubric: str | None,
    runtime_settings: dict | None = None,
) -> tuple[str, str | None, dict]:
    """Return (ai_response, provider_error)."""
    runtime_settings = runtime_settings or {}
    provider_enabled = bool(runtime_settings.get("effective_provider_enabled", bool(settings.openai_api_key)))
    model_name = str(runtime_settings.get("openai_model") or settings.openai_model)
    timeout_seconds = float(runtime_settings.get("openai_timeout_seconds") or settings.openai_timeout_seconds)
    max_output_tokens = int(runtime_settings.get("openai_max_output_tokens") or settings.openai_max_output_tokens)
    metadata = {
        "prompt_version": AI_CHAT_PROMPT_VERSION,
        "runtime_snapshot": build_runtime_snapshot(runtime_settings),
        "provider": model_name if provider_enabled else "local",
    }
    try:
        if not provider_enabled:
            observability_state.record_ai_generation(status="fallback", provider="local")
            return _fallback_response(question_text, rubric, student_answer), "OpenAI key not configured", metadata

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

        client = OpenAI(api_key=settings.openai_api_key, timeout=timeout_seconds)
        raw = ""
        if hasattr(client, "responses"):
            response = client.responses.create(
                model=model_name,
                temperature=0.2,
                max_output_tokens=max_output_tokens,
                input=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            raw = (getattr(response, "output_text", "") or "").strip()
        else:
            response = client.chat.completions.create(
                model=model_name,
                temperature=0.2,
                max_tokens=max_output_tokens,
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
        observability_state.record_ai_generation(status="completed", provider=model_name)
        return raw[:4000], None, metadata
    except Exception as exc:
        metadata["provider"] = "local"
        observability_state.record_ai_generation(status="fallback", provider="local")
        return _fallback_response(question_text, rubric, student_answer), str(exc)[:300], metadata
