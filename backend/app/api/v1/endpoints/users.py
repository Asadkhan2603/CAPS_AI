from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import math
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.responses import StreamingResponse

from app.core.config import settings
from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import CLASS_SCHEMA_VERSION, CLUB_SCHEMA_VERSION, USER_SCHEMA_VERSION
from app.core.security import get_password_hash, require_permission
from app.models.users import user_admin_list_item, user_public
from app.schemas.user import (
    FilterOptionCount,
    PermissionTemplateCreate,
    PermissionTemplateOut,
    PermissionTemplateUpdate,
    UserActivityResponse,
    UsersAdminDashboardResponse,
    UserAdminListItem,
    UserAdminProfileUpdate,
    UsersAdminCapabilitiesResponse,
    UsersAdminTelemetryEvent,
    UserBulkExtensionsResponse,
    UserBulkExtensionsResultItem,
    UserBulkExtensionsUpdate,
    UserBulkStatusResponse,
    UserBulkStatusResultItem,
    UserBulkStatusUpdate,
    UserCreate,
    UserFilterPresetCreate,
    UserFilterPresetOut,
    UserFilterPresetQuery,
    UserFilterPresetUpdate,
    UserExtensionRolesUpdate,
    UserImportCommitRequest,
    UserImportCommitResponse,
    UserImportPreviewResponse,
    UserImportPreviewRow,
    UserInvitationCreate,
    UserInvitationOut,
    UserOut,
    UsersAdminListResponse,
    UsersFilterOptionsResponse,
    UserStatusUpdate,
)
from app.services.audit import log_audit_event
from app.services.class_slot_read_models import sync_class_slot_read_models_for_offering_query
from app.services.class_representative_governance import (
    synchronize_student_class_representative_binding,
)
from app.services.club_governance import assign_student_as_club_president, clear_student_club_president
from app.services.course_offering_read_models import sync_course_offering_read_models_for_query
from app.services.governance import enforce_review_approval
from app.services.section_read_models import sync_section_read_models_for_ids
from app.services.student_profiles import ensure_student_profile_for_user
from app.services.users_admin_observability import build_users_admin_dashboard

router = APIRouter()
logger = logging.getLogger("caps_api.users")

ROLE_ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    "teacher": {"year_head", "class_coordinator", "club_coordinator"},
    "student": {"club_president", "class_representative"},
}

ADMIN_SORT_FIELDS = {
    "full_name": "full_name",
    "email": "email",
    "role": "role",
    "admin_type": "admin_type",
    "is_active": "is_active",
    "last_active_at": "last_active_at",
    "created_at": "created_at",
    "updated_at": "updated_at",
    "department": "profile.department",
    "designation": "profile.designation",
}

ADMIN_LIST_PROJECTION = {
    "_id": 1,
    "full_name": 1,
    "email": 1,
    "avatar_filename": 1,
    "avatar_updated_at": 1,
    "role": 1,
    "admin_type": 1,
    "is_active": 1,
    "extended_roles": 1,
    "last_active_at": 1,
    "created_at": 1,
    "updated_at": 1,
    "profile.department": 1,
    "profile.designation": 1,
    "last_permission_change_at": 1,
    "last_permission_change_by": 1,
    "last_status_change_at": 1,
    "last_status_change_by": 1,
}

IMPORT_COLUMNS = {"full_name", "email", "role", "admin_type", "extended_roles"}


def _normalized_admin_type(current_user: dict[str, Any] | None) -> str:
    if not isinstance(current_user, dict):
        return ""
    value = str(current_user.get("admin_type") or "").strip().lower()
    if value:
        return value
    if str(current_user.get("role") or "").strip().lower() == "admin":
        return "admin"
    return ""


def _is_internal_admin(current_user: dict[str, Any] | None) -> bool:
    if not isinstance(current_user, dict):
        return False
    if str(current_user.get("role") or "").strip().lower() != "admin":
        return False

    admin_type = _normalized_admin_type(current_user)
    user_id = str(current_user.get("_id") or current_user.get("id") or "").strip().lower()
    email = str(current_user.get("email") or "").strip().lower()
    email_domain = email.split("@", 1)[1].strip().lower() if "@" in email else ""

    internal_user_ids = {str(item).strip().lower() for item in (settings.users_rollout_internal_user_ids or []) if str(item).strip()}
    internal_emails = {str(item).strip().lower() for item in (settings.users_rollout_internal_emails or []) if str(item).strip()}
    internal_domains = {str(item).strip().lower() for item in (settings.users_rollout_internal_email_domains or []) if str(item).strip()}
    internal_admin_types = {
        str(item).strip().lower()
        for item in (settings.users_rollout_internal_admin_types or [])
        if str(item).strip()
    }

    if user_id and user_id in internal_user_ids:
        return True
    if email and email in internal_emails:
        return True
    if email_domain and email_domain in internal_domains:
        return True
    if admin_type and admin_type in internal_admin_types:
        return True
    return False


def _users_rollout_context(current_user: dict[str, Any] | None) -> dict[str, Any]:
    stage = str(settings.users_rollout_stage or "all_admins").strip().lower()
    role = str((current_user or {}).get("role") or "").strip().lower()
    admin_type = _normalized_admin_type(current_user)

    if role != "admin":
        return {
            "stage": stage,
            "cohort": "non_admin",
            "allowed": False,
            "reason": "Users admin workspace is limited to admin users.",
        }

    if _is_internal_admin(current_user):
        cohort = "internal_admin"
    elif admin_type == "super_admin":
        cohort = "super_admin"
    else:
        cohort = "admin"

    if stage == "internal_admins":
        allowed = cohort == "internal_admin"
        reason = (
            "Users admin rollout is currently limited to internal admins."
            if not allowed
            else "Rollout stage: internal admins."
        )
    elif stage == "super_admins":
        allowed = cohort in {"internal_admin", "super_admin"}
        reason = (
            "Users admin rollout is currently limited to super admins."
            if not allowed
            else "Rollout stage: super admins."
        )
    else:
        allowed = True
        reason = "Rollout stage: all admins."

    return {
        "stage": stage if stage in {"internal_admins", "super_admins", "all_admins"} else "all_admins",
        "cohort": cohort,
        "allowed": allowed,
        "reason": reason,
    }


def _users_capabilities(current_user: dict[str, Any] | None = None) -> dict[str, Any]:
    rollout = _users_rollout_context(current_user)
    access_allowed = bool(rollout["allowed"])
    base_capabilities = {
        "workspace": bool(settings.users_capability_workspace_enabled),
        "activity": bool(settings.users_capability_activity_enabled),
        "bulk_operations": bool(settings.users_capability_bulk_operations_enabled),
        "permission_templates": bool(settings.users_capability_permission_templates_enabled),
        "invitations": bool(settings.users_capability_invitations_enabled),
        "import_export": bool(settings.users_capability_import_export_enabled),
        "inline_editing": bool(settings.users_capability_inline_editing_enabled),
        "compact_density": bool(settings.users_capability_compact_density_enabled),
        "responsive_workflows": bool(settings.users_capability_responsive_workflows_enabled),
        "table_virtualization": bool(settings.users_capability_table_virtualization_enabled),
        "http_cache_validation": bool(settings.users_capability_http_cache_validation_enabled),
    }
    effective_capabilities = {
        key: (value and access_allowed)
        for key, value in base_capabilities.items()
    }
    effective_capabilities["rollout_stage"] = rollout["stage"]
    effective_capabilities["rollout_cohort"] = rollout["cohort"]
    effective_capabilities["rollout_access"] = access_allowed
    effective_capabilities["rollout_reason"] = rollout["reason"] if not access_allowed else None
    return effective_capabilities


def _require_users_capability(capability: str, current_user: dict[str, Any] | None = None) -> None:
    capabilities = _users_capabilities(current_user)
    value = capabilities.get(capability)
    if value is False:
        rollout_access = bool(capabilities.get("rollout_access"))
        rollout_reason = str(capabilities.get("rollout_reason") or "").strip()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if not rollout_access else status.HTTP_404_NOT_FOUND,
            detail=rollout_reason or f"Users capability '{capability}' is disabled",
        )


async def _record_users_telemetry(
    *,
    event: str,
    outcome: Literal["success", "error"] = "success",
    actor_user_id: str | None = None,
    scope: str | None = None,
    severity: Literal["low", "medium", "high"] = "low",
    metadata: dict[str, Any] | None = None,
) -> None:
    if not settings.users_admin_telemetry_enabled:
        return

    document = {
        "event": str(event or "").strip() or "users.unknown",
        "outcome": outcome,
        "actor_user_id": actor_user_id,
        "scope": (scope or "").strip() or None,
        "severity": severity,
        "metadata": metadata if isinstance(metadata, dict) else {},
        "created_at": _utc_now(),
    }
    try:
        await db.users_admin_telemetry.insert_one(document)
    except Exception:
        logger.warning(
            {
                "event": "users.telemetry.persist_failed",
                "telemetry_event": document["event"],
                "outcome": outcome,
            }
        )

    log_level = logger.warning if outcome == "error" or severity in {"medium", "high"} else logger.info
    log_level(
        {
            "event": "users.telemetry",
            "telemetry_event": document["event"],
            "outcome": outcome,
            "scope": document["scope"],
            "severity": severity,
            "actor_user_id": actor_user_id,
            "metadata": document["metadata"],
        }
    )


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_str_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    out: list[str] = []
    seen: set[str] = set()
    for raw in values:
        for part in str(raw or "").split(","):
            value = part.strip()
            if not value:
                continue
            if value in seen:
                continue
            seen.add(value)
            out.append(value)
    return out


def _build_range_query(start: datetime | None, end: datetime | None) -> dict[str, datetime] | None:
    query: dict[str, datetime] = {}
    if start is not None:
        query["$gte"] = start
    if end is not None:
        query["$lte"] = end
    return query or None


def _build_admin_user_query(
    *,
    q: str | None,
    roles: list[str],
    is_active: bool | None,
    admin_types: list[str],
    extensions: list[str],
    department: str | None,
    created_from: datetime | None,
    created_to: datetime | None,
    last_active_from: datetime | None,
    last_active_to: datetime | None,
) -> dict[str, Any]:
    query: dict[str, Any] = {}
    if q:
        needle = re.escape(q.strip())
        query["$or"] = [
            {"full_name": {"$regex": needle, "$options": "i"}},
            {"email": {"$regex": needle, "$options": "i"}},
        ]
    if roles:
        query["role"] = {"$in": roles}
    if is_active is not None:
        query["is_active"] = is_active
    if admin_types:
        query["admin_type"] = {"$in": admin_types}
    if extensions:
        query["extended_roles"] = {"$in": extensions}
    if department:
        query["profile.department"] = {"$regex": f"^{re.escape(department.strip())}$", "$options": "i"}

    created_range = _build_range_query(created_from, created_to)
    if created_range:
        query["created_at"] = created_range

    last_active_range = _build_range_query(last_active_from, last_active_to)
    if last_active_range:
        query["last_active_at"] = last_active_range
    return query


def _build_admin_sort(sort_by: str, sort_dir: Literal["asc", "desc"]) -> list[tuple[str, int]]:
    field = ADMIN_SORT_FIELDS.get(sort_by, "updated_at")
    direction = 1 if sort_dir == "asc" else -1
    return [(field, direction), ("_id", 1)]


def _pages(total: int, limit: int) -> int:
    if limit <= 0:
        return 0
    return math.ceil(total / limit)


def _public_invitation(document: dict[str, Any]) -> UserInvitationOut:
    now = _utc_now()
    status_value = str(document.get("status") or "pending")
    expires_at = document.get("expires_at")
    if status_value == "pending" and isinstance(expires_at, datetime) and expires_at < now:
        status_value = "expired"

    token = str(document.get("token") or "")
    invitation_link = f"/workspace/invitations/accept?token={token}"
    return UserInvitationOut(
        id=str(document.get("_id")),
        full_name=document.get("full_name", ""),
        email=document.get("email", ""),
        role=document.get("role", "student"),
        admin_type=document.get("admin_type"),
        extended_roles=document.get("extended_roles", []) or [],
        role_scope=document.get("role_scope", {}) or {},
        status=status_value,
        invitation_link=invitation_link,
        created_at=document.get("created_at"),
        expires_at=expires_at,
    )


def _public_permission_template(document: dict[str, Any]) -> PermissionTemplateOut:
    return PermissionTemplateOut(
        id=str(document.get("_id")),
        name=document.get("name", ""),
        description=document.get("description"),
        role=document.get("role", "student"),
        admin_type=document.get("admin_type"),
        extended_roles=document.get("extended_roles", []) or [],
        role_scope=document.get("role_scope", {}) or {},
        created_at=document.get("created_at"),
        updated_at=document.get("updated_at"),
    )


async def _ensure_builtin_permission_templates() -> None:
    now = _utc_now()
    await db.user_permission_templates.update_one(
        {"role": "student", "name": "Class Representative (CR)"},
        {
            "$setOnInsert": {
                "name": "Class Representative (CR)",
                "description": "Generic preset for section-level class representatives. Choose section and seat at assignment time.",
                "role": "student",
                "admin_type": None,
                "extended_roles": ["class_representative"],
                "role_scope": {},
                "created_by_user_id": "system",
                "created_at": now,
                "updated_at": now,
            }
        },
        upsert=True,
    )


def _validate_permission_template_scope(role: str, extensions: list[str], role_scope: dict[str, Any]) -> None:
    if role == "student" and "class_representative" in set(extensions) and not (role_scope.get("class_representative") if isinstance(role_scope, dict) else None):
        return
    _validate_role_scope_requirements(role, extensions, role_scope)


def _normalized_filter_preset_query(raw: dict[str, Any] | None) -> UserFilterPresetQuery:
    payload = raw if isinstance(raw, dict) else {}
    normalized: dict[str, Any] = {
        "q": str(payload.get("q") or "").strip() or None,
        "role": str(payload.get("role") or "").strip() or None,
        "status": str(payload.get("status") or "").strip() or None,
        "admin_type": str(payload.get("admin_type") or "").strip() or None,
        "extension": str(payload.get("extension") or "").strip() or None,
        "department": str(payload.get("department") or "").strip() or None,
        "sort_by": str(payload.get("sort_by") or "updated_at").strip() or "updated_at",
        "sort_dir": str(payload.get("sort_dir") or "desc").strip().lower() or "desc",
        "limit": payload.get("limit", 25),
    }
    return UserFilterPresetQuery.model_validate(normalized)


def _public_filter_preset(document: dict[str, Any]) -> UserFilterPresetOut:
    return UserFilterPresetOut(
        id=str(document.get("_id")),
        name=document.get("name", ""),
        query=_normalized_filter_preset_query(document.get("query")),
        created_at=document.get("created_at"),
        updated_at=document.get("updated_at"),
    )


def _validate_extensions_for_role(role: str, extensions: list[str]) -> None:
    allowed = ROLE_ALLOWED_EXTENSIONS.get(role, set())
    if not allowed and extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This role does not support extension roles",
        )
    invalid = [item for item in extensions if item not in allowed]
    if invalid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid extension roles for {role}: {', '.join(invalid)}",
        )


def _validate_role_scope_requirements(role: str, extensions: list[str], role_scope: dict[str, Any]) -> None:
    if role == "teacher" and "class_coordinator" in extensions:
        class_scope = role_scope.get("class_coordinator") if isinstance(role_scope, dict) else None
        class_id = class_scope.get("class_id") if isinstance(class_scope, dict) else None
        if not class_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="class_coordinator requires class_coordinator.class_id",
            )

    if role == "student" and "club_president" in extensions:
        club_scope = role_scope.get("club_president") if isinstance(role_scope, dict) else None
        club_id = club_scope.get("club_id") if isinstance(club_scope, dict) else None
        if not club_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="club_president requires club_president.club_id",
            )

    if role == "student" and "class_representative" in extensions:
        representative_scope = role_scope.get("class_representative") if isinstance(role_scope, dict) else None
        class_id = representative_scope.get("class_id") if isinstance(representative_scope, dict) else None
        seat = representative_scope.get("seat") if isinstance(representative_scope, dict) else None
        if not class_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="class_representative requires class_representative.class_id",
            )
        if seat not in {"cr_1", "cr_2"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="class_representative requires class_representative.seat as cr_1 or cr_2",
            )


def _normalize_role_scope_payload(
    *,
    role: str,
    extensions: list[str],
    role_scope: Any,
) -> dict[str, Any]:
    if hasattr(role_scope, "model_dump"):
        role_scope = role_scope.model_dump(exclude_none=True)
    role_scope = dict(role_scope or {}) if isinstance(role_scope, dict) else {}
    _validate_role_scope_requirements(role, extensions, role_scope)

    if role == "teacher":
        role_scope.pop("club_president", None)
        role_scope.pop("class_representative", None)
        if "class_coordinator" not in extensions:
            role_scope.pop("class_coordinator", None)
    elif role == "student":
        role_scope.pop("class_coordinator", None)
        if "class_representative" not in extensions:
            role_scope.pop("class_representative", None)
        if "club_president" not in extensions:
            role_scope.pop("club_president", None)
    else:
        role_scope = {}
    return role_scope


def _actor_display_name(current_user: dict[str, Any] | None) -> str:
    if not isinstance(current_user, dict):
        return ""
    for key in ("full_name", "email", "id", "_id"):
        value = str(current_user.get(key) or "").strip()
        if value:
            return value
    return ""


def _normalize_if_none_match(value: str | None) -> set[str]:
    if not value:
        return set()
    variants: set[str] = set()
    for part in str(value).split(","):
        token = part.strip()
        if not token:
            continue
        variants.add(token)
        normalized = token
        if normalized.startswith("W/"):
            normalized = normalized[2:].strip()
        normalized = normalized.strip('"')
        if normalized:
            variants.add(normalized)
            variants.add(f'"{normalized}"')
            variants.add(f'W/"{normalized}"')
    return variants


def _build_admin_list_etag(
    *,
    query: dict[str, Any],
    sort_spec: list[tuple[str, int]],
    page: int,
    limit: int,
    total: int,
    rows: list[dict[str, Any]],
) -> str:
    payload = {
        "query": query,
        "sort": sort_spec,
        "page": int(page),
        "limit": int(limit),
        "total": int(total),
        "rows": [
            {
                "id": str(row.get("_id") or ""),
                "updated_at": row.get("updated_at").isoformat()
                if isinstance(row.get("updated_at"), datetime)
                else None,
                "status_changed_at": row.get("last_status_change_at").isoformat()
                if isinstance(row.get("last_status_change_at"), datetime)
                else None,
                "permission_changed_at": row.get("last_permission_change_at").isoformat()
                if isinstance(row.get("last_permission_change_at"), datetime)
                else None,
            }
            for row in rows
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":")).encode("utf-8")
    digest = hashlib.sha1(encoded).hexdigest()
    return f'W/"{digest}"'


async def _synchronize_role_scope_bindings(
    *,
    user_id: str,
    role: str,
    extensions: list[str],
    role_scope: dict[str, Any],
    clear_existing: bool = False,
) -> tuple[dict[str, Any], set[str]]:
    affected_section_ids: set[str] = set()
    next_scope = dict(role_scope or {})

    if role == "teacher":
        if clear_existing:
            affected_section_ids.update(
                str(item.get("_id"))
                for item in await db.classes.find({"class_coordinator_user_id": user_id}, {"_id": 1}).to_list(length=5000)
                if item.get("_id")
            )
        if "class_coordinator" in extensions:
            class_scope = next_scope.get("class_coordinator", {}) if isinstance(next_scope, dict) else {}
            class_id = class_scope.get("class_id")
            if class_id:
                affected_section_ids.add(class_id)
                class_doc = await db.classes.find_one({"_id": parse_object_id(class_id)})
                if not class_doc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Class not found for class coordinator scope",
                    )
                if clear_existing:
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
                next_scope["class_coordinator"] = class_scope
        else:
            next_scope.pop("class_coordinator", None)
            if clear_existing:
                await db.classes.update_many(
                    {"class_coordinator_user_id": user_id},
                    {"$set": {"class_coordinator_user_id": None, "schema_version": CLASS_SCHEMA_VERSION}},
                )
        next_scope.pop("club_president", None)

    if role == "student":
        if "club_president" in extensions:
            club_scope = next_scope.get("club_president", {}) if isinstance(next_scope, dict) else {}
            club_id = club_scope.get("club_id")
            if club_id:
                club_doc = await db.clubs.find_one({"_id": parse_object_id(club_id)})
                if not club_doc:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Club not found for club president scope",
                    )
                await assign_student_as_club_president(user_id, club_id, sync_target_user_record=False)
                next_scope["club_president"] = {"club_id": club_id}
        else:
            next_scope.pop("club_president", None)
            if clear_existing:
                await clear_student_club_president(user_id, sync_target_user_record=False)
        if "class_representative" in extensions:
            representative_scope = next_scope.get("class_representative", {}) if isinstance(next_scope, dict) else {}
            normalized_scope, representative_section_ids = await synchronize_student_class_representative_binding(
                student_user_id=user_id,
                scope=representative_scope,
                clear_existing=clear_existing,
                database=db,
            )
            affected_section_ids.update(representative_section_ids)
            if normalized_scope:
                next_scope["class_representative"] = normalized_scope
            else:
                next_scope.pop("class_representative", None)
        else:
            next_scope.pop("class_representative", None)
            if clear_existing:
                _cleared_scope, representative_section_ids = await synchronize_student_class_representative_binding(
                    student_user_id=user_id,
                    scope=None,
                    clear_existing=True,
                    database=db,
                )
                affected_section_ids.update(representative_section_ids)
        next_scope.pop("class_coordinator", None)

    if role not in {"teacher", "student"}:
        next_scope = {}

    return next_scope, affected_section_ids


def _parse_import_extended_roles(raw: str | None) -> list[str]:
    if not raw:
        return []
    values: list[str] = []
    seen: set[str] = set()
    chunks = re.split(r"[|,;]", raw)
    for chunk in chunks:
        value = chunk.strip()
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        values.append(value)
    return values


def _normalize_import_row(raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "full_name": str(raw.get("full_name") or "").strip(),
        "email": str(raw.get("email") or "").strip().lower(),
        "role": str(raw.get("role") or "").strip().lower(),
        "admin_type": str(raw.get("admin_type") or "").strip().lower() or None,
        "extended_roles": _parse_import_extended_roles(str(raw.get("extended_roles") or "")),
    }


def _validate_import_row_payload(row: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    full_name = row.get("full_name")
    email = row.get("email")
    role = row.get("role")
    admin_type = row.get("admin_type")
    extended_roles = row.get("extended_roles") or []

    if not full_name or len(full_name) < 2:
        errors.append("full_name must be at least 2 characters")
    if not email or "@" not in email:
        errors.append("email is invalid")
    if role not in {"admin", "teacher", "student"}:
        errors.append("role must be one of admin, teacher, student")

    if role == "admin":
        if not admin_type:
            row["admin_type"] = "admin"
    elif admin_type:
        errors.append("admin_type is only allowed for admin role")

    if role in {"teacher", "student"}:
        try:
            _validate_extensions_for_role(role, extended_roles)
        except HTTPException as exc:
            errors.append(str(exc.detail))
    elif extended_roles:
        errors.append("extended_roles are only allowed for teacher or student roles")

    return errors


async def _apply_extension_update(
    *,
    user_id: str,
    payload: UserExtensionRolesUpdate,
    current_user_id: str,
    current_user_name: str | None = None,
) -> dict[str, Any]:
    user_obj_id = parse_object_id(user_id)
    user = await db.users.find_one({"_id": user_obj_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    role = str(user.get("role") or "")
    extensions = list(payload.extended_roles or [])
    _validate_extensions_for_role(role, extensions)

    previous_extensions = list(user.get("extended_roles") or [])
    previous_scope = dict(user.get("role_scope") or {})
    role_scope = _normalize_role_scope_payload(role=role, extensions=extensions, role_scope=payload.role_scope)
    role_scope, affected_section_ids = await _synchronize_role_scope_bindings(
        user_id=user_id,
        role=role,
        extensions=extensions,
        role_scope=role_scope,
        clear_existing=True,
    )

    now = _utc_now()
    await db.users.update_one(
        {"_id": user_obj_id},
        {
            "$set": {
                "extended_roles": extensions,
                "role_scope": role_scope,
                "updated_at": now,
                "last_permission_change_at": now,
                "last_permission_change_by": str(current_user_name or current_user_id),
                "schema_version": USER_SCHEMA_VERSION,
            }
        },
    )
    updated = await db.users.find_one({"_id": user_obj_id})

    reason = (payload.change_reason or "").strip()
    detail = f"Updated {role} extension roles"
    if reason:
        detail = f"{detail}. Reason: {reason}"
    await log_audit_event(
        actor_user_id=current_user_id,
        action="update_extensions",
        entity_type="user",
        entity_id=user_id,
        action_type="role_change",
        detail=detail,
        old_value={"extended_roles": previous_extensions, "role_scope": previous_scope},
        new_value={"extended_roles": extensions, "role_scope": role_scope, "change_reason": reason or None},
        severity="medium",
    )

    affected_section_ids.update(
        str(item.get("_id"))
        for item in await db.classes.find({"class_coordinator_user_id": user_id}, {"_id": 1}).to_list(length=5000)
        if item.get("_id")
    )
    affected_section_ids.update(
        str(item.get("_id"))
        for item in await db.classes.find(
            {
                "$or": [
                    {"class_representatives.cr_1.user_id": user_id},
                    {"class_representatives.cr_2.user_id": user_id},
                ]
            },
            {"_id": 1},
        ).to_list(length=5000)
        if item.get("_id")
    )
    if affected_section_ids:
        await sync_section_read_models_for_ids(section_ids=sorted(affected_section_ids), database=db)

    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user")
    return updated


async def _apply_status_update(
    *,
    user_id: str,
    is_active: bool,
    reason: str,
    current_user: dict[str, Any],
) -> dict[str, Any]:
    user_obj_id = parse_object_id(user_id)
    if str(current_user.get("_id")) == user_id and not is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot deactivate yourself")

    user = await db.users.find_one({"_id": user_obj_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    affected_section_ids = {
        str(item.get("_id"))
        for item in await db.classes.find({"class_coordinator_user_id": user_id}, {"_id": 1}).to_list(length=5000)
        if item.get("_id")
    }
    affected_section_ids.update(
        str(item.get("_id"))
        for item in await db.classes.find(
            {
                "$or": [
                    {"class_representatives.cr_1.user_id": user_id},
                    {"class_representatives.cr_2.user_id": user_id},
                ]
            },
            {"_id": 1},
        ).to_list(length=5000)
        if item.get("_id")
    )

    now = _utc_now()
    actor_label = _actor_display_name(current_user) or str(current_user.get("_id") or "")
    await db.users.update_one(
        {"_id": user_obj_id},
        {
            "$set": {
                "is_active": is_active,
                "updated_at": now,
                "last_status_change_at": now,
                "last_status_change_by": actor_label,
                "schema_version": USER_SCHEMA_VERSION,
            }
        },
    )

    if not is_active:
        await db.classes.update_many(
            {"class_coordinator_user_id": user_id},
            {"$set": {"class_coordinator_user_id": None, "schema_version": CLASS_SCHEMA_VERSION}},
        )
        representative_sections = await db.classes.find(
            {
                "$or": [
                    {"class_representatives.cr_1.user_id": user_id},
                    {"class_representatives.cr_2.user_id": user_id},
                ]
            },
            {"_id": 1, "class_representatives": 1},
        ).to_list(length=5000)
        for section in representative_sections:
            section_id = str(section.get("_id") or "")
            representatives = dict(section.get("class_representatives") or {})
            changed = False
            for seat in ("cr_1", "cr_2"):
                seat_state = dict(representatives.get(seat) or {})
                if str(seat_state.get("user_id") or "") == user_id:
                    representatives[seat] = {"user_id": None, "full_name": None}
                    changed = True
            if changed:
                if section_id:
                    affected_section_ids.add(section_id)
                await db.classes.update_one(
                    {"_id": section["_id"]},
                    {"$set": {"class_representatives": representatives, "schema_version": CLASS_SCHEMA_VERSION}},
                )
        await db.clubs.update_many(
            {"coordinator_user_id": user_id},
            {"$set": {"coordinator_user_id": None, "schema_version": CLUB_SCHEMA_VERSION}},
        )
        await db.clubs.update_many(
            {"president_user_id": user_id},
            {"$set": {"president_user_id": None, "schema_version": CLUB_SCHEMA_VERSION}},
        )
        await synchronize_student_class_representative_binding(
            student_user_id=user_id,
            scope=None,
            clear_existing=True,
            database=db,
        )

    action = "activate_user" if is_active else "deactivate_user"
    await log_audit_event(
        actor_user_id=str(current_user.get("_id")),
        action=action,
        entity_type="user",
        entity_id=user_id,
        action_type="role_change",
        detail=f"User {'activated' if is_active else 'deactivated'}. Reason: {reason}",
        new_value={"is_active": is_active, "reason": reason},
        severity="high" if not is_active else "medium",
    )

    if not is_active:
        await sync_course_offering_read_models_for_query(query={"teacher_user_id": user_id}, database=db)
        await sync_class_slot_read_models_for_offering_query(offering_query={"teacher_user_id": user_id}, database=db)
    if affected_section_ids:
        await sync_section_read_models_for_ids(section_ids=sorted(affected_section_ids), database=db)

    updated = await db.users.find_one({"_id": user_obj_id})
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user")
    return updated


@router.get("/", response_model=list[UserOut])
async def list_users(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    role: str | None = Query(default=None, min_length=1, max_length=50),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=1000, ge=1, le=1000),
    _current_user=Depends(require_permission("users.read")),
) -> list[UserOut]:
    query: dict[str, Any] = {}
    if q:
        needle = re.escape(q)
        query["$or"] = [
            {"full_name": {"$regex": needle, "$options": "i"}},
            {"email": {"$regex": needle, "$options": "i"}},
        ]
    if role:
        query["role"] = role
    if is_active is not None:
        query["is_active"] = is_active

    users = await db.users.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [UserOut(**user_public(user)) for user in users]


@router.get("/admin/capabilities", response_model=UsersAdminCapabilitiesResponse)
async def get_users_admin_capabilities(
    current_user=Depends(require_permission("users.read")),
) -> UsersAdminCapabilitiesResponse:
    return UsersAdminCapabilitiesResponse(**_users_capabilities(current_user))


@router.post("/admin/telemetry")
async def capture_users_admin_telemetry(
    payload: UsersAdminTelemetryEvent,
    current_user=Depends(require_permission("users.read")),
) -> dict[str, str]:
    await _record_users_telemetry(
        event=payload.event,
        outcome=payload.outcome,
        actor_user_id=str(current_user.get("_id")),
        scope=payload.scope,
        severity=payload.severity,
        metadata=payload.metadata,
    )
    return {"status": "ok"}


@router.get("/admin/dashboard", response_model=UsersAdminDashboardResponse)
async def get_users_admin_dashboard(
    window_minutes: int = Query(default=60, ge=5, le=1440),
    bucket_minutes: int = Query(default=5, ge=1, le=60),
    current_user=Depends(require_permission("users.read")),
) -> UsersAdminDashboardResponse:
    _require_users_capability("workspace", current_user)
    started = time.perf_counter()
    try:
        response = await build_users_admin_dashboard(
            window_minutes=window_minutes,
            bucket_minutes=bucket_minutes,
            database=db,
        )

        await _record_users_telemetry(
            event="users.admin.dashboard",
            outcome="success",
            actor_user_id=str(current_user.get("_id")),
            scope="workspace",
            metadata={
                "window_minutes": window_minutes,
                "bucket_minutes": bucket_minutes,
                "request_count": response.latency.request_count,
                "duration_ms": int((time.perf_counter() - started) * 1000),
            },
        )
        return response
    except Exception:
        await _record_users_telemetry(
            event="users.admin.dashboard",
            outcome="error",
            actor_user_id=str(current_user.get("_id")),
            scope="workspace",
            severity="medium",
            metadata={
                "window_minutes": window_minutes,
                "bucket_minutes": bucket_minutes,
                "duration_ms": int((time.perf_counter() - started) * 1000),
            },
        )
        raise


@router.get("/admin/list", response_model=UsersAdminListResponse)
async def list_users_admin(
    request: Request,
    response: Response,
    q: str | None = Query(default=None, min_length=1, max_length=100),
    roles: list[str] | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    admin_types: list[str] | None = Query(default=None),
    extensions: list[str] | None = Query(default=None),
    department: str | None = Query(default=None, min_length=1, max_length=120),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    last_active_from: datetime | None = Query(default=None),
    last_active_to: datetime | None = Query(default=None),
    sort_by: str = Query(default="updated_at", min_length=1, max_length=50),
    sort_dir: Literal["asc", "desc"] = Query(default="desc"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
    current_user=Depends(require_permission("users.read")),
) -> UsersAdminListResponse:
    _require_users_capability("workspace", current_user)
    started = time.perf_counter()
    try:
        query = _build_admin_user_query(
            q=q,
            roles=_normalize_str_list(roles),
            is_active=is_active,
            admin_types=_normalize_str_list(admin_types),
            extensions=_normalize_str_list(extensions),
            department=department,
            created_from=created_from,
            created_to=created_to,
            last_active_from=last_active_from,
            last_active_to=last_active_to,
        )
        sort_spec = _build_admin_sort(sort_by=sort_by, sort_dir=sort_dir)

        skip = (page - 1) * limit
        rows = (
            await db.users.find(query, projection=ADMIN_LIST_PROJECTION)
            .sort(sort_spec)
            .skip(skip)
            .limit(limit)
            .to_list(length=limit)
        )
        total = await db.users.count_documents(query)
        etag_value: str | None = None
        if settings.users_capability_http_cache_validation_enabled:
            etag_value = _build_admin_list_etag(
                query=query,
                sort_spec=sort_spec,
                page=page,
                limit=limit,
                total=total,
                rows=rows,
            )
            response.headers["ETag"] = etag_value
            response.headers["Cache-Control"] = "private, max-age=0, must-revalidate"

            normalized_if_none_match = _normalize_if_none_match(request.headers.get("If-None-Match"))
            if etag_value in normalized_if_none_match:
                await _record_users_telemetry(
                    event="users.admin.list",
                    outcome="success",
                    actor_user_id=str(current_user.get("_id")),
                    scope="workspace",
                    metadata={
                        "page": page,
                        "limit": limit,
                        "returned": 0,
                        "total": total,
                        "cached": True,
                        "duration_ms": int((time.perf_counter() - started) * 1000),
                    },
                )
                return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers={"ETag": etag_value})  # type: ignore[return-value]

        duration_ms = int((time.perf_counter() - started) * 1000)
        await _record_users_telemetry(
            event="users.admin.list",
            outcome="success",
            actor_user_id=str(current_user.get("_id")),
            scope="workspace",
            metadata={
                "page": page,
                "limit": limit,
                "returned": len(rows),
                "total": total,
                "etag_enabled": bool(settings.users_capability_http_cache_validation_enabled),
                "duration_ms": duration_ms,
            },
        )
        return UsersAdminListResponse(
            items=[UserAdminListItem(**user_admin_list_item(row)) for row in rows],
            page=page,
            limit=limit,
            total=total,
            total_pages=_pages(total, limit),
        )
    except Exception:
        duration_ms = int((time.perf_counter() - started) * 1000)
        await _record_users_telemetry(
            event="users.admin.list",
            outcome="error",
            actor_user_id=str(current_user.get("_id")),
            scope="workspace",
            severity="medium",
            metadata={"page": page, "limit": limit, "duration_ms": duration_ms},
        )
        raise


@router.get("/filter-options", response_model=UsersFilterOptionsResponse)
async def list_user_filter_options(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    roles: list[str] | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    admin_types: list[str] | None = Query(default=None),
    extensions: list[str] | None = Query(default=None),
    department: str | None = Query(default=None, min_length=1, max_length=120),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    last_active_from: datetime | None = Query(default=None),
    last_active_to: datetime | None = Query(default=None),
    current_user=Depends(require_permission("users.read")),
) -> UsersFilterOptionsResponse:
    _require_users_capability("workspace", current_user)
    query = _build_admin_user_query(
        q=q,
        roles=_normalize_str_list(roles),
        is_active=is_active,
        admin_types=_normalize_str_list(admin_types),
        extensions=_normalize_str_list(extensions),
        department=department,
        created_from=created_from,
        created_to=created_to,
        last_active_from=last_active_from,
        last_active_to=last_active_to,
    )

    role_rows = await db.users.aggregate(
        [{"$match": query}, {"$group": {"_id": "$role", "count": {"$sum": 1}}}, {"$sort": {"_id": 1}}]
    ).to_list(length=50)
    admin_type_rows = await db.users.aggregate(
        [
            {"$match": query},
            {"$group": {"_id": "$admin_type", "count": {"$sum": 1}}},
            {"$match": {"_id": {"$nin": [None, ""]}}},
            {"$sort": {"_id": 1}},
        ]
    ).to_list(length=100)
    extension_rows = await db.users.aggregate(
        [
            {"$match": query},
            {"$unwind": "$extended_roles"},
            {"$group": {"_id": "$extended_roles", "count": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
    ).to_list(length=100)
    department_rows = await db.users.aggregate(
        [
            {"$match": query},
            {"$group": {"_id": "$profile.department", "count": {"$sum": 1}}},
            {"$match": {"_id": {"$nin": [None, ""]}}},
            {"$sort": {"_id": 1}},
        ]
    ).to_list(length=200)
    status_rows = await db.users.aggregate(
        [{"$match": query}, {"$group": {"_id": "$is_active", "count": {"$sum": 1}}}]
    ).to_list(length=10)
    response = UsersFilterOptionsResponse(
        roles=[FilterOptionCount(value=str(item.get("_id") or ""), count=int(item.get("count") or 0)) for item in role_rows if item.get("_id")],
        admin_types=[FilterOptionCount(value=str(item.get("_id") or ""), count=int(item.get("count") or 0)) for item in admin_type_rows if item.get("_id")],
        extensions=[FilterOptionCount(value=str(item.get("_id") or ""), count=int(item.get("count") or 0)) for item in extension_rows if item.get("_id")],
        departments=[FilterOptionCount(value=str(item.get("_id") or ""), count=int(item.get("count") or 0)) for item in department_rows if item.get("_id")],
        status=[FilterOptionCount(value="active" if bool(item.get("_id")) else "inactive", count=int(item.get("count") or 0)) for item in status_rows],
    )
    await _record_users_telemetry(
        event="users.admin.filter_options",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="workspace",
        metadata={
            "roles": len(response.roles),
            "admin_types": len(response.admin_types),
            "extensions": len(response.extensions),
            "departments": len(response.departments),
            "status": len(response.status),
        },
    )
    return response


@router.get("/filter-presets", response_model=list[UserFilterPresetOut])
async def list_user_filter_presets(
    current_user=Depends(require_permission("users.read")),
) -> list[UserFilterPresetOut]:
    user_id = str(current_user.get("_id"))
    rows = (
        await db.user_filter_presets.find({"created_by_user_id": user_id})
        .sort([("updated_at", -1), ("created_at", -1)])
        .to_list(length=250)
    )
    return [_public_filter_preset(row) for row in rows]


@router.post("/filter-presets", response_model=UserFilterPresetOut, status_code=status.HTTP_201_CREATED)
async def create_user_filter_preset(
    payload: UserFilterPresetCreate,
    current_user=Depends(require_permission("users.read")),
) -> UserFilterPresetOut:
    user_id = str(current_user.get("_id"))
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preset name is required")
    name_normalized = name.casefold()

    existing = await db.user_filter_presets.find_one(
        {"created_by_user_id": user_id, "name_normalized": name_normalized}
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A preset with this name already exists")

    now = _utc_now()
    query = _normalized_filter_preset_query(payload.query.model_dump(exclude_none=True)).model_dump(exclude_none=True)
    document = {
        "created_by_user_id": user_id,
        "name": name,
        "name_normalized": name_normalized,
        "query": query,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.user_filter_presets.insert_one(document)
    created = await db.user_filter_presets.find_one({"_id": result.inserted_id})

    await log_audit_event(
        actor_user_id=user_id,
        action="create_user_filter_preset",
        entity_type="user_filter_preset",
        entity_id=str(result.inserted_id),
        action_type="user_management",
        detail=f"Created users filter preset {name}",
        new_value={"name": name, "query": query},
        severity="low",
    )

    if not created:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create filter preset")
    return _public_filter_preset(created)


@router.patch("/filter-presets/{preset_id}", response_model=UserFilterPresetOut)
async def update_user_filter_preset(
    preset_id: str,
    payload: UserFilterPresetUpdate,
    current_user=Depends(require_permission("users.read")),
) -> UserFilterPresetOut:
    user_id = str(current_user.get("_id"))
    preset_obj_id = parse_object_id(preset_id)
    existing = await db.user_filter_presets.find_one({"_id": preset_obj_id, "created_by_user_id": user_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filter preset not found")

    update_data: dict[str, Any] = {}
    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Preset name is required")
        name_normalized = name.casefold()
        duplicate = await db.user_filter_presets.find_one(
            {
                "created_by_user_id": user_id,
                "name_normalized": name_normalized,
                "_id": {"$ne": preset_obj_id},
            }
        )
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A preset with this name already exists")
        update_data["name"] = name
        update_data["name_normalized"] = name_normalized

    if payload.query is not None:
        update_data["query"] = _normalized_filter_preset_query(payload.query.model_dump(exclude_none=True)).model_dump(
            exclude_none=True
        )

    if not update_data:
        return _public_filter_preset(existing)

    update_data["updated_at"] = _utc_now()
    await db.user_filter_presets.update_one({"_id": preset_obj_id}, {"$set": update_data})
    updated = await db.user_filter_presets.find_one({"_id": preset_obj_id})

    await log_audit_event(
        actor_user_id=user_id,
        action="update_user_filter_preset",
        entity_type="user_filter_preset",
        entity_id=preset_id,
        action_type="user_management",
        detail=f"Updated users filter preset {(update_data.get('name') or existing.get('name') or preset_id)}",
        old_value={"name": existing.get("name"), "query": existing.get("query")},
        new_value={"name": (updated or {}).get("name"), "query": (updated or {}).get("query")},
        severity="low",
    )

    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update filter preset")
    return _public_filter_preset(updated)


@router.delete("/filter-presets/{preset_id}")
async def delete_user_filter_preset(
    preset_id: str,
    current_user=Depends(require_permission("users.read")),
) -> dict[str, str]:
    user_id = str(current_user.get("_id"))
    preset_obj_id = parse_object_id(preset_id)
    existing = await db.user_filter_presets.find_one({"_id": preset_obj_id, "created_by_user_id": user_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Filter preset not found")

    await db.user_filter_presets.delete_one({"_id": preset_obj_id})
    await log_audit_event(
        actor_user_id=user_id,
        action="delete_user_filter_preset",
        entity_type="user_filter_preset",
        entity_id=preset_id,
        action_type="user_management",
        detail=f"Deleted users filter preset {existing.get('name') or preset_id}",
        old_value={"name": existing.get("name"), "query": existing.get("query")},
        severity="medium",
    )
    return {"message": "Filter preset deleted"}


@router.get("/export.csv")
async def export_users_csv(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    roles: list[str] | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    admin_types: list[str] | None = Query(default=None),
    extensions: list[str] | None = Query(default=None),
    department: str | None = Query(default=None, min_length=1, max_length=120),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    last_active_from: datetime | None = Query(default=None),
    last_active_to: datetime | None = Query(default=None),
    sort_by: str = Query(default="updated_at", min_length=1, max_length=50),
    sort_dir: Literal["asc", "desc"] = Query(default="desc"),
    current_user=Depends(require_permission("users.read")),
):
    _require_users_capability("import_export", current_user)
    started = time.perf_counter()
    query = _build_admin_user_query(
        q=q,
        roles=_normalize_str_list(roles),
        is_active=is_active,
        admin_types=_normalize_str_list(admin_types),
        extensions=_normalize_str_list(extensions),
        department=department,
        created_from=created_from,
        created_to=created_to,
        last_active_from=last_active_from,
        last_active_to=last_active_to,
    )
    sort_spec = _build_admin_sort(sort_by=sort_by, sort_dir=sort_dir)

    rows = await db.users.find(query, projection=ADMIN_LIST_PROJECTION).sort(sort_spec).limit(100000).to_list(length=100000)

    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "id",
            "full_name",
            "email",
            "role",
            "admin_type",
            "is_active",
            "extended_roles",
            "department",
            "designation",
            "last_active_at",
            "created_at",
            "updated_at",
        ],
    )
    writer.writeheader()
    for row in rows:
        item = user_admin_list_item(row)
        writer.writerow(
            {
                "id": item.get("id"),
                "full_name": item.get("full_name") or "",
                "email": item.get("email") or "",
                "role": item.get("role") or "",
                "admin_type": item.get("admin_type") or "",
                "is_active": "true" if item.get("is_active") else "false",
                "extended_roles": "|".join(item.get("extended_roles") or []),
                "department": item.get("department") or "",
                "designation": item.get("designation") or "",
                "last_active_at": (item.get("last_active_at") or "").isoformat() if item.get("last_active_at") else "",
                "created_at": (item.get("created_at") or "").isoformat() if item.get("created_at") else "",
                "updated_at": (item.get("updated_at") or "").isoformat() if item.get("updated_at") else "",
            }
        )

    filename = f"users-export-{_utc_now().strftime('%Y%m%d-%H%M%S')}.csv"
    duration_ms = int((time.perf_counter() - started) * 1000)
    await _record_users_telemetry(
        event="users.admin.export_csv",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="import_export",
        metadata={"rows": len(rows), "duration_ms": duration_ms},
    )
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/invitations", response_model=UserInvitationOut, status_code=status.HTTP_201_CREATED)
async def create_user_invitation(
    payload: UserInvitationCreate,
    current_user=Depends(require_permission("users.update")),
) -> UserInvitationOut:
    _require_users_capability("invitations", current_user)
    email = payload.email.lower().strip()
    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")

    if payload.role == "admin":
        admin_type = payload.admin_type or "admin"
    else:
        if payload.admin_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="admin_type is allowed only for admin accounts",
            )
        admin_type = None

    extended_roles = list(payload.extended_roles or [])
    if payload.role in {"teacher", "student"}:
        _validate_extensions_for_role(payload.role, extended_roles)
        role_scope = _normalize_role_scope_payload(
            role=payload.role,
            extensions=extended_roles,
            role_scope=payload.role_scope,
        )
    elif extended_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extended roles are only allowed for teacher or student accounts",
        )
    else:
        role_scope = {}

    now = _utc_now()
    token = secrets.token_urlsafe(32)
    document = {
        "full_name": payload.full_name.strip(),
        "email": email,
        "role": payload.role,
        "admin_type": admin_type,
        "extended_roles": extended_roles,
        "role_scope": role_scope,
        "token": token,
        "status": "pending",
        "created_by_user_id": str(current_user.get("_id")),
        "created_at": now,
        "expires_at": now + timedelta(days=payload.expires_in_days),
    }
    result = await db.user_invitations.insert_one(document)
    created = await db.user_invitations.find_one({"_id": result.inserted_id})

    await log_audit_event(
        actor_user_id=str(current_user.get("_id")),
        action="create_user_invitation",
        entity_type="user_invitation",
        entity_id=str(result.inserted_id),
        action_type="user_management",
        detail=f"Created invitation for {email}",
        new_value={
            "email": email,
            "role": payload.role,
            "admin_type": admin_type,
            "extended_roles": extended_roles,
            "role_scope": role_scope,
        },
        severity="low",
    )

    if not created:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create invitation")
    await _record_users_telemetry(
        event="users.admin.invitation_create",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="invitations",
        metadata={
            "role": payload.role,
            "admin_type": admin_type,
            "has_scope": bool(role_scope),
            "email_domain": email.split("@")[-1] if "@" in email else None,
        },
    )
    return _public_invitation(created)


@router.get("/invitations", response_model=list[UserInvitationOut])
async def list_user_invitations(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    status_filter: Literal["pending", "expired", "accepted"] | None = Query(default=None, alias="status"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
    current_user=Depends(require_permission("users.read")),
) -> list[UserInvitationOut]:
    _require_users_capability("invitations", current_user)
    query: dict[str, Any] = {}
    if q:
        needle = re.escape(q)
        query["$or"] = [
            {"full_name": {"$regex": needle, "$options": "i"}},
            {"email": {"$regex": needle, "$options": "i"}},
        ]
    if status_filter in {"pending", "accepted"}:
        query["status"] = status_filter

    skip = (page - 1) * limit
    rows = await db.user_invitations.find(query).sort([("created_at", -1)]).skip(skip).limit(limit).to_list(length=limit)
    public_rows = [_public_invitation(row) for row in rows]
    if status_filter == "expired":
        public_rows = [item for item in public_rows if item.status == "expired"]
    await _record_users_telemetry(
        event="users.admin.invitation_list",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="invitations",
        metadata={"returned": len(public_rows), "status_filter": status_filter},
    )
    return public_rows


@router.post("/import/preview", response_model=UserImportPreviewResponse)
async def preview_user_import(
    file: UploadFile = File(...),
    current_user=Depends(require_permission("users.update")),
) -> UserImportPreviewResponse:
    _require_users_capability("import_export", current_user)
    if not str(file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only CSV files are supported")

    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV must be UTF-8 encoded") from exc

    reader = csv.DictReader(io.StringIO(decoded))
    if not reader.fieldnames:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV header is missing")

    missing = IMPORT_COLUMNS.difference(set(name.strip() for name in reader.fieldnames if name))
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Missing required CSV columns: {', '.join(sorted(missing))}",
        )

    rows: list[UserImportPreviewRow] = []
    total_rows = 0
    valid_rows = 0
    for index, raw in enumerate(reader, start=2):
        if raw is None:
            continue
        normalized = _normalize_import_row(raw)
        errors = _validate_import_row_payload(normalized)
        row = UserImportPreviewRow(
            row_number=index,
            full_name=normalized.get("full_name") or None,
            email=normalized.get("email") or None,
            role=normalized.get("role") or None,
            admin_type=normalized.get("admin_type"),
            extended_roles=normalized.get("extended_roles") or [],
            valid=not errors,
            errors=errors,
        )
        rows.append(row)
        total_rows += 1
        if not errors:
            valid_rows += 1

    response = UserImportPreviewResponse(
        rows=rows,
        total_rows=total_rows,
        valid_rows=valid_rows,
        invalid_rows=max(total_rows - valid_rows, 0),
    )
    await _record_users_telemetry(
        event="users.admin.import_preview",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="import_export",
        metadata={"total_rows": total_rows, "valid_rows": valid_rows, "invalid_rows": max(total_rows - valid_rows, 0)},
    )
    return response


@router.post("/import/commit", response_model=UserImportCommitResponse)
async def commit_user_import(
    payload: UserImportCommitRequest,
    current_user=Depends(require_permission("users.update")),
) -> UserImportCommitResponse:
    _require_users_capability("import_export", current_user)
    if payload.mode == "create" and not payload.default_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="default_password is required when mode=create",
        )

    now = _utc_now()
    created_count = 0
    invited_count = 0
    skipped_count = 0

    for row in payload.rows:
        email = row.email.lower().strip()
        existing_user = await db.users.find_one({"email": email})
        if existing_user:
            skipped_count += 1
            continue

        role = row.role
        admin_type = row.admin_type
        extensions = list(row.extended_roles or [])

        if role == "admin":
            admin_type = admin_type or "admin"
        elif admin_type:
            skipped_count += 1
            continue

        if role in {"teacher", "student"}:
            try:
                _validate_extensions_for_role(role, extensions)
            except HTTPException:
                skipped_count += 1
                continue
        elif extensions:
            skipped_count += 1
            continue

        if payload.mode == "invite":
            invitation = {
                "full_name": row.full_name.strip(),
                "email": email,
                "role": role,
                "admin_type": admin_type,
                "extended_roles": extensions,
                "token": secrets.token_urlsafe(32),
                "status": "pending",
                "created_by_user_id": str(current_user.get("_id")),
                "created_at": now,
                "expires_at": now + timedelta(days=7),
            }
            await db.user_invitations.insert_one(invitation)
            invited_count += 1
            continue

        user_doc = {
            "full_name": row.full_name.strip(),
            "email": email,
            "hashed_password": get_password_hash(payload.default_password or ""),
            "role": role,
            "admin_type": admin_type,
            "extended_roles": extensions,
            "role_scope": {},
            "is_active": True,
            "must_change_password": True,
            "created_at": now,
            "updated_at": now,
            "schema_version": USER_SCHEMA_VERSION,
        }
        created_result = await db.users.insert_one(user_doc)
        created = await db.users.find_one({"_id": created_result.inserted_id})
        try:
            if created:
                await ensure_student_profile_for_user(created)
        except Exception:
            await db.users.delete_one({"_id": created_result.inserted_id})
            skipped_count += 1
            continue
        created_count += 1

    await log_audit_event(
        actor_user_id=str(current_user.get("_id")),
        action="commit_user_import",
        entity_type="users",
        entity_id=None,
        action_type="bulk_user_management",
        detail=f"Import commit completed in {payload.mode} mode",
        new_value={
            "mode": payload.mode,
            "created_count": created_count,
            "invited_count": invited_count,
            "skipped_count": skipped_count,
        },
        severity="medium",
    )

    response = UserImportCommitResponse(
        mode=payload.mode,
        created_count=created_count,
        invited_count=invited_count,
        skipped_count=skipped_count,
    )
    await _record_users_telemetry(
        event="users.admin.import_commit",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="import_export",
        severity="medium",
        metadata={
            "mode": payload.mode,
            "created_count": created_count,
            "invited_count": invited_count,
            "skipped_count": skipped_count,
        },
    )
    return response


@router.get("/permission-templates", response_model=list[PermissionTemplateOut])
async def list_permission_templates(
    role: str | None = Query(default=None),
    admin_type: str | None = Query(default=None),
    current_user=Depends(require_permission("users.read")),
) -> list[PermissionTemplateOut]:
    _require_users_capability("permission_templates", current_user)
    await _ensure_builtin_permission_templates()
    query: dict[str, Any] = {}
    if role:
        query["role"] = role
    if admin_type:
        query["admin_type"] = admin_type
    rows = await db.user_permission_templates.find(query).sort([("updated_at", -1), ("created_at", -1)]).to_list(length=500)
    await _record_users_telemetry(
        event="users.admin.permission_templates.list",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="permission_templates",
        metadata={"returned": len(rows), "role_filter": role, "admin_type_filter": admin_type},
    )
    return [_public_permission_template(row) for row in rows]


@router.post("/permission-templates", response_model=PermissionTemplateOut, status_code=status.HTTP_201_CREATED)
async def create_permission_template(
    payload: PermissionTemplateCreate,
    current_user=Depends(require_permission("users.update")),
) -> PermissionTemplateOut:
    _require_users_capability("permission_templates", current_user)
    extended_roles = list(payload.extended_roles or [])
    role_scope = payload.role_scope.model_dump(exclude_none=True) if payload.role_scope else {}

    if payload.role in {"teacher", "student"}:
        _validate_extensions_for_role(payload.role, extended_roles)
        _validate_permission_template_scope(payload.role, extended_roles, role_scope)
    elif extended_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extended roles are only allowed for teacher or student templates",
        )

    now = _utc_now()
    document = {
        "name": payload.name.strip(),
        "description": payload.description.strip() if payload.description else None,
        "role": payload.role,
        "admin_type": payload.admin_type,
        "extended_roles": extended_roles,
        "role_scope": role_scope,
        "created_by_user_id": str(current_user.get("_id")),
        "created_at": now,
        "updated_at": now,
    }
    result = await db.user_permission_templates.insert_one(document)
    created = await db.user_permission_templates.find_one({"_id": result.inserted_id})

    await log_audit_event(
        actor_user_id=str(current_user.get("_id")),
        action="create_permission_template",
        entity_type="permission_template",
        entity_id=str(result.inserted_id),
        action_type="user_management",
        detail=f"Created permission template {payload.name.strip()}",
        new_value={
            "role": payload.role,
            "admin_type": payload.admin_type,
            "extended_roles": extended_roles,
        },
        severity="low",
    )

    if not created:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create template")
    await _record_users_telemetry(
        event="users.admin.permission_templates.create",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="permission_templates",
        metadata={"role": payload.role, "admin_type": payload.admin_type, "extended_roles": len(extended_roles)},
    )
    return _public_permission_template(created)


@router.patch("/permission-templates/{template_id}", response_model=PermissionTemplateOut)
async def update_permission_template(
    template_id: str,
    payload: PermissionTemplateUpdate,
    current_user=Depends(require_permission("users.update")),
) -> PermissionTemplateOut:
    _require_users_capability("permission_templates", current_user)
    template_obj_id = parse_object_id(template_id)
    existing = await db.user_permission_templates.find_one({"_id": template_obj_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    update_data = payload.model_dump(exclude_unset=True)
    effective_role = update_data.get("role", existing.get("role"))
    effective_extended_roles = update_data.get("extended_roles", existing.get("extended_roles", [])) or []

    role_scope_payload = update_data.get("role_scope")
    if hasattr(role_scope_payload, "model_dump"):
        role_scope_payload = role_scope_payload.model_dump(exclude_none=True)
    effective_role_scope = role_scope_payload if role_scope_payload is not None else existing.get("role_scope", {})

    if effective_role in {"teacher", "student"}:
        _validate_extensions_for_role(effective_role, effective_extended_roles)
        _validate_permission_template_scope(effective_role, effective_extended_roles, effective_role_scope or {})
    elif effective_extended_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extended roles are only allowed for teacher or student templates",
        )

    if "name" in update_data and isinstance(update_data["name"], str):
        update_data["name"] = update_data["name"].strip()
    if "description" in update_data and isinstance(update_data["description"], str):
        update_data["description"] = update_data["description"].strip() or None
    if role_scope_payload is not None:
        update_data["role_scope"] = effective_role_scope or {}
    update_data["updated_at"] = _utc_now()

    await db.user_permission_templates.update_one({"_id": template_obj_id}, {"$set": update_data})
    updated = await db.user_permission_templates.find_one({"_id": template_obj_id})

    await log_audit_event(
        actor_user_id=str(current_user.get("_id")),
        action="update_permission_template",
        entity_type="permission_template",
        entity_id=template_id,
        action_type="user_management",
        detail="Updated permission template",
        old_value={
            "name": existing.get("name"),
            "role": existing.get("role"),
            "extended_roles": existing.get("extended_roles", []),
            "role_scope": existing.get("role_scope", {}),
        },
        new_value={
            "name": (updated or {}).get("name"),
            "role": (updated or {}).get("role"),
            "extended_roles": (updated or {}).get("extended_roles", []),
            "role_scope": (updated or {}).get("role_scope", {}),
        },
        severity="low",
    )

    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update template")
    await _record_users_telemetry(
        event="users.admin.permission_templates.update",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="permission_templates",
        metadata={"template_id": template_id},
    )
    return _public_permission_template(updated)


@router.delete("/permission-templates/{template_id}")
async def delete_permission_template(
    template_id: str,
    current_user=Depends(require_permission("users.update")),
) -> dict[str, str]:
    _require_users_capability("permission_templates", current_user)
    template_obj_id = parse_object_id(template_id)
    existing = await db.user_permission_templates.find_one({"_id": template_obj_id})
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    await db.user_permission_templates.delete_one({"_id": template_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user.get("_id")),
        action="delete_permission_template",
        entity_type="permission_template",
        entity_id=template_id,
        action_type="user_management",
        detail=f"Deleted permission template {existing.get('name') or template_id}",
        old_value={
            "name": existing.get("name"),
            "role": existing.get("role"),
            "extended_roles": existing.get("extended_roles", []),
        },
        severity="medium",
    )
    await _record_users_telemetry(
        event="users.admin.permission_templates.delete",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="permission_templates",
        severity="medium",
        metadata={"template_id": template_id, "name": existing.get("name")},
    )
    return {"message": "Template deleted"}


@router.post("/bulk/status", response_model=UserBulkStatusResponse)
async def bulk_update_user_status(
    payload: UserBulkStatusUpdate,
    current_user=Depends(require_permission("users.update")),
) -> UserBulkStatusResponse:
    _require_users_capability("bulk_operations", current_user)
    unique_user_ids = list(dict.fromkeys(payload.user_ids))
    results: list[UserBulkStatusResultItem] = []
    updated_count = 0

    for user_id in unique_user_ids:
        try:
            await _apply_status_update(
                user_id=user_id,
                is_active=payload.is_active,
                reason=payload.reason,
                current_user=current_user,
            )
            results.append(UserBulkStatusResultItem(user_id=user_id, success=True, message=None))
            updated_count += 1
        except HTTPException as exc:
            results.append(UserBulkStatusResultItem(user_id=user_id, success=False, message=str(exc.detail)))

    response = UserBulkStatusResponse(
        updated_count=updated_count,
        failed_count=max(len(results) - updated_count, 0),
        results=results,
    )
    await _record_users_telemetry(
        event="users.admin.bulk_status",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="bulk_operations",
        severity="medium",
        metadata={
            "requested_count": len(unique_user_ids),
            "updated_count": response.updated_count,
            "failed_count": response.failed_count,
            "target_is_active": payload.is_active,
        },
    )
    return response


@router.patch("/bulk/extensions", response_model=UserBulkExtensionsResponse)
async def bulk_update_user_extensions(
    payload: UserBulkExtensionsUpdate,
    current_user=Depends(require_permission("users.update")),
) -> UserBulkExtensionsResponse:
    _require_users_capability("bulk_operations", current_user)
    results: list[UserBulkExtensionsResultItem] = []
    updated_count = 0

    for update_item in payload.updates:
        extension_payload = UserExtensionRolesUpdate(
            extended_roles=update_item.extended_roles,
            role_scope=update_item.role_scope,
            change_reason=payload.change_reason,
        )
        try:
            await _apply_extension_update(
                user_id=update_item.user_id,
                payload=extension_payload,
                current_user_id=str(current_user.get("_id")),
                current_user_name=_actor_display_name(current_user),
            )
            results.append(UserBulkExtensionsResultItem(user_id=update_item.user_id, success=True, message=None))
            updated_count += 1
        except HTTPException as exc:
            results.append(UserBulkExtensionsResultItem(user_id=update_item.user_id, success=False, message=str(exc.detail)))

    response = UserBulkExtensionsResponse(
        updated_count=updated_count,
        failed_count=max(len(results) - updated_count, 0),
        results=results,
    )
    await _record_users_telemetry(
        event="users.admin.bulk_extensions",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="bulk_operations",
        severity="medium",
        metadata={
            "requested_count": len(payload.updates),
            "updated_count": response.updated_count,
            "failed_count": response.failed_count,
        },
    )
    return response


@router.post("/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    current_user=Depends(require_permission("users.update")),
) -> UserOut:
    _require_users_capability("workspace", current_user)
    email = payload.email.lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email is already registered")

    extended_roles = list(payload.extended_roles or [])
    if payload.role in {"teacher", "student"}:
        _validate_extensions_for_role(payload.role, extended_roles)
        role_scope = _normalize_role_scope_payload(
            role=payload.role,
            extensions=extended_roles,
            role_scope=payload.role_scope,
        )
    elif extended_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extended roles are only allowed for teacher or student accounts",
        )
    else:
        role_scope = {}

    if payload.role == "admin":
        admin_type = payload.admin_type or "admin"
    else:
        if payload.admin_type is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="admin_type is allowed only for admin accounts",
            )
        admin_type = None

    now = _utc_now()
    document = {
        "full_name": payload.full_name.strip(),
        "email": email,
        "hashed_password": get_password_hash(payload.password),
        "role": payload.role,
        "admin_type": admin_type,
        "extended_roles": extended_roles,
        "role_scope": role_scope,
        "is_active": True,
        "must_change_password": False,
        "created_at": now,
        "updated_at": now,
        "last_permission_change_at": now if role_scope or extended_roles else None,
        "last_permission_change_by": _actor_display_name(current_user) or str(current_user.get("_id") or ""),
        "schema_version": USER_SCHEMA_VERSION,
    }
    result = await db.users.insert_one(document)
    created = await db.users.find_one({"_id": result.inserted_id})
    try:
        if created:
            await ensure_student_profile_for_user(created)
            normalized_scope, affected_sections = await _synchronize_role_scope_bindings(
                user_id=str(created.get("_id")),
                role=payload.role,
                extensions=extended_roles,
                role_scope=role_scope,
                clear_existing=False,
            )
            await db.users.update_one(
                {"_id": result.inserted_id},
                {
                    "$set": {
                        "role_scope": normalized_scope,
                        "updated_at": _utc_now(),
                        "schema_version": USER_SCHEMA_VERSION,
                    }
                },
            )
            created = await db.users.find_one({"_id": result.inserted_id})
    except Exception:
        try:
            if payload.role == "student":
                await clear_student_club_president(str(result.inserted_id), sync_target_user_record=False)
        except Exception:
            pass
        await db.users.delete_one({"_id": result.inserted_id})
        raise

    if not created:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create user")
    await _record_users_telemetry(
        event="users.admin.user_create",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="workspace",
        metadata={"role": payload.role, "admin_type": admin_type, "has_scope": bool(role_scope)},
    )
    return UserOut(**user_public(created))


@router.get("/{user_id}/activity", response_model=UserActivityResponse)
async def get_user_activity(
    user_id: str,
    action: str | None = Query(default=None, min_length=1, max_length=100),
    severity: Literal["low", "medium", "high"] | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=25, ge=1, le=100),
    current_user=Depends(require_permission("users.read")),
) -> UserActivityResponse:
    _require_users_capability("activity", current_user)
    user_obj_id = parse_object_id(user_id)
    user = await db.users.find_one({"_id": user_obj_id}, {"_id": 1})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    query: dict[str, Any] = {
        "$or": [
            {"entity_type": "user", "entity_id": user_id},
            {"actor_user_id": user_id},
        ]
    }
    if action:
        query["action"] = action
    if severity:
        query["severity"] = severity

    total = await db.audit_logs.count_documents(query)
    skip = (page - 1) * limit
    rows = await db.audit_logs.find(query).sort([("created_at", -1)]).skip(skip).limit(limit).to_list(length=limit)
    items: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item["id"] = str(item.pop("_id"))
        items.append(item)

    response = UserActivityResponse(
        items=items,
        page=page,
        limit=limit,
        total=total,
        total_pages=_pages(total, limit),
    )
    await _record_users_telemetry(
        event="users.admin.activity",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="activity",
        metadata={"user_id": user_id, "page": page, "limit": limit, "returned": len(items), "total": total},
    )
    return response


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: str,
    current_user=Depends(require_permission("users.read")),
) -> UserOut:
    _require_users_capability("workspace", current_user)
    user = await db.users.find_one({"_id": parse_object_id(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserOut(**user_public(user))


@router.patch("/{user_id}/profile", response_model=UserOut)
async def update_user_profile_admin(
    user_id: str,
    payload: UserAdminProfileUpdate,
    current_user=Depends(require_permission("users.update")),
) -> UserOut:
    _require_users_capability("inline_editing", current_user)
    user_obj_id = parse_object_id(user_id)
    user = await db.users.find_one({"_id": user_obj_id})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    update_data = payload.model_dump(exclude_unset=True)
    reason = str(update_data.pop("change_reason", "") or "").strip()
    set_data: dict[str, Any] = {}
    old_value: dict[str, Any] = {}
    new_value: dict[str, Any] = {}

    if "full_name" in update_data:
        full_name = str(update_data.get("full_name") or "").strip()
        if len(full_name) < 2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="full_name must be at least 2 characters")
        if full_name != str(user.get("full_name") or ""):
            set_data["full_name"] = full_name
            old_value["full_name"] = user.get("full_name")
            new_value["full_name"] = full_name

    profile_fields = ("phone", "department", "designation", "organization")
    existing_profile = dict(user.get("profile") or {})
    next_profile = dict(existing_profile)
    profile_changed = False
    for field in profile_fields:
        if field not in update_data:
            continue
        raw_value = update_data.get(field)
        normalized = raw_value.strip() if isinstance(raw_value, str) else None
        normalized = normalized or None
        if next_profile.get(field) == normalized:
            continue
        next_profile[field] = normalized
        profile_changed = True
        old_value[f"profile.{field}"] = existing_profile.get(field)
        new_value[f"profile.{field}"] = normalized

    if profile_changed:
        set_data["profile"] = next_profile

    if not set_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No profile fields changed")

    set_data["updated_at"] = _utc_now()
    set_data["schema_version"] = USER_SCHEMA_VERSION
    await db.users.update_one({"_id": user_obj_id}, {"$set": set_data})
    updated = await db.users.find_one({"_id": user_obj_id})
    if not updated:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update user profile")

    detail = "Updated admin-safe user profile fields"
    if reason:
        detail = f"{detail}. Reason: {reason}"
    await log_audit_event(
        actor_user_id=str(current_user.get("_id")),
        action="update_user_profile",
        entity_type="user",
        entity_id=user_id,
        action_type="user_management",
        detail=detail,
        old_value=old_value or None,
        new_value={**new_value, "change_reason": reason or None} if new_value else {"change_reason": reason or None},
        severity="low",
    )
    await _record_users_telemetry(
        event="users.admin.profile_update",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="inline_editing",
        metadata={"user_id": user_id, "changed_fields": sorted(list(new_value.keys()))},
    )

    return UserOut(**user_public(updated))


@router.patch("/{user_id}/extensions", response_model=UserOut)
async def update_user_extension_roles(
    user_id: str,
    payload: UserExtensionRolesUpdate,
    review_id: str | None = Query(default=None),
    current_user=Depends(require_permission("users.update")),
) -> UserOut:
    _require_users_capability("workspace", current_user)
    await enforce_review_approval(
        current_user=current_user,
        review_id=review_id,
        action="users.update.extensions",
        entity_type="user",
        entity_id=user_id,
        review_type="role_change",
    )
    updated = await _apply_extension_update(
        user_id=user_id,
        payload=payload,
        current_user_id=str(current_user.get("_id")),
        current_user_name=_actor_display_name(current_user),
    )
    await _record_users_telemetry(
        event="users.admin.extensions_update",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="workspace",
        metadata={"user_id": user_id, "extended_roles": len(payload.extended_roles or [])},
    )
    return UserOut(**user_public(updated))


@router.patch("/{user_id}/status", response_model=UserOut)
async def update_user_status(
    user_id: str,
    payload: UserStatusUpdate,
    current_user=Depends(require_permission("users.update")),
) -> UserOut:
    _require_users_capability("workspace", current_user)
    updated = await _apply_status_update(
        user_id=user_id,
        is_active=payload.is_active,
        reason=payload.reason,
        current_user=current_user,
    )
    await _record_users_telemetry(
        event="users.admin.status_update",
        outcome="success",
        actor_user_id=str(current_user.get("_id")),
        scope="workspace",
        severity="medium",
        metadata={"user_id": user_id, "is_active": payload.is_active},
    )
    return UserOut(**user_public(updated))


@router.delete("/{user_id}")
async def deactivate_user(
    user_id: str,
    reason: str | None = Query(default=None, min_length=3, max_length=500),
    current_user=Depends(require_permission("users.update")),
) -> dict[str, str]:
    _require_users_capability("workspace", current_user)
    await _apply_status_update(
        user_id=user_id,
        is_active=False,
        reason=reason or "Legacy deactivation via DELETE /users/{user_id}",
        current_user=current_user,
    )
    return {"message": "User deactivated"}
