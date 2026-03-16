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
from app.services.master_hierarchy import (
    build_faculty_business_id,
    coalesce_code,
    coalesce_text,
    ensure_master_hierarchy_change_is_safe,
    normalize_code,
)
from app.services.audit import log_destructive_action_event
from app.services.governance import enforce_review_approval

router = APIRouter()


def _materialize_faculty_names(payload: FacultyCreate | FacultyUpdate) -> tuple[str | None, str | None, str | None]:
    faculty_name = coalesce_text(getattr(payload, "faculty_name", None), getattr(payload, "name", None))
    faculty_code = coalesce_code(getattr(payload, "faculty_code", None), getattr(payload, "code", None))
    faculty_id = normalize_code(getattr(payload, "faculty_id", None))
    if faculty_code and not faculty_id:
        faculty_id = build_faculty_business_id(faculty_code)
    return faculty_name, faculty_code, faculty_id


async def _resolve_university_fields(
    *,
    university_id: str | None,
    university_master_id: str | None,
    university_name: str | None,
    require_existing: bool,
) -> tuple[str | None, str | None, str | None, str | None]:
    if university_id:
        university = await db.universities.find_one({"_id": parse_object_id(university_id)})
        if not university:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="University not found for provided university_id")
        university_business_id = str(university.get("university_id") or "")
        return str(university["_id"]), university_business_id, str(university.get("university_name") or ""), university_business_id

    resolved_master_id = normalize_code(university_master_id)
    resolved_name = coalesce_text(university_name)
    if resolved_master_id:
        university = await db.universities.find_one({"university_id": resolved_master_id})
        if not university:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="University not found for provided university_master_id",
            )
        university_business_id = str(university.get("university_id") or "")
        return str(university["_id"]), university_business_id, str(university.get("university_name") or ""), university_business_id
    if require_existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faculty must be linked to an existing university.",
        )
    return None, resolved_master_id, resolved_name, resolved_master_id


@router.get("/", response_model=List[FacultyOut])
async def list_faculties(
    university_id: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[FacultyOut]:
    query = {}
    if university_id:
        query["university_id"] = university_id
    if q:
        query["$or"] = [
            {"faculty_name": {"$regex": q, "$options": "i"}},
            {"name": {"$regex": q, "$options": "i"}},
            {"faculty_code": {"$regex": q, "$options": "i"}},
            {"code": {"$regex": q, "$options": "i"}},
            {"faculty_id": {"$regex": q, "$options": "i"}},
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
    faculty_name, faculty_code, faculty_id = _materialize_faculty_names(payload)
    if not faculty_name or not faculty_code or not faculty_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Faculty name and code are required")
    university_ref_id, university_master_id, resolved_university_name, university_code = await _resolve_university_fields(
        university_id=payload.university_id,
        university_master_id=payload.university_master_id,
        university_name=payload.university_name,
        require_existing=True,
    )
    duplicate = await db.faculties.find_one(
        {
            "$or": [
                {"faculty_id": faculty_id},
                {"faculty_code": faculty_code},
                {"code": faculty_code},
            ]
        }
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Faculty ID or code already exists")
    document = {
        "faculty_id": faculty_id,
        "faculty_code": faculty_code,
        "faculty_name": faculty_name,
        "name": faculty_name,
        "code": faculty_code,
        "university_id": university_ref_id,
        "university_master_id": university_master_id,
        "university_name": resolved_university_name,
        "university_code": university_code,
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
    current = await db.faculties.find_one({"_id": faculty_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")
    update_data = payload.model_dump(exclude_none=True)
    if any(key in update_data for key in ("university_name", "university_code")) and not any(
        key in update_data for key in ("university_id", "university_master_id")
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="University lineage fields are derived from the selected university and cannot be edited independently.",
        )
    next_name, next_code, next_faculty_id = _materialize_faculty_names(payload)
    if any(key in update_data for key in ("faculty_name", "name")):
        update_data["faculty_name"] = next_name
        update_data["name"] = next_name
    if any(key in update_data for key in ("faculty_code", "code")):
        update_data["faculty_code"] = next_code
        update_data["code"] = next_code
    if any(key in update_data for key in ("faculty_id", "faculty_code", "code")):
        update_data["faculty_id"] = next_faculty_id
    if any(key in update_data for key in ("university_id", "university_master_id")):
        university_ref_id, university_master_id, resolved_university_name, university_code = await _resolve_university_fields(
            university_id=update_data.get("university_id", current.get("university_id")),
            university_master_id=update_data.get("university_master_id", current.get("university_master_id")),
            university_name=update_data.get("university_name", current.get("university_name")),
            require_existing=True,
        )
        if university_ref_id != current.get("university_id"):
            try:
                await ensure_master_hierarchy_change_is_safe(
                    db,
                    entity_kind="faculty",
                    entity_doc_id=faculty_id,
                    operation="move to another university",
                )
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        update_data["university_id"] = university_ref_id
        update_data["university_master_id"] = university_master_id
        update_data["university_name"] = resolved_university_name
        update_data["university_code"] = university_code
    next_code_value = update_data.get("faculty_code", current.get("faculty_code") or current.get("code"))
    next_id_value = update_data.get("faculty_id", current.get("faculty_id"))
    if next_code_value or next_id_value:
        duplicate = await db.faculties.find_one(
            {
                "_id": {"$ne": faculty_obj_id},
                "$or": [
                    {"faculty_id": next_id_value},
                    {"faculty_code": next_code_value},
                    {"code": next_code_value},
                ],
            }
        )
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Faculty ID or code already exists")
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
    try:
        await ensure_master_hierarchy_change_is_safe(
            db,
            entity_kind="faculty",
            entity_doc_id=faculty_id,
            operation="archive",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
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
