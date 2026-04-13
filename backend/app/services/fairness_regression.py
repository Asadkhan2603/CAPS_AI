from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.config import settings
from app.services.ai_evaluation import compute_heuristic_evaluation_metrics


def build_default_fairness_regression_cases() -> dict[str, str]:
    return {
        "concise_answer": (
            "Gradient descent updates weights using loss gradients, validation checks, "
            "and regularization to improve generalization."
        ),
        "verbose_answer": (
            "Neural network optimization uses gradient descent to update weights, monitors "
            "validation performance to avoid overfitting, and applies regularization so the "
            "model generalizes better across unseen examples. The optimizer follows the loss "
            "surface, checks feedback from held-out data, and adjusts learning behavior to "
            "improve stability and final accuracy."
        ),
        "formula_heavy_answer": (
            "y_hat = wx + b. loss = mse(y, y_hat). update w using gradient descent and "
            "regularization with validation checks."
        ),
        "prose_formula_answer": (
            "A model predicts outputs from weighted inputs, measures error with mean squared "
            "loss, updates weights through gradient descent, and uses regularization plus "
            "validation checks to improve generalization."
        ),
        "english_answer": (
            "Neural network optimization uses gradient descent, validation data, and "
            "regularization to improve model generalization."
        ),
        "mixed_language_answer": (
            "Neural network optimization mein gradient descent, validation data, aur "
            "regularization model generalization ko improve karte hain."
        ),
        "unicode_mixed_script_answer": (
            "न्यूरल नेटवर्क optimization mein gradient descent, validation डेटा, aur "
            "regularization model generalization ko improve karte hain."
        ),
        "short_correct_answer": (
            "Gradient descent updates weights using loss gradients and validation feedback."
        ),
        "short_expanded_answer": (
            "Gradient descent updates weights using loss gradients, checks validation feedback, "
            "and applies regularization so the model generalizes better on unseen data."
        ),
        "rubric_bullet_answer": (
            "Design: modular layers. Algorithm: backpropagation. Testing: validation split, "
            "learning-rate checks, and error analysis."
        ),
        "rubric_prose_answer": (
            "The design uses modular layers, the algorithm relies on backpropagation, and the "
            "testing plan covers validation splits, learning-rate checks, and error analysis."
        ),
    }


def _score_text(text: str) -> float:
    metrics = compute_heuristic_evaluation_metrics(text, max_score=10.0)
    return round(float(metrics["score"]), 2)


def run_fairness_regression_suite() -> dict[str, Any]:
    cases = build_default_fairness_regression_cases()
    scores = {case_id: _score_text(text) for case_id, text in cases.items()}

    checks = [
        {
            "id": "concise_vs_verbose",
            "baseline_score": scores["concise_answer"],
            "comparison_score": scores["verbose_answer"],
            "delta": round(scores["verbose_answer"] - scores["concise_answer"], 2),
            "max_allowed_delta": round(float(settings.fairness_gate_max_concise_delta), 2),
            "notes": "Verbose detail can help, but concise correct answers should not be heavily penalized.",
        },
        {
            "id": "formula_vs_prose",
            "baseline_score": scores["formula_heavy_answer"],
            "comparison_score": scores["prose_formula_answer"],
            "delta": round(scores["prose_formula_answer"] - scores["formula_heavy_answer"], 2),
            "max_allowed_delta": round(float(settings.fairness_gate_max_formula_delta), 2),
            "notes": "Formula-heavy technical answers should stay within a limited penalty band.",
        },
        {
            "id": "english_vs_mixed_language",
            "baseline_score": scores["english_answer"],
            "comparison_score": scores["mixed_language_answer"],
            "delta": round(abs(scores["english_answer"] - scores["mixed_language_answer"]), 2),
            "max_allowed_delta": round(float(settings.fairness_gate_max_mixed_language_eval_delta), 2),
            "notes": "Mixed-language phrasing should not drift far from the equivalent English answer.",
        },
        {
            "id": "mixed_language_vs_unicode_script",
            "baseline_score": scores["mixed_language_answer"],
            "comparison_score": scores["unicode_mixed_script_answer"],
            "delta": round(abs(scores["mixed_language_answer"] - scores["unicode_mixed_script_answer"]), 2),
            "max_allowed_delta": round(float(settings.fairness_gate_max_unicode_eval_delta), 2),
            "notes": "Unicode-tokenized multilingual answers should remain close to transliterated mixed-language answers.",
        },
        {
            "id": "short_correct_vs_expanded_correct",
            "baseline_score": scores["short_correct_answer"],
            "comparison_score": scores["short_expanded_answer"],
            "delta": round(scores["short_expanded_answer"] - scores["short_correct_answer"], 2),
            "max_allowed_delta": round(float(settings.fairness_gate_max_short_answer_delta), 2),
            "notes": "Short correct answers can score slightly lower, but not enough to punish brevity unfairly.",
        },
        {
            "id": "rubric_bullets_vs_rubric_prose",
            "baseline_score": scores["rubric_bullet_answer"],
            "comparison_score": scores["rubric_prose_answer"],
            "delta": round(abs(scores["rubric_bullet_answer"] - scores["rubric_prose_answer"]), 2),
            "max_allowed_delta": round(float(settings.fairness_gate_max_rubric_shape_delta), 2),
            "notes": "Rubric-shaped technical answers should stay close whether written as bullets or prose.",
        },
    ]

    failures: list[str] = []
    for check in checks:
        check["passed"] = bool(check["delta"] <= check["max_allowed_delta"])
        if not check["passed"]:
            failures.append(
                f"{check['id']} delta {check['delta']} exceeded {check['max_allowed_delta']}"
            )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "max_concise_delta": round(float(settings.fairness_gate_max_concise_delta), 2),
            "max_formula_delta": round(float(settings.fairness_gate_max_formula_delta), 2),
            "max_mixed_language_eval_delta": round(float(settings.fairness_gate_max_mixed_language_eval_delta), 2),
            "max_unicode_eval_delta": round(float(settings.fairness_gate_max_unicode_eval_delta), 2),
            "max_short_answer_delta": round(float(settings.fairness_gate_max_short_answer_delta), 2),
            "max_rubric_shape_delta": round(float(settings.fairness_gate_max_rubric_shape_delta), 2),
        },
        "scores": scores,
        "checks": checks,
        "summary": {
            "check_count": len(checks),
            "passed_count": sum(1 for item in checks if item["passed"]),
            "failed_count": len(failures),
            "max_observed_delta": round(max((item["delta"] for item in checks), default=0.0), 2),
        },
        "recommendations": {
            "keep_provider_fallback_separate": True,
            "next_focus": "Add reviewer-confirmed multilingual grading samples before raising fairness expectations.",
        },
        "gates": {
            "passed": not failures,
            "failures": failures,
        },
    }
