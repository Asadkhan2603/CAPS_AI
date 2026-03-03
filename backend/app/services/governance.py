from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status

from app.core.database import db
from app.core.mongo import parse_object_id


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
        {"$set": {"key": "governance_policy", "value": current, "updated_at": _now()}},
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
            }
        },
    )
    updated = await db.admin_action_reviews.find_one({"_id": row["_id"]})
    return updated or row


async def enforce_review_approval(
    *,
    current_user: dict[str, Any],
    review_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    review_type: str = "destructive",
) -> None:
    if current_user.get("role") != "admin":
        return

    policy = await get_governance_policy()
    if review_type == "role_change":
        enabled = policy.get("role_change_approval_enabled", False)
    else:
        enabled = policy.get("two_person_rule_enabled", False)
    if not enabled:
        return

    if not review_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Approval required: provide review_id for {review_type} action",
        )

    review = await db.admin_action_reviews.find_one({"_id": parse_object_id(review_id)})
    if not review:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval review not found")
    if review.get("status") != "approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Approval review is not approved")
    if review.get("requested_by") == str(current_user.get("_id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Two-person rule violation")

    if review.get("review_type") != review_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approval type mismatch")
    if review.get("action") != action or review.get("entity_type") != entity_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approval scope mismatch")
    if entity_id and review.get("entity_id") and review.get("entity_id") != entity_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Approval entity mismatch")

    await db.admin_action_reviews.update_one(
        {"_id": review["_id"]},
        {
            "$set": {
                "status": "executed",
                "executed_by": str(current_user.get("_id")),
                "executed_at": _now(),
                "updated_at": _now(),
            }
        },
    )
