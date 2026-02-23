from datetime import datetime, timedelta, timezone
from typing import Any, List

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.clubs import club_application_public, club_member_public, club_public
from app.schemas.club import (
    ClubAnalyticsOut,
    ClubApplicationOut,
    ClubApplicationReview,
    ClubCreate,
    ClubMembershipOut,
    ClubMembershipUpdate,
    ClubOut,
    ClubUpdate,
)
from app.services.audit import log_audit_event

router = APIRouter()


async def _resolve_user(user_id: str | None) -> dict[str, Any] | None:
    if not user_id:
        return None
    if not ObjectId.is_valid(user_id):
        return None
    try:
        return await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception:
        return None


def _is_admin(user: dict[str, Any]) -> bool:
    return user.get("role") == "admin"


def _is_teacher(user: dict[str, Any]) -> bool:
    return user.get("role") == "teacher"


def _teacher_has_extension(user: dict[str, Any], extension: str) -> bool:
    return extension in (user.get("extended_roles") or [])


async def _can_manage_club(user: dict[str, Any], club: dict[str, Any]) -> bool:
    if _is_admin(user):
        return True
    if not _is_teacher(user):
        return False
    if club.get("coordinator_user_id") == str(user.get("_id")):
        return True
    return _teacher_has_extension(user, "club_coordinator")


async def _can_view_members(user: dict[str, Any], club: dict[str, Any]) -> bool:
    if await _can_manage_club(user, club):
        return True
    if club.get("president_user_id") == str(user.get("_id")):
        return True
    return False


async def _ensure_club(club_id: str) -> dict[str, Any]:
    club = await db.clubs.find_one({"_id": parse_object_id(club_id)})
    if not club:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Club not found")
    return club


async def _enrich_club_document(document: dict[str, Any]) -> dict[str, Any]:
    row = dict(document)
    coordinator = await _resolve_user(row.get("coordinator_user_id"))
    president = await _resolve_user(row.get("president_user_id"))
    row["coordinator_name"] = coordinator.get("full_name") if coordinator else None
    row["coordinator_email"] = coordinator.get("email") if coordinator else None
    row["president_name"] = president.get("full_name") if president else None
    row["president_email"] = president.get("email") if president else None
    try:
        row["member_count"] = await db.club_members.count_documents(
            {"club_id": str(row.get("_id")), "status": "active"}
        )
    except Exception:
        row["member_count"] = 0
    return row


@router.get("/", response_model=List[ClubOut])
async def list_clubs(
    status_filter: str | None = Query(default=None, alias="status"),
    is_active: bool | None = Query(default=None),
    registration_open: bool | None = Query(default=None),
    academic_year: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[ClubOut]:
    query: dict[str, Any] = {}

    if status_filter:
        query["status"] = status_filter
    if academic_year:
        query["academic_year"] = academic_year
    if registration_open is not None:
        query["registration_open"] = registration_open

    if is_active is not None:
        if is_active:
            query["status"] = {"$in": ["draft", "active"]}
        else:
            query["status"] = {"$in": ["closed", "suspended", "archived"]}

    if current_user.get("role") == "student":
        query.setdefault("status", {"$nin": ["draft"]})

    items = await db.clubs.find(query).sort("updated_at", -1).skip(skip).limit(limit).to_list(length=limit)

    enriched = [await _enrich_club_document(item) for item in items]
    return [ClubOut(**club_public(item)) for item in enriched]


@router.post("/", response_model=ClubOut, status_code=status.HTTP_201_CREATED)
async def create_club(
    payload: ClubCreate,
    current_user=Depends(require_roles(["admin"])),
) -> ClubOut:
    if payload.coordinator_user_id:
        teacher = await _resolve_user(payload.coordinator_user_id)
        if not teacher:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coordinator not found")
        if teacher.get("role") != "teacher":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coordinator must be a teacher")

    if payload.president_user_id:
        president = await _resolve_user(payload.president_user_id)
        if not president:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="President not found")
        if president.get("role") != "student":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="President must be a student")

    slug = (payload.slug or payload.name).strip().lower().replace(" ", "-")
    duplicate_slug = await db.clubs.find_one({"slug": slug, "academic_year": payload.academic_year})
    if duplicate_slug:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Club slug already exists for this academic year")

    now = datetime.now(timezone.utc)
    document = {
        "name": payload.name.strip(),
        "slug": slug,
        "description": payload.description,
        "category": payload.category,
        "department_id": payload.department_id,
        "academic_year": payload.academic_year,
        "coordinator_user_id": payload.coordinator_user_id,
        "president_user_id": payload.president_user_id,
        "status": payload.status,
        "registration_open": bool(payload.registration_open),
        "membership_type": payload.membership_type,
        "max_members": payload.max_members,
        "logo_url": payload.logo_url,
        "banner_url": payload.banner_url,
        "created_by": str(current_user["_id"]),
        "created_at": now,
        "updated_at": now,
        # Legacy compatibility
        "is_active": payload.status in {"draft", "active"},
    }

    if document["status"] == "active" and not document.get("coordinator_user_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coordinator is required before activation")

    result = await db.clubs.insert_one(document)
    created = await db.clubs.find_one({"_id": result.inserted_id})
    enriched = await _enrich_club_document(created)

    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="create",
        entity_type="club",
        entity_id=str(result.inserted_id),
        detail="Created club",
    )
    return ClubOut(**club_public(enriched))


@router.patch("/{club_id}", response_model=ClubOut)
async def update_club(
    club_id: str,
    payload: ClubUpdate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> ClubOut:
    club = await _ensure_club(club_id)
    if not await _can_manage_club(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to manage this club")

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if "coordinator_user_id" in update_data and update_data["coordinator_user_id"]:
        teacher = await _resolve_user(update_data["coordinator_user_id"])
        if not teacher or teacher.get("role") != "teacher":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coordinator must be a teacher")

    if "president_user_id" in update_data and update_data["president_user_id"]:
        president = await _resolve_user(update_data["president_user_id"])
        if not president or president.get("role") != "student":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="President must be a student")

    next_status = update_data.get("status", club.get("status", "active"))
    coordinator_id = update_data.get("coordinator_user_id", club.get("coordinator_user_id"))
    registration_open = update_data.get("registration_open", club.get("registration_open", False))

    if next_status == "active" and not coordinator_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Coordinator is required before activation")

    if registration_open and next_status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration can be opened only when club is active",
        )

    if next_status == "archived":
        has_active_events = await db.club_events.count_documents(
            {"club_id": club_id, "status": {"$in": ["draft", "open", "closed"]}}
        )
        if has_active_events:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Archive blocked: club has active events")
        update_data["archived_at"] = datetime.now(timezone.utc)
        update_data["registration_open"] = False

    update_data["updated_at"] = datetime.now(timezone.utc)
    update_data["is_active"] = next_status in {"draft", "active"}

    await db.clubs.update_one({"_id": parse_object_id(club_id)}, {"$set": update_data})
    updated = await db.clubs.find_one({"_id": parse_object_id(club_id)})
    enriched = await _enrich_club_document(updated)

    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="update",
        entity_type="club",
        entity_id=club_id,
        detail="Updated club settings",
    )
    return ClubOut(**club_public(enriched))


@router.post("/{club_id}/join")
async def join_club(
    club_id: str,
    current_user=Depends(require_roles(["student"])),
) -> dict[str, Any]:
    club = await _ensure_club(club_id)
    if club.get("status") != "active":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Club is not active")
    if not club.get("registration_open", False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Club registration is closed")

    student_user_id = str(current_user["_id"])

    existing_member = await db.club_members.find_one(
        {"club_id": club_id, "student_user_id": student_user_id, "status": {"$in": ["active", "inactive"]}}
    )
    if existing_member:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already a club member")

    max_members = club.get("max_members")
    if max_members:
        active_member_count = await db.club_members.count_documents({"club_id": club_id, "status": "active"})
        if active_member_count >= int(max_members):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Club membership capacity reached")

    if club.get("membership_type") == "open":
        now = datetime.now(timezone.utc)
        result = await db.club_members.insert_one(
            {
                "club_id": club_id,
                "student_user_id": student_user_id,
                "student_name": current_user.get("full_name"),
                "student_email": current_user.get("email"),
                "role": "member",
                "status": "active",
                "joined_at": now,
                "left_at": None,
            }
        )
        return {
            "status": "approved",
            "membership_id": str(result.inserted_id),
            "message": "Joined club successfully",
        }

    pending = await db.club_applications.find_one(
        {"club_id": club_id, "student_user_id": student_user_id, "status": "pending"}
    )
    if pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Application already pending")

    result = await db.club_applications.insert_one(
        {
            "club_id": club_id,
            "student_user_id": student_user_id,
            "student_name": current_user.get("full_name"),
            "student_email": current_user.get("email"),
            "status": "pending",
            "applied_at": datetime.now(timezone.utc),
            "reviewed_by": None,
            "reviewed_at": None,
        }
    )
    return {
        "status": "pending",
        "application_id": str(result.inserted_id),
        "message": "Application submitted for coordinator approval",
    }


@router.get("/{club_id}/members", response_model=List[ClubMembershipOut])
async def list_members(
    club_id: str,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[ClubMembershipOut]:
    club = await _ensure_club(club_id)

    query: dict[str, Any] = {"club_id": club_id}
    if not await _can_view_members(current_user, club):
        if current_user.get("role") != "student":
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view members")
        query["student_user_id"] = str(current_user["_id"])

    items = await db.club_members.find(query).sort("joined_at", -1).to_list(length=1000)
    return [ClubMembershipOut(**club_member_public(item)) for item in items]


@router.patch("/{club_id}/members/{member_id}", response_model=ClubMembershipOut)
async def update_member(
    club_id: str,
    member_id: str,
    payload: ClubMembershipUpdate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> ClubMembershipOut:
    club = await _ensure_club(club_id)
    if not await _can_manage_club(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to manage this club")

    member_obj_id = parse_object_id(member_id)
    member = await db.club_members.find_one({"_id": member_obj_id, "club_id": club_id})
    if not member:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if update_data.get("role") == "president":
        existing_president = await db.club_members.find_one(
            {
                "club_id": club_id,
                "role": "president",
                "status": "active",
                "_id": {"$ne": member_obj_id},
            }
        )
        if existing_president:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only one president is allowed per club")
        await db.clubs.update_one(
            {"_id": parse_object_id(club_id)}, {"$set": {"president_user_id": member.get("student_user_id")}}
        )

    if update_data.get("status") in {"inactive", "removed"}:
        update_data["left_at"] = datetime.now(timezone.utc)

    await db.club_members.update_one({"_id": member_obj_id}, {"$set": update_data})
    updated = await db.club_members.find_one({"_id": member_obj_id})
    return ClubMembershipOut(**club_member_public(updated))


@router.get("/{club_id}/applications", response_model=List[ClubApplicationOut])
async def list_applications(
    club_id: str,
    status_filter: str | None = Query(default=None, alias="status"),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[ClubApplicationOut]:
    club = await _ensure_club(club_id)

    query: dict[str, Any] = {"club_id": club_id}
    if status_filter:
        query["status"] = status_filter

    if await _can_view_members(current_user, club):
        pass
    elif current_user.get("role") == "student":
        query["student_user_id"] = str(current_user["_id"])
    else:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view applications")

    items = await db.club_applications.find(query).sort("applied_at", -1).to_list(length=1000)
    return [ClubApplicationOut(**club_application_public(item)) for item in items]


@router.patch("/{club_id}/applications/{application_id}", response_model=ClubApplicationOut)
async def review_application(
    club_id: str,
    application_id: str,
    payload: ClubApplicationReview,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> ClubApplicationOut:
    club = await _ensure_club(club_id)
    if not await _can_manage_club(current_user, club):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to review applications")

    application_obj_id = parse_object_id(application_id)
    application = await db.club_applications.find_one({"_id": application_obj_id, "club_id": club_id})
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")

    if application.get("status") != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Application already reviewed")

    now = datetime.now(timezone.utc)
    await db.club_applications.update_one(
        {"_id": application_obj_id},
        {
            "$set": {
                "status": payload.status,
                "reviewed_by": str(current_user["_id"]),
                "reviewed_at": now,
            }
        },
    )

    if payload.status == "approved":
        exists = await db.club_members.find_one(
            {
                "club_id": club_id,
                "student_user_id": application.get("student_user_id"),
                "status": {"$in": ["active", "inactive"]},
            }
        )
        if not exists:
            await db.club_members.insert_one(
                {
                    "club_id": club_id,
                    "student_user_id": application.get("student_user_id"),
                    "student_name": application.get("student_name"),
                    "student_email": application.get("student_email"),
                    "role": "member",
                    "status": "active",
                    "joined_at": now,
                    "left_at": None,
                }
            )

    updated = await db.club_applications.find_one({"_id": application_obj_id})
    return ClubApplicationOut(**club_application_public(updated))


@router.get("/{club_id}/analytics", response_model=ClubAnalyticsOut)
async def get_club_analytics(
    club_id: str,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> ClubAnalyticsOut:
    club = await _ensure_club(club_id)

    if not await _can_view_members(current_user, club):
        if current_user.get("role") != "student" or club.get("president_user_id") != str(current_user.get("_id")):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view club analytics")

    total_members = await db.club_members.count_documents({"club_id": club_id})
    active_members = await db.club_members.count_documents({"club_id": club_id, "status": "active"})
    inactive_members = await db.club_members.count_documents({"club_id": club_id, "status": {"$in": ["inactive", "removed"]}})

    since = datetime.now(timezone.utc) - timedelta(days=30)
    growth_30d = await db.club_members.count_documents({"club_id": club_id, "joined_at": {"$gte": since}})

    total_events = await db.club_events.count_documents({"club_id": club_id})
    upcoming_events = await db.club_events.count_documents({"club_id": club_id, "status": {"$in": ["draft", "open", "closed"]}})
    completed_events = await db.club_events.count_documents({"club_id": club_id, "status": {"$in": ["completed", "archived"]}})

    regs = await db.event_registrations.count_documents({"event_id": {"$in": [
        str(item["_id"])
        for item in await db.club_events.find({"club_id": club_id}, {"_id": 1, "capacity": 1}).to_list(length=1000)
    ]}})
    cap_docs = await db.club_events.find({"club_id": club_id}, {"capacity": 1}).to_list(length=1000)
    total_capacity = sum(max(1, int(item.get("capacity") or 0)) for item in cap_docs)
    attendance_pct = round((regs / total_capacity) * 100, 2) if total_capacity else 0.0

    pending_applications = await db.club_applications.count_documents({"club_id": club_id, "status": "pending"})

    return ClubAnalyticsOut(
        club_id=club_id,
        total_members=total_members,
        active_members=active_members,
        inactive_members=inactive_members,
        membership_growth_30d=growth_30d,
        total_events=total_events,
        upcoming_events=upcoming_events,
        completed_events=completed_events,
        average_attendance_pct=attendance_pct,
        pending_applications=pending_applications,
    )
