from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.students import student_public
from app.schemas.student import StudentCreate, StudentOut, StudentUpdate

router = APIRouter()


@router.get("/", response_model=List[StudentOut])
async def list_students(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    section_id: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[StudentOut]:
    query = {}
    if q:
        query["$or"] = [
            {"full_name": {"$regex": q, "$options": "i"}},
            {"roll_number": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
        ]
    if section_id:
        query["section_id"] = section_id
    if is_active is not None:
        query["is_active"] = is_active

    cursor = db.students.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [StudentOut(**student_public(item)) for item in items]


@router.get("/{student_id}", response_model=StudentOut)
async def get_student(
    student_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> StudentOut:
    item = await db.students.find_one({"_id": parse_object_id(student_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return StudentOut(**student_public(item))


@router.post("/", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: StudentCreate,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> StudentOut:
    duplicate_roll = await db.students.find_one({"roll_number": payload.roll_number.strip()})
    if duplicate_roll:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Roll number already exists")

    if payload.section_id:
        section = await db.sections.find_one({"_id": parse_object_id(payload.section_id)})
        if not section:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Section not found for provided section_id",
            )

    document = {
        "full_name": payload.full_name.strip(),
        "roll_number": payload.roll_number.strip(),
        "email": payload.email.lower().strip() if payload.email else None,
        "section_id": payload.section_id,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.students.insert_one(document)
    created = await db.students.find_one({"_id": result.inserted_id})
    return StudentOut(**student_public(created))


@router.put("/{student_id}", response_model=StudentOut)
async def update_student(
    student_id: str,
    payload: StudentUpdate,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> StudentOut:
    student_obj_id = parse_object_id(student_id)
    current = await db.students.find_one({"_id": student_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    update_data = payload.model_dump(exclude_none=True)
    if "email" in update_data and update_data["email"]:
        update_data["email"] = update_data["email"].lower().strip()
    if "full_name" in update_data and update_data["full_name"]:
        update_data["full_name"] = update_data["full_name"].strip()
    if "roll_number" in update_data and update_data["roll_number"]:
        update_data["roll_number"] = update_data["roll_number"].strip()
        duplicate_roll = await db.students.find_one({"roll_number": update_data["roll_number"]})
        if duplicate_roll and duplicate_roll.get("_id") != student_obj_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Roll number already exists")
    if "section_id" in update_data and update_data["section_id"]:
        section = await db.sections.find_one({"_id": parse_object_id(update_data["section_id"])})
        if not section:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Section not found for provided section_id",
            )

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    result = await db.students.update_one(
        {"_id": student_obj_id},
        {"$set": update_data},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    updated = await db.students.find_one({"_id": student_obj_id})
    return StudentOut(**student_public(updated))


@router.delete("/{student_id}")
async def delete_student(
    student_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> dict:
    result = await db.students.delete_one({"_id": parse_object_id(student_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return {"message": "Student deleted"}
