from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.users import user_public
from app.schemas.user import UserExtensionRolesUpdate, UserOut
from app.services.audit import log_audit_event

router = APIRouter()


@router.get("/", response_model=List[UserOut])
async def list_users(
    _current_user=Depends(require_roles(["admin"])),
) -> List[UserOut]:
    users = await db.users.find({}).to_list(length=1000)
    return [UserOut(**user_public(user)) for user in users]


@router.patch("/{user_id}/extensions", response_model=UserOut)
async def update_user_extension_roles(
    user_id: str,
    payload: UserExtensionRolesUpdate,
    current_user=Depends(require_roles(["admin"])),
) -> UserOut:
    user_obj_id = parse_object_id(user_id)
    user = await db.users.find_one({"_id": user_obj_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.get("role") != "teacher":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extension roles can only be assigned to teachers",
        )

    await db.users.update_one({"_id": user_obj_id}, {"$set": {"extended_roles": payload.extended_roles}})
    updated = await db.users.find_one({"_id": user_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="update_extensions",
        entity_type="user",
        entity_id=user_id,
        detail="Updated teacher extension roles",
    )
    return UserOut(**user_public(updated))
