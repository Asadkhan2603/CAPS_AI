from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import List

from bson import ObjectId
from fastapi import APIRouter, Depends, Query

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission
from app.schemas.governance import (
    AdminActionReviewCreate,
    AdminActionReviewDecision,
    AdminActionReviewOut,
    GovernancePolicyUpdate,
)
from app.services.audit import log_audit_event
from app.services.governance import (
    approve_admin_review,
    create_admin_review,
    get_governance_policy,
    set_governance_policy,
)

router = APIRouter()


def _review_public(row: dict) -> AdminActionReviewOut:
    return AdminActionReviewOut(
        id=str(row.get("_id")),
        review_type=row.get("review_type"),
        action=row.get("action"),
        entity_type=row.get("entity_type"),
        entity_id=row.get("entity_id"),
        reason=row.get("reason"),
        status=row.get("status"),
        requested_by=row.get("requested_by"),
        reviewed_by=row.get("reviewed_by"),
        reviewed_at=row.get("reviewed_at"),
        executed_by=row.get("executed_by"),
        executed_at=row.get("executed_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


@router.get("/policy")
async def get_policy(
    _current_user=Depends(require_permission("system.read")),
) -> dict:
    return {"policy": await get_governance_policy()}


@router.patch("/policy")
async def update_policy(
    payload: GovernancePolicyUpdate,
    current_user=Depends(require_permission("system.read")),
) -> dict:
    updated = await set_governance_policy(payload.model_dump(exclude_none=True))
    await log_audit_event(
        actor_user_id=str(current_user.get("_id")),
        action="update",
        action_type="governance_policy_update",
        entity_type="governance_policy",
        entity_id="global",
        detail="Updated governance policy",
        new_value=updated,
        severity="high",
    )
    return {"policy": updated}


@router.post("/reviews", response_model=AdminActionReviewOut)
async def create_review(
    payload: AdminActionReviewCreate,
    current_user=Depends(require_permission("system.read")),
) -> AdminActionReviewOut:
    created = await create_admin_review(
        requested_by=str(current_user.get("_id")),
        review_type=payload.review_type,
        action=payload.action,
        entity_type=payload.entity_type,
        entity_id=payload.entity_id,
        reason=payload.reason,
        metadata=payload.metadata,
    )
    return _review_public(created)


@router.get("/reviews", response_model=List[AdminActionReviewOut])
async def list_reviews(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=100, ge=1, le=500),
    _current_user=Depends(require_permission("system.read")),
) -> List[AdminActionReviewOut]:
    query = {}
    if status_filter:
        query["status"] = status_filter
    rows = await db.admin_action_reviews.find(query).sort("created_at", -1).limit(limit).to_list(length=limit)
    return [_review_public(row) for row in rows]


@router.patch("/reviews/{review_id}", response_model=AdminActionReviewOut)
async def decide_review(
    review_id: str,
    payload: AdminActionReviewDecision,
    current_user=Depends(require_permission("system.read")),
) -> AdminActionReviewOut:
    updated = await approve_admin_review(
        review_id=review_id,
        approver_id=str(current_user.get("_id")),
        approve=payload.approve,
        note=payload.note,
    )
    await log_audit_event(
        actor_user_id=str(current_user.get("_id")),
        action="approve" if payload.approve else "reject",
        action_type="admin_review_decision",
        entity_type="admin_action_review",
        entity_id=review_id,
        detail="Reviewed governance approval request",
        new_value={"status": updated.get("status")},
        severity="high",
    )
    return _review_public(updated)


@router.get("/dashboard")
async def governance_dashboard(
    _current_user=Depends(require_permission("system.read")),
) -> dict:
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)
    policy = await get_governance_policy()
    pending_reviews = await db.admin_action_reviews.count_documents({"status": "pending"})
    approved_reviews_24h = await db.admin_action_reviews.count_documents(
        {"status": "approved", "reviewed_at": {"$gte": day_ago}}
    )
    anomalies_24h = await db.audit_logs.count_documents(
        {"action_type": "login_anomaly", "created_at": {"$gte": day_ago}}
    )
    locked_accounts = await db.users.count_documents({"lockout_until": {"$gte": now}})
    return {
        "timestamp": now,
        "policy": policy,
        "pending_reviews": pending_reviews,
        "approved_reviews_24h": approved_reviews_24h,
        "login_anomalies_24h": anomalies_24h,
        "locked_accounts": locked_accounts,
    }


@router.get("/sessions")
async def list_sessions(
    status_filter: str | None = Query(default=None, alias="status"),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    _current_user=Depends(require_permission("system.read")),
) -> dict:
    collection = getattr(db, "user_sessions", None)
    if collection is None:
        return {"items": [], "total": 0}

    query = {}
    if user_id:
        query["user_id"] = user_id
    if status_filter == "active":
        query["revoked_at"] = None
    elif status_filter == "revoked":
        query["revoked_at"] = {"$ne": None}

    rows = await collection.find(query).sort("created_at", -1).limit(limit).to_list(length=limit)
    user_ids = sorted({row.get("user_id") for row in rows if row.get("user_id")})
    user_map = {}
    if user_ids:
        object_ids = [parse_object_id(uid) for uid in user_ids if uid and ObjectId.is_valid(uid)]
        users = await db.users.find({"_id": {"$in": object_ids}}, {"full_name": 1, "email": 1}).to_list(length=len(object_ids))
        user_map = {str(user.get("_id")): user for user in users}

    items = []
    for row in rows:
        uid = row.get("user_id")
        user = user_map.get(uid, {})
        items.append(
            {
                "id": str(row.get("_id")),
                "user_id": uid,
                "user_name": user.get("full_name"),
                "user_email": user.get("email"),
                "fingerprint": row.get("fingerprint"),
                "ip_address": row.get("ip_address") or row.get("last_seen_ip"),
                "last_seen_ip": row.get("last_seen_ip"),
                "user_agent": row.get("user_agent"),
                "created_at": row.get("created_at"),
                "last_seen_at": row.get("last_seen_at"),
                "rotated_at": row.get("rotated_at"),
                "revoked_at": row.get("revoked_at"),
                "status": "revoked" if row.get("revoked_at") else "active",
            }
        )
    return {"items": items, "total": len(items)}
