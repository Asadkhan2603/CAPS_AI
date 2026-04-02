from __future__ import annotations

from typing import Any


def permission_public(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "key": document.get("key", ""),
        "name": document.get("name", ""),
        "module": document.get("module", ""),
        "module_key": document.get("module_key", ""),
        "description": document.get("description"),
        "is_system": document.get("is_system", True),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "schema_version": document.get("schema_version", 1),
    }


def role_public(
    document: dict[str, Any],
    *,
    permission_keys: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "code": document.get("code", ""),
        "name": document.get("name", ""),
        "description": document.get("description"),
        "permission_keys": permission_keys or [],
        "permission_groups": sorted(document.get("permission_groups", []) or []),
        "is_system": document.get("is_system", True),
        "is_active": document.get("is_active", True),
        "deleted_at": document.get("deleted_at"),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "schema_version": document.get("schema_version", 1),
    }


def scope_public(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(document["_id"]),
        "user_id": document.get("user_id", ""),
        "department_id": document.get("department_id"),
        "year_id": document.get("year_id"),
        "created_at": document.get("created_at"),
        "updated_at": document.get("updated_at"),
        "schema_version": document.get("schema_version", 1),
    }
