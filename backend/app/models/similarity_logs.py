from typing import Any, Dict

from app.core.schema_versions import SIMILARITY_LOG_SCHEMA_VERSION, normalize_schema_version


def similarity_log_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "source_submission_id": document.get("source_submission_id"),
        "matched_submission_id": document.get("matched_submission_id"),
        "source_assignment_id": document.get("source_assignment_id"),
        "matched_assignment_id": document.get("matched_assignment_id"),
        "source_class_id": document.get("source_class_id"),
        "matched_class_id": document.get("matched_class_id"),
        "visible_to_extensions": document.get("visible_to_extensions", []),
        "score": document.get("score", 0.0),
        "threshold": document.get("threshold", 0.0),
        "is_flagged": document.get("is_flagged", False),
        "engine_version": document.get("engine_version"),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=SIMILARITY_LOG_SCHEMA_VERSION,
        ),
    }
