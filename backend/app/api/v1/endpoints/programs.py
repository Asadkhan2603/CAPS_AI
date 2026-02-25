from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission, require_roles
from app.models.programs import program_public
from app.schemas.program import ProgramCreate, ProgramOut, ProgramUpdate

router = APIRouter()


@router.get("/", response_model=List[ProgramOut])
async def list_programs(
    department_id: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[ProgramOut]:
    query = {}
    if department_id:
        query["department_id"] = department_id
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"code": {"$regex": q, "$options": "i"}},
        ]
    if is_active is not None:
        query["is_active"] = is_active
    items = await db.programs.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [ProgramOut(**program_public(item)) for item in items]


@router.get("/{program_id}", response_model=ProgramOut)
async def get_program(
    program_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> ProgramOut:
    item = await db.programs.find_one({"_id": parse_object_id(program_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return ProgramOut(**program_public(item))


@router.post("/", response_model=ProgramOut, status_code=status.HTTP_201_CREATED)
async def create_program(
    payload: ProgramCreate,
    _current_user=Depends(require_permission("academic:manage")),
) -> ProgramOut:
    department = await db.departments.find_one({"_id": parse_object_id(payload.department_id)})
    if not department:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department not found for provided department_id")
    normalized_code = payload.code.strip().upper()
    existing = await db.programs.find_one({"code": normalized_code})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program code already exists")
    document = {
        "name": payload.name.strip(),
        "code": normalized_code,
        "department_id": payload.department_id,
        "description": payload.description,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.programs.insert_one(document)
    created = await db.programs.find_one({"_id": result.inserted_id})
    return ProgramOut(**program_public(created))


@router.put("/{program_id}", response_model=ProgramOut)
async def update_program(
    program_id: str,
    payload: ProgramUpdate,
    _current_user=Depends(require_permission("academic:manage")),
) -> ProgramOut:
    program_obj_id = parse_object_id(program_id)
    update_data = payload.model_dump(exclude_none=True)
    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()
    if "code" in update_data and update_data["code"]:
        update_data["code"] = update_data["code"].strip().upper()
        duplicate = await db.programs.find_one({"code": update_data["code"]})
        if duplicate and duplicate.get("_id") != program_obj_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program code already exists")
    if "department_id" in update_data:
        department = await db.departments.find_one({"_id": parse_object_id(update_data["department_id"])})
        if not department:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department not found for provided department_id")
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    result = await db.programs.update_one({"_id": program_obj_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    updated = await db.programs.find_one({"_id": program_obj_id})
    return ProgramOut(**program_public(updated))


@router.delete("/{program_id}")
async def delete_program(
    program_id: str,
    _current_user=Depends(require_permission("academic:manage")),
) -> dict:
    result = await db.programs.update_one(
        {"_id": parse_object_id(program_id), "is_active": True},
        {"$set": {"is_active": False, "deleted_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return {"message": "Program archived"}
