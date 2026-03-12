from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import CLASS_SCHEMA_VERSION, CLUB_SCHEMA_VERSION, USER_SCHEMA_VERSION
from app.core.security import get_password_hash, require_permission
from app.models.users import user_public
from app.schemas.user import UserCreate, UserExtensionRolesUpdate, UserOut
from app.services.audit import log_audit_event
from app.services.governance import enforce_review_approval

router = APIRouter()

ROLE_ALLOWED_EXTENSIONS = {
    "teacher": {"year_head", "class_coordinator", "club_coordinator"},
    "student": {"club_president"},
}


@router.get("/", response_model=List[UserOut])
async def list_users(
    _current_user=Depends(require_permission("users.read")),
) -> List[UserOut]:
    users = await db.users.find({}).to_list(length=1000)
    return [UserOut(**user_public(user)) for user in users]


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    _current_user=Depends(require_permission("users.update")),
) -> UserOut:
    email = payload.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")

    extended_roles = payload.extended_roles or []
    if payload.role != "teacher" and extended_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extended roles are only allowed for teacher accounts",
        )

    if payload.role == "admin":
        admin_type = payload.admin_type or "admin"
    else:
        if payload.admin_type is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="admin_type is allowed only for admin accounts",
            )
        admin_type = None

    document = {
        "full_name": payload.full_name.strip(),
        "email": email,
        "hashed_password": get_password_hash(payload.password),
        "role": payload.role,
        "admin_type": admin_type,
        "extended_roles": extended_roles,
        "role_scope": {},
        "is_active": True,
        "must_change_password": False,
        "schema_version": USER_SCHEMA_VERSION,
    }
    result = await db.users.insert_one(document)
    created = await db.users.find_one({"_id": result.inserted_id})
    return UserOut(**user_public(created))


@router.patch("/{user_id}/extensions", response_model=UserOut)
async def update_user_extension_roles(
    user_id: str,
    payload: UserExtensionRolesUpdate,
    review_id: str | None = Query(default=None),
    current_user=Depends(require_permission("users.update")),
) -> UserOut:
    user_obj_id = parse_object_id(user_id)
    user = await db.users.find_one({"_id": user_obj_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    role = user.get("role")
    await enforce_review_approval(
        current_user=current_user,
        review_id=review_id,
        action="users.update.extensions",
        entity_type="user",
        entity_id=user_id,
        review_type="role_change",
    )
    allowed = ROLE_ALLOWED_EXTENSIONS.get(role, set())
    if not allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This role does not support extension roles")
    invalid = [item for item in payload.extended_roles if item not in allowed]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid extension roles for {role}: {', '.join(invalid)}",
        )

    previous_extensions = list(user.get("extended_roles") or [])
    previous_scope = dict(user.get("role_scope") or {})
    role_scope = payload.role_scope.model_dump(exclude_none=True) if payload.role_scope else {}

    if role == "teacher":
        if "class_coordinator" in payload.extended_roles:
            class_scope = role_scope.get("class_coordinator", {}) if isinstance(role_scope, dict) else {}
            class_id = class_scope.get("class_id")
            if class_id:
                class_doc = await db.classes.find_one({"_id": parse_object_id(class_id)})
                if not class_doc:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Class not found for class coordinator scope")
                await db.classes.update_many(
                    {"class_coordinator_user_id": user_id},
                    {"$set": {"class_coordinator_user_id": None, "schema_version": CLASS_SCHEMA_VERSION}},
                )
                await db.classes.update_one(
                    {"_id": parse_object_id(class_id)},
                    {"$set": {"class_coordinator_user_id": user_id, "schema_version": CLASS_SCHEMA_VERSION}},
                )
                class_scope["faculty_id"] = class_doc.get("faculty_id")
                class_scope["department_id"] = class_doc.get("department_id")
                class_scope["program_id"] = class_doc.get("program_id")
                class_scope["specialization_id"] = class_doc.get("specialization_id")
                class_scope["batch_id"] = class_doc.get("batch_id")
                class_scope["semester_id"] = class_doc.get("semester_id")
                role_scope["class_coordinator"] = class_scope
        else:
            role_scope.pop("class_coordinator", None)
            await db.classes.update_many(
                {"class_coordinator_user_id": user_id},
                {"$set": {"class_coordinator_user_id": None, "schema_version": CLASS_SCHEMA_VERSION}},
            )

        role_scope.pop("club_president", None)

    if role == "student":
        if "club_president" in payload.extended_roles:
            club_scope = role_scope.get("club_president", {}) if isinstance(role_scope, dict) else {}
            club_id = club_scope.get("club_id")
            if club_id:
                club_doc = await db.clubs.find_one({"_id": parse_object_id(club_id)})
                if not club_doc:
                    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Club not found for club president scope")
                await db.clubs.update_many(
                    {"president_user_id": user_id},
                    {"$set": {"president_user_id": None, "schema_version": CLUB_SCHEMA_VERSION}},
                )
                await db.clubs.update_one(
                    {"_id": parse_object_id(club_id)},
                    {"$set": {"president_user_id": user_id, "schema_version": CLUB_SCHEMA_VERSION}},
                )
                role_scope["club_president"] = {"club_id": club_id}
        else:
            role_scope.pop("club_president", None)
            await db.clubs.update_many(
                {"president_user_id": user_id},
                {"$set": {"president_user_id": None, "schema_version": CLUB_SCHEMA_VERSION}},
            )

        role_scope.pop("class_coordinator", None)

    await db.users.update_one(
        {"_id": user_obj_id},
        {
            "$set": {
                "extended_roles": payload.extended_roles,
                "role_scope": role_scope,
                "schema_version": USER_SCHEMA_VERSION,
            }
        },
    )
    updated = await db.users.find_one({"_id": user_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="update_extensions",
        entity_type="user",
        entity_id=user_id,
        action_type="role_change",
        detail=f"Updated {role} extension roles",
        old_value={"extended_roles": previous_extensions, "role_scope": previous_scope},
        new_value={"extended_roles": payload.extended_roles, "role_scope": role_scope},
        severity="medium",
    )
    return UserOut(**user_public(updated))


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: str,
    current_user=Depends(require_permission("users.update")),
) -> dict:
    user_obj_id = parse_object_id(user_id)
    if str(current_user.get("_id")) == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")

    user = await db.users.find_one({"_id": user_obj_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    await db.users.update_one(
        {"_id": user_obj_id},
        {"$set": {"is_active": False, "schema_version": USER_SCHEMA_VERSION}},
    )
    await db.classes.update_many(
        {"class_coordinator_user_id": user_id},
        {"$set": {"class_coordinator_user_id": None, "schema_version": CLASS_SCHEMA_VERSION}},
    )
    await db.clubs.update_many(
        {"coordinator_user_id": user_id},
        {"$set": {"coordinator_user_id": None, "schema_version": CLUB_SCHEMA_VERSION}},
    )
    await db.clubs.update_many(
        {"president_user_id": user_id},
        {"$set": {"president_user_id": None, "schema_version": CLUB_SCHEMA_VERSION}},
    )
    await log_audit_event(
        actor_user_id=str(current_user.get("_id")),
        action="deactivate_user",
        entity_type="user",
        entity_id=user_id,
        action_type="role_change",
        detail="User deactivated by super admin",
        severity="high",
    )
    return {"message": "User deactivated"}
