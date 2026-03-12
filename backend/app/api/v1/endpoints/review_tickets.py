from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import EVALUATION_SCHEMA_VERSION, REVIEW_TICKET_SCHEMA_VERSION
from app.core.security import require_roles
from app.models.review_tickets import review_ticket_public
from app.schemas.review_ticket import (
    ReviewTicketCreate,
    ReviewTicketDecision,
    ReviewTicketOut,
)
from app.services.audit import log_audit_event

router = APIRouter()


@router.get("/", response_model=List[ReviewTicketOut])
async def list_review_tickets(
    status_filter: str | None = Query(default=None, alias="status"),
    evaluation_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[ReviewTicketOut]:
    query = {}
    if status_filter:
        query["status"] = status_filter
    if evaluation_id:
        query["evaluation_id"] = evaluation_id
    if current_user.get("role") == "teacher":
        query["requested_by_user_id"] = str(current_user["_id"])

    items = await db.review_tickets.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [ReviewTicketOut(**review_ticket_public(item)) for item in items]


@router.post("/", response_model=ReviewTicketOut, status_code=status.HTTP_201_CREATED)
async def create_review_ticket(
    payload: ReviewTicketCreate,
    current_user=Depends(require_roles(["teacher"])),
) -> ReviewTicketOut:
    evaluation = await db.evaluations.find_one({"_id": parse_object_id(payload.evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evaluation not found for provided evaluation_id")
    if evaluation.get("teacher_user_id") != str(current_user["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to request reopen for this evaluation")
    if not evaluation.get("is_finalized", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evaluation is not locked")

    existing = await db.review_tickets.find_one(
        {"evaluation_id": payload.evaluation_id, "status": "pending"}
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Pending review ticket already exists")

    document = {
        "evaluation_id": payload.evaluation_id,
        "requested_by_user_id": str(current_user["_id"]),
        "reason": payload.reason.strip(),
        "status": "pending",
        "resolved_by_user_id": None,
        "resolved_at": None,
        "created_at": datetime.now(timezone.utc),
        "schema_version": REVIEW_TICKET_SCHEMA_VERSION,
    }
    result = await db.review_tickets.insert_one(document)
    created = await db.review_tickets.find_one({"_id": result.inserted_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="create_reopen_request",
        entity_type="review_ticket",
        entity_id=str(result.inserted_id),
        detail=f"Requested reopen for evaluation {payload.evaluation_id}",
    )
    return ReviewTicketOut(**review_ticket_public(created))


@router.patch("/{ticket_id}/approve", response_model=ReviewTicketOut)
async def approve_review_ticket(
    ticket_id: str,
    payload: ReviewTicketDecision,
    current_user=Depends(require_roles(["admin"])),
) -> ReviewTicketOut:
    ticket_obj_id = parse_object_id(ticket_id)
    ticket = await db.review_tickets.find_one({"_id": ticket_obj_id})
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review ticket not found")
    if ticket.get("status") != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Review ticket already resolved")

    evaluation_id = ticket.get("evaluation_id")
    await db.evaluations.update_one(
        {"_id": parse_object_id(evaluation_id)},
        {
            "$set": {
                "is_finalized": False,
                "schema_version": EVALUATION_SCHEMA_VERSION,
            }
        },
    )
    await db.review_tickets.update_one(
        {"_id": ticket_obj_id},
        {
            "$set": {
                "status": "approved",
                "resolved_by_user_id": str(current_user["_id"]),
                "resolved_at": datetime.now(timezone.utc),
                "reason": payload.reason.strip() if payload.reason else ticket.get("reason"),
                "schema_version": REVIEW_TICKET_SCHEMA_VERSION,
            }
        },
    )
    updated = await db.review_tickets.find_one({"_id": ticket_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="approve_reopen_request",
        entity_type="review_ticket",
        entity_id=ticket_id,
        detail=f"Approved reopen for evaluation {evaluation_id}",
    )
    return ReviewTicketOut(**review_ticket_public(updated))


@router.patch("/{ticket_id}/reject", response_model=ReviewTicketOut)
async def reject_review_ticket(
    ticket_id: str,
    payload: ReviewTicketDecision,
    current_user=Depends(require_roles(["admin"])),
) -> ReviewTicketOut:
    ticket_obj_id = parse_object_id(ticket_id)
    ticket = await db.review_tickets.find_one({"_id": ticket_obj_id})
    if not ticket:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review ticket not found")
    if ticket.get("status") != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Review ticket already resolved")

    await db.review_tickets.update_one(
        {"_id": ticket_obj_id},
        {
            "$set": {
                "status": "rejected",
                "resolved_by_user_id": str(current_user["_id"]),
                "resolved_at": datetime.now(timezone.utc),
                "reason": payload.reason.strip() if payload.reason else ticket.get("reason"),
                "schema_version": REVIEW_TICKET_SCHEMA_VERSION,
            }
        },
    )
    updated = await db.review_tickets.find_one({"_id": ticket_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="reject_reopen_request",
        entity_type="review_ticket",
        entity_id=ticket_id,
        detail=f"Rejected reopen for evaluation {ticket.get('evaluation_id')}",
    )
    return ReviewTicketOut(**review_ticket_public(updated))
