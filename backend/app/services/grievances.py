from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable
from uuid import uuid4

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import GRIEVANCE_SCHEMA_VERSION
from app.services.notifications import create_notifications_bulk
from app.services.public_ids import build_public_id, persist_public_id
from app.services.rbac import build_user_scope_filter, merge_query_with_scope_filter, resolve_admin_role_document
from app.services.section_mapping import coordinator_scope_class_id, is_section_coordinator

GRIEVANCE_ESCALATION_HOURS = 24
UNRESOLVED_GRIEVANCE_STATUSES = {"open", "in_progress", "reopened"}
GRIEVANCE_STAGES = ("coordinator", "hod", "dean")
FALLBACK_ADMIN_TYPES = {"academic_admin", "super_admin"}
STAFF_ROLES = {"admin", "teacher"}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def grievance_due_at(*, from_dt: datetime | None = None) -> datetime:
    base = from_dt or utc_now()
    return base + timedelta(hours=GRIEVANCE_ESCALATION_HOURS)


def build_timeline_entry(
    *,
    kind: str,
    message: str,
    visibility: str = "public",
    stage: str | None = None,
    actor: dict[str, Any] | None = None,
    forwarded_to: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    created_at: datetime | None = None,
) -> dict[str, Any]:
    return {
        "entry_id": uuid4().hex,
        "kind": kind,
        "visibility": visibility,
        "message": message.strip(),
        "stage": stage,
        "actor_user_id": str(actor.get("_id")) if actor and actor.get("_id") else None,
        "actor_name": actor.get("full_name") if actor else None,
        "actor_email": actor.get("email") if actor else None,
        "forwarded_to_user_id": str(forwarded_to.get("_id")) if forwarded_to and forwarded_to.get("_id") else None,
        "forwarded_to_name": forwarded_to.get("full_name") if forwarded_to else None,
        "forwarded_to_email": forwarded_to.get("email") if forwarded_to else None,
        "created_at": created_at or utc_now(),
        "metadata": metadata or None,
    }


async def student_profile_for_user(current_user: dict[str, Any], *, database: Any | None = None) -> dict[str, Any]:
    active_db = database if database is not None else db
    user_id = str(current_user.get("_id") or "")
    user_email = str(current_user.get("email") or "").strip().lower()
    student = await active_db.students.find_one(
        {
            "is_active": True,
            "$or": [{"user_id": user_id}, {"email": user_email}],
        }
    )
    if not student:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student profile not found")
    return student


async def grievance_or_404(grievance_id: str, *, database: Any | None = None) -> dict[str, Any]:
    active_db = database if database is not None else db
    grievance = await active_db.grievances.find_one({"_id": parse_object_id(grievance_id)})
    if not grievance:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Grievance not found")
    return grievance


async def section_for_grievance(grievance: dict[str, Any], *, database: Any | None = None) -> dict[str, Any] | None:
    active_db = database if database is not None else db
    section_id = str(grievance.get("section_id") or "").strip()
    if not section_id or not ObjectId.is_valid(section_id):
        return None
    return await active_db.classes.find_one({"_id": ObjectId(section_id)})


async def _active_user(user_id: str, *, database: Any | None = None) -> dict[str, Any] | None:
    active_db = database if database is not None else db
    if not user_id or not ObjectId.is_valid(user_id):
        return None
    return await active_db.users.find_one({"_id": ObjectId(user_id), "is_active": True})


async def _admin_users_for_role(
    role_code: str,
    *,
    department_id: str | None = None,
    database: Any | None = None,
) -> list[dict[str, Any]]:
    active_db = database if database is not None else db
    normalized_role_code = role_code.strip().upper()
    query = {
        "role": "admin",
        "is_active": True,
        "$or": [{"admin_type": normalized_role_code.lower()}, {"rbac_role_code": normalized_role_code}],
    }
    rows = await active_db.users.find(query).to_list(length=500)
    if normalized_role_code not in {"HOD", "DEAN"} or not department_id:
        return rows

    user_ids = [str(item.get("_id")) for item in rows if item.get("_id")]
    if not user_ids:
        return []
    scopes = await active_db.scopes.find(
        {"user_id": {"$in": user_ids}, "department_id": department_id}
    ).to_list(length=500)
    scoped_user_ids = {scope.get("user_id") for scope in scopes if scope.get("user_id")}
    return [row for row in rows if str(row.get("_id")) in scoped_user_ids]


async def stage_recipients(
    grievance: dict[str, Any],
    stage: str,
    *,
    database: Any | None = None,
) -> list[dict[str, Any]]:
    active_db = database if database is not None else db
    if stage == "coordinator":
        section = await section_for_grievance(grievance, database=active_db)
        coordinator_user_id = str(section.get("class_coordinator_user_id") or "") if section else ""
        coordinator = await _active_user(coordinator_user_id, database=active_db)
        return [coordinator] if coordinator and coordinator.get("role") == "teacher" else []
    if stage == "hod":
        return await _admin_users_for_role("HOD", department_id=grievance.get("department_id"), database=active_db)
    if stage == "dean":
        return await _admin_users_for_role("DEAN", department_id=grievance.get("department_id"), database=active_db)
    return []


async def fallback_recipients(*, database: Any | None = None) -> list[dict[str, Any]]:
    active_db = database if database is not None else db
    query = {
        "role": "admin",
        "is_active": True,
        "$or": [
            {"admin_type": {"$in": sorted(FALLBACK_ADMIN_TYPES)}},
            {"rbac_role_code": {"$in": ["ACADEMIC_ADMIN", "SUPER_ADMIN"]}},
        ],
    }
    return await active_db.users.find(query).to_list(length=500)


async def next_available_stage(
    grievance: dict[str, Any],
    *,
    from_stage: str | None = None,
    database: Any | None = None,
) -> tuple[str | None, list[dict[str, Any]], list[str]]:
    active_db = database if database is not None else db
    skipped: list[str] = []
    stages = list(GRIEVANCE_STAGES)
    start_index = 0
    if from_stage in stages:
        start_index = stages.index(from_stage) + 1
    for stage in stages[start_index:]:
        recipients = await stage_recipients(grievance, stage, database=active_db)
        if recipients:
            return stage, recipients, skipped
        skipped.append(stage)
    return None, [], skipped


async def first_available_stage(
    grievance: dict[str, Any],
    *,
    database: Any | None = None,
) -> tuple[str | None, list[dict[str, Any]], list[str]]:
    return await next_available_stage(grievance, from_stage=None, database=database)


async def admin_role_code(current_user: dict[str, Any], *, database: Any | None = None) -> str | None:
    role_doc = await resolve_admin_role_document(current_user, database if database is not None else db)
    return role_doc.get("code") if role_doc else None


async def teacher_scope_section_ids(current_user: dict[str, Any], *, database: Any | None = None) -> set[str]:
    active_db = database if database is not None else db
    scoped_class_id = coordinator_scope_class_id(current_user)
    if scoped_class_id:
        return {scoped_class_id}
    if current_user.get("role") != "teacher":
        return set()
    rows = await active_db.classes.find(
        {"class_coordinator_user_id": str(current_user.get("_id")), "is_active": True},
        {"_id": 1},
    ).to_list(length=100)
    return {str(row["_id"]) for row in rows if row.get("_id")}


async def teacher_can_view_grievance(current_user: dict[str, Any], grievance: dict[str, Any], *, database: Any | None = None) -> bool:
    if grievance.get("assigned_resolver_user_id") == str(current_user.get("_id")):
        return True
    if current_user.get("role") != "teacher":
        return False
    if "class_coordinator" not in set(current_user.get("extended_roles") or []):
        return False
    section = await section_for_grievance(grievance, database=database)
    return is_section_coordinator(current_user, section)


async def admin_has_department_access(current_user: dict[str, Any], grievance: dict[str, Any], *, database: Any | None = None) -> bool:
    active_db = database if database is not None else db
    if grievance.get("assigned_resolver_user_id") == str(current_user.get("_id")):
        return True
    if current_user.get("role") != "admin":
        return False
    role_code = await admin_role_code(current_user, database=active_db)
    if role_code in {"SUPER_ADMIN", "ACADEMIC_ADMIN"}:
        return True
    if role_code not in {"HOD", "DEAN"}:
        return False
    scope_filter = await build_user_scope_filter(
        current_user,
        department_field="department_id",
        year_field=None,
        database=active_db,
    )
    scoped_query = merge_query_with_scope_filter({"department_id": grievance.get("department_id")}, scope_filter)
    return scoped_query != {"_id": {"$exists": False}}


async def can_view_grievance(current_user: dict[str, Any], grievance: dict[str, Any], *, database: Any | None = None) -> bool:
    if current_user.get("role") == "student":
        return grievance.get("student_user_id") == str(current_user.get("_id"))
    if current_user.get("role") == "teacher":
        return await teacher_can_view_grievance(current_user, grievance, database=database)
    if current_user.get("role") == "admin":
        return await admin_has_department_access(current_user, grievance, database=database)
    return False


async def can_manage_current_stage(current_user: dict[str, Any], grievance: dict[str, Any], *, database: Any | None = None) -> bool:
    active_db = database if database is not None else db
    if current_user.get("role") == "teacher":
        if grievance.get("current_stage") != "coordinator":
            return False
        return await teacher_can_view_grievance(current_user, grievance, database=active_db)
    if current_user.get("role") != "admin":
        return False
    role_code = await admin_role_code(current_user, database=active_db)
    if role_code in {"SUPER_ADMIN", "ACADEMIC_ADMIN"}:
        return True
    stage_role_map = {"hod": "HOD", "dean": "DEAN"}
    expected_role = stage_role_map.get(str(grievance.get("current_stage") or ""))
    if not expected_role or role_code != expected_role:
        return False
    return await admin_has_department_access(current_user, grievance, database=active_db)


async def can_add_public_comment(current_user: dict[str, Any], grievance: dict[str, Any], *, database: Any | None = None) -> bool:
    if current_user.get("role") == "student":
        return grievance.get("student_user_id") == str(current_user.get("_id"))
    if grievance.get("assigned_resolver_user_id") == str(current_user.get("_id")):
        return True
    return await can_manage_current_stage(current_user, grievance, database=database)


async def can_add_internal_note(current_user: dict[str, Any], grievance: dict[str, Any], *, database: Any | None = None) -> bool:
    if current_user.get("role") not in STAFF_ROLES:
        return False
    if grievance.get("assigned_resolver_user_id") == str(current_user.get("_id")):
        return True
    return await can_manage_current_stage(current_user, grievance, database=database)


async def can_forward_grievance(current_user: dict[str, Any], grievance: dict[str, Any], *, database: Any | None = None) -> bool:
    return await can_manage_current_stage(current_user, grievance, database=database)


async def can_update_status(current_user: dict[str, Any], grievance: dict[str, Any], *, database: Any | None = None) -> bool:
    if grievance.get("status") == "routing_failed":
        if current_user.get("role") != "admin":
            return False
        role_code = await admin_role_code(current_user, database=database if database is not None else db)
        return role_code in {"SUPER_ADMIN", "ACADEMIC_ADMIN"}
    if grievance.get("status") == "resolved":
        return False
    if grievance.get("assigned_resolver_user_id") == str(current_user.get("_id")):
        return True
    return await can_manage_current_stage(current_user, grievance, database=database)


async def can_resolve_grievance(current_user: dict[str, Any], grievance: dict[str, Any], *, database: Any | None = None) -> bool:
    return await can_manage_current_stage(current_user, grievance, database=database)


async def can_reopen_grievance(current_user: dict[str, Any], grievance: dict[str, Any], *, database: Any | None = None) -> bool:
    return current_user.get("role") == "student" and grievance.get("student_user_id") == str(current_user.get("_id"))


async def grievance_inbox_query(current_user: dict[str, Any], *, view: str, database: Any | None = None) -> dict[str, Any]:
    active_db = database if database is not None else db
    if current_user.get("role") == "teacher":
        if view == "assigned":
            return {"assigned_resolver_user_id": str(current_user.get("_id"))}
        section_ids = sorted(await teacher_scope_section_ids(current_user, database=active_db))
        if not section_ids:
            return {"_id": {"$exists": False}}
        return {"section_id": {"$in": section_ids}}

    if current_user.get("role") != "admin":
        return {"_id": {"$exists": False}}

    role_code = await admin_role_code(current_user, database=active_db)
    if view == "assigned":
        return {"assigned_resolver_user_id": str(current_user.get("_id"))}
    if view == "fallback":
        if role_code not in {"SUPER_ADMIN", "ACADEMIC_ADMIN"}:
            return {"_id": {"$exists": False}}
        return {"status": "routing_failed"}
    if role_code in {"SUPER_ADMIN", "ACADEMIC_ADMIN"}:
        return {"current_stage": view}
    stage_role_map = {"hod": "HOD", "dean": "DEAN"}
    expected_role = stage_role_map.get(view)
    if role_code != expected_role:
        return {"_id": {"$exists": False}}
    base_query = {"current_stage": view}
    scope_filter = await build_user_scope_filter(
        current_user,
        department_field="department_id",
        year_field=None,
        database=active_db,
    )
    return merge_query_with_scope_filter(base_query, scope_filter)


def grievance_stage_notification(stage: str, grievance: dict[str, Any]) -> tuple[str, str]:
    public_id = grievance.get("public_id") or build_public_id("grievance", grievance, prefer_existing=True) or "grievance"
    title = f"Grievance {public_id} requires attention"
    stage_label = stage.replace("_", " ").title()
    message = f"{grievance.get('title') or 'Student grievance'} is now with {stage_label}."
    return title, message


async def notify_stage_recipients(
    grievance: dict[str, Any],
    stage: str,
    recipients: Iterable[dict[str, Any]],
    *,
    created_by: str | None = None,
) -> int:
    recipient_ids = [str(item.get("_id")) for item in recipients if item and item.get("_id")]
    if not recipient_ids:
        return 0
    title, message = grievance_stage_notification(stage, grievance)
    return await create_notifications_bulk(
        title=title,
        message=message,
        priority="high",
        scope="grievance",
        target_user_ids=recipient_ids,
        created_by=created_by,
    )


async def notify_users_about_grievance(
    grievance: dict[str, Any],
    *,
    user_ids: Iterable[str],
    title: str,
    message: str,
    created_by: str | None = None,
) -> int:
    normalized_ids = [str(user_id) for user_id in user_ids if user_id]
    if not normalized_ids:
        return 0
    return await create_notifications_bulk(
        title=title,
        message=message,
        priority="normal",
        scope="grievance",
        target_user_ids=normalized_ids,
        created_by=created_by,
    )


async def route_new_grievance(
    grievance: dict[str, Any],
    *,
    database: Any | None = None,
) -> tuple[str, list[dict[str, Any]], list[str]]:
    return await first_available_stage(grievance, database=database)


async def persist_grievance(document: dict[str, Any], *, database: Any | None = None) -> dict[str, Any]:
    active_db = database if database is not None else db
    persist_public_id(document, kind="grievance")
    result = await active_db.grievances.insert_one(document)
    public_id = build_public_id("grievance", {**document, "_id": result.inserted_id}, prefer_existing=False)
    if public_id:
        await active_db.grievances.update_one({"_id": result.inserted_id}, {"$set": {"public_id": public_id}})
    return await active_db.grievances.find_one({"_id": result.inserted_id})


async def append_timeline_entry(
    grievance_id: str,
    entry: dict[str, Any],
    *,
    set_fields: dict[str, Any] | None = None,
    database: Any | None = None,
) -> dict[str, Any]:
    active_db = database if database is not None else db
    update_doc: dict[str, Any] = {
        "$push": {"timeline": entry},
        "$set": {"schema_version": GRIEVANCE_SCHEMA_VERSION},
    }
    if set_fields:
        update_doc["$set"].update(set_fields)
    await active_db.grievances.update_one({"_id": parse_object_id(grievance_id)}, update_doc)
    return await active_db.grievances.find_one({"_id": parse_object_id(grievance_id)})


async def escalate_due_grievances(*, limit: int = 200, database: Any | None = None) -> int:
    active_db = database if database is not None else db
    now = utc_now()
    rows = await active_db.grievances.find(
        {
            "status": {"$in": sorted(UNRESOLVED_GRIEVANCE_STATUSES)},
            "stage_due_at": {"$lte": now},
        }
    ).sort("stage_due_at", 1).limit(limit).to_list(length=limit)
    processed = 0

    for grievance in rows:
        grievance_id = str(grievance.get("_id"))
        next_stage, recipients, skipped = await next_available_stage(
            grievance,
            from_stage=str(grievance.get("current_stage") or ""),
            database=active_db,
        )
        new_timeline = list(grievance.get("timeline") or [])
        for skipped_stage in skipped:
            new_timeline.append(
                build_timeline_entry(
                    kind="escalated",
                    stage=skipped_stage,
                    message=f"No active {skipped_stage.title()} recipient was available. Skipping this stage.",
                    metadata={"skipped": True},
                    created_at=now,
                )
            )

        if next_stage and recipients:
            new_timeline.append(
                build_timeline_entry(
                    kind="escalated",
                    stage=next_stage,
                    message=f"Automatically escalated to {next_stage.title()} after 24 hours without resolution.",
                    created_at=now,
                )
            )
            await active_db.grievances.update_one(
                {"_id": grievance["_id"]},
                {
                    "$set": {
                        "current_stage": next_stage,
                        "assigned_resolver_user_id": None,
                        "assigned_resolver_name": None,
                        "assigned_resolver_email": None,
                        "forwarded_by_user_id": None,
                        "forwarded_by_name": None,
                        "forwarded_by_email": None,
                        "forwarded_at": None,
                        "status": "open",
                        "stage_due_at": grievance_due_at(from_dt=now),
                        "timeline": new_timeline,
                        "schema_version": GRIEVANCE_SCHEMA_VERSION,
                    }
                },
            )
            updated = await active_db.grievances.find_one({"_id": grievance["_id"]})
            await notify_stage_recipients(updated, next_stage, recipients, created_by=None)
            await notify_users_about_grievance(
                updated,
                user_ids=[updated.get("student_user_id")],
                title="Your grievance was escalated",
                message=f"{updated.get('title') or 'Your grievance'} has been escalated to {next_stage.title()}.",
                created_by=None,
            )
            processed += 1
            continue

        fallback_users = await fallback_recipients(database=active_db)
        new_timeline.append(
            build_timeline_entry(
                kind="routing_failed",
                stage=str(grievance.get("current_stage") or "coordinator"),
                message="No valid escalation owner was available. Sent to academic admin fallback queue.",
                created_at=now,
            )
        )
        await active_db.grievances.update_one(
            {"_id": grievance["_id"]},
            {
                "$set": {
                    "status": "routing_failed",
                    "stage_due_at": None,
                    "assigned_resolver_user_id": None,
                    "assigned_resolver_name": None,
                    "assigned_resolver_email": None,
                    "forwarded_by_user_id": None,
                    "forwarded_by_name": None,
                    "forwarded_by_email": None,
                    "forwarded_at": None,
                    "timeline": new_timeline,
                    "schema_version": GRIEVANCE_SCHEMA_VERSION,
                }
            },
        )
        updated = await active_db.grievances.find_one({"_id": grievance["_id"]})
        await notify_users_about_grievance(
            updated,
            user_ids=[str(item.get("_id")) for item in fallback_users if item.get("_id")],
            title="Grievance routing failed",
            message=f"{updated.get('title') or 'A grievance'} needs manual reassignment.",
            created_by=None,
        )
        processed += 1

    return processed
