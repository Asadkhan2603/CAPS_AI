from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def apply_is_active_filter(query: dict[str, Any], is_active: bool | None) -> dict[str, Any]:
    if is_active is not None:
        query["is_active"] = is_active
    return query


def build_soft_delete_update(
    *,
    deleted_by: str | None,
    deleted_at: datetime | None = None,
    extra_fields: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    set_fields: dict[str, Any] = {
        "is_active": False,
        "deleted_at": deleted_at or datetime.now(timezone.utc),
    }
    if deleted_by is not None:
        set_fields["deleted_by"] = deleted_by
    if extra_fields:
        set_fields.update(extra_fields)
    return {"$set": set_fields}


def build_state_update(set_fields: dict[str, Any]) -> dict[str, dict[str, Any]]:
    update_doc: dict[str, dict[str, Any]] = {"$set": set_fields}
    if set_fields.get("is_active") is True:
        update_doc["$unset"] = {
            "deleted_at": "",
            "deleted_by": "",
            "is_deleted": "",
        }
    return update_doc


def build_soft_deleted_query(*, include_legacy_marker: bool = False) -> dict[str, Any]:
    canonical_query: dict[str, Any] = {"deleted_at": {"$ne": None}}
    if not include_legacy_marker:
        return canonical_query
    return {
        "$or": [
            canonical_query,
            {
                "$and": [
                    {"is_deleted": True},
                    {"$or": [{"deleted_at": {"$exists": False}}, {"deleted_at": None}]},
                ]
            },
        ]
    }


def build_restore_update(
    *,
    restored_by: str,
    restored_at: datetime | None = None,
) -> dict[str, dict[str, Any]]:
    return {
        "$set": {
            "is_active": True,
            "restored_at": restored_at or datetime.now(timezone.utc),
            "restored_by": restored_by,
        },
        "$unset": {
            "deleted_at": "",
            "deleted_by": "",
            "is_deleted": "",
        },
    }
