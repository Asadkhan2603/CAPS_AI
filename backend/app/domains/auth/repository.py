from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from app.core.database import db as core_db
from app.core.redis_store import redis_store


class AuthRepository:
    def __init__(self, db_provider: Callable[[], Any] | None = None):
        self._db_provider = db_provider

    @property
    def _db(self):
        return self._db_provider() if self._db_provider else core_db

    async def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        return await self._db.users.find_one({"email": email})

    async def find_user_by_id(self, user_obj_id) -> dict[str, Any] | None:
        return await self._db.users.find_one({"_id": user_obj_id})

    async def ensure_email_unique_index(self) -> None:
        await self._db.users.create_index("email", unique=True)

    async def insert_user(self, document: dict[str, Any]):
        return await self._db.users.insert_one(document)

    async def update_user(self, user_obj_id, set_data: dict[str, Any]) -> None:
        await self._db.users.update_one({"_id": user_obj_id}, {"$set": set_data})

    async def is_any_admin_registered(self) -> bool:
        existing_admin = await self._db.users.find_one({"role": "admin"})
        return bool(existing_admin)

    async def find_blacklisted_jti(self, jti: str) -> dict[str, Any] | None:
        if await redis_store.is_blacklisted(jti):
            return {"jti": jti}
        collection = getattr(self._db, "token_blacklist", None)
        if collection is None:
            return None
        return await collection.find_one({"jti": jti})

    async def blacklist_jti(self, document: dict[str, Any]) -> None:
        collection = getattr(self._db, "token_blacklist", None)
        if not document.get("jti"):
            return
        await redis_store.mark_blacklisted(
            jti=document.get("jti"),
            expires_at=document.get("expires_at"),
        )
        if collection is None:
            return
        existing = await collection.find_one({"jti": document["jti"]})
        if not existing:
            await collection.insert_one(document)

    async def clear_login_failures(self, user_obj_id) -> None:
        await self.update_user(
            user_obj_id,
            {"failed_login_attempts": 0, "last_failed_login_at": None, "lockout_until": None},
        )

    async def record_login_failure(
        self,
        *,
        user: dict[str, Any],
        now: datetime,
        lockout_window_minutes: int,
        max_attempts: int,
        lockout_duration_minutes: int,
    ) -> None:
        window_start = now.timestamp() - (lockout_window_minutes * 60)
        last_failed = user.get("last_failed_login_at")
        if last_failed and getattr(last_failed, "tzinfo", None) is None:
            last_failed = last_failed.replace(tzinfo=now.tzinfo)
        failed_attempts = int(user.get("failed_login_attempts") or 0)
        if not last_failed or last_failed.timestamp() < window_start:
            failed_attempts = 0

        failed_attempts += 1
        update_data: dict[str, Any] = {
            "failed_login_attempts": failed_attempts,
            "last_failed_login_at": now,
        }
        if failed_attempts >= max_attempts:
            from datetime import timedelta

            update_data["lockout_until"] = now + timedelta(minutes=lockout_duration_minutes)
            update_data["failed_login_attempts"] = 0

        await self.update_user(user["_id"], update_data)

    async def create_session(self, document: dict[str, Any]) -> None:
        sessions = getattr(self._db, "user_sessions", None)
        if sessions is None:
            return
        await sessions.insert_one(document)

    async def find_active_session_by_refresh_jti(self, refresh_jti: str) -> dict[str, Any] | None:
        sessions = getattr(self._db, "user_sessions", None)
        if sessions is None:
            return None
        return await sessions.find_one({"refresh_jti": refresh_jti, "revoked_at": None})

    async def revoke_session_by_refresh_jti(self, refresh_jti: str, *, revoked_at: datetime) -> None:
        sessions = getattr(self._db, "user_sessions", None)
        if sessions is None:
            return
        await sessions.update_one(
            {"refresh_jti": refresh_jti, "revoked_at": None},
            {"$set": {"revoked_at": revoked_at}},
        )

    async def rotate_session_refresh_jti(
        self,
        old_refresh_jti: str,
        *,
        new_refresh_jti: str,
        rotated_at: datetime,
        ip_address: str | None = None,
        fingerprint: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        sessions = getattr(self._db, "user_sessions", None)
        if sessions is None:
            return
        await sessions.update_one(
            {"refresh_jti": old_refresh_jti, "revoked_at": None},
            {
                "$set": {
                    "refresh_jti": new_refresh_jti,
                    "rotated_at": rotated_at,
                    "last_seen_at": rotated_at,
                    "last_seen_ip": ip_address,
                    "fingerprint": fingerprint,
                    "user_agent": user_agent,
                }
            },
        )

    async def find_recent_sessions(self, user_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
        sessions = getattr(self._db, "user_sessions", None)
        if sessions is None:
            return []
        cursor = sessions.find({"user_id": user_id, "revoked_at": None})
        if hasattr(cursor, "sort"):
            cursor = cursor.sort("created_at", -1).limit(limit)
            return await cursor.to_list(length=limit)
        rows = await cursor.limit(limit).to_list(length=limit)
        rows.sort(key=lambda row: row.get("created_at"), reverse=True)
        return rows[:limit]
