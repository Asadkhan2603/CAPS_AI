from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId

from app.core.database import db
from app.core.schema_versions import STUDENT_SCHEMA_VERSION
from app.services.public_ids import persist_public_id, persist_public_id_update


def _normalize_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_email(value: Any) -> str | None:
    text = _normalize_text(value)
    return text.lower() if text else None


def _normalize_roll_number(value: Any) -> str | None:
    text = _normalize_text(value)
    return text.upper() if text else None


async def _resolve_section_id(profile: dict[str, Any]) -> str | None:
    raw_class_id = _normalize_text(profile.get("class_id"))
    if raw_class_id and ObjectId.is_valid(raw_class_id):
        section = await db.classes.find_one({"_id": ObjectId(raw_class_id)})
        if section:
            return raw_class_id

    class_name = _normalize_text(profile.get("class_name"))
    if class_name:
        section = await db.classes.find_one({"name": class_name})
        if section:
            return str(section["_id"])

    return None


async def _used_roll_numbers() -> set[str]:
    return {
        value.upper()
        for value in await db.students.distinct("roll_number")
        if _normalize_text(value)
    }


def _generated_roll_number_for_user(user_id: str, used_roll_numbers: set[str]) -> str:
    base = f"USR-{user_id[-8:]}".upper()
    candidate = base
    suffix = 1
    while candidate in used_roll_numbers:
        candidate = f"{base[:26]}-{suffix}"
        suffix += 1
    return candidate


async def ensure_student_profile_for_user(user: dict[str, Any] | None) -> dict[str, Any] | None:
    if not user or user.get("role") != "student" or not user.get("_id"):
        return None

    user_id = str(user["_id"])
    profile = dict(user.get("profile") or {})
    email = _normalize_email(user.get("email")) or _normalize_email(profile.get("official_email"))
    full_name = _normalize_text(user.get("full_name")) or "Student"
    requested_roll_number = _normalize_roll_number(profile.get("roll_number"))

    existing = await db.students.find_one({"user_id": user_id})
    if not existing and email:
        existing = await db.students.find_one({"email": email, "is_active": True})
    if not existing and requested_roll_number:
        existing = await db.students.find_one({"roll_number": requested_roll_number, "is_active": True})

    section_id = await _resolve_section_id(profile)

    if existing:
        update_data: dict[str, Any] = {
            "user_id": user_id,
            "full_name": full_name,
            "email": email,
            "is_active": bool(user.get("is_active", True)),
            "schema_version": STUDENT_SCHEMA_VERSION,
        }
        if section_id and not existing.get("class_id"):
            update_data["class_id"] = section_id
        if not existing.get("roll_number"):
            used_roll_numbers = await _used_roll_numbers()
            update_data["roll_number"] = requested_roll_number or _generated_roll_number_for_user(user_id, used_roll_numbers)
        persist_public_id_update(existing, update_data, kind="student")
        await db.students.update_one({"_id": existing["_id"]}, {"$set": update_data})
        return await db.students.find_one({"_id": existing["_id"]})

    used_roll_numbers = await _used_roll_numbers()
    roll_number = requested_roll_number
    if not roll_number or roll_number in used_roll_numbers:
        roll_number = _generated_roll_number_for_user(user_id, used_roll_numbers)

    document = {
        "user_id": user_id,
        "full_name": full_name,
        "roll_number": roll_number,
        "email": email,
        "class_id": section_id,
        "group_id": None,
        "is_active": bool(user.get("is_active", True)),
        "created_at": user.get("created_at") or datetime.now(timezone.utc),
        "schema_version": STUDENT_SCHEMA_VERSION,
    }
    persist_public_id(document, kind="student")
    result = await db.students.insert_one(document)
    return await db.students.find_one({"_id": result.inserted_id})
