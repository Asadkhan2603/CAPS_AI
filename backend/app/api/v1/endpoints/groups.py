from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import GROUP_SCHEMA_VERSION
from app.core.security import require_roles
from app.models.groups import group_public
from app.schemas.group_item import GroupCreate, GroupOut, GroupUpdate
from app.services.class_slot_read_models import sync_class_slot_read_models_for_offering_query
from app.services.course_offering_read_models import sync_course_offering_read_models_for_query
from app.services.public_ids import persist_public_id, persist_public_id_update
from app.services.academic_students import resolve_student_academic_context_for_user

router = APIRouter()


async def _ensure_section_access(*, current_user: dict, section_id: str, write_mode: bool) -> dict:
    section = await db.classes.find_one({"_id": parse_object_id(section_id), "is_active": True})
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    role = current_user.get("role")
    if role == "admin":
        return section
    if role != "teacher":
        if write_mode:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to manage groups")
        return section
    owns = section.get("class_coordinator_user_id") == str(current_user.get("_id"))
    if write_mode and not owns:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only class coordinator can manage groups")
    return section


@router.get("/", response_model=List[GroupOut])
async def list_groups(
    section_id: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[GroupOut]:
    query = {}
    if section_id:
        await _ensure_section_access(current_user=current_user, section_id=section_id, write_mode=False)
        query["section_id"] = section_id
    if q:
        query["$or"] = [{"name": {"$regex": q, "$options": "i"}}, {"code": {"$regex": q, "$options": "i"}}]
    if is_active is not None:
        query["is_active"] = is_active
    if current_user.get("role") == "student":
        student = await resolve_student_academic_context_for_user(current_user, database=db)
        if not student or not student.get("canonical_class_id"):
            return []
        query["section_id"] = student.get("canonical_class_id")
    items = await db.groups.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [GroupOut(**group_public(item)) for item in items]


@router.post("/", response_model=GroupOut, status_code=status.HTTP_201_CREATED)
async def create_group(
    payload: GroupCreate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> GroupOut:
    await _ensure_section_access(current_user=current_user, section_id=payload.section_id, write_mode=True)
    duplicate = await db.groups.find_one(
        {"section_id": payload.section_id, "code": payload.code.strip().upper(), "is_active": True}
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Group code already exists in this section")
    document = {
        "section_id": payload.section_id,
        "name": payload.name.strip(),
        "code": payload.code.strip().upper(),
        "description": payload.description,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "schema_version": GROUP_SCHEMA_VERSION,
    }
    persist_public_id(document, kind="group")
    result = await db.groups.insert_one(document)
    created = await db.groups.find_one({"_id": result.inserted_id})
    return GroupOut(**group_public(created))


@router.put("/{group_id}", response_model=GroupOut)
async def update_group(
    group_id: str,
    payload: GroupUpdate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> GroupOut:
    group_obj_id = parse_object_id(group_id)
    current = await db.groups.find_one({"_id": group_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    await _ensure_section_access(current_user=current_user, section_id=current["section_id"], write_mode=True)
    update_data = payload.model_dump(exclude_none=True)
    if "name" in update_data:
        update_data["name"] = update_data["name"].strip()
    if "code" in update_data:
        update_data["code"] = update_data["code"].strip().upper()
        duplicate = await db.groups.find_one(
            {"section_id": current["section_id"], "code": update_data["code"], "_id": {"$ne": group_obj_id}, "is_active": True}
        )
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Group code already exists in this section")
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    persist_public_id_update(current, update_data, kind="group")
    await db.groups.update_one(
        {"_id": group_obj_id},
        {"$set": {**update_data, "schema_version": GROUP_SCHEMA_VERSION}},
    )
    updated = await db.groups.find_one({"_id": group_obj_id})
    await sync_course_offering_read_models_for_query(query={"group_id": group_id}, database=db)
    await sync_class_slot_read_models_for_offering_query(offering_query={"group_id": group_id}, database=db)
    return GroupOut(**group_public(updated))


@router.delete("/{group_id}")
async def delete_group(
    group_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> dict:
    group_obj_id = parse_object_id(group_id)
    current = await db.groups.find_one({"_id": group_obj_id, "is_active": True})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    await _ensure_section_access(current_user=current_user, section_id=current["section_id"], write_mode=True)
    await db.groups.update_one(
        {"_id": group_obj_id},
        {
            "$set": {
                "is_active": False,
                "deleted_at": datetime.now(timezone.utc),
                "schema_version": GROUP_SCHEMA_VERSION,
            }
        },
    )
    await sync_course_offering_read_models_for_query(query={"group_id": group_id}, database=db)
    await sync_class_slot_read_models_for_offering_query(offering_query={"group_id": group_id}, database=db)
    return {"message": "Group archived"}
