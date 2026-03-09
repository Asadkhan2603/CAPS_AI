from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission, require_roles
from app.models.programs import program_public
from app.schemas.program import ProgramCreate, ProgramOut, ProgramUpdate

router = APIRouter()

MIN_DURATION_YEARS = 3
MAX_DURATION_YEARS = 5
SEMESTERS_PER_YEAR = 2
PROGRAM_DURATION_EDITOR_ADMIN_TYPES = {"super_admin", "academic_admin", "department_admin"}


def _validate_duration_years(duration_years: int) -> int:
    if duration_years < MIN_DURATION_YEARS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course duration must be at least 3 years.",
        )
    if duration_years > MAX_DURATION_YEARS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course duration cannot exceed 5 years.",
        )
    return int(duration_years)


def _current_admin_type(current_user: dict) -> str:
    return current_user.get("admin_type") or "admin"


def _ensure_program_duration_editor(current_user: dict) -> None:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin or department admin can configure course duration.",
        )
    if _current_admin_type(current_user) not in PROGRAM_DURATION_EDITOR_ADMIN_TYPES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admin or department admin can configure course duration.",
        )


async def _program_has_enrolled_semester_students(program_id: str) -> bool:
    cursor = db.classes.find(
        {"program_id": program_id, "semester_id": {"$nin": [None, ""]}},
        {"_id": 1},
    )
    batch_ids: list[str] = []
    async for item in cursor:
        if item.get("_id"):
            batch_ids.append(str(item["_id"]))
        if len(batch_ids) >= 500:
            if await db.enrollments.find_one({"class_id": {"$in": batch_ids}}):
                return True
            batch_ids.clear()
    if batch_ids and await db.enrollments.find_one({"class_id": {"$in": batch_ids}}):
        return True
    return False


async def _sync_program_semesters(program_id: str, total_semesters: int) -> None:
    now = datetime.now(timezone.utc)
    batches = await db.batches.find({"program_id": program_id}, {"_id": 1}).to_list(length=5000)
    for batch in batches:
        batch_id = str(batch["_id"])
        existing = await db.semesters.find({"batch_id": batch_id}, {"_id": 1, "semester_number": 1, "is_active": 1}).to_list(length=200)
        by_number = {int(item.get("semester_number")): item for item in existing if item.get("semester_number") is not None}

        # Ensure expected semesters exist and are active.
        for semester_number in range(1, total_semesters + 1):
            current = by_number.get(semester_number)
            if not current:
                await db.semesters.insert_one(
                    {
                        "batch_id": batch_id,
                        "semester_number": semester_number,
                        "label": f"Semester {semester_number}",
                        "is_active": True,
                        "created_at": now,
                    }
                )
            elif not current.get("is_active", True):
                await db.semesters.update_one(
                    {"_id": current["_id"]},
                    {"$set": {"is_active": True, "updated_at": now}},
                )

        # Archive semesters beyond configured total.
        await db.semesters.update_many(
            {"batch_id": batch_id, "semester_number": {"$gt": total_semesters}, "is_active": True},
            {"$set": {"is_active": False, "updated_at": now}},
        )


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
    current_user=Depends(require_roles(["admin"])),
) -> ProgramOut:
    _ensure_program_duration_editor(current_user)
    department = await db.departments.find_one({"_id": parse_object_id(payload.department_id)})
    if not department:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department not found for provided department_id")
    duration_years = _validate_duration_years(payload.duration_years)
    normalized_code = payload.code.strip().upper()
    existing = await db.programs.find_one({"code": normalized_code})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program code already exists")
    document = {
        "name": payload.name.strip(),
        "code": normalized_code,
        "department_id": payload.department_id,
        "duration_years": duration_years,
        "total_semesters": duration_years * SEMESTERS_PER_YEAR,
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
    current_user=Depends(require_roles(["admin"])),
) -> ProgramOut:
    _ensure_program_duration_editor(current_user)
    program_obj_id = parse_object_id(program_id)
    current = await db.programs.find_one({"_id": program_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")

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

    if "duration_years" in update_data:
        new_duration_years = _validate_duration_years(int(update_data["duration_years"]))
        previous_duration_years = int(current.get("duration_years") or 4)
        if new_duration_years != previous_duration_years and await _program_has_enrolled_semester_students(program_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot change course duration because students are already enrolled in existing semesters.",
            )
        update_data["duration_years"] = new_duration_years
        update_data["total_semesters"] = new_duration_years * SEMESTERS_PER_YEAR

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    result = await db.programs.update_one({"_id": program_obj_id}, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    updated = await db.programs.find_one({"_id": program_obj_id})
    if "duration_years" in update_data:
        await _sync_program_semesters(program_id, int(update_data["total_semesters"]))
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
