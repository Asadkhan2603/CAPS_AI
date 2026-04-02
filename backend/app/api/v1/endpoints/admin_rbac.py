from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import check_role
from app.core.security import get_password_hash
from app.core.schema_versions import USER_SCHEMA_VERSION
from app.schemas.rbac import (
    RbacAdminCreate,
    RbacAdminOut,
    RbacAdminStatusUpdate,
    RbacAdminUpdate,
    RbacDesignOut,
    RbacPermissionOut,
    RbacRoleCreate,
    RbacRoleOut,
    RbacRoleUpdate,
)
from app.services.audit import log_audit_event
from app.services.rbac import (
    build_rbac_design_payload,
    create_role,
    delete_role,
    ensure_default_rbac_state,
    get_permission_catalog,
    get_role_by_id,
    initialize_admin_role_fields,
    list_roles,
    replace_scope_assignments,
    replace_user_permission_overrides,
    serialize_admin_user,
    update_role,
)

router = APIRouter()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def _require_super_admin(current_user=Depends(check_role("SUPER_ADMIN"))):
    return current_user


async def _get_admin_user_or_404(user_id: str) -> dict:
    user = await db.users.find_one({"_id": parse_object_id(user_id), "role": "admin"})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")
    return user


@router.get("/design", response_model=RbacDesignOut)
async def get_rbac_design(
    _current_user=Depends(_require_super_admin),
) -> RbacDesignOut:
    await ensure_default_rbac_state(db)
    return RbacDesignOut(**build_rbac_design_payload())


@router.get("/permissions", response_model=list[RbacPermissionOut])
async def get_permissions(
    _current_user=Depends(_require_super_admin),
) -> list[RbacPermissionOut]:
    return [RbacPermissionOut(**item) for item in await get_permission_catalog(db)]


@router.get("/roles", response_model=list[RbacRoleOut])
async def get_roles(
    _current_user=Depends(_require_super_admin),
) -> list[RbacRoleOut]:
    return [RbacRoleOut(**item) for item in await list_roles(db)]


@router.post("/roles", response_model=RbacRoleOut, status_code=status.HTTP_201_CREATED)
async def create_rbac_role(
    payload: RbacRoleCreate,
    current_user=Depends(_require_super_admin),
) -> RbacRoleOut:
    created = await create_role(payload.model_dump(), database=db)
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="create_role",
        action_type="rbac_role_create",
        entity_type="rbac_role",
        entity_id=created["id"],
        detail=f"Created RBAC role {created['code']}",
        new_value=created,
        severity="high",
    )
    return RbacRoleOut(**created)


@router.patch("/roles/{role_id}", response_model=RbacRoleOut)
async def update_rbac_role(
    role_id: str,
    payload: RbacRoleUpdate,
    current_user=Depends(_require_super_admin),
) -> RbacRoleOut:
    existing = await get_role_by_id(role_id, db)
    updated = await update_role(role_id, payload.model_dump(exclude_unset=True), database=db)
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="update_role",
        action_type="rbac_role_update",
        entity_type="rbac_role",
        entity_id=role_id,
        detail=f"Updated RBAC role {updated['code']}",
        old_value=existing,
        new_value=updated,
        severity="high",
    )
    return RbacRoleOut(**updated)


@router.delete("/roles/{role_id}", response_model=RbacRoleOut)
async def remove_rbac_role(
    role_id: str,
    current_user=Depends(_require_super_admin),
) -> RbacRoleOut:
    existing = await get_role_by_id(role_id, db)
    deleted = await delete_role(role_id, database=db)
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="delete_role",
        action_type="rbac_role_delete",
        entity_type="rbac_role",
        entity_id=role_id,
        detail=f"Deleted RBAC role {deleted['code']}",
        old_value=existing,
        new_value=deleted,
        severity="high",
    )
    return RbacRoleOut(**deleted)


@router.get("/admins", response_model=list[RbacAdminOut])
async def list_admins(
    include_deleted: bool = Query(default=False),
    _current_user=Depends(_require_super_admin),
) -> list[RbacAdminOut]:
    query = {"role": "admin"}
    if not include_deleted:
        query["status"] = {"$ne": "deleted"}
    rows = await db.users.find(query).sort("created_at", -1).to_list(length=500)
    items = []
    for row in rows:
        items.append(RbacAdminOut(**(await serialize_admin_user(row, database=db))))
    return items


@router.post("/admins", response_model=RbacAdminOut, status_code=status.HTTP_201_CREATED)
async def create_admin(
    payload: RbacAdminCreate,
    current_user=Depends(_require_super_admin),
) -> RbacAdminOut:
    email = payload.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")

    document = {
        "full_name": payload.full_name.strip(),
        "email": email,
        "hashed_password": get_password_hash(payload.password),
        "role": "admin",
        "extended_roles": [],
        "role_scope": {},
        "is_active": payload.is_active,
        "status": "active" if payload.is_active else "inactive",
        "must_change_password": False,
        "created_at": _utc_now(),
        "updated_at": None,
        "deleted_at": None,
        "schema_version": USER_SCHEMA_VERSION,
    }
    document = await initialize_admin_role_fields(document, role_code=payload.role_code, database=db)
    result = await db.users.insert_one(document)
    user_id = str(result.inserted_id)
    await replace_user_permission_overrides(
        user_id,
        allow_permission_keys=payload.allow_permission_keys,
        deny_permission_keys=payload.deny_permission_keys,
        database=db,
    )
    await replace_scope_assignments(
        user_id,
        [item.model_dump(exclude_none=True) for item in payload.scopes],
        database=db,
    )
    created = await _get_admin_user_or_404(user_id)
    serialized = await serialize_admin_user(created, database=db)
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="create_admin",
        action_type="rbac_admin_create",
        entity_type="admin_user",
        entity_id=user_id,
        detail=f"Created admin user {email}",
        new_value=serialized,
        severity="high",
    )
    return RbacAdminOut(**serialized)


@router.get("/admins/{user_id}", response_model=RbacAdminOut)
async def get_admin(
    user_id: str,
    _current_user=Depends(_require_super_admin),
) -> RbacAdminOut:
    admin_user = await _get_admin_user_or_404(user_id)
    return RbacAdminOut(**(await serialize_admin_user(admin_user, database=db)))


@router.patch("/admins/{user_id}", response_model=RbacAdminOut)
async def update_admin(
    user_id: str,
    payload: RbacAdminUpdate,
    current_user=Depends(_require_super_admin),
) -> RbacAdminOut:
    admin_user = await _get_admin_user_or_404(user_id)
    old_serialized = await serialize_admin_user(admin_user, database=db)
    if str(current_user["_id"]) == user_id:
        if payload.is_active is False:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")
        if payload.role_code is not None and payload.role_code.strip().upper() != "SUPER_ADMIN":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot change your own role away from SUPER_ADMIN")
    set_data = {"updated_at": _utc_now(), "schema_version": USER_SCHEMA_VERSION}
    if payload.full_name is not None:
        set_data["full_name"] = payload.full_name.strip()
    if payload.is_active is not None:
        set_data["is_active"] = payload.is_active
        set_data["status"] = "active" if payload.is_active else "inactive"
    if payload.role_code is not None:
        role_fields = await initialize_admin_role_fields(
            {"role": "admin", "admin_type": payload.role_code.lower(), "is_active": set_data.get("is_active", admin_user.get("is_active", True))},
            role_code=payload.role_code,
            database=db,
        )
        set_data["role_id"] = role_fields.get("role_id")
        set_data["rbac_role_code"] = role_fields.get("rbac_role_code")
        set_data["admin_type"] = role_fields.get("admin_type")

    await db.users.update_one({"_id": admin_user["_id"]}, {"$set": set_data})
    if payload.scopes is not None:
        await replace_scope_assignments(
            user_id,
            [item.model_dump(exclude_none=True) for item in payload.scopes],
            database=db,
        )
    if payload.allow_permission_keys is not None or payload.deny_permission_keys is not None:
        await replace_user_permission_overrides(
            user_id,
            allow_permission_keys=payload.allow_permission_keys or [],
            deny_permission_keys=payload.deny_permission_keys or [],
            database=db,
        )
    updated = await _get_admin_user_or_404(user_id)
    serialized = await serialize_admin_user(updated, database=db)
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="update_admin",
        action_type="rbac_admin_update",
        entity_type="admin_user",
        entity_id=user_id,
        detail=f"Updated admin user {serialized['email']}",
        old_value=old_serialized,
        new_value=serialized,
        severity="high",
    )
    return RbacAdminOut(**serialized)


@router.patch("/admins/{user_id}/status", response_model=RbacAdminOut)
async def update_admin_status(
    user_id: str,
    payload: RbacAdminStatusUpdate,
    current_user=Depends(_require_super_admin),
) -> RbacAdminOut:
    if str(current_user["_id"]) == user_id and not payload.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")
    admin_user = await _get_admin_user_or_404(user_id)
    await db.users.update_one(
        {"_id": admin_user["_id"]},
        {
            "$set": {
                "is_active": payload.is_active,
                "status": "active" if payload.is_active else "inactive",
                "updated_at": _utc_now(),
                "schema_version": USER_SCHEMA_VERSION,
            }
        },
    )
    updated = await _get_admin_user_or_404(user_id)
    serialized = await serialize_admin_user(updated, database=db)
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="activate_admin" if payload.is_active else "deactivate_admin",
        action_type="rbac_admin_status",
        entity_type="admin_user",
        entity_id=user_id,
        detail=f"{'Activated' if payload.is_active else 'Deactivated'} admin user {serialized['email']}",
        old_value={"is_active": admin_user.get("is_active", True), "status": admin_user.get("status")},
        new_value={"is_active": payload.is_active, "status": serialized["status"]},
        severity="high",
    )
    return RbacAdminOut(**serialized)


@router.delete("/admins/{user_id}", response_model=RbacAdminOut)
async def soft_delete_admin(
    user_id: str,
    current_user=Depends(_require_super_admin),
) -> RbacAdminOut:
    if str(current_user["_id"]) == user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete yourself")
    admin_user = await _get_admin_user_or_404(user_id)
    old_serialized = await serialize_admin_user(admin_user, database=db)
    await db.users.update_one(
        {"_id": admin_user["_id"]},
        {
            "$set": {
                "is_active": False,
                "status": "deleted",
                "deleted_at": _utc_now(),
                "updated_at": _utc_now(),
                "schema_version": USER_SCHEMA_VERSION,
            }
        },
    )
    deleted = await _get_admin_user_or_404(user_id)
    serialized = await serialize_admin_user(deleted, database=db)
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="delete_admin",
        action_type="rbac_admin_delete",
        entity_type="admin_user",
        entity_id=user_id,
        detail=f"Soft deleted admin user {serialized['email']}",
        old_value=old_serialized,
        new_value=serialized,
        severity="high",
    )
    return RbacAdminOut(**serialized)
