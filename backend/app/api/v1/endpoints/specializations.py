from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission, require_roles
from app.core.soft_delete import apply_is_active_filter, build_soft_delete_update, build_state_update
from app.models.specializations import specialization_public
from app.schemas.specialization import SpecializationCreate, SpecializationOut, SpecializationUpdate
from app.services.audit import log_destructive_action_event
from app.services.governance import enforce_review_approval

router = APIRouter()


@router.get("/", response_model=List[SpecializationOut])
async def list_specializations(
    program_id: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[SpecializationOut]:
    query: dict[str, Any] = {}
    if program_id:
        query["program_id"] = program_id
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"code": {"$regex": q, "$options": "i"}},
        ]
    apply_is_active_filter(query, is_active)
    items = await db.specializations.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [SpecializationOut(**specialization_public(item)) for item in items]


@router.get("/{specialization_id}", response_model=SpecializationOut)
async def get_specialization(
    specialization_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> SpecializationOut:
    item = await db.specializations.find_one({"_id": parse_object_id(specialization_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialization not found")
    return SpecializationOut(**specialization_public(item))


@router.post("/", response_model=SpecializationOut, status_code=status.HTTP_201_CREATED)
async def create_specialization(
    payload: SpecializationCreate,
    _current_user=Depends(require_permission("specializations.manage")),
) -> SpecializationOut:
    program = await db.programs.find_one({"_id": parse_object_id(payload.program_id)})
    if not program:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program not found for provided program_id")
    normalized_code = payload.code.strip().upper()
    existing = await db.specializations.find_one({"code": normalized_code})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specialization code already exists")
    document = {
        "name": payload.name.strip(),
        "code": normalized_code,
        "program_id": payload.program_id,
        "description": payload.description,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.specializations.insert_one(document)
    created = await db.specializations.find_one({"_id": result.inserted_id})
    return SpecializationOut(**specialization_public(created))


@router.put("/{specialization_id}", response_model=SpecializationOut)
async def update_specialization(
    specialization_id: str,
    payload: SpecializationUpdate,
    _current_user=Depends(require_permission("specializations.manage")),
) -> SpecializationOut:
    specialization_obj_id = parse_object_id(specialization_id)
    update_data = payload.model_dump(exclude_none=True)
    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()
    if "code" in update_data and update_data["code"]:
        update_data["code"] = update_data["code"].strip().upper()
        duplicate = await db.specializations.find_one({"code": update_data["code"]})
        if duplicate and duplicate.get("_id") != specialization_obj_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specialization code already exists")
    if "program_id" in update_data:
        program = await db.programs.find_one({"_id": parse_object_id(update_data["program_id"])})
        if not program:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program not found for provided program_id")
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    result = await db.specializations.update_one({"_id": specialization_obj_id}, build_state_update(update_data))
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialization not found")
    updated = await db.specializations.find_one({"_id": specialization_obj_id})
    return SpecializationOut(**specialization_public(updated))


@router.delete("/{specialization_id}")
async def delete_specialization(
    specialization_id: str,
    review_id: str | None = Query(default=None),
    current_user=Depends(require_permission("specializations.manage")),
) -> dict:
    actor_user_id = str(current_user.get("_id") or "") or None
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="specializations.delete",
        entity_type="specialization",
        entity_id=specialization_id,
        stage="requested",
        detail="Specialization delete requested",
        review_id=review_id,
        metadata={"admin_type": current_user.get("admin_type")},
    )
    governance_completed = bool(await enforce_review_approval(
        current_user=current_user,
        review_id=review_id,
        action="specializations.delete",
        entity_type="specialization",
        entity_id=specialization_id,
    ))
    result = await db.specializations.update_one(
        {"_id": parse_object_id(specialization_id), "is_active": True},
        build_soft_delete_update(deleted_by=str(current_user.get("_id"))),
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialization not found")
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="specializations.delete",
        entity_type="specialization",
        entity_id=specialization_id,
        stage="completed",
        detail="Specialization archived",
        review_id=review_id,
        governance_completed=governance_completed,
        outcome="archived",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    return {"message": "Specialization archived"}
