from __future__ import annotations

import re
from collections import Counter
from typing import Iterable, List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from app.core.config import settings
from app.core.schema_versions import SIMILARITY_RETRIEVAL_ARTIFACT_SCHEMA_VERSION
from app.services.similarity_rollout import resolve_similarity_stop_words, tokenize_for_similarity


_SENTENCE_RE = re.compile(r"[.!?]+")
_RETRIEVAL_ARTIFACT_VERSION = f"retrieval-v{SIMILARITY_RETRIEVAL_ARTIFACT_SCHEMA_VERSION}"


def normalize_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip().lower())
    return cleaned


def tokenize_text(text: str) -> list[str]:
    return tokenize_for_similarity(text)


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


def compute_overlap_stats(
    source_text: str,
    matched_text: str,
    prompt_terms: set[str] | None = None,
) -> dict:
    source_tokens = set(tokenize_text(source_text))
    matched_tokens = set(tokenize_text(matched_text))
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
) -> list[dict]:
    prompt_terms = prompt_terms or set()
    source_sentences = split_sentences(source_text)
    matched_sentences = split_sentences(matched_text)
    if not source_sentences or not matched_sentences:
        return []

    scored_pairs: list[tuple[float, dict]] = []
    for source_sentence in source_sentences[:20]:
        source_tokens = set(tokenize_text(source_sentence))
        if not source_tokens:
            continue
        for matched_sentence in matched_sentences[:20]:
            matched_tokens = set(tokenize_text(matched_sentence))
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
    if settings.similarity_tokenizer_mode == "unicode_words" or settings.similarity_language_detection_enabled:
        vectorizer = TfidfVectorizer(
            stop_words=stop_words,
            tokenizer=tokenize_text,
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
