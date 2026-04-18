from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Callable

from bson import ObjectId
from pymongo.errors import DuplicateKeyError

from app.core.database import db as core_db
from app.core.redis_store import redis_store
from app.core.schema_versions import USER_SCHEMA_VERSION, USER_SESSION_SCHEMA_VERSION


class AuthRepository:
    def __init__(self, db_provider: Callable[[], Any] | None = None):
        self._db_provider = db_provider

    @property
    def _db(self):
        return self._db_provider() if self._db_provider else core_db

    async def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        user = await self._db.users.find_one({"email": email})
        if user:
            return user
        escaped = re.escape(email)
        return await self._db.users.find_one({"email": {"$regex": f"^{escaped}$", "$options": "i"}})

    async def find_any_admin(self) -> dict[str, Any] | None:
        return await self._db.users.find_one({"role": "admin"})

    async def find_user_by_id(self, user_obj_id) -> dict[str, Any] | None:
        return await self._db.users.find_one({"_id": user_obj_id})

    async def ensure_email_unique_index(self) -> None:
        await self._db.users.create_index("email", unique=True)

    async def insert_user(self, document: dict[str, Any]):
        return await self._db.users.insert_one(
            {
                **document,
                "schema_version": USER_SCHEMA_VERSION,
            }
        )

    async def update_user(self, user_obj_id, set_data: dict[str, Any]) -> None:
        await self._db.users.update_one(
            {"_id": user_obj_id},
            {"$set": {**set_data, "schema_version": USER_SCHEMA_VERSION}},
        )

    async def delete_user(self, user_obj_id) -> None:
        await self._db.users.delete_one({"_id": user_obj_id})

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
            try:
                await collection.insert_one(document)
            except DuplicateKeyError:
                # Concurrent refresh/logout requests may blacklist the same JTI at the same time.
                return

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
        document = {
            **document,
            "schema_version": USER_SESSION_SCHEMA_VERSION,
        }
        await sessions.insert_one(document)

    async def find_active_session_by_refresh_jti(self, refresh_jti: str) -> dict[str, Any] | None:
        sessions = getattr(self._db, "user_sessions", None)
        if sessions is None:
            return None
        return await sessions.find_one({"refresh_jti": refresh_jti, "revoked_at": None})

    async def find_active_session_by_id(self, session_id: str) -> dict[str, Any] | None:
        sessions = getattr(self._db, "user_sessions", None)
        if sessions is None:
            return None
        try:
            session_obj_id = ObjectId(session_id)
        except Exception:
            return None
        return await sessions.find_one({"_id": session_obj_id, "revoked_at": None})

    async def revoke_session_by_refresh_jti(self, refresh_jti: str, *, revoked_at: datetime) -> None:
        sessions = getattr(self._db, "user_sessions", None)
        if sessions is None:
            return
        await sessions.update_one(
            {"refresh_jti": refresh_jti, "revoked_at": None},
            {"$set": {"revoked_at": revoked_at, "schema_version": USER_SESSION_SCHEMA_VERSION}},
        )

    async def revoke_session_by_id(self, session_id: str, *, revoked_at: datetime) -> bool:
        sessions = getattr(self._db, "user_sessions", None)
        if sessions is None:
            return False
        try:
            session_obj_id = ObjectId(session_id)
        except Exception:
            return False
        result = await sessions.update_one(
            {"_id": session_obj_id, "revoked_at": None},
            {"$set": {"revoked_at": revoked_at, "schema_version": USER_SESSION_SCHEMA_VERSION}},
        )
        return bool(getattr(result, "matched_count", 0))

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
                    "schema_version": USER_SESSION_SCHEMA_VERSION,
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

    # =====================
    # MFA Methods
    # =====================

    async def save_totp_secret(self, user_obj_id, secret: str, backup_codes: list[dict]) -> None:
        """Save TOTP secret and backup codes for a user."""
        now = datetime.now(datetime.now().astimezone().tzinfo)
        await self.update_user(
            user_obj_id,
            {
                "mfa_totp_secret": secret,
                "mfa_totp_enabled": False,  # Not confirmed yet
                "mfa_backup_codes": backup_codes,
                "mfa_backup_codes_generated_at": now,
                "updated_at": now,
            },
        )

    async def confirm_totp(self, user_obj_id) -> None:
        """Mark TOTP as confirmed/enabled."""
        now = datetime.now(datetime.now().astimezone().tzinfo)
        await self.update_user(
            user_obj_id,
            {
                "mfa_totp_enabled": True,
                "mfa_totp_confirmed_at": now,
                "updated_at": now,
            },
        )

    async def disable_totp(self, user_obj_id) -> None:
        """Disable TOTP for a user."""
        now = datetime.now(datetime.now().astimezone().tzinfo)
        await self.update_user(
            user_obj_id,
            {
                "mfa_totp_enabled": False,
                "mfa_totp_secret": None,
                "mfa_backup_codes": [],
                "updated_at": now,
            },
        )

    async def save_email_otp(self, user_obj_id, otp_hash: str, expires_at: datetime) -> None:
        """Save email OTP temporarily."""
        await self.update_user(
            user_obj_id,
            {
                "mfa_email_otp_hash": otp_hash,
                "mfa_email_otp_expires_at": expires_at,
                "mfa_email_attempts": 0,
                "updated_at": datetime.now(datetime.now().astimezone().tzinfo),
            },
        )

    async def save_sms_otp(self, user_obj_id, otp_hash: str, expires_at: datetime) -> None:
        """Save SMS OTP temporarily."""
        await self.update_user(
            user_obj_id,
            {
                "mfa_sms_otp_hash": otp_hash,
                "mfa_sms_otp_expires_at": expires_at,
                "mfa_sms_attempts": 0,
                "updated_at": datetime.now(datetime.now().astimezone().tzinfo),
            },
        )

    async def verify_mfa_status(self, user_id: str) -> dict[str, Any]:
        """Get MFA status for a user."""
        user = await self.find_user_by_id(user_id)
        if not user:
            return {}
        return {
            "totp_enabled": user.get("mfa_totp_enabled", False),
            "email_enabled": user.get("mfa_email_enabled", False),
            "sms_enabled": user.get("mfa_sms_enabled", False),
            "backup_codes_count": len(user.get("mfa_backup_codes", [])),
        }

    async def consume_backup_code(self, user_obj_id, code_hash: str) -> bool:
        """Consume a backup code and mark it as used."""
        user = await self.find_user_by_id(user_obj_id)
        if not user:
            return False

        backup_codes = user.get("mfa_backup_codes", [])
        for i, code in enumerate(backup_codes):
            if code.get("code_hash") == code_hash and not code.get("used"):
                backup_codes[i]["used"] = True
                backup_codes[i]["used_at"] = datetime.now(datetime.now().astimezone().tzinfo)
                await self.update_user(
                    user_obj_id,
                    {
                        "mfa_backup_codes": backup_codes,
                        "updated_at": datetime.now(datetime.now().astimezone().tzinfo),
                    },
                )
                return True
        return False

    async def increment_mfa_attempts(self, user_obj_id, mfa_type: str) -> int:
        """Increment MFA verification attempts."""
        user = await self.find_user_by_id(user_obj_id)
        if not user:
            return 0

        if mfa_type == "email":
            attempts = user.get("mfa_email_attempts", 0) + 1
            await self.update_user(
                user_obj_id,
                {"mfa_email_attempts": attempts, "updated_at": datetime.now(datetime.now().astimezone().tzinfo)},
            )
            return attempts
        elif mfa_type == "sms":
            attempts = user.get("mfa_sms_attempts", 0) + 1
            await self.update_user(
                user_obj_id,
                {"mfa_sms_attempts": attempts, "updated_at": datetime.now(datetime.now().astimezone().tzinfo)},
            )
            return attempts
        return 0

    async def clear_mfa_attempts(self, user_obj_id) -> None:
        """Clear MFA verification attempts."""
        now = datetime.now(datetime.now().astimezone().tzinfo)
        await self.update_user(
            user_obj_id,
            {
                "mfa_email_attempts": 0,
                "mfa_sms_attempts": 0,
                "mfa_email_otp_hash": None,
                "mfa_sms_otp_hash": None,
                "updated_at": now,
            },
        )
