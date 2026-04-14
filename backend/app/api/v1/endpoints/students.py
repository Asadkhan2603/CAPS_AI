from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import STUDENT_SCHEMA_VERSION
from app.core.security import require_permission, require_roles
from app.models.students import student_public
from app.schemas.student import (
    StudentCreate,
    StudentDuplicateCaseOut,
    StudentMergeExecuteIn,
    StudentMergeExecuteOut,
    StudentMergePreviewIn,
    StudentMergePreviewOut,
    StudentOut,
    StudentUpdate,
)
from app.services.academic_students import resolve_student_placement_snapshot
from app.services.audit import log_audit_event
from app.services.public_ids import persist_public_id, persist_public_id_update
from app.services.student_merge import execute_student_merge, list_duplicate_cases, preview_merge_case

router = APIRouter()


async def _student_out(document: dict) -> StudentOut:
    placement = await resolve_student_placement_snapshot(document, database=db)
    return StudentOut(**student_public({**document, **placement}))


async def _resolve_user_id(*, user_id: str | None, email: str | None) -> str | None:
    normalized_user_id = str(user_id or "").strip() or None
    if normalized_user_id:
        user = await db.users.find_one({"_id": parse_object_id(normalized_user_id), "is_active": True})
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User not found for provided user_id")
        if user.get("role") != "student":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user_id must reference a student user")
        return normalized_user_id

    normalized_email = (email or "").strip().lower()
    if not normalized_email:
        return None
    user = await db.users.find_one({"email": normalized_email, "role": "student", "is_active": True}, {"_id": 1})
    return str(user["_id"]) if user and user.get("_id") else None


@router.get("/", response_model=List[StudentOut])
async def list_students(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    class_id: str | None = Query(default=None),
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
    if class_id:
        query["class_id"] = class_id
    if is_active is not None:
        query["is_active"] = is_active

    cursor = db.students.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [await _student_out(item) for item in items]


@router.get("/duplicate-audit")
async def student_duplicate_audit(
    _current_user=Depends(require_permission("academic:manage")),
) -> dict:
    rows = await db.students.find({}, {"full_name": 1, "roll_number": 1, "email": 1, "user_id": 1, "class_id": 1, "is_active": 1}).to_list(length=5000)
    groupings: dict[tuple[str, str], list[dict]] = {}
    for item in rows:
        keys = []
        if item.get("roll_number"):
            keys.append(("roll_number", str(item.get("roll_number")).strip().lower()))
        if item.get("email"):
            keys.append(("email", str(item.get("email")).strip().lower()))
        if item.get("user_id"):
            keys.append(("user_id", str(item.get("user_id")).strip()))
        for key_type, key_value in keys:
            if not key_value:
                continue
            groupings.setdefault((key_type, key_value), []).append(item)

    duplicate_groups = []
    for (key_type, key_value), items in groupings.items():
        if len(items) < 2:
            continue
        duplicate_groups.append(
            {
                "match_type": key_type,
                "match_value": key_value,
                "count": len(items),
                "students": [
                    {
                        "id": str(item.get("_id")),
                        "full_name": item.get("full_name"),
                        "roll_number": item.get("roll_number"),
                        "email": item.get("email"),
                        "user_id": item.get("user_id"),
                        "class_id": item.get("class_id"),
                        "is_active": bool(item.get("is_active", True)),
                    }
                    for item in items
                ],
            }
        )

    duplicate_groups.sort(key=lambda item: (-item["count"], item["match_type"], item["match_value"]))
    summary = {
        "total_students": len(rows),
        "duplicate_groups": len(duplicate_groups),
        "roll_number_groups": sum(1 for item in duplicate_groups if item["match_type"] == "roll_number"),
        "email_groups": sum(1 for item in duplicate_groups if item["match_type"] == "email"),
        "user_id_groups": sum(1 for item in duplicate_groups if item["match_type"] == "user_id"),
    }
    return {"summary": summary, "groups": duplicate_groups[:50]}


@router.get("/duplicate-cases", response_model=List[StudentDuplicateCaseOut])
async def student_duplicate_cases(
    limit: int = Query(default=25, ge=1, le=100),
    _current_user=Depends(require_roles(["admin"])),
) -> List[StudentDuplicateCaseOut]:
    return [StudentDuplicateCaseOut(**item) for item in await list_duplicate_cases(database=db, limit=limit)]


@router.post("/merge/preview", response_model=StudentMergePreviewOut)
async def preview_student_merge(
    payload: StudentMergePreviewIn,
    _current_user=Depends(require_roles(["admin"])),
) -> StudentMergePreviewOut:
    preview = await preview_merge_case(
        seed_student_ids=payload.seed_student_ids,
        preferred_primary_student_id=payload.preferred_primary_student_id,
        database=db,
    )
    return StudentMergePreviewOut(**preview)


@router.post("/merge/execute", response_model=StudentMergeExecuteOut)
async def execute_student_merge_endpoint(
    payload: StudentMergeExecuteIn,
    current_user=Depends(require_roles(["admin"])),
) -> StudentMergeExecuteOut:
    if not payload.confirm_hard_delete:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="confirm_hard_delete must be true")

    result = await execute_student_merge(
        primary_student_id=payload.primary_student_id,
        duplicate_student_ids=payload.duplicate_student_ids,
        resolved_profile=payload.resolved_profile.model_dump(),
        actor_user_id=str(current_user.get("_id") or ""),
        reason=payload.reason,
        database=db,
    )
    audit_log = await log_audit_event(
        actor_user_id=str(current_user.get("_id") or ""),
        action="merge_student_duplicates",
        entity_type="student",
        entity_id=payload.primary_student_id,
        detail=payload.reason,
        old_value={
            "deleted_student_ids": result["deleted_student_ids"],
            "duplicate_student_ids": payload.duplicate_student_ids,
        },
        new_value=result["audit_payload"],
        severity="high",
    )
    return StudentMergeExecuteOut(
        merged_student=await _student_out(result["merged_student_document"]),
        deleted_student_ids=result["deleted_student_ids"],
        rewrite_counts=result["rewrite_counts"],
        warnings=result["warnings"],
        audit_log_id=str(audit_log.get("_id")) if audit_log and audit_log.get("_id") else None,
    )


@router.get("/{student_id}", response_model=StudentOut)
async def get_student(
    student_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> StudentOut:
    item = await db.students.find_one({"_id": parse_object_id(student_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return await _student_out(item)


@router.post("/", response_model=StudentOut, status_code=status.HTTP_201_CREATED)
async def create_student(
    payload: StudentCreate,
    _current_user=Depends(require_permission("academic:manage")),
) -> StudentOut:
    duplicate_roll = await db.students.find_one({"roll_number": payload.roll_number.strip()})
    if duplicate_roll:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Roll number already exists")

    if payload.class_id:
        class_doc = await db.classes.find_one({"_id": parse_object_id(payload.class_id)})
        if not class_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Class not found for provided class_id",
            )
    if payload.group_id:
        group_doc = await db.groups.find_one({"_id": parse_object_id(payload.group_id), "is_active": True})
        if not group_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group not found for provided group_id",
            )
        if payload.class_id and group_doc.get("section_id") != payload.class_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="group_id does not belong to provided class_id",
            )

    document = {
        "full_name": payload.full_name.strip(),
        "roll_number": payload.roll_number.strip(),
        "email": payload.email.lower().strip() if payload.email else None,
        "user_id": await _resolve_user_id(user_id=payload.user_id, email=payload.email),
        "class_id": payload.class_id,
        "group_id": payload.group_id,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "schema_version": STUDENT_SCHEMA_VERSION,
    }
    persist_public_id(document, kind="student")
    result = await db.students.insert_one(document)
    created = await db.students.find_one({"_id": result.inserted_id})
    return await _student_out(created)


@router.put("/{student_id}", response_model=StudentOut)
async def update_student(
    student_id: str,
    payload: StudentUpdate,
    _current_user=Depends(require_permission("academic:manage")),
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
    if "class_id" in update_data and update_data["class_id"]:
        class_doc = await db.classes.find_one({"_id": parse_object_id(update_data["class_id"])})
        if not class_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Class not found for provided class_id",
            )
    target_class_id = update_data.get("class_id", current.get("class_id"))
    target_group_id = update_data.get("group_id", current.get("group_id"))
    if target_group_id:
        group_doc = await db.groups.find_one({"_id": parse_object_id(target_group_id), "is_active": True})
        if not group_doc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Group not found for provided group_id",
            )
        if target_class_id and group_doc.get("section_id") != target_class_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="group_id does not belong to provided class_id",
            )

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    if "user_id" in update_data or "email" in update_data:
        update_data["user_id"] = await _resolve_user_id(
            user_id=update_data.get("user_id", current.get("user_id")),
            email=update_data.get("email", current.get("email")),
        )
    persist_public_id_update(current, update_data, kind="student")

    result = await db.students.update_one(
        {"_id": student_obj_id},
        {"$set": {**update_data, "schema_version": STUDENT_SCHEMA_VERSION}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    updated = await db.students.find_one({"_id": student_obj_id})
    return await _student_out(updated)


@router.delete("/{student_id}")
async def delete_student(
    student_id: str,
    _current_user=Depends(require_permission("academic:manage")),
) -> dict:
    result = await db.students.delete_one({"_id": parse_object_id(student_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")
    return {"message": "Student deleted"}
