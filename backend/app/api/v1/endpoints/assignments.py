from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.assignments import assignment_public
from app.schemas.assignment import AssignmentCreate, AssignmentOut, AssignmentUpdate

router = APIRouter()


@router.get("/", response_model=List[AssignmentOut])
async def list_assignments(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    subject_id: str | None = Query(default=None),
    section_id: str | None = Query(default=None),
    created_by: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[AssignmentOut]:
    query = {}
    if q:
        query["title"] = {"$regex": q, "$options": "i"}
    if subject_id:
        query["subject_id"] = subject_id
    if section_id:
        query["section_id"] = section_id
    if created_by:
        query["created_by"] = created_by

    cursor = db.assignments.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [AssignmentOut(**assignment_public(item)) for item in items]


@router.get("/{assignment_id}", response_model=AssignmentOut)
async def get_assignment(
    assignment_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> AssignmentOut:
    item = await db.assignments.find_one({"_id": parse_object_id(assignment_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return AssignmentOut(**assignment_public(item))


@router.post("/", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    payload: AssignmentCreate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> AssignmentOut:
    document = {
        "title": payload.title.strip(),
        "description": payload.description,
        "subject_id": payload.subject_id,
        "section_id": payload.section_id,
        "due_date": payload.due_date,
        "total_marks": payload.total_marks,
        "created_by": str(current_user.get("_id")),
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.assignments.insert_one(document)
    created = await db.assignments.find_one({"_id": result.inserted_id})
    return AssignmentOut(**assignment_public(created))


@router.put("/{assignment_id}", response_model=AssignmentOut)
async def update_assignment(
    assignment_id: str,
    payload: AssignmentUpdate,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> AssignmentOut:
    update_data = payload.model_dump(exclude_none=True)
    if "title" in update_data and update_data["title"]:
        update_data["title"] = update_data["title"].strip()
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    result = await db.assignments.update_one(
        {"_id": parse_object_id(assignment_id)},
        {"$set": update_data},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    updated = await db.assignments.find_one({"_id": parse_object_id(assignment_id)})
    return AssignmentOut(**assignment_public(updated))


@router.delete("/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> dict:
    result = await db.assignments.delete_one({"_id": parse_object_id(assignment_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return {"message": "Assignment deleted"}
