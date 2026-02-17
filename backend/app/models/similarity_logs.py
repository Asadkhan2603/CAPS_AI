from typing import Any, Dict


def similarity_log_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "source_submission_id": document.get("source_submission_id"),
        "matched_submission_id": document.get("matched_submission_id"),
        "score": document.get("score", 0.0),
        "threshold": document.get("threshold", 0.0),
        "is_flagged": document.get("is_flagged", False),
        "created_at": document.get("created_at"),
    }
