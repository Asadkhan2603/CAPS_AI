from __future__ import annotations

from typing import Any, Dict

from app.core.schema_versions import AI_EVALUATION_RUN_SCHEMA_VERSION, normalize_schema_version


def ai_evaluation_run_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(document.get("_id")),
        "evaluation_id": document.get("evaluation_id"),
        "submission_id": document.get("submission_id"),
        "actor_user_id": document.get("actor_user_id"),
        "ai_score": document.get("ai_score"),
        "ai_feedback": document.get("ai_feedback"),
        "ai_status": document.get("ai_status"),
        "ai_provider": document.get("ai_provider"),
        "ai_prompt_version": document.get("ai_prompt_version"),
        "ai_runtime_snapshot": document.get("ai_runtime_snapshot"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=AI_EVALUATION_RUN_SCHEMA_VERSION,
        ),
        "ai_confidence": document.get("ai_confidence"),
        "ai_strengths": list(document.get("ai_strengths") or []),
        "ai_gaps": list(document.get("ai_gaps") or []),
        "ai_suggestions": list(document.get("ai_suggestions") or []),
        "ai_risk_flags": list(document.get("ai_risk_flags") or []),
        "grade": document.get("grade"),
        "internal_total": document.get("internal_total"),
        "grand_total": document.get("grand_total"),
        "created_at": document.get("created_at"),
    }
