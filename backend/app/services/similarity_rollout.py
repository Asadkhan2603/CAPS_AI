from __future__ import annotations

import re
from typing import Iterable

from app.core.config import settings


_ASCII_TOKEN_RE = re.compile(r"[a-zA-Z0-9]+")
_UNICODE_WORD_RE = re.compile(r"\w+", flags=re.UNICODE)
_LATIN_RE = re.compile(r"[A-Za-z]")
_DEVANAGARI_RE = re.compile(r"[\u0900-\u097F]")
_ROMANIZED_HINDI_HINTS = {
    "aur",
    "bhi",
    "hain",
    "ho",
    "kar",
    "karte",
    "ki",
    "ko",
    "mein",
    "par",
    "se",
    "tha",
    "thi",
    "wala",
    "wali",
}

_VALID_TOKENIZER_MODES = {"ascii_legacy", "unicode_words"}
_VALID_STOPWORD_STRATEGIES = {"english_only", "disabled", "language_aware_planned"}
_VALID_MIXED_LANGUAGE_MODES = {"keep_all_tokens", "per_script_shadow"}


def _normalize_choice(value: str, allowed: set[str], fallback: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized if normalized in allowed else fallback


def detect_language_profile(text: str) -> dict[str, int | str | bool]:
    raw = text or ""
    latin_chars = len(_LATIN_RE.findall(raw))
    devanagari_chars = len(_DEVANAGARI_RE.findall(raw))
    digit_chars = sum(1 for char in raw if char.isdigit())
    alpha_chars = sum(1 for char in raw if char.isalpha())
    lowered_tokens = [token.lower() for token in _UNICODE_WORD_RE.findall(raw) if any(char.isalpha() for char in token)]
    romanized_hindi_hint_count = sum(1 for token in lowered_tokens if token in _ROMANIZED_HINDI_HINTS)
    mixed_language_hint = bool(latin_chars and romanized_hindi_hint_count >= 2)
    primary_script = "unknown"
    if latin_chars or devanagari_chars:
        primary_script = "latin" if latin_chars >= devanagari_chars else "devanagari"
    return {
        "primary_script": primary_script,
        "mixed_script": sum(1 for count in (latin_chars, devanagari_chars) if count > 0) > 1,
        "mixed_language_hint": mixed_language_hint,
        "romanized_hindi_hint_count": romanized_hindi_hint_count,
        "latin_chars": latin_chars,
        "devanagari_chars": devanagari_chars,
        "digit_chars": digit_chars,
        "alpha_chars": alpha_chars,
    }


def resolve_tokenizer_mode_for_texts(texts: Iterable[str]) -> str:
    tokenizer_mode = _normalize_choice(settings.similarity_tokenizer_mode, _VALID_TOKENIZER_MODES, "ascii_legacy")
    profiles = [detect_language_profile(text) for text in texts if text]
    mixed_script = any(bool(profile["mixed_script"]) or bool(profile.get("mixed_language_hint")) for profile in profiles)
    any_non_latin = any(profile["primary_script"] != "latin" for profile in profiles if profile["alpha_chars"])
    if mixed_script or any_non_latin:
        return "unicode_words"
    return tokenizer_mode


def tokenize_for_similarity(text: str, tokenizer_mode: str | None = None) -> list[str]:
    tokenizer_mode = tokenizer_mode or resolve_tokenizer_mode_for_texts([text])
    if tokenizer_mode == "unicode_words":
        return [
            token.lower()
            for token in _UNICODE_WORD_RE.findall(text or "")
            if any(char.isalnum() for char in token)
        ]
    return _ASCII_TOKEN_RE.findall((text or "").lower())


def resolve_similarity_stop_words(texts: Iterable[str]) -> str | None:
    strategy = _normalize_choice(
        settings.similarity_stopword_strategy,
        _VALID_STOPWORD_STRATEGIES,
        "english_only",
    )
    if strategy == "disabled":
        return None
    profiles = [detect_language_profile(text) for text in texts if text]
    if not profiles:
        return "english" if strategy == "english_only" else None

    mixed_script = any(bool(profile["mixed_script"]) or bool(profile.get("mixed_language_hint")) for profile in profiles)
    any_non_latin = any(profile["primary_script"] != "latin" for profile in profiles if profile["alpha_chars"])
    if mixed_script or any_non_latin:
        return None
    return "english" if strategy == "english_only" else None


def should_capture_semantic_shadow(
    *,
    rank: int,
    lexical_score: float,
    threshold: float,
    raw_candidate_count: int | None = None,
) -> bool:
    if not settings.semantic_shadow_enabled:
        return False
    capture_top_n = max(0, int(settings.semantic_shadow_capture_top_n))
    if raw_candidate_count is not None and raw_candidate_count > max(1, int(settings.similarity_sync_inline_candidate_limit)):
        return lexical_score >= threshold or rank <= capture_top_n
    if lexical_score >= threshold:
        return True
    if rank <= capture_top_n:
        return True
    return lexical_score >= max(0.0, min(float(settings.semantic_shadow_min_lexical_score), 1.0))


def build_similarity_rollout_plan() -> dict[str, object]:
    tokenizer_mode = _normalize_choice(
        settings.similarity_tokenizer_mode,
        _VALID_TOKENIZER_MODES,
        "ascii_legacy",
    )
    stopword_strategy = _normalize_choice(
        settings.similarity_stopword_strategy,
        _VALID_STOPWORD_STRATEGIES,
        "english_only",
    )
    mixed_language_mode = _normalize_choice(
        settings.similarity_mixed_language_mode,
        _VALID_MIXED_LANGUAGE_MODES,
        "keep_all_tokens",
    )
    return {
        "semantic_shadow": {
            "enabled": bool(settings.semantic_shadow_enabled),
            "capture_top_n": max(0, int(settings.semantic_shadow_capture_top_n)),
            "min_lexical_score": max(0.0, min(float(settings.semantic_shadow_min_lexical_score), 1.0)),
            "cross_assignment_enabled": bool(settings.similarity_cross_assignment_enabled),
            "flagging_mode": "shadow_only",
            "calibration_thresholds": {
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
        },
        "multilingual": {
            "language_detection_enabled": bool(settings.similarity_language_detection_enabled),
            "language_detector": str(settings.similarity_language_detector or "unicode_script_heuristic"),
            "tokenizer_mode": tokenizer_mode,
            "stopword_strategy": stopword_strategy,
            "mixed_language_mode": mixed_language_mode,
            "notes": [
                "Use unicode-script heuristic detection before enabling multilingual scoring.",
                "Keep mixed-language submissions in shadow analysis until benchmark coverage is stable.",
                "Disable English stop-word filtering automatically when non-Latin or mixed scripts are detected.",
            ],
        },
        "fairness_regression": {
            "max_concise_delta": round(float(settings.fairness_gate_max_concise_delta), 2),
            "max_formula_delta": round(float(settings.fairness_gate_max_formula_delta), 2),
            "max_mixed_language_eval_delta": round(float(settings.fairness_gate_max_mixed_language_eval_delta), 2),
            "max_unicode_eval_delta": round(float(settings.fairness_gate_max_unicode_eval_delta), 2),
            "max_short_answer_delta": round(float(settings.fairness_gate_max_short_answer_delta), 2),
            "max_rubric_shape_delta": round(float(settings.fairness_gate_max_rubric_shape_delta), 2),
            "gate_mode": "regression_only",
        },
    }
