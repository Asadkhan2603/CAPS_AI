from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import UNIVERSITY_SCHEMA_VERSION
from app.core.security import require_permission, require_roles
from app.core.soft_delete import apply_is_active_filter, build_soft_delete_update, build_state_update
from app.models.universities import university_public
from app.schemas.university import UniversityCreate, UniversityOut, UniversityUpdate
from app.services.master_hierarchy import ensure_master_hierarchy_change_is_safe

router = APIRouter()


@router.get("/", response_model=List[UniversityOut])
async def list_universities(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[UniversityOut]:
    query = {}
    if q:
        query["$or"] = [
            {"university_name": {"$regex": q, "$options": "i"}},
            {"university_id": {"$regex": q, "$options": "i"}},
        ]
    apply_is_active_filter(query, is_active)
    items = await db.universities.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [UniversityOut(**university_public(item)) for item in items]


@router.get("/{university_doc_id}", response_model=UniversityOut)
async def get_university(
    university_doc_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> UniversityOut:
    item = await db.universities.find_one({"_id": parse_object_id(university_doc_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="University not found")
    return UniversityOut(**university_public(item))


@router.post("/", response_model=UniversityOut, status_code=status.HTTP_201_CREATED)
async def create_university(
    payload: UniversityCreate,
    _current_user=Depends(require_permission("universities.manage")),
) -> UniversityOut:
    university_id = payload.university_id.strip().upper()
    existing = await db.universities.find_one({"university_id": university_id})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="University ID already exists")
    document = {
        "university_id": university_id,
        "university_name": payload.university_name.strip(),
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "schema_version": UNIVERSITY_SCHEMA_VERSION,
    }
    result = await db.universities.insert_one(document)
    created = await db.universities.find_one({"_id": result.inserted_id})
    return UniversityOut(**university_public(created))


@router.put("/{university_doc_id}", response_model=UniversityOut)
async def update_university(
    university_doc_id: str,
    payload: UniversityUpdate,
    _current_user=Depends(require_permission("universities.manage")),
) -> UniversityOut:
    university_obj_id = parse_object_id(university_doc_id)
    update_data = payload.model_dump(exclude_none=True)
    if "university_id" in update_data:
        update_data["university_id"] = update_data["university_id"].strip().upper()
        duplicate = await db.universities.find_one({"university_id": update_data["university_id"]})
        if duplicate and duplicate.get("_id") != university_obj_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="University ID already exists")
    if "university_name" in update_data:
        update_data["university_name"] = update_data["university_name"].strip()
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    update_data["schema_version"] = UNIVERSITY_SCHEMA_VERSION
    result = await db.universities.update_one({"_id": university_obj_id}, build_state_update(update_data))
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="University not found")
    updated = await db.universities.find_one({"_id": university_obj_id})
    return UniversityOut(**university_public(updated))


@router.delete("/{university_doc_id}")
async def delete_university(
    university_doc_id: str,
    _current_user=Depends(require_permission("universities.manage")),
) -> dict:
    try:
        await ensure_master_hierarchy_change_is_safe(
            db,
            entity_kind="university",
            entity_doc_id=university_doc_id,
            operation="archive",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    result = await db.universities.update_one(
        {"_id": parse_object_id(university_doc_id), "is_active": True},
        build_soft_delete_update(extra_fields={"schema_version": UNIVERSITY_SCHEMA_VERSION}),
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="University not found")
    return {"message": "University archived"}
