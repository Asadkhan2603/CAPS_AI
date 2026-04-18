from typing import Any, Dict

from app.core.schema_versions import SIMILARITY_LOG_SCHEMA_VERSION, normalize_schema_version
from app.services.semantic_rollout_readiness import calibration_eligible, language_bucket_for_row


def _stringify_reference(value: Any) -> Any:
    return str(value) if value is not None else None


def _normalize_extraction_quality(value: Any) -> dict[str, float] | None:
    if isinstance(value, dict):
        normalized: dict[str, float] = {}
        for key in ("source", "matched"):
            numeric = value.get(key)
            if isinstance(numeric, (int, float)):
                normalized[key] = max(0.0, min(float(numeric), 1.0))
        return normalized or None
    if isinstance(value, (int, float)):
        score = max(0.0, min(float(value), 1.0))
        return {"source": score, "matched": score}
    if isinstance(value, str):
        quality_map = {
            "excellent": 1.0,
            "high": 0.9,
            "good": 0.75,
            "medium": 0.5,
            "moderate": 0.5,
            "low": 0.2,
            "poor": 0.1,
        }
        score = quality_map.get(value.strip().lower())
        if score is not None:
            return {"source": score, "matched": score}
    return None


def similarity_log_public(document: Dict[str, Any], *, include_evidence: bool = False) -> Dict[str, Any]:
    review_status = document.get("review_status")
    review_finalized_at = document.get("review_finalized_at")
    semantic_shadow_score = document.get("semantic_shadow_score")
    is_calibration_eligible = calibration_eligible(document)
    return {
        "id": str(document["_id"]),
        "source_submission_id": _stringify_reference(document.get("source_submission_id")),
        "matched_submission_id": _stringify_reference(document.get("matched_submission_id")),
        "source_submission_public_id": document.get("source_submission_public_id"),
        "matched_submission_public_id": document.get("matched_submission_public_id"),
        "source_assignment_id": _stringify_reference(document.get("source_assignment_id")),
        "matched_assignment_id": _stringify_reference(document.get("matched_assignment_id")),
        "source_assignment_label": document.get("source_assignment_label"),
        "matched_assignment_label": document.get("matched_assignment_label"),
        "source_submission_summary": document.get("source_submission_summary"),
        "matched_submission_summary": document.get("matched_submission_summary"),
        "source_class_id": _stringify_reference(document.get("source_class_id")),
        "matched_class_id": _stringify_reference(document.get("matched_class_id")),
        "visible_to_extensions": document.get("visible_to_extensions", []),
        "score": document.get("score", 0.0),
        "threshold": document.get("threshold", 0.0),
        "is_flagged": document.get("is_flagged", False),
        "evidence_excerpts": document.get("evidence_excerpts", []) if include_evidence else [],
        "overlap_stats": document.get("overlap_stats") if include_evidence else None,
        "extraction_quality": _normalize_extraction_quality(document.get("extraction_quality")),
        "extraction_diagnostics": document.get("extraction_diagnostics"),
        "semantic_shadow_score": semantic_shadow_score,
        "decision_mode": document.get("decision_mode"),
        "suppression_reason": document.get("suppression_reason"),
        "risk_signals": document.get("risk_signals"),
        "tokenization_mode_applied": document.get("tokenization_mode_applied"),
        "semantic_review_candidate": bool(document.get("semantic_review_candidate")),
        "match_scope": document.get("match_scope"),
        "language_profile": document.get("language_profile"),
        "candidate_count": document.get("candidate_count"),
        "cap_reached": document.get("cap_reached", False),
        "review_status": review_status,
        "review_reason_code": document.get("review_reason_code"),
        "review_notes": document.get("review_notes"),
        "reviewed_by_user_id": document.get("reviewed_by_user_id"),
        "reviewed_at": document.get("reviewed_at"),
        "review_updated_at": document.get("review_updated_at"),
        "review_finalized_at": review_finalized_at,
        "review_finalized_by_user_id": document.get("review_finalized_by_user_id"),
        "counts_toward_calibration": is_calibration_eligible,
        "calibration_eligible": is_calibration_eligible,
        "language_bucket": language_bucket_for_row(document),
        "engine_version": document.get("engine_version"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=SIMILARITY_LOG_SCHEMA_VERSION,
        ),
        "related_shadow_candidates": document.get("related_shadow_candidates", []) if include_evidence else [],
    }
