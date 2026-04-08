from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import db as core_db
from app.core.mongo import parse_object_id
from app.core.schema_versions import (
    PERMISSION_SCHEMA_VERSION,
    ROLE_PERMISSION_SCHEMA_VERSION,
    ROLE_SCHEMA_VERSION,
    USER_PERMISSION_SCHEMA_VERSION,
    USER_SCHEMA_VERSION,
    USER_SCOPE_SCHEMA_VERSION,
)
from app.models.rbac import permission_public, role_public, scope_public
from app.models.users import user_public

RBAC_PERMISSION_ACTIONS = (
    "view",
    "create",
    "edit",
    "delete",
    "approve",
    "assign_role",
    "activate",
    "deactivate",
    "export",
    "generate",
)

RBAC_PERMISSION_GROUPS: dict[str, dict[str, str]] = {
    "student_management": {
        "name": "Student Management",
        "description": "Student profile, lifecycle, and record administration.",
    },
    "faculty_management": {
        "name": "Faculty Management",
        "description": "Faculty and academic owner administration.",
    },
    "complaints": {
        "name": "Complaints",
        "description": "Complaint intake, triage, and review workflows.",
    },
    "reports": {
        "name": "Reports",
        "description": "Operational, audit, and academic reporting workflows.",
    },
    "users": {
        "name": "Users",
        "description": "User account administration, lifecycle, and role assignment.",
    },
    "communication": {
        "name": "Communication",
        "description": "Announcements, messaging, and outbound communication workflows.",
    },
    "clubs": {
        "name": "Clubs",
        "description": "Club administration, membership, and event operations.",
    },
    "subjects": {
        "name": "Subjects",
        "description": "Subject catalog administration and academic subject governance.",
    },
    "analytics": {
        "name": "Analytics",
        "description": "Analytical dashboards, data insights, and metric generation.",
    },
    "audit": {
        "name": "Audit",
        "description": "Audit trail review, export, and evidence workflows.",
    },
    "system": {
        "name": "System",
        "description": "Platform configuration, operational recovery, and system oversight.",
    },
}

SYSTEM_ADMIN_ROLE_DEFINITIONS: dict[str, dict[str, Any]] = {
    "SUPER_ADMIN": {
        "name": "Super Admin",
        "description": "Owns the RBAC system, admin lifecycle, and all platform permissions.",
        "scope_required": False,
    },
    "COMPLIANCE_ADMIN": {
        "name": "Compliance Admin",
        "description": "Owns complaints review and report compliance workflows.",
        "scope_required": False,
    },
    "ACADEMIC_ADMIN": {
        "name": "Academic Admin",
        "description": "Owns student and faculty academic administration.",
        "scope_required": False,
    },
    "YEAR_ADMIN": {
        "name": "Year Admin",
        "description": "Manages year-scoped student workflows and reporting.",
        "scope_required": True,
    },
    "HOD": {
        "name": "Head of Department",
        "description": "Manages department-scoped faculty and student oversight.",
        "scope_required": True,
    },
    "DEAN": {
        "name": "Dean",
        "description": "Approves and reviews academic operations across assigned units.",
        "scope_required": True,
    },
}

ADMIN_ROLE_CODE_ALIASES = {
    "super_admin": "SUPER_ADMIN",
    "compliance_admin": "COMPLIANCE_ADMIN",
    "academic_admin": "ACADEMIC_ADMIN",
    "year_admin": "YEAR_ADMIN",
    "hod": "HOD",
    "dean": "DEAN",
}

LEGACY_PERMISSION_ALIASES: dict[str, set[str]] = {
    "analytics.read": {"analytics.view"},
    "audit.read": {"audit.view"},
    "system.read": {"system.view"},
    "universities.manage": {"faculty_management.create", "faculty_management.edit", "faculty_management.delete"},
    "faculties.manage": {"faculty_management.create", "faculty_management.edit", "faculty_management.delete"},
    "departments.manage": {"faculty_management.create", "faculty_management.edit", "faculty_management.delete"},
    "programs.manage": {"student_management.create", "student_management.edit", "student_management.delete"},
    "specializations.manage": {"student_management.create", "student_management.edit", "student_management.delete"},
    "batches.manage": {"student_management.create", "student_management.edit", "student_management.delete"},
    "semesters.manage": {"student_management.create", "student_management.edit", "student_management.delete"},
    "sections.manage": {"student_management.create", "student_management.edit", "student_management.delete"},
    "students.manage": {"student_management.create", "student_management.edit", "student_management.delete"},
    "students.bulk_import": {"student_management.create", "student_management.activate"},
    "students.bulk_map": {"student_management.edit"},
    "sections.lock_mapping": {"student_management.approve"},
}


def _permission_keys(module_key: str, *actions: str) -> set[str]:
    return {f"{module_key}.{action}" for action in actions}


FULL_MODULE_ACTIONS = RBAC_PERMISSION_ACTIONS
MANAGEMENT_ACTIONS = ("view", "create", "edit", "delete", "approve", "activate", "deactivate", "export", "generate")
OVERSIGHT_ACTIONS = ("view", "approve", "export", "generate")
EDITOR_ACTIONS = ("view", "edit", "approve", "export", "generate")
CONTENT_AUTHOR_ACTIONS = ("view", "create", "edit", "approve")
CONTENT_EDITOR_ACTIONS = ("view", "create", "edit")
READ_AND_REPORT_ACTIONS = ("view", "export", "generate")


ALL_RBAC_PERMISSION_KEYS: set[str] = {
    f"{module_key}.{action}"
    for module_key in RBAC_PERMISSION_GROUPS
    for action in RBAC_PERMISSION_ACTIONS
}

DEFAULT_ROLE_PERMISSION_MATRIX: dict[str, set[str]] = {
    "SUPER_ADMIN": set(ALL_RBAC_PERMISSION_KEYS),
    "COMPLIANCE_ADMIN": _permission_keys("complaints", "view", "edit", "approve", "export", "generate")
    | _permission_keys("reports", *READ_AND_REPORT_ACTIONS)
    | _permission_keys("analytics", *READ_AND_REPORT_ACTIONS)
    | _permission_keys("audit", *READ_AND_REPORT_ACTIONS)
    | _permission_keys("system", "view"),
    "ACADEMIC_ADMIN": _permission_keys(
        "student_management",
        *MANAGEMENT_ACTIONS,
    )
    | _permission_keys(
        "faculty_management",
        *MANAGEMENT_ACTIONS,
    )
    | _permission_keys("subjects", *MANAGEMENT_ACTIONS)
    | _permission_keys("communication", "view", "create", "edit", "delete", "approve")
    | _permission_keys("clubs", "view", "create", "edit", "delete", "approve", "export", "generate")
    | _permission_keys("complaints", *OVERSIGHT_ACTIONS)
    | _permission_keys("reports", *READ_AND_REPORT_ACTIONS)
    | _permission_keys("analytics", *READ_AND_REPORT_ACTIONS),
    "YEAR_ADMIN": _permission_keys("student_management", "view", "edit", "approve", "activate", "deactivate", "export", "generate")
    | _permission_keys("subjects", *READ_AND_REPORT_ACTIONS)
    | _permission_keys("communication", *CONTENT_EDITOR_ACTIONS)
    | _permission_keys("complaints", "view", "approve")
    | _permission_keys("reports", *READ_AND_REPORT_ACTIONS),
    "HOD": _permission_keys("student_management", *OVERSIGHT_ACTIONS)
    | _permission_keys("faculty_management", "view", "edit", "approve", "activate", "deactivate", "export", "generate")
    | _permission_keys("subjects", *EDITOR_ACTIONS)
    | _permission_keys("communication", *CONTENT_AUTHOR_ACTIONS)
    | _permission_keys("complaints", "view", "approve")
    | _permission_keys("reports", *READ_AND_REPORT_ACTIONS),
    "DEAN": _permission_keys("student_management", *OVERSIGHT_ACTIONS)
    | _permission_keys("faculty_management", "view", "approve", "activate", "deactivate", "export", "generate")
    | _permission_keys("subjects", *OVERSIGHT_ACTIONS)
    | _permission_keys("communication", "view", "approve", "export", "generate")
    | _permission_keys("complaints", *OVERSIGHT_ACTIONS)
    | _permission_keys("reports", *OVERSIGHT_ACTIONS)
    | _permission_keys("analytics", *READ_AND_REPORT_ACTIONS)
    | _permission_keys("audit", *READ_AND_REPORT_ACTIONS),
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def get_collection(database: Any, name: str):
    collection = getattr(database, name, None)
    if collection is not None:
        return collection
    try:
        return database[name]
    except Exception:
        return None


def normalize_admin_role_code(raw_value: str | None) -> str | None:
    if not raw_value:
        return None
    normalized = raw_value.strip().upper()
    if normalized in SYSTEM_ADMIN_ROLE_DEFINITIONS:
        return normalized
    return ADMIN_ROLE_CODE_ALIASES.get(raw_value.strip().lower())


def is_rbac_enabled(database: Any | None = None) -> bool:
    active_db = database if database is not None else core_db
    return all(
        get_collection(active_db, name) is not None
        for name in ("roles", "permissions", "role_permissions", "user_permissions", "scopes")
    )


def build_rbac_design_payload() -> dict[str, Any]:
    roles = []
    for code, role_meta in SYSTEM_ADMIN_ROLE_DEFINITIONS.items():
        roles.append(
            {
                "code": code,
                "name": role_meta["name"],
                "description": role_meta["description"],
                "scope_required": role_meta["scope_required"],
                "permissions": sorted(DEFAULT_ROLE_PERMISSION_MATRIX.get(code, set())),
            }
        )
    permission_groups = [
        {
            "key": module_key,
            "name": meta["name"],
            "description": meta["description"],
            "actions": list(RBAC_PERMISSION_ACTIONS),
        }
        for module_key, meta in RBAC_PERMISSION_GROUPS.items()
    ]
    return {
        "roles": roles,
        "permission_groups": permission_groups,
        "scope_fields": ["department_id", "year_id"],
    }


async def ensure_default_rbac_state(database: Any | None = None) -> dict[str, Any]:
    active_db = database if database is not None else core_db
    if not is_rbac_enabled(active_db):
        return {"roles": {}, "permissions": {}}

    roles_collection = get_collection(active_db, "roles")
    permissions_collection = get_collection(active_db, "permissions")
    role_permissions_collection = get_collection(active_db, "role_permissions")

    permission_map: dict[str, dict[str, Any]] = {}
    now = utc_now()
    for module_key, meta in RBAC_PERMISSION_GROUPS.items():
        for action in RBAC_PERMISSION_ACTIONS:
            key = f"{module_key}.{action}"
            existing = await permissions_collection.find_one({"key": key})
            if existing is None:
                payload = {
                    "key": key,
                    "name": action,
                    "module": meta["name"],
                    "module_key": module_key,
                    "description": f"{action.replace('_', ' ').title()} access for {meta['name']}",
                    "is_system": True,
                    "is_active": True,
                    "created_at": now,
                    "updated_at": now,
                    "schema_version": PERMISSION_SCHEMA_VERSION,
                }
                result = await permissions_collection.insert_one(payload)
                existing = await permissions_collection.find_one({"_id": result.inserted_id})
            permission_map[key] = existing

    role_map: dict[str, dict[str, Any]] = {}
    for code, meta in SYSTEM_ADMIN_ROLE_DEFINITIONS.items():
        existing_role = await roles_collection.find_one({"code": code})
        if existing_role is None:
            payload = {
                "code": code,
                "name": meta["name"],
                "description": meta["description"],
                "scope_required": meta["scope_required"],
                "permission_groups": sorted(
                    {
                        permission_key.split(".", 1)[0]
                        for permission_key in DEFAULT_ROLE_PERMISSION_MATRIX.get(code, set())
                    }
                ),
                "is_system": True,
                "is_active": True,
                "created_at": now,
                "updated_at": now,
                "schema_version": ROLE_SCHEMA_VERSION,
            }
            result = await roles_collection.insert_one(payload)
            existing_role = await roles_collection.find_one({"_id": result.inserted_id})
        elif existing_role.get("scope_required") != meta["scope_required"]:
            await roles_collection.update_one(
                {"_id": existing_role["_id"]},
                {
                    "$set": {
                        "scope_required": meta["scope_required"],
                        "updated_at": now,
                        "schema_version": ROLE_SCHEMA_VERSION,
                    }
                },
            )
            existing_role = await roles_collection.find_one({"_id": existing_role["_id"]})
        role_map[code] = existing_role

        desired_permission_ids = {
            str(permission_map[key]["_id"])
            for key in DEFAULT_ROLE_PERMISSION_MATRIX.get(code, set())
            if key in permission_map
        }
        existing_rows = await role_permissions_collection.find(
            {"role_id": str(existing_role["_id"])}
        ).to_list(length=1000)
        existing_permission_ids = {row.get("permission_id") for row in existing_rows}

        for permission_id in desired_permission_ids - existing_permission_ids:
            await role_permissions_collection.insert_one(
                {
                    "role_id": str(existing_role["_id"]),
                    "permission_id": permission_id,
                    "created_at": now,
                    "schema_version": ROLE_PERMISSION_SCHEMA_VERSION,
                }
            )

    return {"roles": role_map, "permissions": permission_map}


async def resolve_admin_role_document(user: dict[str, Any], database: Any | None = None) -> dict[str, Any] | None:
    if user.get("role") != "admin":
        return None
    active_db = database if database is not None else core_db
    if not is_rbac_enabled(active_db):
        return None
    await ensure_default_rbac_state(active_db)

    roles_collection = get_collection(active_db, "roles")
    role_id = user.get("role_id")
    if isinstance(role_id, str) and ObjectId.is_valid(role_id):
        role_doc = await roles_collection.find_one({"_id": ObjectId(role_id)})
        if role_doc:
            return role_doc

    normalized_role_code = normalize_admin_role_code(
        user.get("rbac_role_code") or user.get("admin_type")
    )
    if normalized_role_code:
        return await roles_collection.find_one({"code": normalized_role_code})
    return None


async def initialize_admin_role_fields(
    document: dict[str, Any],
    *,
    role_code: str | None = None,
    database: Any | None = None,
) -> dict[str, Any]:
    active_db = database if database is not None else core_db
    normalized_role_code = normalize_admin_role_code(role_code or document.get("admin_type"))
    if not normalized_role_code or not is_rbac_enabled(active_db):
        return document
    state = await ensure_default_rbac_state(active_db)
    role_doc = state["roles"].get(normalized_role_code)
    if not role_doc:
        return document
    document["role_id"] = str(role_doc["_id"])
    document["rbac_role_code"] = normalized_role_code
    document["admin_type"] = normalized_role_code.lower()
    document["status"] = "active" if document.get("is_active", True) else "inactive"
    return document


async def list_scope_assignments(user_id: str, database: Any | None = None) -> list[dict[str, Any]]:
    active_db = database if database is not None else core_db
    scopes_collection = get_collection(active_db, "scopes")
    if scopes_collection is None:
        return []
    rows = await scopes_collection.find({"user_id": user_id}).to_list(length=500)
    return [scope_public(row) for row in rows]


async def replace_scope_assignments(
    user_id: str,
    scopes: list[dict[str, Any]],
    *,
    database: Any | None = None,
) -> list[dict[str, Any]]:
    active_db = database if database is not None else core_db
    scopes_collection = get_collection(active_db, "scopes")
    if scopes_collection is None:
        return []
    await scopes_collection.delete_many({"user_id": user_id})
    now = utc_now()
    created: list[dict[str, Any]] = []
    for scope in scopes:
        payload = {
            "user_id": user_id,
            "department_id": scope.get("department_id"),
            "year_id": scope.get("year_id"),
            "created_at": now,
            "updated_at": now,
            "schema_version": USER_SCOPE_SCHEMA_VERSION,
        }
        result = await scopes_collection.insert_one(payload)
        row = await scopes_collection.find_one({"_id": result.inserted_id})
        created.append(scope_public(row))
    return created


async def get_permission_catalog(database: Any | None = None) -> list[dict[str, Any]]:
    active_db = database if database is not None else core_db
    permissions_collection = get_collection(active_db, "permissions")
    if permissions_collection is None:
        return []
    await ensure_default_rbac_state(active_db)
    rows = await permissions_collection.find({"is_active": True}).sort("key", 1).to_list(length=500)
    return [permission_public(row) for row in rows]


async def get_role_permission_keys(role_id: str, database: Any | None = None) -> list[str]:
    active_db = database if database is not None else core_db
    role_permissions_collection = get_collection(active_db, "role_permissions")
    permissions_collection = get_collection(active_db, "permissions")
    if role_permissions_collection is None or permissions_collection is None:
        return []
    rows = await role_permissions_collection.find({"role_id": role_id}).to_list(length=500)
    permission_ids = [row.get("permission_id") for row in rows if row.get("permission_id")]
    if not permission_ids:
        return []
    permissions = await permissions_collection.find(
        {"_id": {"$in": [ObjectId(pid) for pid in permission_ids if ObjectId.is_valid(pid)]}}
    ).to_list(length=len(permission_ids))
    return sorted({permission.get("key") for permission in permissions if permission.get("key")})


async def get_role_by_id(role_id: str, database: Any | None = None) -> dict[str, Any]:
    active_db = database if database is not None else core_db
    roles_collection = get_collection(active_db, "roles")
    if roles_collection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RBAC roles are unavailable")
    role_doc = await roles_collection.find_one({"_id": parse_object_id(role_id)})
    if not role_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    permission_keys = await get_role_permission_keys(str(role_doc["_id"]), active_db)
    return role_public(role_doc, permission_keys=permission_keys)


async def list_roles(database: Any | None = None) -> list[dict[str, Any]]:
    active_db = database if database is not None else core_db
    roles_collection = get_collection(active_db, "roles")
    if roles_collection is None:
        return []
    await ensure_default_rbac_state(active_db)
    rows = await roles_collection.find({}).sort("code", 1).to_list(length=500)
    items = []
    for row in rows:
        permission_keys = await get_role_permission_keys(str(row["_id"]), active_db)
        items.append(role_public(row, permission_keys=permission_keys))
    return items


async def sync_role_permissions(
    role_id: str,
    permission_keys: list[str],
    *,
    database: Any | None = None,
) -> list[str]:
    active_db = database if database is not None else core_db
    role_permissions_collection = get_collection(active_db, "role_permissions")
    permissions_collection = get_collection(active_db, "permissions")
    if role_permissions_collection is None or permissions_collection is None:
        return []

    permissions = await permissions_collection.find({"key": {"$in": permission_keys}}).to_list(length=max(len(permission_keys), 1))
    permission_map = {permission.get("key"): permission for permission in permissions}
    missing = sorted(set(permission_keys) - set(permission_map))
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown permission keys: {', '.join(missing)}",
        )

    desired_permission_ids = {str(permission["_id"]) for permission in permissions}
    existing_rows = await role_permissions_collection.find({"role_id": role_id}).to_list(length=500)
    existing_permission_ids = {row.get("permission_id") for row in existing_rows}
    now = utc_now()

    for permission_id in desired_permission_ids - existing_permission_ids:
        await role_permissions_collection.insert_one(
            {
                "role_id": role_id,
                "permission_id": permission_id,
                "created_at": now,
                "schema_version": ROLE_PERMISSION_SCHEMA_VERSION,
            }
        )

    stale_permission_ids = [permission_id for permission_id in existing_permission_ids - desired_permission_ids if permission_id]
    if stale_permission_ids:
        await role_permissions_collection.delete_many(
            {"role_id": role_id, "permission_id": {"$in": stale_permission_ids}}
        )

    return sorted(permission_keys)


async def create_role(payload: dict[str, Any], *, database: Any | None = None) -> dict[str, Any]:
    active_db = database if database is not None else core_db
    roles_collection = get_collection(active_db, "roles")
    if roles_collection is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RBAC roles are unavailable")

    await ensure_default_rbac_state(active_db)
    code = payload["code"].strip().upper()
    existing = await roles_collection.find_one({"code": code})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role code already exists")

    now = utc_now()
    document = {
        "code": code,
        "name": payload["name"].strip(),
        "description": payload.get("description"),
        "permission_groups": sorted({key.split(".", 1)[0] for key in payload.get("permission_keys", [])}),
        "is_system": False,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "schema_version": ROLE_SCHEMA_VERSION,
    }
    result = await roles_collection.insert_one(document)
    role_id = str(result.inserted_id)
    permission_keys = await sync_role_permissions(role_id, payload.get("permission_keys", []), database=active_db)
    created = await roles_collection.find_one({"_id": result.inserted_id})
    return role_public(created, permission_keys=permission_keys)


async def update_role(role_id: str, payload: dict[str, Any], *, database: Any | None = None) -> dict[str, Any]:
    active_db = database if database is not None else core_db
    roles_collection = get_collection(active_db, "roles")
    if roles_collection is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RBAC roles are unavailable")
    role_doc = await roles_collection.find_one({"_id": parse_object_id(role_id)})
    if not role_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    set_data = {"updated_at": utc_now(), "schema_version": ROLE_SCHEMA_VERSION}
    if payload.get("name") is not None:
        set_data["name"] = payload["name"].strip()
    if "description" in payload:
        set_data["description"] = payload.get("description")
    if payload.get("is_active") is not None:
        set_data["is_active"] = payload["is_active"]
    if payload.get("permission_keys") is not None:
        set_data["permission_groups"] = sorted({key.split(".", 1)[0] for key in payload["permission_keys"]})

    await roles_collection.update_one({"_id": role_doc["_id"]}, {"$set": set_data})
    permission_keys = await get_role_permission_keys(role_id, active_db)
    if payload.get("permission_keys") is not None:
        permission_keys = await sync_role_permissions(role_id, payload["permission_keys"], database=active_db)
    updated = await roles_collection.find_one({"_id": role_doc["_id"]})
    return role_public(updated, permission_keys=permission_keys)


async def delete_role(role_id: str, *, database: Any | None = None) -> dict[str, Any]:
    active_db = database if database is not None else core_db
    roles_collection = get_collection(active_db, "roles")
    users_collection = get_collection(active_db, "users")
    if roles_collection is None or users_collection is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RBAC roles are unavailable")

    role_doc = await roles_collection.find_one({"_id": parse_object_id(role_id)})
    if not role_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
    if role_doc.get("is_system"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="System roles cannot be deleted")

    linked_user = await users_collection.find_one({"role_id": role_id, "status": {"$ne": "deleted"}})
    if linked_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Role is assigned to an existing admin")

    await roles_collection.update_one(
        {"_id": role_doc["_id"]},
        {
            "$set": {
                "is_active": False,
                "deleted_at": utc_now(),
                "updated_at": utc_now(),
                "schema_version": ROLE_SCHEMA_VERSION,
            }
        },
    )
    updated = await roles_collection.find_one({"_id": role_doc["_id"]})
    permission_keys = await get_role_permission_keys(role_id, active_db)
    return role_public(updated, permission_keys=permission_keys)


async def replace_user_permission_overrides(
    user_id: str,
    *,
    allow_permission_keys: list[str],
    deny_permission_keys: list[str],
    database: Any | None = None,
) -> None:
    active_db = database if database is not None else core_db
    permissions_collection = get_collection(active_db, "permissions")
    user_permissions_collection = get_collection(active_db, "user_permissions")
    if permissions_collection is None or user_permissions_collection is None:
        return
    combined_keys = sorted(set(allow_permission_keys) | set(deny_permission_keys))
    permission_map: dict[str, dict[str, Any]] = {}
    if combined_keys:
        permissions = await permissions_collection.find({"key": {"$in": combined_keys}}).to_list(length=len(combined_keys))
        permission_map = {permission.get("key"): permission for permission in permissions}
        missing = sorted(set(combined_keys) - set(permission_map))
        if missing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unknown permission keys: {', '.join(missing)}",
            )

    await user_permissions_collection.delete_many({"user_id": user_id})
    if not combined_keys:
        return
    now = utc_now()
    for key in allow_permission_keys:
        permission = permission_map[key]
        await user_permissions_collection.insert_one(
            {
                "user_id": user_id,
                "permission_id": str(permission["_id"]),
                "effect": "allow",
                "created_at": now,
                "schema_version": USER_PERMISSION_SCHEMA_VERSION,
            }
        )
    for key in deny_permission_keys:
        permission = permission_map[key]
        await user_permissions_collection.insert_one(
            {
                "user_id": user_id,
                "permission_id": str(permission["_id"]),
                "effect": "deny",
                "created_at": now,
                "schema_version": USER_PERMISSION_SCHEMA_VERSION,
            }
        )


async def get_effective_permission_keys(user: dict[str, Any], database: Any | None = None) -> list[str]:
    active_db = database if database is not None else core_db
    if user.get("role") != "admin" or not is_rbac_enabled(active_db):
        return []

    role_doc = await resolve_admin_role_document(user, active_db)
    if role_doc is None:
        return []

    permission_keys = set(await get_role_permission_keys(str(role_doc["_id"]), active_db))
    user_permissions_collection = get_collection(active_db, "user_permissions")
    permissions_collection = get_collection(active_db, "permissions")
    if user_permissions_collection is not None and permissions_collection is not None:
        override_rows = await user_permissions_collection.find({"user_id": str(user["_id"])}).to_list(length=500)
        permission_ids = [row.get("permission_id") for row in override_rows if row.get("permission_id")]
        permission_docs = await permissions_collection.find(
            {"_id": {"$in": [ObjectId(pid) for pid in permission_ids if ObjectId.is_valid(pid)]}}
        ).to_list(length=len(permission_ids))
        permission_doc_map = {str(row["_id"]): row for row in permission_docs}
        for row in override_rows:
            permission_doc = permission_doc_map.get(row.get("permission_id"))
            if not permission_doc or not permission_doc.get("key"):
                continue
            if row.get("effect") == "deny":
                permission_keys.discard(permission_doc["key"])
            else:
                permission_keys.add(permission_doc["key"])
    return sorted(permission_keys)


async def get_user_permission_overrides(
    user_id: str,
    *,
    database: Any | None = None,
) -> dict[str, list[str]]:
    active_db = database if database is not None else core_db
    user_permissions_collection = get_collection(active_db, "user_permissions")
    permissions_collection = get_collection(active_db, "permissions")
    if user_permissions_collection is None or permissions_collection is None:
        return {"allow_permission_keys": [], "deny_permission_keys": []}

    rows = await user_permissions_collection.find({"user_id": user_id}).to_list(length=500)
    permission_ids = [row.get("permission_id") for row in rows if row.get("permission_id")]
    permission_docs = await permissions_collection.find(
        {"_id": {"$in": [ObjectId(pid) for pid in permission_ids if ObjectId.is_valid(pid)]}}
    ).to_list(length=len(permission_ids))
    permission_doc_map = {str(permission["_id"]): permission for permission in permission_docs}

    allow_permission_keys: list[str] = []
    deny_permission_keys: list[str] = []
    for row in rows:
        permission = permission_doc_map.get(row.get("permission_id"))
        if not permission or not permission.get("key"):
            continue
        if row.get("effect") == "deny":
            deny_permission_keys.append(permission["key"])
        else:
            allow_permission_keys.append(permission["key"])

    return {
        "allow_permission_keys": sorted(set(allow_permission_keys)),
        "deny_permission_keys": sorted(set(deny_permission_keys)),
    }


async def has_rbac_permission(
    user: dict[str, Any],
    requested_permission: str,
    *,
    database: Any | None = None,
) -> bool:
    active_db = database if database is not None else core_db
    permissions = set(await get_effective_permission_keys(user, active_db))
    if not permissions:
        return False
    if requested_permission in permissions:
        return True
    alias_targets = LEGACY_PERMISSION_ALIASES.get(requested_permission, set())
    return bool(alias_targets.intersection(permissions))


async def build_user_scope_filter(
    user: dict[str, Any],
    *,
    department_field: str = "department_id",
    year_field: str | None = "year_id",
    database: Any | None = None,
) -> dict[str, Any]:
    active_db = database if database is not None else core_db
    role_doc = await resolve_admin_role_document(user, active_db)
    if role_doc is None or role_doc.get("code") == "SUPER_ADMIN":
        return {}
    scopes = await list_scope_assignments(str(user["_id"]), active_db)
    clauses = []
    for scope in scopes:
        clause = {}
        if department_field and scope.get("department_id"):
            clause[department_field] = scope["department_id"]
        if year_field and scope.get("year_id"):
            clause[year_field] = scope["year_id"]
        if clause:
            clauses.append(clause)
    if not clauses:
        if SYSTEM_ADMIN_ROLE_DEFINITIONS.get(role_doc.get("code"), {}).get("scope_required"):
            return {"_id": {"$exists": False}}
        return {}
    if len(clauses) == 1:
        return clauses[0]
    return {"$or": clauses}


async def _resolve_scope_batch_ids(scope: dict[str, Any], database: Any) -> set[str]:
    year_value = str(scope.get("year_id") or "").strip()
    if not year_value:
        return set()
    batches_collection = get_collection(database, "batches")
    if batches_collection is None:
        return set()

    query: dict[str, Any] = {}
    if scope.get("department_id"):
        query["department_id"] = scope["department_id"]

    year_clauses: list[dict[str, Any]] = []
    if year_value.isdigit():
        year_clauses.append({"start_year": int(year_value)})
    if ObjectId.is_valid(year_value):
        year_clauses.append({"_id": ObjectId(year_value)})
    if not year_clauses:
        return set()

    if len(year_clauses) == 1:
        query.update(year_clauses[0])
    else:
        query["$or"] = year_clauses

    rows = await batches_collection.find(query, {"_id": 1}).to_list(length=5000)
    return {str(row["_id"]) for row in rows if row.get("_id")}


async def build_batch_scope_filter(
    user: dict[str, Any],
    *,
    department_field: str = "department_id",
    batch_field: str = "batch_id",
    database: Any | None = None,
) -> dict[str, Any]:
    active_db = database if database is not None else core_db
    role_doc = await resolve_admin_role_document(user, active_db)
    if role_doc is None or role_doc.get("code") == "SUPER_ADMIN":
        return {}

    scopes = await list_scope_assignments(str(user["_id"]), active_db)
    clauses = []
    for scope in scopes:
        clause: dict[str, Any] = {}
        if department_field and scope.get("department_id"):
            clause[department_field] = scope["department_id"]
        if batch_field and scope.get("year_id"):
            batch_ids = await _resolve_scope_batch_ids(scope, active_db)
            if not batch_ids:
                continue
            clause[batch_field] = {"$in": sorted(batch_ids)}
        if clause:
            clauses.append(clause)

    if not clauses:
        if SYSTEM_ADMIN_ROLE_DEFINITIONS.get(role_doc.get("code"), {}).get("scope_required"):
            return {"_id": {"$exists": False}}
        return {}
    if len(clauses) == 1:
        return clauses[0]
    return {"$or": clauses}


async def is_document_in_scope(
    user: dict[str, Any],
    *,
    document: dict[str, Any] | None,
    department_field: str = "department_id",
    year_field: str | None = "year_id",
    database: Any | None = None,
) -> bool:
    if not document:
        return False
    active_db = database if database is not None else core_db
    scope_filter = await build_user_scope_filter(
        user,
        department_field=department_field,
        year_field=year_field,
        database=active_db,
    )
    if not scope_filter:
        return True
    if scope_filter == {"_id": {"$exists": False}}:
        return False

    def _matches_clause(clause: dict[str, Any], row: dict[str, Any]) -> bool:
        for key, value in clause.items():
            row_value = row.get(key)
            if isinstance(value, dict) and "$in" in value:
                if not any(str(row_value) == str(candidate) for candidate in value["$in"]):
                    return False
                continue
            if row_value is None and value is not None:
                return False
            if value is None and row_value is None:
                continue
            if str(row_value) != str(value):
                return False
        return True

    if "$or" in scope_filter:
        return any(_matches_clause(clause, document) for clause in scope_filter["$or"])
    return _matches_clause(scope_filter, document)


async def build_scoped_section_ids_filter(
    user: dict[str, Any],
    *,
    section_id_field: str,
    department_field: str = "department_id",
    batch_field: str = "batch_id",
    database: Any | None = None,
) -> dict[str, Any]:
    active_db = database if database is not None else core_db
    role_doc = await resolve_admin_role_document(user, active_db)
    if role_doc is None or role_doc.get("code") == "SUPER_ADMIN":
        return {}

    scope_filter = await build_batch_scope_filter(
        user,
        department_field=department_field,
        batch_field=batch_field,
        database=active_db,
    )
    if not scope_filter:
        return {}
    if scope_filter == {"_id": {"$exists": False}}:
        return {"_id": {"$exists": False}}

    classes_collection = get_collection(active_db, "classes")
    if classes_collection is None:
        return {"_id": {"$exists": False}}
    rows = await classes_collection.find(scope_filter, {"_id": 1}).to_list(length=5000)
    section_ids = [str(row["_id"]) for row in rows if row.get("_id")]
    if not section_ids:
        return {"_id": {"$exists": False}}
    return {section_id_field: {"$in": section_ids}}


async def is_document_in_batch_scope(
    user: dict[str, Any],
    *,
    document: dict[str, Any] | None,
    department_field: str = "department_id",
    batch_field: str = "batch_id",
    database: Any | None = None,
) -> bool:
    if not document:
        return False
    active_db = database if database is not None else core_db
    scope_filter = await build_batch_scope_filter(
        user,
        department_field=department_field,
        batch_field=batch_field,
        database=active_db,
    )
    if not scope_filter:
        return True
    if scope_filter == {"_id": {"$exists": False}}:
        return False

    def _matches_clause(clause: dict[str, Any], row: dict[str, Any]) -> bool:
        for key, value in clause.items():
            row_value = row.get(key)
            if isinstance(value, dict) and "$in" in value:
                if not any(str(row_value) == str(candidate) for candidate in value["$in"]):
                    return False
                continue
            if row_value is None and value is not None:
                return False
            if value is None and row_value is None:
                continue
            if str(row_value) != str(value):
                return False
        return True

    if "$or" in scope_filter:
        return any(_matches_clause(clause, document) for clause in scope_filter["$or"])
    return _matches_clause(scope_filter, document)


async def admin_role_requires_scope(
    user: dict[str, Any],
    *,
    database: Any | None = None,
) -> bool:
    role_doc = await resolve_admin_role_document(user, database if database is not None else core_db)
    if role_doc is None:
        return False
    return bool(role_doc.get("scope_required"))


_IMPOSSIBLE_QUERY = {"_id": {"$exists": False}}
_MERGE_CONFLICT = object()


def _merge_query_values(left: Any, right: Any) -> Any:
    if left == right:
        return left

    if isinstance(left, dict) and "$in" in left and not isinstance(right, dict):
        return right if right in left["$in"] else _MERGE_CONFLICT
    if isinstance(right, dict) and "$in" in right and not isinstance(left, dict):
        return left if left in right["$in"] else _MERGE_CONFLICT

    if isinstance(left, dict) and isinstance(right, dict) and "$in" in left and "$in" in right:
        intersection = [value for value in left["$in"] if value in right["$in"]]
        if not intersection:
            return _MERGE_CONFLICT
        return {"$in": intersection}

    return _MERGE_CONFLICT


def _merge_query_clause(base_query: dict[str, Any], scope_clause: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base_query)
    for key, value in scope_clause.items():
        existing = merged.get(key)
        if existing is None:
            merged[key] = value
            continue
        resolved_value = _merge_query_values(existing, value)
        if resolved_value is _MERGE_CONFLICT:
            return dict(_IMPOSSIBLE_QUERY)
        merged[key] = resolved_value
    return merged


def merge_query_with_scope_filter(query: dict[str, Any], scope_filter: dict[str, Any]) -> dict[str, Any]:
    if not scope_filter:
        return dict(query)
    if scope_filter == _IMPOSSIBLE_QUERY:
        return dict(_IMPOSSIBLE_QUERY)

    base_query = dict(query)
    if "$or" not in scope_filter:
        return _merge_query_clause(base_query, scope_filter)

    merged_clauses = []
    for clause in scope_filter["$or"]:
        merged_clause = _merge_query_clause(base_query, clause)
        if merged_clause != _IMPOSSIBLE_QUERY:
            merged_clauses.append(merged_clause)

    if not merged_clauses:
        return dict(_IMPOSSIBLE_QUERY)
    if len(merged_clauses) == 1:
        return merged_clauses[0]
    return {"$or": merged_clauses}


async def check_admin_role(
    user: dict[str, Any],
    allowed_role_codes: list[str],
    *,
    database: Any | None = None,
) -> bool:
    role_doc = await resolve_admin_role_document(user, database if database is not None else core_db)
    if role_doc is None:
        return False
    return role_doc.get("code") in {code.strip().upper() for code in allowed_role_codes}


async def serialize_admin_user(
    user: dict[str, Any],
    *,
    database: Any | None = None,
) -> dict[str, Any]:
    active_db = database if database is not None else core_db
    base = user_public(user)
    role_doc = await resolve_admin_role_document(user, active_db)
    permission_keys = await get_effective_permission_keys(user, active_db)
    permission_overrides = await get_user_permission_overrides(str(user["_id"]), database=active_db)
    scopes = await list_scope_assignments(str(user["_id"]), active_db)
    admin_role = None
    if role_doc is not None:
        admin_role = {
            "id": str(role_doc["_id"]),
            "code": role_doc.get("code"),
            "name": role_doc.get("name"),
            "description": role_doc.get("description"),
        }
    return {
        "id": base["id"],
        "full_name": base["full_name"],
        "email": base["email"],
        "role": "admin",
        "admin_type": base.get("admin_type"),
        "rbac_role_code": role_doc.get("code") if role_doc is not None else base.get("rbac_role_code"),
        "admin_role": admin_role,
        "permissions": permission_keys,
        "permission_overrides": permission_overrides,
        "scopes": scopes,
        "is_active": base.get("is_active", True),
        "status": user.get("status") or ("active" if user.get("is_active", True) else "inactive"),
        "must_change_password": base.get("must_change_password", False),
        "created_at": base.get("created_at"),
        "updated_at": user.get("updated_at"),
        "deleted_at": user.get("deleted_at"),
        "schema_version": user.get("schema_version", USER_SCHEMA_VERSION),
    }
