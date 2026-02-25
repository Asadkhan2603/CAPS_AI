from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission, require_roles
from app.models.subjects import subject_public
from app.schemas.subject import SubjectCreate, SubjectOut, SubjectUpdate

router = APIRouter()


@router.get("/", response_model=List[SubjectOut])
async def list_subjects(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[SubjectOut]:
    query = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"code": {"$regex": q, "$options": "i"}},
        ]
    if is_active is not None:
        query["is_active"] = is_active

    cursor = db.subjects.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [SubjectOut(**subject_public(item)) for item in items]


@router.get("/{subject_id}", response_model=SubjectOut)
async def get_subject(
    subject_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> SubjectOut:
    item = await db.subjects.find_one({"_id": parse_object_id(subject_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return SubjectOut(**subject_public(item))


@router.post("/", response_model=SubjectOut, status_code=status.HTTP_201_CREATED)
async def create_subject(
    payload: SubjectCreate,
    _current_user=Depends(require_permission("academic:manage")),
) -> SubjectOut:
    normalized_code = payload.code.strip().upper()
    existing = await db.subjects.find_one({"code": normalized_code})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject code already exists")

    document = {
        "name": payload.name.strip(),
        "code": normalized_code,
        "description": payload.description,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.subjects.insert_one(document)
    created = await db.subjects.find_one({"_id": result.inserted_id})
    return SubjectOut(**subject_public(created))


@router.put("/{subject_id}", response_model=SubjectOut)
async def update_subject(
    subject_id: str,
    payload: SubjectUpdate,
    _current_user=Depends(require_permission("academic:manage")),
) -> SubjectOut:
    subject_obj_id = parse_object_id(subject_id)
    update_data = payload.model_dump(exclude_none=True)
    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()
    if "code" in update_data and update_data["code"]:
        update_data["code"] = update_data["code"].strip().upper()
        duplicate = await db.subjects.find_one({"code": update_data["code"]})
        if duplicate and duplicate.get("_id") != subject_obj_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject code already exists")
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    result = await db.subjects.update_one(
        {"_id": subject_obj_id},
        {"$set": update_data},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")

    updated = await db.subjects.find_one({"_id": subject_obj_id})
    return SubjectOut(**subject_public(updated))


@router.delete("/{subject_id}")
async def delete_subject(
    subject_id: str,
    _current_user=Depends(require_permission("academic:manage")),
) -> dict:
    result = await db.subjects.delete_one({"_id": parse_object_id(subject_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return {"message": "Subject deleted"}
