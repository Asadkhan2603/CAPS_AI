from __future__ import annotations

from typing import Dict

from app.core.config import settings


def _heuristic_score(text: str, max_score: float) -> float:
    words = [w for w in (text or "").split() if w.strip()]
    if not words:
        return 0.0
    richness = min(len(set(words)) / max(len(words), 1), 1.0)
    length_factor = min(len(words) / 400, 1.0)
    score = (0.55 * richness + 0.45 * length_factor) * max_score
    return round(score, 2)


def generate_ai_feedback(text: str, *, max_score: float = 10.0) -> Dict[str, str | float]:
    """Deterministic local fallback used until full LLM rubric integration."""
    score = _heuristic_score(text, max_score)
    if not settings.openai_api_key:
        return {
            "score": score,
            "summary": "Fallback evaluation generated. OpenAI key not configured.",
        }

    return {
        "score": score,
        "summary": "Baseline AI evaluation generated. Replace with rubric prompt pipeline.",
    }
