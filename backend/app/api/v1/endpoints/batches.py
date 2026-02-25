from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission, require_roles
from app.models.batches import batch_public
from app.schemas.batch import BatchCreate, BatchOut, BatchUpdate

router = APIRouter()


@router.get("/", response_model=List[BatchOut])
async def list_batches(
    program_id: str | None = Query(default=None),
    specialization_id: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[BatchOut]:
    query = {}
    if program_id:
        query["program_id"] = program_id
    if specialization_id:
        query["specialization_id"] = specialization_id
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"code": {"$regex": q, "$options": "i"}},
        ]
    if is_active is not None:
        query["is_active"] = is_active
    items = await db.batches.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [BatchOut(**batch_public(item)) for item in items]


@router.get("/{batch_id}", response_model=BatchOut)
async def get_batch(
    batch_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> BatchOut:
    item = await db.batches.find_one({"_id": parse_object_id(batch_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return BatchOut(**batch_public(item))


@router.post("/", response_model=BatchOut, status_code=status.HTTP_201_CREATED)
async def create_batch(
    payload: BatchCreate,
    _current_user=Depends(require_permission("academic:manage")),
) -> BatchOut:
    program = await db.programs.find_one({"_id": parse_object_id(payload.program_id)})
    if not program:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program not found for provided program_id")
    if payload.specialization_id:
        specialization = await db.specializations.find_one({"_id": parse_object_id(payload.specialization_id)})
        if not specialization:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specialization not found for provided specialization_id")
        if specialization.get("program_id") != payload.program_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="specialization_id does not belong to program_id")
    normalized_code = payload.code.strip().upper()
    existing = await db.batches.find_one({"code": normalized_code})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batch code already exists")
    document = {
        "program_id": payload.program_id,
        "specialization_id": payload.specialization_id,
        "name": payload.name.strip(),
        "code": normalized_code,
        "start_year": payload.start_year,
        "end_year": payload.end_year,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.batches.insert_one(document)
    created = await db.batches.find_one({"_id": result.inserted_id})
    return BatchOut(**batch_public(created))


@router.put("/{batch_id}", response_model=BatchOut)
async def update_batch(
    batch_id: str,
    payload: BatchUpdate,
    _current_user=Depends(require_permission("academic:manage")),
) -> BatchOut:
    batch_obj_id = parse_object_id(batch_id)
    current = await db.batches.find_one({"_id": batch_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    update_data = payload.model_dump(exclude_none=True)
    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()
    if "code" in update_data and update_data["code"]:
        update_data["code"] = update_data["code"].strip().upper()
        duplicate = await db.batches.find_one({"code": update_data["code"]})
        if duplicate and duplicate.get("_id") != batch_obj_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batch code already exists")
    target_program_id = update_data.get("program_id", current.get("program_id"))
    if target_program_id:
        program = await db.programs.find_one({"_id": parse_object_id(target_program_id)})
        if not program:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program not found for provided program_id")
    if "specialization_id" in update_data and update_data["specialization_id"]:
        specialization = await db.specializations.find_one({"_id": parse_object_id(update_data["specialization_id"])})
        if not specialization:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specialization not found for provided specialization_id")
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    result = await db.batches.update_one({"_id": batch_obj_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    updated = await db.batches.find_one({"_id": batch_obj_id})
    return BatchOut(**batch_public(updated))


@router.delete("/{batch_id}")
async def delete_batch(
    batch_id: str,
    _current_user=Depends(require_permission("academic:manage")),
) -> dict:
    result = await db.batches.update_one(
        {"_id": parse_object_id(batch_id), "is_active": True},
        {"$set": {"is_active": False, "deleted_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return {"message": "Batch archived"}
