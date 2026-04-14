from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.core.schema_versions import SIMILARITY_RETRIEVAL_ARTIFACT_SCHEMA_VERSION
from app.services.similarity_rollout import (
    resolve_similarity_stop_words,
    resolve_tokenizer_mode_for_texts,
    tokenize_for_similarity,
)


_SENTENCE_RE = re.compile(r"[.!?]+")
_RETRIEVAL_ARTIFACT_VERSION = f"retrieval-v{SIMILARITY_RETRIEVAL_ARTIFACT_SCHEMA_VERSION}"
_GENERIC_OVERLAP_TERMS = {
    "answer",
    "analysis",
    "approach",
    "completed",
    "conclusion",
    "data",
    "design",
    "discussion",
    "experiment",
    "general",
    "implementation",
    "method",
    "model",
    "observation",
    "process",
    "report",
    "result",
    "system",
    "test",
    "testing",
    "verified",
}


def normalize_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip().lower())
    return cleaned


def tokenize_text(text: str, *, tokenizer_mode: str | None = None) -> list[str]:
    return tokenize_for_similarity(text, tokenizer_mode=tokenizer_mode)


def build_similarity_retrieval_artifact(text: str) -> dict:
    raw = (text or "").strip()
    tokens = tokenize_text(raw)
    token_counts = Counter(tokens)
    terms_limit = max(8, int(settings.similarity_retrieval_terms_limit))
    ranked_terms = sorted(token_counts.items(), key=lambda item: (-item[1], item[0]))[:terms_limit]
    return {
        "version": _RETRIEVAL_ARTIFACT_VERSION,
        "token_count": len(tokens),
        "unique_token_count": len(token_counts),
        "terms": [term for term, _ in ranked_terms],
        "char_count": len(raw),
    }


def ensure_similarity_retrieval_artifact(text: str, artifact: dict | None = None) -> dict:
    if settings.similarity_retrieval_cache_enabled and isinstance(artifact, dict):
        if (
            artifact.get("version") == _RETRIEVAL_ARTIFACT_VERSION
            and isinstance(artifact.get("terms"), list)
            and artifact.get("token_count") is not None
        ):
            return artifact
    return build_similarity_retrieval_artifact(text)


def retrieval_artifact_overlap_score(
    source_artifact: dict,
    candidate_artifact: dict,
) -> float:
    source_terms = set(source_artifact.get("terms") or [])
    candidate_terms = set(candidate_artifact.get("terms") or [])
    if not source_terms or not candidate_terms:
        return 0.0
    shared_terms = len(source_terms.intersection(candidate_terms))
    if shared_terms < max(0, int(settings.similarity_prefilter_min_shared_tokens)):
        return 0.0
    source_overlap = shared_terms / max(len(source_terms), 1)
    candidate_overlap = shared_terms / max(len(candidate_terms), 1)
    return round((0.7 * source_overlap) + (0.3 * candidate_overlap), 6)


def shortlist_similarity_candidate_ids(
    source_text: str,
    candidate_artifacts: Iterable[tuple[str, dict]],
    *,
    limit: int | None = None,
) -> List[Tuple[str, float]]:
    source_artifact = ensure_similarity_retrieval_artifact(source_text)
    scored: list[tuple[float, str]] = []
    fallback: list[str] = []
    for submission_id, artifact in candidate_artifacts:
        candidate_artifact = ensure_similarity_retrieval_artifact("", artifact)
        score = retrieval_artifact_overlap_score(source_artifact, candidate_artifact)
        if score > 0:
            scored.append((score, submission_id))
        else:
            fallback.append(submission_id)
    scored.sort(key=lambda item: item[0], reverse=True)
    shortlisted = [(submission_id, score) for score, submission_id in scored]
    if limit is None:
        limit = len(shortlisted) + len(fallback)
    if len(shortlisted) < limit:
        shortlisted.extend((submission_id, 0.0) for submission_id in fallback[: max(0, limit - len(shortlisted))])
    return shortlisted[:limit]


def split_sentences(text: str) -> list[str]:
    parts = [item.strip() for item in _SENTENCE_RE.split(text or "") if item.strip()]
    return parts


def extraction_quality_score(text: str) -> float:
    raw = (text or "").strip()
    if not raw:
        return 0.0
    tokens = tokenize_text(raw)
    token_count = len(tokens)
    char_count = len(raw)
    if token_count == 0 or char_count == 0:
        return 0.0
    token_component = min(token_count / 120.0, 1.0)
    char_component = min(char_count / 800.0, 1.0)
    return round(token_component * char_component, 3)


def token_count(text: str, *, tokenizer_mode: str | None = None) -> int:
    return len(tokenize_text(text, tokenizer_mode=tokenizer_mode))


def compute_overlap_stats(
    source_text: str,
    matched_text: str,
    prompt_terms: set[str] | None = None,
    tokenizer_mode: str | None = None,
) -> dict:
    tokenizer_mode = tokenizer_mode or resolve_tokenizer_mode_for_texts([source_text, matched_text])
    source_tokens = set(tokenize_text(source_text, tokenizer_mode=tokenizer_mode))
    matched_tokens = set(tokenize_text(matched_text, tokenizer_mode=tokenizer_mode))
    overlap_terms = source_tokens.intersection(matched_tokens)
    overlap_ratio = len(overlap_terms) / max(len(source_tokens), 1)
    prompt_terms = prompt_terms or set()
    prompt_overlap_terms = overlap_terms.intersection(prompt_terms)
    prompt_term_discount = len(prompt_overlap_terms) / max(len(overlap_terms), 1)
    effective_overlap_ratio = max(0.0, overlap_ratio * (1.0 - prompt_term_discount))
    return {
        "overlap_ratio": round(overlap_ratio, 4),
        "prompt_term_discount": round(prompt_term_discount, 4),
        "effective_overlap_ratio": round(effective_overlap_ratio, 4),
        "source_token_count": len(source_tokens),
        "matched_token_count": len(matched_tokens),
    }


def extract_top_sentence_overlaps(
    source_text: str,
    matched_text: str,
    prompt_terms: set[str] | None = None,
    max_pairs: int = 3,
    tokenizer_mode: str | None = None,
) -> list[dict]:
    prompt_terms = prompt_terms or set()
    tokenizer_mode = tokenizer_mode or resolve_tokenizer_mode_for_texts([source_text, matched_text])
    source_sentences = split_sentences(source_text)
    matched_sentences = split_sentences(matched_text)
    if not source_sentences or not matched_sentences:
        return []

    scored_pairs: list[tuple[float, dict]] = []
    for source_sentence in source_sentences[:20]:
        source_tokens = set(tokenize_text(source_sentence, tokenizer_mode=tokenizer_mode))
        if not source_tokens:
            continue
        for matched_sentence in matched_sentences[:20]:
            matched_tokens = set(tokenize_text(matched_sentence, tokenizer_mode=tokenizer_mode))
            if not matched_tokens:
                continue
            overlap_terms = source_tokens.intersection(matched_tokens)
            overlap_ratio = len(overlap_terms) / max(len(source_tokens), 1)
            prompt_overlap_terms = overlap_terms.intersection(prompt_terms)
            prompt_term_discount = len(prompt_overlap_terms) / max(len(overlap_terms), 1)
            effective_overlap_ratio = max(0.0, overlap_ratio * (1.0 - prompt_term_discount))
            scored_pairs.append(
                (
                    effective_overlap_ratio,
                    {
                        "source_sentence": source_sentence[:400],
                        "matched_sentence": matched_sentence[:400],
                        "overlap_ratio": round(overlap_ratio, 4),
                        "effective_overlap_ratio": round(effective_overlap_ratio, 4),
                    },
                )
            )
    scored_pairs.sort(key=lambda item: item[0], reverse=True)
    return [payload for _, payload in scored_pairs[:max_pairs]]


def compute_semantic_shadow_score(source_text: str, matched_text: str) -> float | None:
    source = (source_text or "").strip()
    matched = (matched_text or "").strip()
    if not source or not matched:
        return None
    vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5))
    matrix = vectorizer.fit_transform([source.lower(), matched.lower()])
    score = cosine_similarity(matrix[0:1], matrix[1:2]).flatten()[0]
    return round(max(0.0, min(1.0, float(score))), 4)


def prefilter_similarity_candidates(
    source_text: str,
    candidate_texts: Iterable[tuple[str, str]],
) -> List[Tuple[str, str]]:
    candidates = [(submission_id, text) for submission_id, text in candidate_texts if text]
    top_k = max(1, int(settings.similarity_prefilter_top_k))
    if not settings.similarity_prefilter_enabled or len(candidates) <= top_k:
        return candidates

    candidate_artifacts = [
        (submission_id, build_similarity_retrieval_artifact(text))
        for submission_id, text in candidates
    ]
    ranked_ids = [
        submission_id
        for submission_id, _score in shortlist_similarity_candidate_ids(
            source_text,
            candidate_artifacts,
            limit=top_k,
        )
    ]
    text_by_id = {submission_id: text for submission_id, text in candidates}
    return [(submission_id, text_by_id[submission_id]) for submission_id in ranked_ids if submission_id in text_by_id]


def compute_similarity_scores(
    source_text: str,
    candidate_texts: Iterable[tuple[str, str]],
) -> List[Tuple[str, float]]:
    source = normalize_text(source_text)
    candidates = [(submission_id, normalize_text(text)) for submission_id, text in candidate_texts if text]
    if not source or not candidates:
        return []

    corpus = [source, *[text for _, text in candidates]]
    stop_words = resolve_similarity_stop_words(corpus)
    tokenizer_mode = resolve_tokenizer_mode_for_texts(corpus)
    if tokenizer_mode == "unicode_words" or settings.similarity_language_detection_enabled:
        vectorizer = TfidfVectorizer(
            stop_words=stop_words,
            tokenizer=lambda value: tokenize_text(value, tokenizer_mode=tokenizer_mode),
            token_pattern=None,
            lowercase=True,
        )
    else:
        vectorizer = TfidfVectorizer(stop_words=stop_words)
    matrix = vectorizer.fit_transform(corpus)
    source_vector = matrix[0:1]
    candidate_matrix = matrix[1:]
    scores = cosine_similarity(source_vector, candidate_matrix).flatten()

    results = []
    for (submission_id, _), score in zip(candidates, scores):
        normalized_score = max(0.0, min(1.0, float(score)))
        results.append((submission_id, normalized_score))
    results.sort(key=lambda item: item[1], reverse=True)
    return results


def build_similarity_risk_signals(
    source_text: str,
    matched_text: str,
    *,
    prompt_terms: set[str] | None = None,
    overlap_stats: dict | None = None,
    evidence_excerpts: list[dict] | None = None,
    extraction_diagnostics: dict | None = None,
    language_profile: dict | None = None,
    tokenizer_mode: str | None = None,
) -> dict:
    tokenizer_mode = tokenizer_mode or resolve_tokenizer_mode_for_texts([source_text, matched_text])
    prompt_terms = prompt_terms or set()
    overlap_stats = overlap_stats or compute_overlap_stats(
        source_text,
        matched_text,
        prompt_terms=prompt_terms,
        tokenizer_mode=tokenizer_mode,
    )
    evidence_excerpts = evidence_excerpts or []
    source_tokens = set(tokenize_text(source_text, tokenizer_mode=tokenizer_mode))
    matched_tokens = set(tokenize_text(matched_text, tokenizer_mode=tokenizer_mode))
    shared_terms = source_tokens.intersection(matched_tokens)
    non_prompt_shared_terms = shared_terms.difference(prompt_terms)
    generic_shared_terms = {
        term
        for term in shared_terms
        if term in _GENERIC_OVERLAP_TERMS or len(term) <= 3
    }
    extraction_diagnostics = extraction_diagnostics or {}
    source_confidence = extraction_diagnostics.get("source", {}).get("extraction_confidence")
    matched_confidence = extraction_diagnostics.get("matched", {}).get("extraction_confidence")
    numeric_confidences = [
        float(value)
        for value in (source_confidence, matched_confidence)
        if isinstance(value, (int, float))
    ]
    min_extraction_confidence = min(numeric_confidences) if numeric_confidences else 1.0
    effective_excerpt_overlaps = [
        float(item.get("effective_overlap_ratio"))
        for item in evidence_excerpts
        if isinstance(item, dict) and isinstance(item.get("effective_overlap_ratio"), (int, float))
    ]
    min_effective_excerpt_overlap = min(effective_excerpt_overlaps) if effective_excerpt_overlaps else 0.0
    qualifying_excerpt_count = sum(
        1 for value in effective_excerpt_overlaps if value >= float(settings.similarity_min_effective_excerpt_overlap)
    )
    return {
        "prompt_overlap_ratio": round(float(overlap_stats.get("prompt_term_discount") or 0.0), 4),
        "generic_overlap_ratio": round(
            len(generic_shared_terms) / max(len(shared_terms), 1),
            4,
        ),
        "non_prompt_shared_tokens": len(non_prompt_shared_terms),
        "effective_excerpt_count": qualifying_excerpt_count,
        "min_effective_excerpt_overlap": round(min_effective_excerpt_overlap, 4),
        "min_extraction_confidence": round(float(min_extraction_confidence), 4),
        "low_extraction_block": min_extraction_confidence < float(settings.similarity_min_extraction_confidence),
        "language_mismatch": bool(
            language_profile
            and (
                language_profile.get("mixed_or_non_latin")
                or language_profile.get("source", {}).get("primary_script")
                != language_profile.get("matched", {}).get("primary_script")
            )
        ),
        "boilerplate_risk": bool(
            min(len(source_tokens), len(matched_tokens)) <= int(settings.similarity_boilerplate_token_ceiling)
            and (
                len(non_prompt_shared_terms) <= int(settings.similarity_min_non_prompt_shared_tokens)
                or len(generic_shared_terms) / max(len(shared_terms), 1)
                >= float(settings.similarity_generic_overlap_assist_threshold)
            )
        ),
    }


def classify_similarity_decision(
    *,
    lexical_score: float,
    threshold: float,
    semantic_shadow_score: float | None,
    overlap_stats: dict | None,
    risk_signals: dict,
    language_profile: dict | None,
) -> dict[str, Any]:
    overlap_stats = overlap_stats or {}
    semantic_advantage = (
        float(semantic_shadow_score) - float(lexical_score)
        if isinstance(semantic_shadow_score, (int, float))
        else 0.0
    )
    source_token_total = int(overlap_stats.get("source_token_count") or 0)
    matched_token_total = int(overlap_stats.get("matched_token_count") or 0)
    prompt_heavy = float(risk_signals.get("prompt_overlap_ratio") or 0.0) >= float(
        settings.similarity_prompt_overlap_assist_threshold
    )
    generic_heavy = float(risk_signals.get("generic_overlap_ratio") or 0.0) >= float(
        settings.similarity_generic_overlap_assist_threshold
    )
    too_short = min(source_token_total, matched_token_total) < int(settings.similarity_min_token_count)
    insufficient_non_prompt = int(risk_signals.get("non_prompt_shared_tokens") or 0) < int(
        settings.similarity_min_non_prompt_shared_tokens
    )
    weak_excerpts = (
        int(risk_signals.get("effective_excerpt_count") or 0) < 1
        or float(risk_signals.get("min_effective_excerpt_overlap") or 0.0)
        < float(settings.similarity_min_effective_excerpt_overlap)
    )
    low_extraction_block = bool(risk_signals.get("low_extraction_block"))
    min_extraction_confidence = float(risk_signals.get("min_extraction_confidence") or 1.0)
    mixed_or_non_latin = bool(language_profile and language_profile.get("mixed_or_non_latin"))
    semantic_review_candidate = bool(
        semantic_advantage >= float(settings.semantic_shadow_calibration_paraphrase_advantage_min)
        or (mixed_or_non_latin and isinstance(semantic_shadow_score, (int, float)))
        or (
            not low_extraction_block
            and min_extraction_confidence >= float(settings.similarity_borderline_extraction_confidence)
            and min_extraction_confidence < float(settings.similarity_min_extraction_confidence)
        )
    )

    if lexical_score < threshold:
        if semantic_review_candidate:
            return {
                "decision_mode": "assist_only",
                "suppression_reason": "semantic_review_candidate",
                "semantic_review_candidate": True,
            }
        return {
            "decision_mode": "suppressed",
            "suppression_reason": "below_threshold",
            "semantic_review_candidate": False,
        }

    if low_extraction_block:
        return {
            "decision_mode": "suppressed",
            "suppression_reason": "low_extraction_hold",
            "semantic_review_candidate": True,
        }
    if too_short and bool(risk_signals.get("boilerplate_risk")):
        return {
            "decision_mode": "suppressed",
            "suppression_reason": "short_generic_overlap",
            "semantic_review_candidate": False,
        }
    if prompt_heavy:
        return {
            "decision_mode": "assist_only",
            "suppression_reason": "prompt_heavy_overlap",
            "semantic_review_candidate": semantic_review_candidate,
        }
    if insufficient_non_prompt:
        return {
            "decision_mode": "suppressed",
            "suppression_reason": "insufficient_non_prompt_overlap",
            "semantic_review_candidate": semantic_review_candidate,
        }
    if weak_excerpts:
        return {
            "decision_mode": "assist_only",
            "suppression_reason": "weak_excerpt_evidence",
            "semantic_review_candidate": semantic_review_candidate,
        }
    if generic_heavy or bool(risk_signals.get("boilerplate_risk")):
        return {
            "decision_mode": "assist_only",
            "suppression_reason": "boilerplate_overlap",
            "semantic_review_candidate": semantic_review_candidate,
        }
    if mixed_or_non_latin and semantic_review_candidate:
        return {
            "decision_mode": "assist_only",
            "suppression_reason": "multilingual_manual_review",
            "semantic_review_candidate": True,
        }
    return {
        "decision_mode": "flagged",
        "suppression_reason": None,
        "semantic_review_candidate": semantic_review_candidate,
    }
