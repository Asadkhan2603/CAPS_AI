from __future__ import annotations

import re
from typing import Iterable, List, Tuple

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def normalize_text(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", (text or "").strip().lower())
    return cleaned


def compute_similarity_scores(
    source_text: str,
    candidate_texts: Iterable[tuple[str, str]],
) -> List[Tuple[str, float]]:
    source = normalize_text(source_text)
    candidates = [(submission_id, normalize_text(text)) for submission_id, text in candidate_texts if text]
    if not source or not candidates:
        return []

    corpus = [source, *[text for _, text in candidates]]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(corpus)
    source_vector = matrix[0:1]
    candidate_matrix = matrix[1:]
    scores = cosine_similarity(source_vector, candidate_matrix).flatten()

    results = []
    for (submission_id, _), score in zip(candidates, scores):
        results.append((submission_id, float(score)))
    results.sort(key=lambda item: item[1], reverse=True)
    return results
