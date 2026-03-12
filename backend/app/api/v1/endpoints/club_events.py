from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import CLUB_EVENT_SCHEMA_VERSION
from app.core.security import require_roles
from app.models.club_events import club_event_public
from app.schemas.club_event import ClubEventCreate, ClubEventOut, ClubEventUpdate
from app.services.audit import log_audit_event

router = APIRouter()


def _is_admin(current_user: dict) -> bool:
    return current_user.get("role") == "admin"


def _can_manage_event(current_user: dict, club: dict) -> bool:
    if _is_admin(current_user):
        return True
    if current_user.get("role") == "teacher":
        if club.get("coordinator_user_id") == str(current_user.get("_id")):
            return True
        return "club_coordinator" in (current_user.get("extended_roles") or [])
    if current_user.get("role") == "student":
        return club.get("president_user_id") == str(current_user.get("_id"))
    return False


@router.get("/", response_model=List[ClubEventOut])
async def list_club_events(
    club_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[ClubEventOut]:
    query = {"is_deleted": {"$in": [False, None]}}
    if club_id:
        query["club_id"] = club_id
    if status_filter:
        query["status"] = status_filter
    items = await (
        db.club_events.find(query)
        .sort("created_at", -1)
        .skip(skip)
        .limit(limit)
        .to_list(length=limit)
    )
    return [ClubEventOut(**club_event_public(item)) for item in items]


@router.post("/", response_model=ClubEventOut, status_code=status.HTTP_201_CREATED)
async def create_club_event(
    payload: ClubEventCreate,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> ClubEventOut:
    club = await db.clubs.find_one({"_id": parse_object_id(payload.club_id)})
    if not club:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Club not found for provided club_id")
    if club.get("status") == "suspended":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot create event while club is suspended")
    if not _can_manage_event(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to manage this club event")

    if payload.payment_required:
        if not payload.payment_qr_image_url:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment QR image URL is required when payment is enabled",
            )
        if payload.payment_amount is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment amount is required when payment is enabled",
            )

    document = {
        "club_id": payload.club_id,
        "title": payload.title.strip(),
        "description": payload.description,
        "event_type": payload.event_type,
        "visibility": payload.visibility,
        "registration_start": payload.registration_start,
        "registration_end": payload.registration_end,
        "event_date": payload.event_date,
        "capacity": payload.capacity,
        "registration_enabled": payload.registration_enabled,
        "approval_required": payload.approval_required,
        "payment_required": payload.payment_required,
        "payment_qr_image_url": payload.payment_qr_image_url,
        "payment_amount": payload.payment_amount,
        "certificate_enabled": payload.certificate_enabled,
        "status": (
            "draft"
            if current_user.get("role") == "student"
            else ("open" if payload.registration_enabled else "closed")
        ),
        "result_summary": None,
        "created_by": str(current_user["_id"]),
        "created_at": datetime.now(timezone.utc),
        "schema_version": CLUB_EVENT_SCHEMA_VERSION,
    }
    result = await db.club_events.insert_one(document)
    created = await db.club_events.find_one({"_id": result.inserted_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="create",
        entity_type="club_event",
        entity_id=str(result.inserted_id),
        detail="Created club event",
    )
    return ClubEventOut(**club_event_public(created))


@router.put("/{event_id}", response_model=ClubEventOut)
async def update_club_event(
    event_id: str,
    payload: ClubEventUpdate,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> ClubEventOut:
    event_obj_id = parse_object_id(event_id)
    event = await db.club_events.find_one({"_id": event_obj_id})
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club event not found")
    club = await db.clubs.find_one({"_id": parse_object_id(event.get("club_id"))})
    if not club:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Club not found for event")
    if not _can_manage_event(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to manage this club event")

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if "capacity" in update_data:
        registration_count = await db.event_registrations.count_documents(
            {"event_id": event_id, "status": {"$in": ["registered", "approved"]}}
        )
        if update_data["capacity"] < registration_count:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Capacity cannot be lower than existing registrations")

    if update_data.get("status") == "open" and club.get("status") != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only active clubs can open event registrations")

    effective_registration_enabled = update_data.get("registration_enabled", event.get("registration_enabled", True))
    effective_payment_required = update_data.get("payment_required", event.get("payment_required", False))
    effective_payment_qr = update_data.get("payment_qr_image_url", event.get("payment_qr_image_url"))
    effective_payment_amount = update_data.get("payment_amount", event.get("payment_amount"))

    if not effective_registration_enabled:
        update_data["status"] = "closed"

    if effective_payment_required:
        if not effective_payment_qr:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment QR image URL is required when payment is enabled",
            )
        if effective_payment_amount is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payment amount is required when payment is enabled",
            )

    await db.club_events.update_one(
        {"_id": event_obj_id},
        {"$set": {**update_data, "schema_version": CLUB_EVENT_SCHEMA_VERSION}},
    )
    updated = await db.club_events.find_one({"_id": event_obj_id})
    return ClubEventOut(**club_event_public(updated))


@router.delete("/{event_id}")
async def delete_club_event(
    event_id: str,
    current_user=Depends(require_roles(["admin"])),
) -> dict:
    event_obj_id = parse_object_id(event_id)
    existing = await db.club_events.find_one({"_id": event_obj_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club event not found")

    result = await db.club_events.update_one(
        {"_id": event_obj_id},
        {
            "$set": {
                "is_deleted": True,
                "status": "archived",
                "deleted_at": datetime.now(timezone.utc),
                "deleted_by": str(current_user["_id"]),
                "schema_version": CLUB_EVENT_SCHEMA_VERSION,
            }
        },
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club event not found")

    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="delete",
        entity_type="club_event",
        entity_id=event_id,
        detail="Archived club event",
    )
    return {"message": "Club event deleted"}
