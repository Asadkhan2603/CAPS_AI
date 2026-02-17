from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.section_subjects import section_subject_public
from app.schemas.section_subject import (
    SectionSubjectCreate,
    SectionSubjectOut,
    SectionSubjectUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[SectionSubjectOut])
async def list_section_subjects(
    section_id: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    teacher_user_id: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[SectionSubjectOut]:
    query = {}
    if section_id:
        query["section_id"] = section_id
    if subject_id:
        query["subject_id"] = subject_id
    if teacher_user_id:
        query["teacher_user_id"] = teacher_user_id
    if is_active is not None:
        query["is_active"] = is_active

    cursor = db.section_subjects.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [SectionSubjectOut(**section_subject_public(item)) for item in items]


@router.get("/{mapping_id}", response_model=SectionSubjectOut)
async def get_section_subject(
    mapping_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> SectionSubjectOut:
    item = await db.section_subjects.find_one({"_id": parse_object_id(mapping_id)})
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section-subject mapping not found"
        )
    return SectionSubjectOut(**section_subject_public(item))


@router.post("/", response_model=SectionSubjectOut, status_code=status.HTTP_201_CREATED)
async def create_section_subject(
    payload: SectionSubjectCreate,
    _current_user=Depends(require_roles(["admin"])),
) -> SectionSubjectOut:
    section = await db.sections.find_one({"_id": parse_object_id(payload.section_id)})
    if not section:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section not found for provided section_id")

    subject = await db.subjects.find_one({"_id": parse_object_id(payload.subject_id)})
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject not found for provided subject_id")

    if payload.teacher_user_id:
        teacher = await db.users.find_one({"_id": parse_object_id(payload.teacher_user_id)})
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teacher not found for provided teacher_user_id",
            )
        if teacher.get("role") != "teacher":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="teacher_user_id must belong to a teacher role",
            )

    existing = await db.section_subjects.find_one(
        {
            "section_id": payload.section_id,
            "subject_id": payload.subject_id,
        }
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mapping already exists for this section and subject",
        )

    document = {
        "section_id": payload.section_id,
        "subject_id": payload.subject_id,
        "teacher_user_id": payload.teacher_user_id,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.section_subjects.insert_one(document)
    created = await db.section_subjects.find_one({"_id": result.inserted_id})
    return SectionSubjectOut(**section_subject_public(created))


@router.put("/{mapping_id}", response_model=SectionSubjectOut)
async def update_section_subject(
    mapping_id: str,
    payload: SectionSubjectUpdate,
    _current_user=Depends(require_roles(["admin"])),
) -> SectionSubjectOut:
    mapping_obj_id = parse_object_id(mapping_id)
    update_data = payload.model_dump(exclude_none=True)
    if "teacher_user_id" in update_data and update_data["teacher_user_id"]:
        teacher = await db.users.find_one({"_id": parse_object_id(update_data["teacher_user_id"])})
        if not teacher:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Teacher not found for provided teacher_user_id",
            )
        if teacher.get("role") != "teacher":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="teacher_user_id must belong to a teacher role",
            )

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    result = await db.section_subjects.update_one(
        {"_id": mapping_obj_id},
        {"$set": update_data},
    )
    if result.matched_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section-subject mapping not found"
        )
    updated = await db.section_subjects.find_one({"_id": mapping_obj_id})
    return SectionSubjectOut(**section_subject_public(updated))


@router.delete("/{mapping_id}")
async def delete_section_subject(
    mapping_id: str,
    _current_user=Depends(require_roles(["admin"])),
) -> dict:
    result = await db.section_subjects.delete_one({"_id": parse_object_id(mapping_id)})
    if result.deleted_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Section-subject mapping not found"
        )
    return {"message": "Section-subject mapping deleted"}
