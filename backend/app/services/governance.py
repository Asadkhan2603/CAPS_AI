from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, cast

from fastapi import HTTPException, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import ADMIN_ACTION_REVIEW_SCHEMA_VERSION, SETTINGS_SCHEMA_VERSION
from app.services.audit import log_destructive_action_event

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def get_governance_policy() -> dict[str, Any]:
    settings_collection = getattr(db, "settings", None)
    row = None
    if settings_collection is not None:
        try:
            row = await settings_collection.find_one({"key": "governance_policy"})
        except Exception:
            row = None
    policy = (row or {}).get("value") or {}
    return {
        "two_person_rule_enabled": bool(policy.get("two_person_rule_enabled", False)),
        "role_change_approval_enabled": bool(policy.get("role_change_approval_enabled", False)),
        "retention_days_audit": int(policy.get("retention_days_audit", 365)),
        "retention_days_sessions": int(policy.get("retention_days_sessions", 90)),
    }


async def set_governance_policy(payload: dict[str, Any]) -> dict[str, Any]:
    current = await get_governance_policy()
    current.update({k: v for k, v in payload.items() if v is not None})
    settings_collection = getattr(db, "settings", None)
    if settings_collection is None:
        return current
    await settings_collection.update_one(
        {"key": "governance_policy"},
        {
            "$set": {
                "key": "governance_policy",
                "value": current,
                "updated_at": _now(),
                "schema_version": SETTINGS_SCHEMA_VERSION,
            }
        },
        upsert=True,
    )
    return current


async def create_admin_review(
    *,
    requested_by: str,
    review_type: str,
    action: str,
    entity_type: str,
    entity_id: str | None,
    reason: str | None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    doc = {
        "review_type": review_type,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "reason": reason,
        "metadata": metadata or {},
        "requested_by": requested_by,
        "status": "pending",
        "created_at": _now(),
        "updated_at": _now(),
        "schema_version": ADMIN_ACTION_REVIEW_SCHEMA_VERSION,
    }
    result = await db.admin_action_reviews.insert_one(doc)
    created = await db.admin_action_reviews.find_one({"_id": result.inserted_id})
    return created or doc


async def approve_admin_review(*, review_id: str, approver_id: str, approve: bool, note: str | None = None) -> dict[str, Any]:
    row = await db.admin_action_reviews.find_one({"_id": parse_object_id(review_id)})
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found")
    if row.get("status") != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Review already processed")
    if row.get("requested_by") == approver_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Requester cannot approve own action")

    status_value = "approved" if approve else "rejected"
    await db.admin_action_reviews.update_one(
        {"_id": row["_id"]},
        {
            "$set": {
                "status": status_value,
                "reviewed_by": approver_id,
                "reviewed_at": _now(),
                "review_note": note,
                "updated_at": _now(),
                "schema_version": ADMIN_ACTION_REVIEW_SCHEMA_VERSION,
            }
        },
    )
    updated = await db.admin_action_reviews.find_one({"_id": row["_id"]})
    if updated:
        return cast(dict[str, Any], updated)
    return cast(dict[str, Any], row)


async def enforce_review_approval(
    *,
    current_user: dict[str, Any],
    review_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    review_type: str = "destructive",
) -> bool:
    actor_user_id = str(current_user.get("_id") or "") or None

    async def _log_blocked(detail: str, *, review_status: str | None = None) -> None:
        await log_destructive_action_event(
            actor_user_id=actor_user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            stage="governance_blocked",
            detail=detail,
            review_id=review_id,
            governance_required=True,
            governance_completed=False,
            outcome="blocked",
            metadata={
                "review_type": review_type,
                "review_status": review_status,
                "admin_type": current_user.get("admin_type"),
            },
            severity="high",
        )

    if current_user.get("role") != "admin":
        return False

    policy = await get_governance_policy()
    if review_type == "role_change":
        enabled = policy.get("role_change_approval_enabled", False)
    else:
        enabled = policy.get("two_person_rule_enabled", False)
    if not enabled:
        return False

    if not review_id:
        await _log_blocked("Governance approval required but review_id missing", review_status="missing_review_id")
        logger.warning(
            "Governance approval required but review_id missing",
            extra={
                "review_type": review_type,
                "action": action,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "current_user_id": str(current_user.get("_id") or ""),
            },
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Governance approval required. Provide an approved review_id before completing this action.",
        )

    review = await db.admin_action_reviews.find_one({"_id": parse_object_id(review_id)})
    if not review:
        await _log_blocked("Approval review not found", review_status="not_found")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval review not found")
    if review.get("status") != "approved":
        await _log_blocked("Approval review is not approved", review_status=str(review.get("status") or "unknown"))
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Approval review is not approved")
    if review.get("requested_by") == str(current_user.get("_id")):
        await _log_blocked("Two-person rule violation", review_status="self_approval_blocked")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Two-person rule violation")

    if review.get("review_type") != review_type:
        await _log_blocked("Approval type mismatch", review_status="type_mismatch")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approval type mismatch")
    if review.get("action") != action or review.get("entity_type") != entity_type:
        await _log_blocked("Approval scope mismatch", review_status="scope_mismatch")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approval scope mismatch")
    if entity_id and review.get("entity_id") and review.get("entity_id") != entity_id:
        await _log_blocked("Approval entity mismatch", review_status="entity_mismatch")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approval entity mismatch")

    await db.admin_action_reviews.update_one(
        {"_id": review["_id"]},
        {
            "$set": {
                "status": "executed",
                "executed_by": str(current_user.get("_id")),
                "executed_at": _now(),
                "updated_at": _now(),
                "schema_version": ADMIN_ACTION_REVIEW_SCHEMA_VERSION,
            }
        },
    )
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        stage="governance_completed",
        detail="Governance review executed for destructive action",
        review_id=review_id,
        governance_required=True,
        governance_completed=True,
        outcome="approved",
        metadata={
            "review_type": review_type,
            "review_status": "executed",
            "admin_type": current_user.get("admin_type"),
        },
        severity="medium",
    )
    return True
