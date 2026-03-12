from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import FACULTY_SCHEMA_VERSION
from app.core.security import require_permission, require_roles
from app.core.soft_delete import apply_is_active_filter, build_soft_delete_update, build_state_update
from app.models.faculties import faculty_public
from app.schemas.faculty import FacultyCreate, FacultyOut, FacultyUpdate
from app.services.audit import log_destructive_action_event
from app.services.governance import enforce_review_approval

router = APIRouter()


@router.get("/", response_model=List[FacultyOut])
async def list_faculties(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[FacultyOut]:
    query = {}
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"code": {"$regex": q, "$options": "i"}},
        ]
    apply_is_active_filter(query, is_active)
    items = await db.faculties.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [FacultyOut(**faculty_public(item)) for item in items]


@router.get("/{faculty_id}", response_model=FacultyOut)
async def get_faculty(
    faculty_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> FacultyOut:
    item = await db.faculties.find_one({"_id": parse_object_id(faculty_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")
    return FacultyOut(**faculty_public(item))


@router.post("/", response_model=FacultyOut, status_code=status.HTTP_201_CREATED)
async def create_faculty(
    payload: FacultyCreate,
    _current_user=Depends(require_permission("faculties.manage")),
) -> FacultyOut:
    normalized_code = payload.code.strip().upper()
    existing = await db.faculties.find_one({"code": normalized_code})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Faculty code already exists")
    document = {
        "name": payload.name.strip(),
        "code": normalized_code,
        "university_name": payload.university_name.strip() if payload.university_name else None,
        "university_code": payload.university_code.strip().upper() if payload.university_code else None,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "schema_version": FACULTY_SCHEMA_VERSION,
    }
    result = await db.faculties.insert_one(document)
    created = await db.faculties.find_one({"_id": result.inserted_id})
    return FacultyOut(**faculty_public(created))


@router.put("/{faculty_id}", response_model=FacultyOut)
async def update_faculty(
    faculty_id: str,
    payload: FacultyUpdate,
    _current_user=Depends(require_permission("faculties.manage")),
) -> FacultyOut:
    faculty_obj_id = parse_object_id(faculty_id)
    update_data = payload.model_dump(exclude_none=True)
    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()
    if "code" in update_data and update_data["code"]:
        update_data["code"] = update_data["code"].strip().upper()
        duplicate = await db.faculties.find_one({"code": update_data["code"]})
        if duplicate and duplicate.get("_id") != faculty_obj_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Faculty code already exists")
    if "university_name" in update_data and update_data["university_name"]:
        update_data["university_name"] = update_data["university_name"].strip()
    if "university_code" in update_data and update_data["university_code"]:
        update_data["university_code"] = update_data["university_code"].strip().upper()
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    update_data["schema_version"] = FACULTY_SCHEMA_VERSION
    result = await db.faculties.update_one({"_id": faculty_obj_id}, build_state_update(update_data))
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")
    updated = await db.faculties.find_one({"_id": faculty_obj_id})
    return FacultyOut(**faculty_public(updated))


@router.delete("/{faculty_id}")
async def delete_faculty(
    faculty_id: str,
    review_id: str | None = Query(default=None),
    current_user=Depends(require_permission("faculties.manage")),
) -> dict:
    actor_user_id = str(current_user.get("_id") or "") or None
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="faculties.delete",
        entity_type="faculty",
        entity_id=faculty_id,
        stage="requested",
        detail="Faculty delete requested",
        review_id=review_id,
        metadata={"admin_type": current_user.get("admin_type")},
    )
    governance_completed = bool(await enforce_review_approval(
        current_user=current_user,
        review_id=review_id,
        action="faculties.delete",
        entity_type="faculty",
        entity_id=faculty_id,
    ))
    result = await db.faculties.update_one(
        {"_id": parse_object_id(faculty_id), "is_active": True},
        build_soft_delete_update(
            deleted_by=str(current_user.get("_id")),
            extra_fields={"schema_version": FACULTY_SCHEMA_VERSION},
        ),
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="faculties.delete",
        entity_type="faculty",
        entity_id=faculty_id,
        stage="completed",
        detail="Faculty archived",
        review_id=review_id,
        governance_completed=governance_completed,
        outcome="archived",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    return {"message": "Faculty archived"}
