from __future__ import annotations

from fastapi import HTTPException, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import CLASS_SCHEMA_VERSION, USER_SCHEMA_VERSION


def section_mapping_lock_state(section: dict | None) -> dict[str, object]:
    section = section or {}
    return {
        "mapping_locked": bool(section.get("mapping_locked")),
        "mapping_locked_by_user_id": section.get("mapping_locked_by_user_id"),
        "mapping_locked_by_name": section.get("mapping_locked_by_name"),
        "mapping_locked_by_email": section.get("mapping_locked_by_email"),
        "mapping_locked_at": section.get("mapping_locked_at"),
        "mapping_lock_reason": section.get("mapping_lock_reason"),
    }


def is_section_mapping_locked(section: dict | None) -> bool:
    return bool((section or {}).get("mapping_locked"))


def coordinator_scope_class_id(current_user: dict | None) -> str | None:
    if not current_user:
        return None
    role_scope = current_user.get("role_scope") or {}
    class_scope = role_scope.get("class_coordinator", {}) if isinstance(role_scope, dict) else {}
    scoped_class_id = str(class_scope.get("class_id") or "").strip()
    return scoped_class_id or None


def is_section_coordinator(current_user: dict | None, section: dict | None) -> bool:
    if not current_user or not section:
        return False
    if current_user.get("role") != "teacher":
        return False
    extensions = set(current_user.get("extended_roles") or [])
    if "class_coordinator" not in extensions:
        return False
    section_id = str(section.get("_id") or "")
    scoped_class_id = coordinator_scope_class_id(current_user)
    if scoped_class_id and scoped_class_id != section_id:
        return False
    return str(section.get("class_coordinator_user_id") or "") == str(current_user.get("_id") or "")


def can_lock_or_unlock_section(current_user: dict | None, section: dict | None) -> bool:
    if not current_user or not section:
        return False
    if current_user.get("role") == "admin":
        return True
    return is_section_coordinator(current_user, section)


async def get_section_or_404(section_id: str, *, active_only: bool = True) -> dict:
    query: dict[str, object] = {"_id": parse_object_id(section_id)}
    if active_only:
        query["is_active"] = True
    section = await db.classes.find_one(query)
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    return section


async def ensure_section_write_access(
    *,
    current_user: dict,
    section_id: str,
    not_found_detail: str = "Section not found",
    forbidden_detail: str = "Only class coordinator can manage this section",
) -> dict:
    try:
        section = await get_section_or_404(section_id)
    except HTTPException as exc:
        if exc.status_code == status.HTTP_404_NOT_FOUND and not_found_detail != "Section not found":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=not_found_detail) from exc
        raise

    if current_user.get("role") == "admin":
        return section
    if not is_section_coordinator(current_user, section):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=forbidden_detail)
    return section


def _section_name(section: dict | None) -> str:
    if not section:
        return "unknown section"
    return str(section.get("name") or section.get("_id") or "unknown section")


def _person_label(name: str | None, email: str | None) -> str:
    normalized_name = str(name or "").strip()
    normalized_email = str(email or "").strip()
    if normalized_name and normalized_email:
        return f"{normalized_name} ({normalized_email})"
    if normalized_name:
        return normalized_name
    if normalized_email:
        return normalized_email
    return "another user"


def build_class_coordinator_scope(section: dict | None) -> dict[str, object]:
    section = section or {}
    return {
        "faculty_id": section.get("faculty_id"),
        "department_id": section.get("department_id"),
        "program_id": section.get("program_id"),
        "specialization_id": section.get("specialization_id"),
        "batch_id": section.get("batch_id"),
        "semester_id": section.get("semester_id"),
        "class_id": str(section.get("_id")) if section.get("_id") is not None else None,
    }


async def validate_section_coordinator_user(coordinator_user_id: str | None) -> dict | None:
    normalized_user_id = str(coordinator_user_id or "").strip()
    if not normalized_user_id:
        return None
    user = await db.users.find_one({"_id": parse_object_id(normalized_user_id), "is_active": True})
    if not user or user.get("role") != "teacher":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="class_coordinator_user_id must reference an active teacher",
        )
    return user


async def _sync_teacher_class_coordinator_state(*, teacher_user_id: str, preferred_section: dict | None = None) -> dict | None:
    normalized_user_id = str(teacher_user_id or "").strip()
    if not normalized_user_id:
        return None
    user = await db.users.find_one({"_id": parse_object_id(normalized_user_id)})
    if not user:
        return None

    selected_section = None
    if preferred_section and str(preferred_section.get("class_coordinator_user_id") or "") == normalized_user_id:
        selected_section = preferred_section
    if selected_section is None:
        selected_section = await db.classes.find_one({"class_coordinator_user_id": normalized_user_id, "is_active": True})

    extended_roles = [role for role in list(user.get("extended_roles") or []) if role != "class_coordinator"]
    role_scope = dict(user.get("role_scope") or {})
    role_scope.pop("class_coordinator", None)

    if user.get("role") == "teacher" and selected_section:
        extended_roles.append("class_coordinator")
        role_scope["class_coordinator"] = build_class_coordinator_scope(selected_section)

    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "extended_roles": extended_roles,
                "role_scope": role_scope,
                "schema_version": USER_SCHEMA_VERSION,
            }
        },
    )
    return await db.users.find_one({"_id": user["_id"]})


async def sync_section_coordinator_assignment(
    *,
    section_id: str,
    coordinator_user_id: str | None,
    previous_coordinator_user_id: str | None = None,
) -> tuple[dict, dict | None]:
    section = await db.classes.find_one({"_id": parse_object_id(section_id)})
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")

    teacher = await validate_section_coordinator_user(coordinator_user_id)
    normalized_user_id = str(teacher.get("_id")) if teacher else None
    previous_user_id = str(previous_coordinator_user_id or section.get("class_coordinator_user_id") or "").strip() or None
    cleared_user_ids: set[str] = set()

    if normalized_user_id:
        previous_sections = await db.classes.find(
            {
                "class_coordinator_user_id": normalized_user_id,
                "_id": {"$ne": section["_id"]},
            }
        ).to_list(length=100)
        if previous_sections:
            await db.classes.update_many(
                {
                    "class_coordinator_user_id": normalized_user_id,
                    "_id": {"$ne": section["_id"]},
                },
                {"$set": {"class_coordinator_user_id": None, "schema_version": CLASS_SCHEMA_VERSION}},
            )
            cleared_user_ids.add(normalized_user_id)

    if str(section.get("class_coordinator_user_id") or "") != str(normalized_user_id or ""):
        await db.classes.update_one(
            {"_id": section["_id"]},
            {"$set": {"class_coordinator_user_id": normalized_user_id, "schema_version": CLASS_SCHEMA_VERSION}},
        )

    updated_section = await db.classes.find_one({"_id": section["_id"]})

    if previous_user_id and previous_user_id != normalized_user_id:
        await _sync_teacher_class_coordinator_state(teacher_user_id=previous_user_id)
    for cleared_user_id in cleared_user_ids:
        if cleared_user_id != normalized_user_id:
            await _sync_teacher_class_coordinator_state(teacher_user_id=cleared_user_id)

    updated_user = None
    if normalized_user_id:
        updated_user = await _sync_teacher_class_coordinator_state(
            teacher_user_id=normalized_user_id,
            preferred_section=updated_section,
        )

    return updated_section, updated_user


def build_mapping_conflict_messages(
    *,
    current_user: dict,
    target_section: dict,
    source_section: dict | None,
    allow_admin_override: bool,
) -> list[str]:
    messages: list[str] = []
    current_user_id = str(current_user.get("_id") or "")
    target_section_id = str(target_section.get("_id") or "")
    source_section_id = str(source_section.get("_id") or "") if source_section else ""
    same_section = bool(source_section_id and source_section_id == target_section_id)
    target_locked = is_section_mapping_locked(target_section)
    source_locked = is_section_mapping_locked(source_section) if source_section else False
    target_locked_by = str(target_section.get("mapping_locked_by_user_id") or "")
    source_locked_by = str(source_section.get("mapping_locked_by_user_id") or "") if source_section else ""

    if current_user.get("role") == "admin":
        if target_locked and target_locked_by and target_locked_by != current_user_id and not allow_admin_override:
            messages.append(
                f'Target section "{_section_name(target_section)}" is locked by '
                f'{_person_label(target_section.get("mapping_locked_by_name"), target_section.get("mapping_locked_by_email"))}. '
                "Enable admin override to continue."
            )
        if source_locked and not same_section and source_locked_by and source_locked_by != current_user_id and not allow_admin_override:
            messages.append(
                f'Student belongs to locked source section "{_section_name(source_section)}" locked by '
                f'{_person_label(source_section.get("mapping_locked_by_name"), source_section.get("mapping_locked_by_email"))}. '
                "Enable admin override to remap."
            )
        return messages

    if current_user.get("role") != "teacher":
        messages.append("Only admin or class coordinator can map students.")
        return messages

    if not is_section_coordinator(current_user, target_section):
        messages.append(f'You can only map students into your own section "{_section_name(target_section)}".')
    if target_locked and target_locked_by and target_locked_by != current_user_id:
        messages.append(
            f'Target section "{_section_name(target_section)}" is locked by '
            f'{_person_label(target_section.get("mapping_locked_by_name"), target_section.get("mapping_locked_by_email"))}.'
        )
    if source_section and not same_section:
        messages.append(
            f'Student is already mapped to source section "{_section_name(source_section)}". Teacher remap is blocked.'
        )
    if source_locked and not same_section:
        messages.append(
            f'Student belongs to locked source section "{_section_name(source_section)}" locked by '
            f'{_person_label(source_section.get("mapping_locked_by_name"), source_section.get("mapping_locked_by_email"))} '
            "and cannot be remapped."
        )
    return messages
