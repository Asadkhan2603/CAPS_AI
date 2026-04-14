from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.ai_evaluation import compute_heuristic_evaluation_metrics
from app.services.evaluation_ai_module import build_ai_insight


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
        "concise_technical_bullets": (
            "Gradient updates. Validation checks. L2 regularization. Early stopping."
        ),
        "verbose_technical_paragraph": (
            "Model optimization applies iterative gradient updates, tracks validation quality every epoch, "
            "uses L2 regularization to reduce overfitting risk, and applies early stopping when the "
            "generalization gap starts widening."
        ),
        "english_equivalent_short": (
            "Optimization improves with gradient updates, validation monitoring, and regularization."
        ),
        "non_latin_equivalent_short": (
            "अप्टिमाइज़ेशन ग्रेडिएंट अपडेट, वैलिडेशन मॉनिटरिंग, और रेगुलराइज़ेशन से बेहतर होता है।"
        ),
        "code_snippet_answer": (
            "for epoch in range(E): w -= lr * grad(loss); if val_loss > best: stop; loss += lambda_l2 * norm(w)"
        ),
        "code_prose_equivalent": (
            "Each epoch updates weights by the loss gradient, monitors validation loss for early stopping, "
            "and applies L2 regularization to stabilize generalization."
        ),
    }


def _score_text(text: str) -> float:
    metrics = compute_heuristic_evaluation_metrics(text, max_score=10.0)
    return round(float(metrics["score"]), 2)


def _default_check(
    *,
    check_id: str,
    baseline_score: float,
    comparison_score: float,
    delta: float,
    max_allowed_delta: float,
    notes: str,
    bucket: str,
) -> dict[str, Any]:
    return {
        "id": check_id,
        "baseline_score": baseline_score,
        "comparison_score": comparison_score,
        "delta": round(float(delta), 2),
        "max_allowed_delta": round(float(max_allowed_delta), 2),
        "notes": notes,
        "bucket": bucket,
        "source": "default",
    }


def _build_default_checks(scores: dict[str, float]) -> list[dict[str, Any]]:
    checks = [
        _default_check(
            check_id="concise_vs_verbose",
            baseline_score=scores["concise_answer"],
            comparison_score=scores["verbose_answer"],
            delta=scores["verbose_answer"] - scores["concise_answer"],
            max_allowed_delta=float(settings.fairness_gate_max_concise_delta),
            notes="Verbose detail can help, but concise correct answers should not be heavily penalized.",
            bucket="concise_vs_verbose",
        ),
        _default_check(
            check_id="formula_vs_prose",
            baseline_score=scores["formula_heavy_answer"],
            comparison_score=scores["prose_formula_answer"],
            delta=scores["prose_formula_answer"] - scores["formula_heavy_answer"],
            max_allowed_delta=float(settings.fairness_gate_max_formula_delta),
            notes="Formula-heavy technical answers should stay within a limited penalty band.",
            bucket="formula_vs_prose",
        ),
        _default_check(
            check_id="english_vs_mixed_language",
            baseline_score=scores["english_answer"],
            comparison_score=scores["mixed_language_answer"],
            delta=abs(scores["english_answer"] - scores["mixed_language_answer"]),
            max_allowed_delta=float(settings.fairness_gate_max_mixed_language_eval_delta),
            notes="Mixed-language phrasing should not drift far from the equivalent English answer.",
            bucket="multilingual",
        ),
        _default_check(
            check_id="mixed_language_vs_unicode_script",
            baseline_score=scores["mixed_language_answer"],
            comparison_score=scores["unicode_mixed_script_answer"],
            delta=abs(scores["mixed_language_answer"] - scores["unicode_mixed_script_answer"]),
            max_allowed_delta=float(settings.fairness_gate_max_unicode_eval_delta),
            notes="Unicode-tokenized multilingual answers should remain close to transliterated mixed-language answers.",
            bucket="multilingual",
        ),
        _default_check(
            check_id="short_correct_vs_expanded_correct",
            baseline_score=scores["short_correct_answer"],
            comparison_score=scores["short_expanded_answer"],
            delta=scores["short_expanded_answer"] - scores["short_correct_answer"],
            max_allowed_delta=float(settings.fairness_gate_max_short_answer_delta),
            notes="Short correct answers can score slightly lower, but not enough to punish brevity unfairly.",
            bucket="short_answer",
        ),
        _default_check(
            check_id="rubric_bullets_vs_rubric_prose",
            baseline_score=scores["rubric_bullet_answer"],
            comparison_score=scores["rubric_prose_answer"],
            delta=abs(scores["rubric_bullet_answer"] - scores["rubric_prose_answer"]),
            max_allowed_delta=float(settings.fairness_gate_max_rubric_shape_delta),
            notes="Rubric-shaped technical answers should stay close whether written as bullets or prose.",
            bucket="rubric_shape",
        ),
        _default_check(
            check_id="concise_bullets_vs_verbose_technical",
            baseline_score=scores["concise_technical_bullets"],
            comparison_score=scores["verbose_technical_paragraph"],
            delta=scores["verbose_technical_paragraph"] - scores["concise_technical_bullets"],
            max_allowed_delta=float(settings.fairness_gate_max_short_answer_delta),
            notes="Very concise technical bullets should remain close to expanded technical prose.",
            bucket="short_answer",
        ),
        _default_check(
            check_id="english_vs_non_latin_equivalent",
            baseline_score=scores["english_equivalent_short"],
            comparison_score=scores["non_latin_equivalent_short"],
            delta=abs(scores["english_equivalent_short"] - scores["non_latin_equivalent_short"]),
            max_allowed_delta=max(float(settings.fairness_gate_max_unicode_eval_delta), 2.25),
            notes="Non-Latin equivalent content should remain within a narrow fairness band, with a temporary buffer while multilingual fallback calibration is still assist-only.",
            bucket="multilingual",
        ),
        _default_check(
            check_id="code_snippet_vs_code_prose_equivalent",
            baseline_score=scores["code_snippet_answer"],
            comparison_score=scores["code_prose_equivalent"],
            delta=abs(scores["code_snippet_answer"] - scores["code_prose_equivalent"]),
            max_allowed_delta=float(settings.fairness_gate_max_formula_delta),
            notes="Code-like concise answers should remain near prose-equivalent technical answers.",
            bucket="technical_format",
        ),
    ]
    return checks


def _load_external_fairness_checks() -> list[dict[str, Any]]:
    dataset_path = str(settings.fairness_regression_dataset_path or "").strip()
    if not dataset_path:
        return []
    path = Path(dataset_path)
    if not path.exists() or not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    raw_pairs: list[dict[str, Any]] = []
    if isinstance(payload, list):
        raw_pairs = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        pairs = payload.get("pairs")
        if isinstance(pairs, list):
            raw_pairs = [item for item in pairs if isinstance(item, dict)]

    checks: list[dict[str, Any]] = []
    for index, pair in enumerate(raw_pairs):
        baseline_text = str(pair.get("baseline_text") or "").strip()
        comparison_text = str(pair.get("comparison_text") or "").strip()
        if not baseline_text or not comparison_text:
            continue
        baseline_score = _score_text(baseline_text)
        comparison_score = _score_text(comparison_text)
        check_id = str(pair.get("id") or f"external_pair_{index + 1}").strip()
        max_allowed_delta = float(
            pair.get("max_allowed_delta")
            if isinstance(pair.get("max_allowed_delta"), (int, float))
            else settings.fairness_gate_max_rubric_shape_delta
        )
        checks.append(
            {
                "id": check_id,
                "baseline_score": baseline_score,
                "comparison_score": comparison_score,
                "delta": round(abs(comparison_score - baseline_score), 2),
                "max_allowed_delta": round(max_allowed_delta, 2),
                "notes": str(pair.get("notes") or "External fairness dataset pair."),
                "bucket": str(pair.get("bucket") or "external"),
                "source": "external",
            }
        )
    return checks


def run_fairness_regression_suite() -> dict[str, Any]:
    cases = build_default_fairness_regression_cases()
    scores = {case_id: _score_text(text) for case_id, text in cases.items()}

    checks = _build_default_checks(scores)
    checks.extend(_load_external_fairness_checks())

    risk_separation_payload = build_ai_insight(
        submission_text=cases["english_answer"],
        attendance_percent=42,
        internal_total=17,
        grand_total=48,
        grade="C",
        runtime_settings={"effective_provider_enabled": False},
        rubric_criteria=[
            {"label": "Core concept", "max_score": 5, "keywords": ["gradient", "validation"], "notes": "Check concept accuracy."},
            {"label": "Regularization", "max_score": 5, "keywords": ["regularization"], "notes": "Look for overfitting prevention."},
        ],
    )
    academic_text = " ".join(str(item) for item in risk_separation_payload.get("ai_academic_rationale") or []).lower()
    leaked_risk_terms = [
        flag for flag in (risk_separation_payload.get("ai_risk_flags") or [])
        if str(flag).strip().lower() in academic_text
    ]
    checks.append(
        {
            "id": "risk_context_separated_from_academic_rationale",
            "baseline_score": 0.0,
            "comparison_score": float(len(leaked_risk_terms)),
            "delta": float(len(leaked_risk_terms)),
            "max_allowed_delta": round(float(settings.fairness_gate_max_risk_context_leak_delta), 2),
            "notes": "Operational risk flags should not leak into academic rationale text.",
            "bucket": "risk_context",
            "source": "default",
        }
    )

    failures: list[str] = []
    for check in checks:
        check["passed"] = bool(check["delta"] <= check["max_allowed_delta"])
        if not check["passed"]:
            failures.append(
                f"{check['id']} delta {check['delta']} exceeded {check['max_allowed_delta']}"
            )

    minimum_check_count = max(1, int(settings.fairness_regression_min_check_count))
    external_check_count = sum(1 for check in checks if str(check.get("source")) == "external")
    minimum_external_check_count = max(0, int(settings.fairness_regression_min_external_check_count))
    if len(checks) < minimum_check_count:
        failures.append(
            f"fairness check volume {len(checks)} is below minimum required {minimum_check_count}"
        )
    if external_check_count < minimum_external_check_count:
        failures.append(
            f"external fairness checks {external_check_count} are below minimum required {minimum_external_check_count}"
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
            "max_risk_context_leak_delta": round(float(settings.fairness_gate_max_risk_context_leak_delta), 2),
        },
        "scores": scores,
        "checks": checks,
        "coverage": {
            "check_count": len(checks),
            "default_check_count": sum(1 for check in checks if str(check.get("source")) != "external"),
            "external_check_count": external_check_count,
            "minimum_required_check_count": minimum_check_count,
            "minimum_required_external_check_count": minimum_external_check_count,
            "meets_minimum_check_count": len(checks) >= minimum_check_count,
            "meets_minimum_external_check_count": external_check_count >= minimum_external_check_count,
            "dataset_path": str(settings.fairness_regression_dataset_path or "") or None,
        },
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
