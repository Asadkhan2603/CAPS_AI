from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.services.ai_evaluation import compute_heuristic_evaluation_metrics
from app.services.similarity_engine import (
    build_similarity_risk_signals,
    classify_similarity_decision,
    compute_overlap_stats,
    compute_semantic_shadow_score,
    compute_similarity_scores,
    extract_top_sentence_overlaps,
)
from app.services.similarity_rollout import resolve_tokenizer_mode_for_texts


def _lexical_similarity(source_text: str, matched_text: str) -> float:
    scores = compute_similarity_scores(source_text, [("candidate", matched_text)])
    if not scores:
        return 0.0
    return round(float(scores[0][1]), 4)


def _evaluate_similarity_case(case: dict[str, Any]) -> dict[str, Any]:
    source_text = str(case["source_text"])
    matched_text = str(case["matched_text"])
    threshold = float(case.get("threshold", settings.similarity_threshold))
    tokenizer_mode = resolve_tokenizer_mode_for_texts([source_text, matched_text])
    prompt_terms = set(case.get("prompt_terms") or [])
    lexical_score = _lexical_similarity(source_text, matched_text)
    semantic_shadow_score = compute_semantic_shadow_score(source_text, matched_text)
    overlap_stats = compute_overlap_stats(
        source_text,
        matched_text,
        prompt_terms=prompt_terms,
        tokenizer_mode=tokenizer_mode,
    )
    evidence_excerpts = extract_top_sentence_overlaps(
        source_text,
        matched_text,
        prompt_terms=prompt_terms,
        max_pairs=3,
        tokenizer_mode=tokenizer_mode,
    )
    extraction_diagnostics = case.get("extraction_diagnostics") or {
        "source": {"extraction_confidence": 1.0, "low_text_reason": None},
        "matched": {"extraction_confidence": 1.0, "low_text_reason": None},
    }
    language_profile = case.get("language_profile") or {
        "source": {"primary_script": "latin", "mixed_script": False},
        "matched": {"primary_script": "latin", "mixed_script": False},
        "mixed_or_non_latin": tokenizer_mode == "unicode_words",
    }
    risk_signals = build_similarity_risk_signals(
        source_text,
        matched_text,
        prompt_terms=prompt_terms,
        overlap_stats=overlap_stats,
        evidence_excerpts=evidence_excerpts,
        extraction_diagnostics=extraction_diagnostics,
        language_profile=language_profile,
        tokenizer_mode=tokenizer_mode,
    )
    decision = classify_similarity_decision(
        lexical_score=lexical_score,
        threshold=threshold,
        semantic_shadow_score=semantic_shadow_score,
        overlap_stats=overlap_stats,
        risk_signals=risk_signals,
        language_profile=language_profile,
    )

    failures: list[str] = []
    expected_mode = case.get("expected_decision_mode")
    if expected_mode and decision.get("decision_mode") != expected_mode:
        failures.append(
            f"expected decision_mode={expected_mode} but saw {decision.get('decision_mode')}"
        )
    if case.get("expect_not_flagged") and decision.get("decision_mode") == "flagged":
        failures.append("expected case not to auto-flag")
    if case.get("expect_semantic_review_candidate") and not decision.get("semantic_review_candidate"):
        failures.append("expected semantic_review_candidate=true")
    if case.get("expected_tokenization_mode") and tokenizer_mode != case.get("expected_tokenization_mode"):
        failures.append(
            f"expected tokenization_mode={case.get('expected_tokenization_mode')} but saw {tokenizer_mode}"
        )
    expected_suppression_reason = case.get("expected_suppression_reason")
    if expected_suppression_reason and decision.get("suppression_reason") != expected_suppression_reason:
        failures.append(
            f"expected suppression_reason={expected_suppression_reason} but saw {decision.get('suppression_reason')}"
        )

    return {
        "id": case["id"],
        "kind": "similarity",
        "source": str(case.get("source") or "default"),
        "bucket": str(case.get("bucket") or "similarity"),
        "lexical_score": lexical_score,
        "semantic_shadow_score": round(float(semantic_shadow_score or 0.0), 4),
        "decision_mode": decision.get("decision_mode"),
        "suppression_reason": decision.get("suppression_reason"),
        "semantic_review_candidate": bool(decision.get("semantic_review_candidate")),
        "tokenization_mode_applied": tokenizer_mode,
        "risk_signals": risk_signals,
        "passed": not failures,
        "failure_reason": "; ".join(failures) if failures else None,
    }


def _evaluate_evaluation_case(case: dict[str, Any]) -> dict[str, Any]:
    baseline_score = round(float(compute_heuristic_evaluation_metrics(case["baseline_text"], max_score=10.0)["score"]), 2)
    comparison_score = round(float(compute_heuristic_evaluation_metrics(case["comparison_text"], max_score=10.0)["score"]), 2)
    delta = round(abs(comparison_score - baseline_score), 2)
    max_allowed_delta = round(float(case["max_allowed_delta"]), 2)
    passed = bool(delta <= max_allowed_delta)
    return {
        "id": case["id"],
        "kind": "evaluation",
        "source": str(case.get("source") or "default"),
        "bucket": str(case.get("bucket") or "evaluation"),
        "baseline_score": baseline_score,
        "comparison_score": comparison_score,
        "delta": delta,
        "max_allowed_delta": max_allowed_delta,
        "passed": passed,
        "failure_reason": None if passed else f"delta {delta} exceeded {max_allowed_delta}",
    }


def build_default_false_positive_negative_cases() -> list[dict[str, Any]]:
    return [
        {
            "id": "prompt_heavy_original",
            "source": "default",
            "bucket": "false_positive",
            "source_text": "Explain gradient descent, validation, and regularization in neural network training using your own words.",
            "matched_text": "The assignment asks us to explain gradient descent, validation, and regularization in neural network training using our own words.",
            "prompt_terms": {"explain", "gradient", "descent", "validation", "regularization", "neural", "network", "training"},
            "expect_not_flagged": True,
            "expected_decision_mode": "assist_only",
            "expected_suppression_reason": "prompt_heavy_overlap",
        },
        {
            "id": "short_generic_boilerplate",
            "source": "default",
            "bucket": "false_positive",
            "source_text": "I completed the experiment and verified the result.",
            "matched_text": "I completed the experiment and verified the result.",
            "prompt_terms": {"experiment", "result"},
            "expect_not_flagged": True,
            "expected_decision_mode": "suppressed",
            "expected_suppression_reason": "short_generic_overlap",
        },
        {
            "id": "paraphrased_copy",
            "source": "default",
            "bucket": "false_negative",
            "source_text": "Neural network optimization uses gradient descent, validation data, and regularization to improve model generalization.",
            "matched_text": "Improving a model often relies on weight updates from gradients, checking held-out validation results, and adding regularization so performance transfers better.",
            "expect_semantic_review_candidate": True,
            "expected_decision_mode": "assist_only",
            "expected_suppression_reason": "semantic_review_candidate",
        },
        {
            "id": "mixed_language_copy",
            "source": "default",
            "bucket": "false_negative",
            "source_text": "Neural network optimization uses gradient descent, validation data, and regularization to improve model generalization.",
            "matched_text": "Neural network optimization mein gradient descent, validation data, aur regularization model generalization ko improve karte hain.",
            "expect_semantic_review_candidate": True,
            "expected_decision_mode": "assist_only",
            "expected_tokenization_mode": "unicode_words",
        },
        {
            "id": "low_text_extraction_hold",
            "source": "default",
            "bucket": "false_negative",
            "source_text": "Gradient descent uses validation data and regularization to improve generalization.",
            "matched_text": "Gradient descent uses validation data and regularization to improve generalization.",
            "expect_not_flagged": True,
            "expected_decision_mode": "suppressed",
            "expected_suppression_reason": "low_extraction_hold",
            "extraction_diagnostics": {
                "source": {"extraction_confidence": 0.22, "low_text_reason": "empty_pdf_text"},
                "matched": {"extraction_confidence": 0.91, "low_text_reason": None},
            },
        },
        {
            "id": "formula_heavy_fairness",
            "kind": "evaluation",
            "source": "default",
            "bucket": "fairness",
            "baseline_text": "y_hat = wx + b. loss = mse(y, y_hat). update w using gradient descent and regularization with validation checks.",
            "comparison_text": "A model predicts outputs from weighted inputs, measures error with mean squared loss, updates weights through gradient descent, and uses regularization plus validation checks to improve generalization.",
            "max_allowed_delta": float(settings.fairness_gate_max_formula_delta),
        },
        {
            "id": "high_lexical_strong_evidence_flagged",
            "source": "default",
            "bucket": "true_positive",
            "source_text": (
                "Gradient descent adjusts model parameters iteratively while validation loss and regularization terms "
                "are monitored each epoch to preserve generalization quality."
            ),
            "matched_text": (
                "Gradient descent adjusts model parameters iteratively while validation loss and regularization terms "
                "are monitored each epoch to preserve generalization quality."
            ),
            "expected_decision_mode": "flagged",
        },
        {
            "id": "multilingual_non_latin_semantic_candidate",
            "source": "default",
            "bucket": "false_negative",
            "source_text": "Neural optimization improves with gradient updates, validation checks, and regularization.",
            "matched_text": "न्यूरल ऑप्टिमाइजेशन में ग्रेडिएंट अपडेट, वैलिडेशन चेक और रेगुलराइजेशन से बेहतर जनरलाइजेशन मिलता है।",
            "threshold": 0.95,
            "expect_semantic_review_candidate": True,
            "expected_decision_mode": "assist_only",
            "expected_suppression_reason": "semantic_review_candidate",
        },
        {
            "id": "concise_vs_verbose_fairness_pair",
            "kind": "evaluation",
            "source": "default",
            "bucket": "fairness",
            "baseline_text": "Gradient descent with validation and regularization improves generalization.",
            "comparison_text": (
                "Neural network optimization uses gradient descent for iterative updates, validates progress on held-out data, "
                "and applies regularization to reduce overfitting and improve generalization quality."
            ),
            "max_allowed_delta": float(settings.fairness_gate_max_short_answer_delta),
        },
        {
            "id": "unicode_vs_english_eval_pair",
            "kind": "evaluation",
            "source": "default",
            "bucket": "fairness",
            "baseline_text": "Optimization uses gradient descent, validation checks, and regularization.",
            "comparison_text": "ऑप्टिमाइजेशन ग्रेडिएंट डिसेंट, वैलिडेशन चेक और रेगुलराइजेशन से बेहतर होता है।",
            "max_allowed_delta": max(float(settings.fairness_gate_max_unicode_eval_delta), 2.25),
        },
    ]


def _load_external_cases() -> list[dict[str, Any]]:
    dataset_path = str(settings.false_positive_negative_dataset_path or "").strip()
    if not dataset_path:
        return []
    path = Path(dataset_path)
    if not path.exists() or not path.is_file():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []

    raw_cases: list[dict[str, Any]] = []
    if isinstance(payload, list):
        raw_cases = [item for item in payload if isinstance(item, dict)]
    elif isinstance(payload, dict):
        cases = payload.get("cases")
        if isinstance(cases, list):
            raw_cases = [item for item in cases if isinstance(item, dict)]

    output: list[dict[str, Any]] = []
    for index, case in enumerate(raw_cases):
        case_id = str(case.get("id") or f"external_case_{index + 1}").strip()
        kind = str(case.get("kind") or "similarity").strip().lower()
        if kind not in {"similarity", "evaluation"}:
            continue
        hydrated = {
            **case,
            "id": case_id,
            "kind": kind,
            "source": "external",
            "bucket": str(case.get("bucket") or ("fairness" if kind == "evaluation" else "external_similarity")),
        }
        if kind == "evaluation":
            if not str(hydrated.get("baseline_text") or "").strip():
                continue
            if not str(hydrated.get("comparison_text") or "").strip():
                continue
            if not isinstance(hydrated.get("max_allowed_delta"), (int, float)):
                hydrated["max_allowed_delta"] = float(settings.fairness_gate_max_formula_delta)
        else:
            if not str(hydrated.get("source_text") or "").strip():
                continue
            if not str(hydrated.get("matched_text") or "").strip():
                continue
        output.append(hydrated)
    return output


def run_false_positive_negative_regression_suite() -> dict[str, Any]:
    cases = [*build_default_false_positive_negative_cases(), *_load_external_cases()]
    results: list[dict[str, Any]] = []
    failures: list[str] = []

    for case in cases:
        if case.get("kind") == "evaluation":
            result = _evaluate_evaluation_case(case)
        else:
            result = _evaluate_similarity_case(case)
        results.append(result)
        if not result["passed"]:
            failures.append(f"{result['id']}: {result['failure_reason']}")

    total_case_count = len(results)
    external_case_count = sum(1 for item in results if str(item.get("source")) == "external")
    minimum_case_count = max(1, int(settings.false_positive_negative_min_case_count))
    minimum_external_case_count = max(0, int(settings.false_positive_negative_min_external_case_count))
    if total_case_count < minimum_case_count:
        failures.append(
            f"regression case volume {total_case_count} is below minimum required {minimum_case_count}"
        )
    if external_case_count < minimum_external_case_count:
        failures.append(
            f"external regression cases {external_case_count} are below minimum required {minimum_external_case_count}"
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "thresholds": {
            "similarity_threshold": round(float(settings.similarity_threshold), 2),
            "semantic_advantage_trigger": round(float(settings.semantic_shadow_calibration_paraphrase_advantage_min), 2),
            "min_effective_excerpt_overlap": round(float(settings.similarity_min_effective_excerpt_overlap), 2),
            "min_non_prompt_shared_tokens": int(settings.similarity_min_non_prompt_shared_tokens),
            "min_extraction_confidence": round(float(settings.similarity_min_extraction_confidence), 2),
            "max_formula_delta": round(float(settings.fairness_gate_max_formula_delta), 2),
        },
        "cases": results,
        "coverage": {
            "case_count": total_case_count,
            "default_case_count": sum(1 for item in results if str(item.get("source")) != "external"),
            "external_case_count": external_case_count,
            "minimum_required_case_count": minimum_case_count,
            "minimum_required_external_case_count": minimum_external_case_count,
            "meets_minimum_case_count": total_case_count >= minimum_case_count,
            "meets_minimum_external_case_count": external_case_count >= minimum_external_case_count,
            "dataset_path": str(settings.false_positive_negative_dataset_path or "") or None,
        },
        "summary": {
            "case_count": len(results),
            "passed_count": sum(1 for item in results if item["passed"]),
            "failed_count": len(failures),
            "flagged_count": sum(1 for item in results if item.get("decision_mode") == "flagged"),
            "assist_only_count": sum(1 for item in results if item.get("decision_mode") == "assist_only"),
            "suppressed_count": sum(1 for item in results if item.get("decision_mode") == "suppressed"),
        },
        "recommendations": {
            "keep_semantic_shadow_review_only": True,
            "next_focus": "Validate these decision-mode protections against real reviewer outcomes before any threshold promotion.",
        },
        "gates": {
            "passed": not failures,
            "failures": failures,
        },
    }
