from __future__ import annotations

from datetime import datetime
from typing import Any


FINAL_REVIEW_STATUSES = {"fixed", "reopened"}
ALLOWED_CALIBRATION_MATCH_SCOPES = {
    "same_assignment_lexical",
    "same_assignment_shadow",
    "cross_assignment_shadow",
}


def normalize_match_scope(row: dict[str, Any]) -> str | None:
    raw_scope = str(row.get("match_scope") or "").strip().lower()
    if raw_scope in ALLOWED_CALIBRATION_MATCH_SCOPES:
        return raw_scope
    if raw_scope:
        return raw_scope
    if isinstance(row.get("semantic_shadow_score"), (int, float)):
        return "same_assignment_lexical" if bool(row.get("is_flagged")) else "same_assignment_shadow"
    if bool(row.get("is_flagged")):
        return "same_assignment_lexical"
    return None


def scope_bucket_for_row(row: dict[str, Any]) -> str | None:
    match_scope = normalize_match_scope(row)
    if match_scope is None:
        return None
    if match_scope == "cross_assignment_shadow":
        return "cross_assignment"
    if match_scope in {"same_assignment_shadow", "same_assignment_lexical"}:
        return "same_assignment"
    return None


def language_bucket_for_row(row: dict[str, Any]) -> str:
    profile = row.get("language_profile")
    if not isinstance(profile, dict):
        if str(row.get("tokenization_mode_applied") or "").strip().lower() == "unicode_words":
            return "mixed_transliterated"
        return "latin_only"

    source = profile.get("source") if isinstance(profile.get("source"), dict) else {}
    matched = profile.get("matched") if isinstance(profile.get("matched"), dict) else {}
    source_script = str(source.get("primary_script") or "unknown").strip().lower()
    matched_script = str(matched.get("primary_script") or "unknown").strip().lower()
    source_mixed_hint = bool(source.get("mixed_language_hint") or source.get("mixed_script"))
    matched_mixed_hint = bool(matched.get("mixed_language_hint") or matched.get("mixed_script"))

    if source_script not in {"latin", "unknown"} or matched_script not in {"latin", "unknown"}:
        return "non_latin"
    if bool(profile.get("mixed_or_non_latin")) or source_mixed_hint or matched_mixed_hint:
        return "mixed_transliterated"
    return "latin_only"


def calibration_eligible(row: dict[str, Any]) -> bool:
    review_status = str(row.get("review_status") or "").strip().lower()
    review_finalized_at = row.get("review_finalized_at")
    semantic_shadow_score = row.get("semantic_shadow_score")
    match_scope = normalize_match_scope(row)
    return (
        review_status in FINAL_REVIEW_STATUSES
        and isinstance(review_finalized_at, datetime)
        and isinstance(semantic_shadow_score, (int, float))
        and match_scope in ALLOWED_CALIBRATION_MATCH_SCOPES
    )
