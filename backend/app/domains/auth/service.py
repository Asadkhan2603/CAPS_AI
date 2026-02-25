from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from ipaddress import ip_address as parse_ip
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings
from app.core.mongo import parse_object_id
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    get_password_hash,
    verify_password,
)
from app.models.users import user_public
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.services.audit import log_audit_event

from .repository import AuthRepository


class AuthService:
    def __init__(self, repository: AuthRepository | None = None):
        self.repository = repository or AuthRepository()

    @staticmethod
    def _utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _normalize_utc(value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)

    @staticmethod
    def _normalize_ip(value: str | None) -> str | None:
        if not value:
            return None
        return value.split(",")[0].strip()

    @staticmethod
    def _fingerprint(raw: str | None, *, user_agent: str | None, ip_address: str | None) -> str:
        seed = raw or f"{user_agent or ''}|{ip_address or ''}"
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_different_ip_network(a: str | None, b: str | None) -> bool:
        if not a or not b:
            return False
        try:
            ipa = parse_ip(a)
            ipb = parse_ip(b)
            if ipa.version != ipb.version:
                return True
            if ipa.version == 4:
                return str(ipa).rsplit(".", 1)[0] != str(ipb).rsplit(".", 1)[0]
            return str(ipa)[:19] != str(ipb)[:19]
        except Exception:
            return a != b

    async def _detect_login_anomaly(
        self,
        *,
        user_id: str,
        ip_address: str | None,
        fingerprint: str,
    ) -> dict[str, bool]:
        sessions = await self.repository.find_recent_sessions(user_id, limit=8)
        if not sessions:
            return {"new_device": False, "new_network": False}
        latest = sessions[0]
        prior_fingerprints = {row.get("fingerprint") for row in sessions if row.get("fingerprint")}
        new_device = fingerprint not in prior_fingerprints
        new_network = self._is_different_ip_network(ip_address, latest.get("last_seen_ip"))
        return {"new_device": new_device, "new_network": new_network}

    async def register(self, payload: UserCreate) -> UserOut:
        email = payload.email.lower().strip()
        extended_roles = payload.extended_roles or []
        if payload.role != "teacher" and extended_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Extended roles are only allowed for teacher accounts",
            )

        has_admin = await self.repository.is_any_admin_registered()
        if has_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Self-registration is closed. Contact super admin.",
            )

        if payload.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="First account must be admin.",
            )
        admin_type = payload.admin_type or "super_admin"

        existing_user = await self.repository.find_user_by_email(email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered",
            )

        await self.repository.ensure_email_unique_index()
        document = {
            "full_name": payload.full_name.strip(),
            "email": email,
            "hashed_password": get_password_hash(payload.password),
            "role": payload.role,
            "admin_type": admin_type,
            "extended_roles": extended_roles,
            "is_active": True,
            "must_change_password": False,
            "created_at": self._utc_now(),
        }

        try:
            result = await self.repository.insert_user(document)
        except Exception as exc:
            if "duplicate key" in str(exc).lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email is already registered",
                ) from exc
            raise

        created_user = await self.repository.find_user_by_id(result.inserted_id)
        return UserOut(**user_public(created_user))

    async def login(
        self,
        payload: UserLogin,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
        device_fingerprint: str | None = None,
    ) -> Token:
        email = payload.email.lower().strip()
        user = await self.repository.find_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        now = self._utc_now()
        lockout_until = self._normalize_utc(user.get("lockout_until"))
        if lockout_until and now < lockout_until:
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"Account temporarily locked. Try again after {lockout_until.isoformat()}",
            )

        if not verify_password(payload.password, user["hashed_password"]):
            await self.repository.record_login_failure(
                user=user,
                now=now,
                lockout_window_minutes=settings.account_lockout_window_minutes,
                max_attempts=settings.account_lockout_max_attempts,
                lockout_duration_minutes=settings.account_lockout_duration_minutes,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive",
            )

        await self.repository.clear_login_failures(user["_id"])

        access_token = create_access_token(
            user_id=str(user["_id"]),
            email=user["email"],
            role=user["role"],
            admin_type=user.get("admin_type"),
            extended_roles=user.get("extended_roles", []),
        )
        refresh_token = create_refresh_token(
            user_id=str(user["_id"]),
            email=user["email"],
            role=user["role"],
            admin_type=user.get("admin_type"),
            extended_roles=user.get("extended_roles", []),
        )
        refresh_payload = decode_access_token(refresh_token, expected_type="refresh")
        normalized_ip = self._normalize_ip(ip_address)
        fingerprint = self._fingerprint(
            device_fingerprint,
            user_agent=user_agent,
            ip_address=normalized_ip,
        )
        anomaly = await self._detect_login_anomaly(
            user_id=str(user["_id"]),
            ip_address=normalized_ip,
            fingerprint=fingerprint,
        )
        await self.repository.create_session(
            {
                "user_id": str(user["_id"]),
                "refresh_jti": refresh_payload.get("jti"),
                "fingerprint": fingerprint,
                "ip_address": normalized_ip,
                "last_seen_ip": normalized_ip,
                "user_agent": user_agent,
                "created_at": now,
                "last_seen_at": now,
                "rotated_at": None,
                "revoked_at": None,
            }
        )
        if anomaly["new_device"] or anomaly["new_network"]:
            await log_audit_event(
                actor_user_id=str(user["_id"]),
                action="login_anomaly",
                action_type="login_anomaly",
                entity_type="auth",
                entity_id=str(user["_id"]),
                detail=f"New device={anomaly['new_device']} new_network={anomaly['new_network']}",
                ip_address=normalized_ip,
                user_agent=user_agent,
                severity="high",
            )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserOut(**user_public(user)),
        )

    async def refresh(
        self,
        refresh_token_value: str,
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
        device_fingerprint: str | None = None,
    ) -> Token:
        token_payload = decode_access_token(refresh_token_value, expected_type="refresh")
        if await self.repository.find_blacklisted_jti(token_payload.get("jti")):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked")
        session = await self.repository.find_active_session_by_refresh_jti(token_payload.get("jti"))
        if session is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session not found for refresh token")

        user_id = token_payload.get("sub")
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user or not user.get("is_active", True):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User unavailable for refresh")

        access_token = create_access_token(
            user_id=str(user["_id"]),
            email=user["email"],
            role=user["role"],
            admin_type=user.get("admin_type"),
            extended_roles=user.get("extended_roles", []),
        )
        next_refresh_token = create_refresh_token(
            user_id=str(user["_id"]),
            email=user["email"],
            role=user["role"],
            admin_type=user.get("admin_type"),
            extended_roles=user.get("extended_roles", []),
        )

        expires_at = (
            datetime.fromtimestamp(token_payload["exp"], tz=timezone.utc)
            if isinstance(token_payload.get("exp"), (int, float))
            else None
        )
        await self.repository.blacklist_jti(
            {
                "jti": token_payload.get("jti"),
                "token_type": "refresh",
                "user_id": str(user["_id"]),
                "blacklisted_at": self._utc_now(),
                "expires_at": self._normalize_utc(expires_at),
            }
        )
        new_refresh_payload = decode_access_token(next_refresh_token, expected_type="refresh")
        normalized_ip = self._normalize_ip(ip_address)
        await self.repository.rotate_session_refresh_jti(
            token_payload.get("jti"),
            new_refresh_jti=new_refresh_payload.get("jti"),
            rotated_at=self._utc_now(),
            ip_address=normalized_ip,
            fingerprint=self._fingerprint(
                device_fingerprint,
                user_agent=user_agent,
                ip_address=normalized_ip,
            ),
            user_agent=user_agent,
        )
        return Token(
            access_token=access_token,
            refresh_token=next_refresh_token,
            user=UserOut(**user_public(user)),
        )

    async def logout(
        self,
        *,
        current_user: dict[str, Any],
        access_token: str,
        refresh_token_value: str | None = None,
    ) -> dict[str, Any]:
        access_payload = decode_access_token(access_token, expected_type="access")
        access_exp = access_payload.get("exp")
        blacklist_docs = [
            {
                "jti": access_payload.get("jti"),
                "token_type": "access",
                "user_id": str(current_user["_id"]),
                "blacklisted_at": self._utc_now(),
                "expires_at": datetime.fromtimestamp(access_exp, tz=timezone.utc)
                if isinstance(access_exp, (int, float))
                else None,
            }
        ]

        if refresh_token_value:
            refresh_payload = decode_access_token(refresh_token_value, expected_type="refresh")
            refresh_exp = refresh_payload.get("exp")
            blacklist_docs.append(
                {
                    "jti": refresh_payload.get("jti"),
                    "token_type": "refresh",
                    "user_id": str(current_user["_id"]),
                    "blacklisted_at": self._utc_now(),
                    "expires_at": datetime.fromtimestamp(refresh_exp, tz=timezone.utc)
                    if isinstance(refresh_exp, (int, float))
                    else None,
                }
            )
            await self.repository.revoke_session_by_refresh_jti(
                refresh_payload.get("jti"),
                revoked_at=self._utc_now(),
            )

        for doc in blacklist_docs:
            await self.repository.blacklist_jti(doc)

        await log_audit_event(
            actor_user_id=str(current_user["_id"]),
            action="logout",
            action_type="logout",
            entity_type="auth",
            entity_id=str(current_user["_id"]),
            detail="User logout and token revocation",
            severity="low",
        )
        return {"success": True, "message": "Logged out"}
