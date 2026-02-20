from __future__ import annotations

import json
import re
from typing import Dict

from openai import OpenAI

from app.core.config import settings


def _heuristic_score(text: str, max_score: float) -> float:
    words = [w for w in (text or "").split() if w.strip()]
    if not words:
        return 0.0
    richness = min(len(set(words)) / max(len(words), 1), 1.0)
    length_factor = min(len(words) / 400, 1.0)
    score = (0.55 * richness + 0.45 * length_factor) * max_score
    return round(score, 2)


def generate_ai_feedback(text: str, *, max_score: float = 10.0) -> Dict[str, str | float | None]:
    """AI evaluation with OpenAI response parsing + deterministic local fallback."""
    fallback_score = _heuristic_score(text, max_score)
    try:
        if not settings.openai_api_key:
            return {
                "score": fallback_score,
                "summary": "Fallback evaluation generated. OpenAI key not configured.",
                "status": "fallback",
                "provider": "local",
                "error": None,
            }

        client = OpenAI(api_key=settings.openai_api_key, timeout=float(settings.openai_timeout_seconds))
        system_prompt = (
            "You evaluate student submissions. Return strict JSON only with keys "
            "`score` (number) and `summary` (string). Score must be between 0 and 10."
        )
        user_prompt = (
            "Evaluate the following submission text. Focus on clarity, relevance, structure, "
            "and technical quality. Keep summary concise (max 80 words).\n\n"
            f"Submission:\n{text or ''}"
        )

        raw = ""
        if hasattr(client, "responses"):
            response = client.responses.create(
                model=settings.openai_model,
                max_output_tokens=settings.openai_max_output_tokens,
                temperature=0.2,
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

        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        parsed = json.loads(match.group(0) if match else raw)
        ai_score = float(parsed.get("score", fallback_score))
        ai_score = round(max(0.0, min(ai_score, max_score)), 2)
        summary = str(parsed.get("summary") or "").strip()[:800]
        if not summary:
            summary = "AI evaluation generated without summary details."

        return {
            "score": ai_score,
            "summary": summary,
            "status": "completed",
            "provider": settings.openai_model,
            "error": None,
        }
    except Exception as exc:
        return {
            "score": fallback_score,
            "summary": "Fallback evaluation generated due to AI provider error.",
            "status": "fallback",
            "provider": "local",
            "error": str(exc)[:300],
        }
