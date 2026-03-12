from __future__ import annotations

import json
import re
from typing import Dict

from openai import OpenAI

from app.core.config import settings
from app.core.observability import observability_state
from app.services.ai_runtime import AI_EVALUATION_PROMPT_VERSION, build_runtime_snapshot


ACADEMIC_TERMS = {
    "analysis",
    "approach",
    "architecture",
    "algorithm",
    "complexity",
    "design",
    "evaluation",
    "implementation",
    "model",
    "result",
    "system",
    "testing",
    "tradeoff",
    "validation",
}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z0-9]+", (text or "").lower())


def _sentence_count(text: str) -> int:
    parts = [item.strip() for item in re.split(r"[.!?]+", text or "") if item.strip()]
    return len(parts)


def _heuristic_evaluation(text: str, max_score: float) -> dict[str, float | int]:
    tokens = _tokenize(text)
    words = len(tokens)
    unique_words = len(set(tokens))
    sentences = _sentence_count(text)
    avg_sentence_len = (words / sentences) if sentences else 0.0
    lexical_diversity = (unique_words / words) if words else 0.0
    term_hits = sum(1 for token in tokens if token in ACADEMIC_TERMS)
    term_density = (term_hits / words) if words else 0.0

    coverage_component = min(words / 220.0, 1.0)
    structure_component = min(sentences / 8.0, 1.0)
    clarity_component = min(max(avg_sentence_len, 1.0) / 18.0, 1.0)
    vocabulary_component = min(lexical_diversity / 0.55, 1.0)
    academic_component = min(term_density / 0.05, 1.0)

    weighted = (
        0.30 * coverage_component
        + 0.20 * structure_component
        + 0.20 * clarity_component
        + 0.15 * vocabulary_component
        + 0.15 * academic_component
    )
    score = round(max(0.0, min(weighted, 1.0)) * max_score, 2)
    return {
        "score": score,
        "words": words,
        "sentences": sentences,
        "lexical_diversity": round(lexical_diversity, 3),
        "academic_term_hits": term_hits,
        "coverage_component": round(coverage_component, 3),
        "structure_component": round(structure_component, 3),
        "clarity_component": round(clarity_component, 3),
        "vocabulary_component": round(vocabulary_component, 3),
        "academic_component": round(academic_component, 3),
    }


def _heuristic_summary(metrics: dict[str, float | int], *, provider_state: str) -> str:
    strengths = []
    gaps = []
    if float(metrics["coverage_component"]) >= 0.7:
        strengths.append("Good response coverage")
    else:
        gaps.append("Expand answer depth with more key points")
    if float(metrics["structure_component"]) >= 0.6:
        strengths.append("Clear paragraph/sentence structure")
    else:
        gaps.append("Use clearer structure with short logical sections")
    if float(metrics["academic_component"]) >= 0.5:
        strengths.append("Uses domain vocabulary")
    else:
        gaps.append("Include subject terminology and examples")

    strengths_text = "; ".join(strengths) if strengths else "Limited measurable strengths"
    gaps_text = "; ".join(gaps) if gaps else "No major structural gaps detected"
    return (
        f"{provider_state}. "
        f"Score rationale: words={metrics['words']}, sentences={metrics['sentences']}, "
        f"lexical_diversity={metrics['lexical_diversity']}, academic_term_hits={metrics['academic_term_hits']}. "
        f"Strengths: {strengths_text}. "
        f"Gaps: {gaps_text}. "
        "Suggested improvements: add topic-specific examples, concise definitions, and a brief conclusion."
    )


def generate_ai_feedback(
    text: str,
    *,
    max_score: float = 10.0,
    runtime_settings: dict | None = None,
) -> Dict[str, str | float | None | dict]:
    """AI evaluation with OpenAI response parsing + deterministic local fallback."""
    metrics = _heuristic_evaluation(text, max_score)
    fallback_score = float(metrics["score"])
    runtime_settings = runtime_settings or {}
    provider_enabled = bool(runtime_settings.get("effective_provider_enabled", bool(settings.openai_api_key)))
    model_name = str(runtime_settings.get("openai_model") or settings.openai_model)
    timeout_seconds = float(runtime_settings.get("openai_timeout_seconds") or settings.openai_timeout_seconds)
    max_output_tokens = int(runtime_settings.get("openai_max_output_tokens") or settings.openai_max_output_tokens)
    runtime_snapshot = build_runtime_snapshot(runtime_settings)
    try:
        if not provider_enabled:
            payload = {
                "score": fallback_score,
                "summary": _heuristic_summary(metrics, provider_state="Fallback evaluation generated (OpenAI key not configured)"),
                "status": "fallback",
                "provider": "local",
                "error": None,
                "prompt_version": AI_EVALUATION_PROMPT_VERSION,
                "runtime_snapshot": runtime_snapshot,
            }
            observability_state.record_ai_generation(status="fallback", provider="local")
            return payload

        client = OpenAI(api_key=settings.openai_api_key, timeout=timeout_seconds)
        system_prompt = (
            "You evaluate student submissions. Return strict JSON only with keys "
            "`score` (number), `summary` (string), `strengths` (array of strings), "
            "`gaps` (array of strings), `suggestions` (array of strings), and "
            "`confidence` (number from 0 to 1). Score must be between 0 and 10."
        )
        user_prompt = (
            "Evaluate the following submission text. Focus on clarity, relevance, structure, "
            "and technical quality. Keep summary concise (max 80 words) and suggestions actionable.\n\n"
            f"Submission:\n{text or ''}"
        )

        raw = ""
        if hasattr(client, "responses"):
            response = client.responses.create(
                model=model_name,
                max_output_tokens=max_output_tokens,
                temperature=0.2,
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

        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        parsed = json.loads(match.group(0) if match else raw)
        ai_score = float(parsed.get("score", fallback_score))
        ai_score = round(max(0.0, min(ai_score, max_score)), 2)
        summary = str(parsed.get("summary") or "").strip()[:500]
        strengths = parsed.get("strengths") if isinstance(parsed.get("strengths"), list) else []
        gaps = parsed.get("gaps") if isinstance(parsed.get("gaps"), list) else []
        suggestions = parsed.get("suggestions") if isinstance(parsed.get("suggestions"), list) else []
        confidence = parsed.get("confidence")
        confidence_value = None
        if isinstance(confidence, (float, int)):
            confidence_value = max(0.0, min(float(confidence), 1.0))
        if not summary:
            summary = "AI evaluation generated without summary details."
        explainability_tail = (
            f" Strengths: {', '.join(str(item) for item in strengths[:3]) or 'N/A'}."
            f" Gaps: {', '.join(str(item) for item in gaps[:3]) or 'N/A'}."
            f" Suggestions: {', '.join(str(item) for item in suggestions[:3]) or 'N/A'}."
        )
        if confidence_value is not None:
            explainability_tail += f" Confidence: {round(confidence_value, 2)}."

        payload = {
            "score": ai_score,
            "summary": (summary + explainability_tail)[:1200],
            "status": "completed",
            "provider": model_name,
            "error": None,
            "prompt_version": AI_EVALUATION_PROMPT_VERSION,
            "runtime_snapshot": runtime_snapshot,
        }
        observability_state.record_ai_generation(status="completed", provider=model_name)
        return payload
    except Exception as exc:
        payload = {
            "score": fallback_score,
            "summary": _heuristic_summary(metrics, provider_state="Fallback evaluation generated due to AI provider error"),
            "status": "fallback",
            "provider": "local",
            "error": str(exc)[:300],
            "prompt_version": AI_EVALUATION_PROMPT_VERSION,
            "runtime_snapshot": runtime_snapshot,
        }
        observability_state.record_ai_generation(status="fallback", provider="local")
        return payload
