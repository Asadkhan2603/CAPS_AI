from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import GRIEVANCE_SCHEMA_VERSION
from app.core.security import require_roles
from app.models.grievances import grievance_public
from app.models.users import user_public
from app.schemas.grievance import (
    GrievanceCommentCreate,
    GrievanceForwardCreate,
    GrievanceInboxView,
    GrievanceInternalNoteCreate,
    GrievanceOut,
    GrievanceReopenCreate,
    GrievanceStatusUpdate,
)
from app.schemas.user import UserOut
from app.services.audit import log_audit_event
from app.services.grievances import (
    append_timeline_entry,
    can_add_internal_note,
    can_add_public_comment,
    can_forward_grievance,
    can_reopen_grievance,
    can_resolve_grievance,
    can_update_status,
    can_view_grievance,
    fallback_recipients,
    first_available_stage,
    grievance_due_at,
    grievance_inbox_query,
    grievance_or_404,
    notify_stage_recipients,
    notify_users_about_grievance,
    persist_grievance,
    stage_recipients,
    student_profile_for_user,
    utc_now,
    build_timeline_entry,
)

router = APIRouter()

GRIEVANCE_UPLOAD_DIR = Path("uploads/grievances")
MAX_ATTACHMENT_SIZE = 10 * 1024 * 1024
ALLOWED_ATTACHMENT_EXTENSIONS = {".png", ".jpg", ".jpeg", ".pdf", ".doc", ".docx", ".txt", ".md"}


async def _latest_student_section_id(student: dict) -> str | None:
    class_id = str(student.get("class_id") or "").strip()
    if class_id:
        return class_id
    rows = await db.enrollments.find({"student_id": str(student["_id"])}).to_list(length=200)
    rows.sort(key=lambda item: item.get("created_at") or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    for row in rows:
        candidate = str(row.get("class_id") or "").strip()
        if candidate:
            return candidate
    return None


async def _student_context_for_create(current_user: dict) -> tuple[dict, dict, dict | None]:
    student = await student_profile_for_user(current_user, database=db)
    section_id = await _latest_student_section_id(student)
    if not section_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student is not mapped to any section")
    section = await db.classes.find_one({"_id": parse_object_id(section_id)})
    if not section:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student section could not be resolved")
    department = None
    department_id = str(section.get("department_id") or "").strip()
    if department_id:
        department = await db.departments.find_one({"_id": parse_object_id(department_id)})
    return student, section, department


def _grievance_payload(grievance: dict, *, include_internal: bool) -> GrievanceOut:
    return GrievanceOut(**grievance_public(grievance, include_internal=include_internal))


async def _visible_grievance_or_404(grievance_id: str, current_user: dict) -> dict:
    grievance = await grievance_or_404(grievance_id, database=db)
    if not await can_view_grievance(current_user, grievance, database=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this grievance")
    return grievance


def _attachment_suffix(filename: str | None) -> str:
    return Path(filename or "").suffix.lower()


async def _store_attachment(file: UploadFile | None) -> dict[str, object]:
    if not file:
        return {
            "attachment_original_filename": None,
            "attachment_stored_filename": None,
            "attachment_mime_type": None,
            "attachment_size_bytes": None,
        }
    suffix = _attachment_suffix(file.filename)
    if suffix not in ALLOWED_ATTACHMENT_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported grievance attachment type")

    content = await file.read()
    size = len(content)
    if size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded attachment is empty")
    if size > MAX_ATTACHMENT_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attachment exceeds 10MB limit")

    await run_in_threadpool(GRIEVANCE_UPLOAD_DIR.mkdir, parents=True, exist_ok=True)
    stored_name = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}{suffix}"
    saved_path = GRIEVANCE_UPLOAD_DIR / stored_name
    await run_in_threadpool(saved_path.write_bytes, content)
    return {
        "attachment_original_filename": file.filename or "attachment",
        "attachment_stored_filename": stored_name,
        "attachment_mime_type": file.content_type,
        "attachment_size_bytes": size,
    }


@router.get("/mine", response_model=list[GrievanceOut])
async def list_my_grievances(
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(["student"])),
) -> list[GrievanceOut]:
    query = {"student_user_id": str(current_user["_id"])}
    if status_filter:
        query["status"] = status_filter
    rows = await db.grievances.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    return [_grievance_payload(row, include_internal=False) for row in rows]


@router.get("/inbox", response_model=list[GrievanceOut])
async def list_grievance_inbox(
    view: GrievanceInboxView | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    only_overdue: bool = Query(default=False),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> list[GrievanceOut]:
    resolved_view = view
    if not resolved_view:
        if current_user.get("role") == "teacher":
            resolved_view = "coordinator" if "class_coordinator" in set(current_user.get("extended_roles") or []) else "assigned"
        else:
            admin_type = str(current_user.get("admin_type") or "").strip().lower()
            resolved_view = admin_type if admin_type in {"hod", "dean"} else "fallback" if admin_type in {"academic_admin", "super_admin"} else "assigned"

    query = await grievance_inbox_query(current_user, view=resolved_view, database=db)
    if status_filter:
        query["status"] = status_filter
    if only_overdue:
        query["stage_due_at"] = {"$lte": utc_now()}
        query["status"] = {"$in": ["open", "in_progress", "reopened"]}
    if q:
        text_query = {
            "$or": [
                {"title": {"$regex": q, "$options": "i"}},
                {"description": {"$regex": q, "$options": "i"}},
                {"category": {"$regex": q, "$options": "i"}},
                {"student_name": {"$regex": q, "$options": "i"}},
            ]
        }
        query = {"$and": [query, text_query]} if query else text_query

    rows = await db.grievances.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(length=limit)
    visible_rows: list[GrievanceOut] = []
    for row in rows:
        if not await can_view_grievance(current_user, row, database=db):
            continue
        visible_rows.append(_grievance_payload(row, include_internal=True))
    return visible_rows


@router.get("/forward-targets", response_model=list[UserOut])
async def list_grievance_forward_targets(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> list[UserOut]:
    if current_user.get("role") == "teacher" and "class_coordinator" not in set(current_user.get("extended_roles") or []):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only class coordinators can forward grievances")

    query: dict[str, object] = {"is_active": True, "role": {"$in": ["teacher", "admin"]}}
    if q:
        query["$or"] = [
            {"full_name": {"$regex": q, "$options": "i"}},
            {"email": {"$regex": q, "$options": "i"}},
        ]
    rows = await db.users.find(query).sort("full_name", 1).limit(200).to_list(length=200)
    visible_rows = [row for row in rows if str(row.get("_id")) != str(current_user.get("_id"))]
    return [UserOut(**user_public(row)) for row in visible_rows]


@router.get("/{grievance_id}", response_model=GrievanceOut)
async def get_grievance(
    grievance_id: str,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> GrievanceOut:
    grievance = await _visible_grievance_or_404(grievance_id, current_user)
    include_internal = current_user.get("role") in {"admin", "teacher"}
    return _grievance_payload(grievance, include_internal=include_internal)


@router.get("/{grievance_id}/attachment")
async def get_grievance_attachment(
    grievance_id: str,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> FileResponse:
    grievance = await _visible_grievance_or_404(grievance_id, current_user)
    stored_name = grievance.get("attachment_stored_filename")
    if not stored_name:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment not found")
    file_path = GRIEVANCE_UPLOAD_DIR / stored_name
    if not await run_in_threadpool(file_path.exists):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attachment file missing")
    return FileResponse(
        file_path,
        media_type=grievance.get("attachment_mime_type") or "application/octet-stream",
        filename=grievance.get("attachment_original_filename") or file_path.name,
        headers={"Cache-Control": "private, max-age=300, stale-while-revalidate=86400"},
    )


@router.post("/", response_model=GrievanceOut, status_code=status.HTTP_201_CREATED)
async def create_grievance(
    category: str = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    attachment: UploadFile | None = File(default=None),
    current_user=Depends(require_roles(["student"])),
) -> GrievanceOut:
    student, section, department = await _student_context_for_create(current_user)
    attachment_payload = await _store_attachment(attachment)
    now = utc_now()

    base_document = {
        "category": category.strip(),
        "title": title.strip(),
        "description": description.strip(),
        "student_user_id": str(current_user["_id"]),
        "student_id": str(student.get("_id")) if student.get("_id") else None,
        "student_name": current_user.get("full_name"),
        "student_email": current_user.get("email"),
        "section_id": str(section.get("_id")) if section.get("_id") else None,
        "section_name": section.get("name"),
        "department_id": str(section.get("department_id")) if section.get("department_id") else None,
        "department_name": department.get("department_name") if department else None,
        "current_stage": "coordinator",
        "status": "open",
        "stage_due_at": grievance_due_at(from_dt=now),
        "resolved_at": None,
        "resolved_by_user_id": None,
        "resolved_by_name": None,
        "resolved_by_email": None,
        "assigned_resolver_user_id": None,
        "assigned_resolver_name": None,
        "assigned_resolver_email": None,
        "forwarded_by_user_id": None,
        "forwarded_by_name": None,
        "forwarded_by_email": None,
        "forwarded_at": None,
        "created_at": now,
        "schema_version": GRIEVANCE_SCHEMA_VERSION,
        "timeline": [
            build_timeline_entry(
                kind="submitted",
                stage="coordinator",
                message="Grievance submitted by student.",
                actor=current_user,
                created_at=now,
            )
        ],
        **attachment_payload,
    }

    stage, recipients, skipped = await first_available_stage(base_document, database=db)
    if stage and recipients:
        base_document["current_stage"] = stage
        for skipped_stage in skipped:
            base_document["timeline"].append(
                build_timeline_entry(
                    kind="escalated",
                    stage=skipped_stage,
                    message=f"No active {skipped_stage.title()} recipient was available. Skipping this stage.",
                    metadata={"skipped": True},
                    created_at=now,
                )
            )
        if stage != "coordinator":
            base_document["timeline"].append(
                build_timeline_entry(
                    kind="escalated",
                    stage=stage,
                    message=f"Grievance was routed directly to {stage.title()} because an earlier owner was unavailable.",
                    created_at=now,
                )
            )
    else:
        base_document["status"] = "routing_failed"
        base_document["stage_due_at"] = None
        base_document["timeline"].append(
            build_timeline_entry(
                kind="routing_failed",
                stage="coordinator",
                message="No valid coordinator, HOD, or Dean recipient was available. Sent to academic admin fallback queue.",
                created_at=now,
            )
        )
        recipients = await fallback_recipients(database=db)

    created = await persist_grievance(base_document, database=db)
    if created.get("status") == "routing_failed":
        await notify_users_about_grievance(
            created,
            user_ids=[str(item.get("_id")) for item in recipients if item.get("_id")],
            title="Grievance routing failed",
            message=f"{created.get('title') or 'A grievance'} needs manual reassignment.",
            created_by=str(current_user["_id"]),
        )
    else:
        await notify_stage_recipients(created, created.get("current_stage"), recipients, created_by=str(current_user["_id"]))

    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="create_grievance",
        entity_type="grievance",
        entity_id=str(created.get("_id")),
        detail=f"Created grievance {created.get('title')}",
    )
    return _grievance_payload(created, include_internal=False)


@router.post("/{grievance_id}/comments", response_model=GrievanceOut)
async def add_grievance_comment(
    grievance_id: str,
    payload: GrievanceCommentCreate,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> GrievanceOut:
    grievance = await _visible_grievance_or_404(grievance_id, current_user)
    if not await can_add_public_comment(current_user, grievance, database=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to comment on this grievance")

    entry = build_timeline_entry(
        kind="public_comment",
        stage=str(grievance.get("current_stage") or "coordinator"),
        message=payload.message,
        actor=current_user,
    )
    updated = await append_timeline_entry(grievance_id, entry, database=db)

    target_user_ids: set[str] = set()
    if current_user.get("role") == "student":
        recipients = await stage_recipients(updated, str(updated.get("current_stage") or "coordinator"), database=db)
        target_user_ids.update(str(item.get("_id")) for item in recipients if item.get("_id"))
        if updated.get("assigned_resolver_user_id"):
            target_user_ids.add(str(updated.get("assigned_resolver_user_id")))
    else:
        target_user_ids.add(str(updated.get("student_user_id")))
        if updated.get("assigned_resolver_user_id") and updated.get("assigned_resolver_user_id") != str(current_user.get("_id")):
            target_user_ids.add(str(updated.get("assigned_resolver_user_id")))
        if updated.get("assigned_resolver_user_id") == str(current_user.get("_id")):
            recipients = await stage_recipients(updated, str(updated.get("current_stage") or "coordinator"), database=db)
            target_user_ids.update(str(item.get("_id")) for item in recipients if item.get("_id"))

    await notify_users_about_grievance(
        updated,
        user_ids=sorted(target_user_ids),
        title="Grievance updated",
        message=f"{updated.get('title') or 'A grievance'} has a new public comment.",
        created_by=str(current_user.get("_id")),
    )
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="comment_grievance",
        entity_type="grievance",
        entity_id=grievance_id,
        detail="Added public grievance comment",
    )
    include_internal = current_user.get("role") in {"admin", "teacher"}
    return _grievance_payload(updated, include_internal=include_internal)


@router.post("/{grievance_id}/internal-notes", response_model=GrievanceOut)
async def add_grievance_internal_note(
    grievance_id: str,
    payload: GrievanceInternalNoteCreate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> GrievanceOut:
    grievance = await _visible_grievance_or_404(grievance_id, current_user)
    if not await can_add_internal_note(current_user, grievance, database=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to add internal notes")

    entry = build_timeline_entry(
        kind="internal_note",
        visibility="internal",
        stage=str(grievance.get("current_stage") or "coordinator"),
        message=payload.message,
        actor=current_user,
    )
    updated = await append_timeline_entry(grievance_id, entry, database=db)
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="internal_note_grievance",
        entity_type="grievance",
        entity_id=grievance_id,
        detail="Added internal grievance note",
    )
    return _grievance_payload(updated, include_internal=True)


@router.post("/{grievance_id}/forward", response_model=GrievanceOut)
async def forward_grievance(
    grievance_id: str,
    payload: GrievanceForwardCreate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> GrievanceOut:
    grievance = await _visible_grievance_or_404(grievance_id, current_user)
    if not await can_forward_grievance(current_user, grievance, database=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to forward this grievance")

    target_user = await db.users.find_one({"_id": parse_object_id(payload.target_user_id), "is_active": True})
    if not target_user or target_user.get("role") not in {"admin", "teacher"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Forward target must be an active teacher or admin")

    entry = build_timeline_entry(
        kind="forwarded",
        stage=str(grievance.get("current_stage") or "coordinator"),
        message=payload.note or f"Forwarded to {target_user.get('full_name') or 'resolver'} for faster resolution.",
        actor=current_user,
        forwarded_to=target_user,
    )
    updated = await append_timeline_entry(
        grievance_id,
        entry,
        set_fields={
            "assigned_resolver_user_id": str(target_user["_id"]),
            "assigned_resolver_name": target_user.get("full_name"),
            "assigned_resolver_email": target_user.get("email"),
            "forwarded_by_user_id": str(current_user["_id"]),
            "forwarded_by_name": current_user.get("full_name"),
            "forwarded_by_email": current_user.get("email"),
            "forwarded_at": utc_now(),
        },
        database=db,
    )
    await notify_users_about_grievance(
        updated,
        user_ids=[str(target_user["_id"])],
        title="Grievance assigned to you",
        message=f"{updated.get('title') or 'A grievance'} was forwarded to you for faster resolution.",
        created_by=str(current_user["_id"]),
    )
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="forward_grievance",
        entity_type="grievance",
        entity_id=grievance_id,
        detail=f"Forwarded grievance to {target_user.get('email')}",
    )
    return _grievance_payload(updated, include_internal=True)


@router.patch("/{grievance_id}/status", response_model=GrievanceOut)
async def update_grievance_status(
    grievance_id: str,
    payload: GrievanceStatusUpdate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> GrievanceOut:
    grievance = await _visible_grievance_or_404(grievance_id, current_user)
    if not await can_update_status(current_user, grievance, database=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this grievance")
    if payload.status == "resolved" and not await can_resolve_grievance(current_user, grievance, database=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the current stage owner can resolve this grievance")

    now = utc_now()
    if payload.status == "resolved":
        entry = build_timeline_entry(
            kind="resolved",
            stage=str(grievance.get("current_stage") or "coordinator"),
            message=payload.resolution_note or "Grievance resolved.",
            actor=current_user,
            created_at=now,
        )
        set_fields = {
            "status": "resolved",
            "resolved_at": now,
            "resolved_by_user_id": str(current_user["_id"]),
            "resolved_by_name": current_user.get("full_name"),
            "resolved_by_email": current_user.get("email"),
            "stage_due_at": None,
            "assigned_resolver_user_id": None,
            "assigned_resolver_name": None,
            "assigned_resolver_email": None,
        }
        updated = await append_timeline_entry(grievance_id, entry, set_fields=set_fields, database=db)
        await notify_users_about_grievance(
            updated,
            user_ids=[str(updated.get("student_user_id"))],
            title="Grievance resolved",
            message=f"{updated.get('title') or 'Your grievance'} has been marked resolved.",
            created_by=str(current_user["_id"]),
        )
    else:
        entry = build_timeline_entry(
            kind="status_changed",
            stage=str(grievance.get("current_stage") or "coordinator"),
            message="Marked grievance as in progress.",
            actor=current_user,
            created_at=now,
        )
        updated = await append_timeline_entry(
            grievance_id,
            entry,
            set_fields={
                "status": "in_progress",
                "resolved_at": None,
                "resolved_by_user_id": None,
                "resolved_by_name": None,
                "resolved_by_email": None,
            },
            database=db,
        )

    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="update_grievance_status",
        entity_type="grievance",
        entity_id=grievance_id,
        detail=f"Updated grievance status to {payload.status}",
    )
    return _grievance_payload(updated, include_internal=True)


@router.post("/{grievance_id}/reopen", response_model=GrievanceOut)
async def reopen_grievance(
    grievance_id: str,
    payload: GrievanceReopenCreate,
    current_user=Depends(require_roles(["student"])),
) -> GrievanceOut:
    grievance = await _visible_grievance_or_404(grievance_id, current_user)
    if grievance.get("status") != "resolved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only resolved grievances can be reopened")
    if not await can_reopen_grievance(current_user, grievance, database=db):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to reopen this grievance")

    now = utc_now()
    recipients = await stage_recipients(grievance, str(grievance.get("current_stage") or "coordinator"), database=db)
    new_status = "reopened"
    timeline_message = payload.message or "Student reopened the grievance."
    notification_title = "Grievance reopened"
    notification_message = f"{grievance.get('title') or 'A grievance'} was reopened by the student."
    recipient_ids = [str(item.get("_id")) for item in recipients if item.get("_id")]

    if not recipient_ids:
        new_status = "routing_failed"
        fallback_users = await fallback_recipients(database=db)
        recipient_ids = [str(item.get("_id")) for item in fallback_users if item.get("_id")]
        timeline_message = "Student reopened the grievance, but no stage owner was available. Sent to academic admin fallback queue."
        notification_title = "Reopened grievance needs reassignment"
        notification_message = f"{grievance.get('title') or 'A grievance'} was reopened and needs manual reassignment."

    entry = build_timeline_entry(
        kind="reopened",
        stage=str(grievance.get("current_stage") or "coordinator"),
        message=timeline_message,
        actor=current_user,
        created_at=now,
    )
    updated = await append_timeline_entry(
        grievance_id,
        entry,
        set_fields={
            "status": new_status,
            "resolved_at": None,
            "resolved_by_user_id": None,
            "resolved_by_name": None,
            "resolved_by_email": None,
            "stage_due_at": grievance_due_at(from_dt=now) if new_status != "routing_failed" else None,
            "assigned_resolver_user_id": None,
            "assigned_resolver_name": None,
            "assigned_resolver_email": None,
            "forwarded_by_user_id": None,
            "forwarded_by_name": None,
            "forwarded_by_email": None,
            "forwarded_at": None,
        },
        database=db,
    )
    await notify_users_about_grievance(
        updated,
        user_ids=recipient_ids,
        title=notification_title,
        message=notification_message,
        created_by=str(current_user["_id"]),
    )
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="reopen_grievance",
        entity_type="grievance",
        entity_id=grievance_id,
        detail="Reopened grievance",
    )
    return _grievance_payload(updated, include_internal=False)
