from __future__ import annotations

import asyncio
import os
from datetime import datetime, timezone

from app.core.database import db
from app.core.schema_versions import USER_SCHEMA_VERSION
from app.core.security import get_password_hash
from app.services.student_profiles import ensure_student_profile_for_user


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _configured_users() -> list[dict[str, object]]:
    password = os.getenv("DEFAULT_USER_PASSWORD", "CapsAi@2026!")
    return [
        {
            "full_name": os.getenv("DEFAULT_SUPER_ADMIN_NAME", "Asad Khan"),
            "email": os.getenv("DEFAULT_SUPER_ADMIN_EMAIL", "asadkhan60708@gmail.com"),
            "role": "admin",
            "admin_type": "super_admin",
            "password": password,
        },
        {
            "full_name": os.getenv("DEFAULT_TEACHER_NAME", "Berlin Kind"),
            "email": os.getenv("DEFAULT_TEACHER_EMAIL", "berlinkind70809@gmail.com"),
            "role": "teacher",
            "admin_type": None,
            "password": password,
        },
        {
            "full_name": os.getenv("DEFAULT_STUDENT_NAME", "Medicaps Student"),
            "email": os.getenv("DEFAULT_STUDENT_EMAIL", "en22ce301013@medicaps.ac.in"),
            "role": "student",
            "admin_type": None,
            "password": password,
        },
    ]


async def _seed_user(spec: dict[str, object]) -> None:
    now = datetime.now(timezone.utc)
    email = str(spec["email"]).strip().lower()
    document = {
        "full_name": str(spec["full_name"]).strip(),
        "email": email,
        "hashed_password": get_password_hash(str(spec["password"])),
        "role": spec["role"],
        "admin_type": spec["admin_type"],
        "extended_roles": [],
        "is_active": True,
        "must_change_password": False,
        "failed_login_attempts": 0,
        "last_failed_login_at": None,
        "lockout_until": None,
        "created_at": now,
        "updated_at": now,
        "schema_version": USER_SCHEMA_VERSION,
    }
    existing = await db.users.find_one({"email": {"$regex": f"^{email}$", "$options": "i"}})
    if existing:
        await db.users.update_one({"_id": existing["_id"]}, {"$set": document})
        user = await db.users.find_one({"_id": existing["_id"]})
        action = "updated"
    else:
        result = await db.users.insert_one(document)
        user = await db.users.find_one({"_id": result.inserted_id})
        action = "created"

    if spec["role"] == "student":
        await ensure_student_profile_for_user(user)

    print(f"{action}:{email}:{spec['role']}")


async def main() -> None:
    if not _as_bool(os.getenv("SEED_DEFAULT_USERS"), default=False):
        print("seed_default_users: skipped")
        return

    await db.users.create_index("email", unique=True)
    for user in _configured_users():
        await _seed_user(user)


if __name__ == "__main__":
    asyncio.run(main())
