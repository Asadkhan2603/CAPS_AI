from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.sections import section_public
from app.schemas.section import SectionCreate, SectionOut, SectionUpdate

router = APIRouter()


@router.get("/", response_model=List[SectionOut])
async def list_sections(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    academic_year: str | None = Query(default=None),
    semester: int | None = Query(default=None, ge=1, le=12),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[SectionOut]:
    query = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"program": {"$regex": q, "$options": "i"}},
        ]
    if academic_year:
        query["academic_year"] = academic_year
    if semester is not None:
        query["semester"] = semester
    if is_active is not None:
        query["is_active"] = is_active

    cursor = db.sections.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [SectionOut(**section_public(item)) for item in items]


@router.get("/{section_id}", response_model=SectionOut)
async def get_section(
    section_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> SectionOut:
    item = await db.sections.find_one({"_id": parse_object_id(section_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    return SectionOut(**section_public(item))


@router.post("/", response_model=SectionOut, status_code=status.HTTP_201_CREATED)
async def create_section(
    payload: SectionCreate,
    _current_user=Depends(require_roles(["admin"])),
) -> SectionOut:
    document = {
        "name": payload.name.strip(),
        "program": payload.program.strip(),
        "academic_year": payload.academic_year.strip(),
        "semester": payload.semester,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.sections.insert_one(document)
    created = await db.sections.find_one({"_id": result.inserted_id})
    return SectionOut(**section_public(created))


@router.put("/{section_id}", response_model=SectionOut)
async def update_section(
    section_id: str,
    payload: SectionUpdate,
    _current_user=Depends(require_roles(["admin"])),
) -> SectionOut:
    update_data = payload.model_dump(exclude_none=True)
    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()
    if "program" in update_data and update_data["program"]:
        update_data["program"] = update_data["program"].strip()
    if "academic_year" in update_data and update_data["academic_year"]:
        update_data["academic_year"] = update_data["academic_year"].strip()
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    result = await db.sections.update_one(
        {"_id": parse_object_id(section_id)},
        {"$set": update_data},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    updated = await db.sections.find_one({"_id": parse_object_id(section_id)})
    return SectionOut(**section_public(updated))


@router.delete("/{section_id}")
async def delete_section(
    section_id: str,
    _current_user=Depends(require_roles(["admin"])),
) -> dict:
    result = await db.sections.delete_one({"_id": parse_object_id(section_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    return {"message": "Section deleted"}
