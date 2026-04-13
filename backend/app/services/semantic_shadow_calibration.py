from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.services.similarity_engine import compute_semantic_shadow_score, compute_similarity_scores


def build_default_semantic_shadow_calibration_cases() -> list[dict[str, str]]:
    return [
        {
            "id": "exact_copy",
            "expectation": "exact_match",
            "source_text": (
                "Neural network optimization uses gradient descent, validation data, "
                "and regularization to improve model generalization."
            ),
            "matched_text": (
                "Neural network optimization uses gradient descent, validation data, "
                "and regularization to improve model generalization."
            ),
        },
        {
            "id": "english_paraphrase",
            "expectation": "paraphrase_advantage",
            "source_text": (
                "Neural network optimization uses gradient descent, validation data, "
                "and regularization to improve model generalization."
            ),
            "matched_text": (
                "Improving a model often relies on weight updates from gradients, checking "
                "held-out validation results, and adding regularization so performance transfers better."
            ),
        },
        {
            "id": "mixed_language_shadow",
            "expectation": "mixed_language_advantage",
            "source_text": (
                "Neural network optimization uses gradient descent, validation data, "
                "and regularization to improve model generalization."
            ),
            "matched_text": (
                "Neural network optimization mein gradient descent, validation data, aur "
                "regularization model generalization ko improve karte hain."
            ),
        },
        {
            "id": "unrelated_control",
            "expectation": "unrelated_low",
            "source_text": (
                "Neural network optimization uses gradient descent, validation data, "
                "and regularization to improve model generalization."
            ),
            "matched_text": (
                "Campus event planning requires venue booking, poster design, volunteer "
                "scheduling, and sponsorship tracking."
            ),
        },
    ]


def _lexical_similarity_for_pair(source_text: str, matched_text: str) -> float:
    scores = compute_similarity_scores(source_text, [("candidate", matched_text)])
    if not scores:
        return 0.0
    return round(float(scores[0][1]), 4)


def _evaluate_case(case: dict[str, str]) -> dict[str, Any]:
    lexical_score = _lexical_similarity_for_pair(case["source_text"], case["matched_text"])
    semantic_shadow_score = compute_semantic_shadow_score(case["source_text"], case["matched_text"])
    semantic_value = float(semantic_shadow_score or 0.0)
    delta = round(semantic_value - lexical_score, 4)
    expectation = case["expectation"]
    failure_reason = None

    if expectation == "exact_match":
        if lexical_score < float(settings.semantic_shadow_calibration_exact_min) or semantic_value < float(
            settings.semantic_shadow_calibration_exact_min
        ):
            failure_reason = (
                "Exact-copy calibration fell below the configured minimum "
                f"{round(float(settings.semantic_shadow_calibration_exact_min), 3)}"
            )
    elif expectation == "paraphrase_advantage":
        if delta < float(settings.semantic_shadow_calibration_paraphrase_advantage_min):
            failure_reason = (
                "Paraphrase semantic advantage fell below the configured minimum "
                f"{round(float(settings.semantic_shadow_calibration_paraphrase_advantage_min), 3)}"
            )
    elif expectation == "mixed_language_advantage":
        if delta < float(settings.semantic_shadow_calibration_mixed_language_advantage_min):
            failure_reason = (
                "Mixed-language semantic advantage fell below the configured minimum "
                f"{round(float(settings.semantic_shadow_calibration_mixed_language_advantage_min), 3)}"
            )
    elif expectation == "unrelated_low":
        if semantic_value > float(settings.semantic_shadow_calibration_unrelated_max):
            failure_reason = (
                "Unrelated semantic shadow exceeded the configured maximum "
                f"{round(float(settings.semantic_shadow_calibration_unrelated_max), 3)}"
            )

    return {
        "id": case["id"],
        "expectation": expectation,
        "lexical_score": lexical_score,
        "semantic_shadow_score": round(semantic_value, 4),
        "semantic_advantage": delta,
        "passed": failure_reason is None,
        "failure_reason": failure_reason,
    }


def run_semantic_shadow_calibration() -> dict[str, Any]:
    case_results = [_evaluate_case(case) for case in build_default_semantic_shadow_calibration_cases()]
    failures = [item["failure_reason"] for item in case_results if item["failure_reason"]]
    paraphrase_advantages = [
        item["semantic_advantage"]
        for item in case_results
        if item["expectation"] in {"paraphrase_advantage", "mixed_language_advantage"}
    ]
    unrelated_controls = [item["semantic_shadow_score"] for item in case_results if item["expectation"] == "unrelated_low"]
    exact_scores = [
        min(item["lexical_score"], item["semantic_shadow_score"])
        for item in case_results
        if item["expectation"] == "exact_match"
    ]

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generated_thresholds": {
            "exact_min": round(float(settings.semantic_shadow_calibration_exact_min), 3),
            "paraphrase_advantage_min": round(
                float(settings.semantic_shadow_calibration_paraphrase_advantage_min),
                3,
            ),
            "mixed_language_advantage_min": round(
                float(settings.semantic_shadow_calibration_mixed_language_advantage_min),
                3,
            ),
            "unrelated_max": round(float(settings.semantic_shadow_calibration_unrelated_max), 3),
        },
        "summary": {
            "case_count": len(case_results),
            "passed_count": sum(1 for item in case_results if item["passed"]),
            "failed_count": len(failures),
            "min_exact_alignment": round(min(exact_scores or [0.0]), 4),
            "min_semantic_advantage": round(min(paraphrase_advantages or [0.0]), 4),
            "max_unrelated_shadow": round(max(unrelated_controls or [0.0]), 4),
        },
        "recommendations": {
            "keep_shadow_only": True,
            "next_focus": "Compare stored shadow scores against reviewer-confirmed cases before semantic promotion.",
            "recommended_semantic_advantage_trigger": round(min(paraphrase_advantages or [0.15]), 4),
        },
        "gates": {
            "passed": not failures,
            "failures": failures,
        },
        "cases": case_results,
    }
