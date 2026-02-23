from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission
from app.models.users import user_public
from app.schemas.user import UserExtensionRolesUpdate, UserOut
from app.services.audit import log_audit_event

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


@router.patch("/{user_id}/extensions", response_model=UserOut)
async def update_user_extension_roles(
    user_id: str,
    payload: UserExtensionRolesUpdate,
    current_user=Depends(require_permission("users.update")),
) -> UserOut:
    user_obj_id = parse_object_id(user_id)
    user = await db.users.find_one({"_id": user_obj_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    role = user.get("role")
    allowed = ROLE_ALLOWED_EXTENSIONS.get(role, set())
    if not allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This role does not support extension roles")
    invalid = [item for item in payload.extended_roles if item not in allowed]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid extension roles for {role}: {', '.join(invalid)}",
        )

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
                    {"$set": {"class_coordinator_user_id": None}},
                )
                await db.classes.update_one(
                    {"_id": parse_object_id(class_id)},
                    {"$set": {"class_coordinator_user_id": user_id}},
                )
                class_scope["course_id"] = class_doc.get("course_id")
                class_scope["year_id"] = class_doc.get("year_id")
                role_scope["class_coordinator"] = class_scope
        else:
            role_scope.pop("class_coordinator", None)
            await db.classes.update_many(
                {"class_coordinator_user_id": user_id},
                {"$set": {"class_coordinator_user_id": None}},
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
                    {"$set": {"president_user_id": None}},
                )
                await db.clubs.update_one(
                    {"_id": parse_object_id(club_id)},
                    {"$set": {"president_user_id": user_id}},
                )
                role_scope["club_president"] = {"club_id": club_id}
        else:
            role_scope.pop("club_president", None)
            await db.clubs.update_many(
                {"president_user_id": user_id},
                {"$set": {"president_user_id": None}},
            )

        role_scope.pop("class_coordinator", None)

    await db.users.update_one(
        {"_id": user_obj_id},
        {"$set": {"extended_roles": payload.extended_roles, "role_scope": role_scope}},
    )
    updated = await db.users.find_one({"_id": user_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="update_extensions",
        entity_type="user",
        entity_id=user_id,
        detail=f"Updated {role} extension roles",
    )
    return UserOut(**user_public(updated))
