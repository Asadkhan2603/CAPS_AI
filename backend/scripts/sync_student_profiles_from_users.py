from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import Any

from bson import ObjectId

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import db
from app.core.schema_versions import ENROLLMENT_SCHEMA_VERSION, STUDENT_SCHEMA_VERSION


def normalize_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def normalize_email(value: Any) -> str | None:
    text = normalize_text(value)
    return text.lower() if text else None


async def resolve_section_id(profile: dict[str, Any]) -> str | None:
    raw_class_id = normalize_text(profile.get("class_id"))
    if raw_class_id and ObjectId.is_valid(raw_class_id):
      section = await db.classes.find_one({"_id": ObjectId(raw_class_id)})
      if section:
          return raw_class_id

    class_name = normalize_text(profile.get("class_name"))
    if class_name:
        section = await db.classes.find_one({"name": class_name})
        if section:
            return str(section["_id"])

    return None


def build_generated_roll_number(user: dict[str, Any], used_roll_numbers: set[str]) -> str:
    base = f"USR-{str(user['_id'])[-8:]}".upper()
    candidate = base
    suffix = 1
    while candidate in used_roll_numbers:
        candidate = f"{base[:26]}-{suffix}"
        suffix += 1
    return candidate


async def ensure_enrollment(student: dict[str, Any], *, section_id: str) -> None:
    existing = await db.enrollments.find_one({"class_id": section_id, "student_id": str(student["_id"])})
    if existing:
        return
    await db.enrollments.insert_one(
        {
            "class_id": section_id,
            "student_id": str(student["_id"]),
            "student_roll_number": student.get("roll_number"),
            "assigned_by_user_id": str(student.get("user_id") or ""),
            "created_at": datetime.now(timezone.utc),
            "schema_version": ENROLLMENT_SCHEMA_VERSION,
        }
    )


async def sync_student_profiles(*, apply_changes: bool) -> dict[str, int]:
    summary = {
        "student_users": 0,
        "created_profiles": 0,
        "linked_existing_profiles": 0,
        "created_enrollments": 0,
        "generated_roll_numbers": 0,
        "unassigned_profiles": 0,
        "already_synced": 0,
    }

    student_users = await db.users.find({"role": "student"}).to_list(length=None)
    summary["student_users"] = len(student_users)

    used_roll_numbers = {
        normalize_text(value).upper()
        for value in await db.students.distinct("roll_number")
        if normalize_text(value)
    }

    for user in student_users:
        email = normalize_email(user.get("email")) or normalize_email((user.get("profile") or {}).get("official_email"))
        profile = user.get("profile") or {}
        roll_number = normalize_text(profile.get("roll_number"))
        if roll_number:
            roll_number = roll_number.upper()
        else:
            roll_number = build_generated_roll_number(user, used_roll_numbers)
            summary["generated_roll_numbers"] += 1
        used_roll_numbers.add(roll_number)

        existing = await db.students.find_one({"user_id": str(user["_id"])})
        if existing:
            summary["already_synced"] += 1
            continue

        existing = await db.students.find_one({"email": email, "is_active": True}) if email else None
        if not existing:
            existing = await db.students.find_one({"roll_number": roll_number, "is_active": True})

        section_id = await resolve_section_id(profile)
        if not section_id:
            summary["unassigned_profiles"] += 1

        if existing:
            summary["linked_existing_profiles"] += 1
            if apply_changes:
                update_fields = {
                    "user_id": str(user["_id"]),
                    "schema_version": STUDENT_SCHEMA_VERSION,
                }
                if not existing.get("class_id") and section_id:
                    update_fields["class_id"] = section_id
                await db.students.update_one({"_id": existing["_id"]}, {"$set": update_fields})
                refreshed = await db.students.find_one({"_id": existing["_id"]})
                if section_id:
                    before = await db.enrollments.count_documents({"class_id": section_id, "student_id": str(refreshed["_id"])})
                    await ensure_enrollment(refreshed, section_id=section_id)
                    after = await db.enrollments.count_documents({"class_id": section_id, "student_id": str(refreshed["_id"])})
                    if after > before:
                        summary["created_enrollments"] += 1
            continue

        document = {
            "user_id": str(user["_id"]),
            "full_name": normalize_text(user.get("full_name")) or "Student",
            "roll_number": roll_number,
            "email": email,
            "enrollment_number": normalize_text(profile.get("enrollment_number")),
            "phone": normalize_text(profile.get("official_phone")) or normalize_text(profile.get("phone")),
            "class_id": section_id,
            "group_id": None,
            "is_active": bool(user.get("is_active", True)),
            "created_at": user.get("created_at") or datetime.now(timezone.utc),
            "schema_version": STUDENT_SCHEMA_VERSION,
        }

        if apply_changes:
            result = await db.students.insert_one(document)
            created = await db.students.find_one({"_id": result.inserted_id})
            summary["created_profiles"] += 1
            if section_id:
                before = await db.enrollments.count_documents({"class_id": section_id, "student_id": str(created["_id"])})
                await ensure_enrollment(created, section_id=section_id)
                after = await db.enrollments.count_documents({"class_id": section_id, "student_id": str(created["_id"])})
                if after > before:
                    summary["created_enrollments"] += 1
        else:
            summary["created_profiles"] += 1
            if section_id:
                summary["created_enrollments"] += 1

    return summary


async def main() -> None:
    parser = argparse.ArgumentParser(description="Create missing student profiles from existing student user accounts.")
    parser.add_argument("--apply", action="store_true", help="Write changes to the database. Without this flag the script runs in dry-run mode.")
    args = parser.parse_args()

    summary = await sync_student_profiles(apply_changes=args.apply)
    mode = "APPLY" if args.apply else "DRY RUN"
    print(f"[{mode}] Student profile sync summary")
    for key, value in summary.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())
