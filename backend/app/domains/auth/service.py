from __future__ import annotations

from datetime import datetime, timezone, timedelta
import json
import hashlib
from ipaddress import ip_address as parse_ip
import secrets
import string
import re
from typing import Any
import io
import base64
from uuid import uuid4

import pyotp  # type: ignore[import-not-found]
import qrcode  # type: ignore[import-not-found]
from fastapi import HTTPException, status
from jose import jwt
try:
    from twilio.rest import Client as TwilioClient  # type: ignore[import-not-found]
except Exception:  # pragma: no cover - optional dependency at import-time
    TwilioClient = None

try:
    from webauthn import (  # type: ignore[import-not-found]
        base64url_to_bytes,
        generate_authentication_options,
        generate_registration_options,
        options_to_json,
        verify_authentication_response,
        verify_registration_response,
    )
    from webauthn.helpers.structs import (  # type: ignore[import-not-found]
        AuthenticatorAttachment,
        AuthenticatorSelectionCriteria,
        PublicKeyCredentialDescriptor,
        UserVerificationRequirement,
    )
    WEBAUTHN_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency at import-time
    WEBAUTHN_AVAILABLE = False

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
from app.schemas.auth import BootstrapStatus, DevBootstrapAdminRequest, Token, LoginAnomaly
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.services.rbac import serialize_admin_user
from app.services.audit import log_audit_event
from app.services.student_profiles import ensure_student_profile_for_user

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

    @staticmethod
    def _format_anomaly_message(anomaly: dict) -> str:
        """Format anomaly detection messages for user notification."""
        parts = []
        if anomaly.get("new_device"):
            parts.append("New device detected")
        if anomaly.get("new_network"):
            parts.append("New location detected")
        if not parts:
            return None
        return ". ".join(parts) + ". Please verify your account for security."

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

    @staticmethod
    def _generate_recovery_codes(count: int = 8, code_length: int = 12) -> list[str]:
        """Generate alphanumeric recovery codes for account recovery."""
        chars = string.ascii_letters + string.digits
        codes = []
        for _ in range(count):
            code = ''.join(secrets.choice(chars) for _ in range(code_length))
            codes.append(code)
        return codes

    @staticmethod
    def _hash_recovery_code(code: str) -> str:
        """Hash recovery code using SHA256 for secure storage."""
        return hashlib.sha256(code.encode()).hexdigest()

    async def generate_recovery_codes(self, user_id: str) -> dict[str, Any]:
        """Generate new recovery codes for user account recovery."""
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        codes = self._generate_recovery_codes()
        hashed_codes = [
            {
                "code_hash": self._hash_recovery_code(code),
                "used": False,
                "used_at": None,
            }
            for code in codes
        ]

        now = self._utc_now()
        await self.repository.update_user(
            user["_id"],
            {
                "recovery_codes": hashed_codes,
                "recovery_codes_generated_at": now,
                "updated_at": now,
            },
        )

        await log_audit_event(
            actor_user_id=user_id,
            action="recovery_codes_generated",
            action_type="security_config",
            entity_type="account",
            entity_id=user_id,
            detail="Recovery codes generated for account recovery",
            severity="high",
        )

        return {
            "codes": codes,
            "generated_at": now,
            "message": "Store these codes safely. Each code can be used once to recover your account.",
        }

    async def verify_recovery_code(self, user_id: str, recovery_code: str) -> bool:
        """Verify and consume a recovery code for account recovery."""
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        recovery_codes = user.get("recovery_codes", [])
        code_hash = self._hash_recovery_code(recovery_code)

        for i, stored_code in enumerate(recovery_codes):
            if stored_code.get("code_hash") == code_hash:
                if stored_code.get("used"):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Recovery code already used",
                    )

                now = self._utc_now()
                recovery_codes[i]["used"] = True
                recovery_codes[i]["used_at"] = now

                await self.repository.update_user(
                    user["_id"],
                    {
                        "recovery_codes": recovery_codes,
                        "updated_at": now,
                    },
                )

                await log_audit_event(
                    actor_user_id=user_id,
                    action="recovery_code_used",
                    action_type="account_recovery",
                    entity_type="account",
                    entity_id=user_id,
                    detail="Recovery code successfully used for account access",
                    severity="high",
                )

                return True

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid recovery code",
        )

    async def get_login_history(
        self,
        user_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """Get login history for account activity dashboard (Gap-012)."""
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        sessions = await self.repository.find_recent_sessions(user_id, limit=100)
        
        entries = []
        for session in sessions:
            entries.append({
                "timestamp": session.get("last_seen_at") or session.get("created_at"),
                "ip_address": session.get("ip_address"),
                "device_fingerprint": session.get("fingerprint")[:16] if session.get("fingerprint") else None,
                "user_agent": session.get("user_agent"),
                "browser": self._extract_browser(session.get("user_agent")),
                "os": self._extract_os(session.get("user_agent")),
                "device_type": "desktop" if "desktop" in (session.get("user_agent") or "").lower() else "mobile" if "mobile" in (session.get("user_agent") or "").lower() else "unknown",
                "location": None,  # Placeholder for IP geolocation
                "success": True,
                "anomaly": False,
                "locked_out": False,
            })

        skip = (page - 1) * page_size
        paginated = entries[skip : skip + page_size]

        return {
            "total_count": len(entries),
            "page": page,
            "page_size": page_size,
            "entries": paginated,
        }

    async def get_account_activity(
        self,
        user_id: str,
        *,
        current_device_fingerprint: str | None = None,
        current_user_agent: str | None = None,
        current_ip_address: str | None = None,
    ) -> dict[str, Any]:
        """Get account activity summary for dashboard (Gap-014)."""
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        now = self._utc_now()
        sessions = await self.repository.find_recent_sessions(user_id, limit=100)
        normalized_current_ip = self._normalize_ip(current_ip_address)
        current_fingerprint = self._fingerprint(
            current_device_fingerprint,
            user_agent=current_user_agent,
            ip_address=normalized_current_ip,
        ) if (current_device_fingerprint or current_user_agent or normalized_current_ip) else None
        
        # Count logins in different time windows
        import datetime as dt
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = today - dt.timedelta(days=7)

        normalized_created_at = [
            self._normalize_utc(s.get("created_at")) or now
            for s in sessions
        ]
        login_attempts_today = len([created_at for created_at in normalized_created_at if created_at >= today])
        login_attempts_week = len([created_at for created_at in normalized_created_at if created_at >= week_ago])
        
        # Build active sessions list
        active_sessions = []
        for session in sessions[:5]:  # Show last 5 sessions
            session_fingerprint = session.get("fingerprint")
            is_current = bool(current_fingerprint and session_fingerprint == current_fingerprint)
            active_sessions.append({
                "session_id": str(session.get("_id", "")),
                "session_label": str(session.get("_id", ""))[:16],
                "device_fingerprint": session_fingerprint[:16] if session_fingerprint else "unknown",
                "device_name": self._extract_browser(session.get("user_agent")) or "Unknown Device",
                "ip_address": session.get("ip_address") or "unknown",
                "browser": self._extract_browser(session.get("user_agent")),
                "os": self._extract_os(session.get("user_agent")),
                "created_at": session.get("created_at", now),
                "last_active_at": session.get("last_seen_at", now),
                "is_current": is_current,
            })

        # Get recent logins for display
        recent_logins = []
        for session in sessions[:10]:
            recent_logins.append({
                "timestamp": session.get("last_seen_at", session.get("created_at")),
                "ip_address": session.get("ip_address"),
                "device_fingerprint": session.get("fingerprint")[:16] if session.get("fingerprint") else None,
                "user_agent": session.get("user_agent"),
                "browser": self._extract_browser(session.get("user_agent")),
                "os": self._extract_os(session.get("user_agent")),
                "device_type": "desktop" if "desktop" in (session.get("user_agent") or "").lower() else "mobile",
                "location": None,
                "success": True,
                "anomaly": False,
                "locked_out": False,
            })

        return {
            "login_attempts_today": login_attempts_today,
            "login_attempts_week": login_attempts_week,
            "unusual_activity": False,
            "last_login": sessions[0].get("last_seen_at", now) if sessions else None,
            "total_sessions": len(sessions),
            "active_sessions": active_sessions,
            "recent_logins": recent_logins,
        }

    async def terminate_session(
        self,
        *,
        current_user: dict[str, Any],
        session_id: str,
        current_device_fingerprint: str | None = None,
        current_user_agent: str | None = None,
        current_ip_address: str | None = None,
    ) -> dict[str, Any]:
        """Terminate one active session owned by the authenticated user."""
        resolved_session_id = (session_id or "").strip()
        if not resolved_session_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Session ID is required")

        session = await self.repository.find_active_session_by_id(resolved_session_id)
        if not session:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        current_user_id = str(current_user["_id"])
        if session.get("user_id") != current_user_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to terminate this session")

        normalized_current_ip = self._normalize_ip(current_ip_address)
        if current_device_fingerprint or current_user_agent or normalized_current_ip:
            current_fingerprint = self._fingerprint(
                current_device_fingerprint,
                user_agent=current_user_agent,
                ip_address=normalized_current_ip,
            )
            if session.get("fingerprint") == current_fingerprint:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Use logout to terminate the current session")

        now = self._utc_now()
        revoked = await self.repository.revoke_session_by_id(resolved_session_id, revoked_at=now)
        if not revoked:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found")

        refresh_jti = session.get("refresh_jti")
        if refresh_jti:
            await self.repository.blacklist_jti(
                {
                    "jti": refresh_jti,
                    "token_type": "refresh",
                    "user_id": current_user_id,
                    "blacklisted_at": now,
                    "expires_at": None,
                }
            )

        await log_audit_event(
            actor_user_id=current_user_id,
            action="session_terminated",
            action_type="session_terminated",
            entity_type="auth",
            entity_id=resolved_session_id,
            detail="User terminated an active account session",
            severity="medium",
        )
        return {
            "success": True,
            "message": f"Session {resolved_session_id[:16]} has been terminated",
            "session_id": resolved_session_id,
        }

    @staticmethod
    def _extract_browser(user_agent: str | None) -> str | None:
        """Extract browser name from user agent string."""
        if not user_agent:
            return None
        ua = user_agent.lower()
        if "chrome" in ua:
            return "Chrome"
        elif "firefox" in ua:
            return "Firefox"
        elif "safari" in ua:
            return "Safari"
        elif "edge" in ua:
            return "Edge"
        elif "opera" in ua:
            return "Opera"
        return None

    @staticmethod
    def _extract_os(user_agent: str | None) -> str | None:
        """Extract operating system from user agent string."""
        if not user_agent:
            return None
        ua = user_agent.lower()
        if "windows" in ua:
            return "Windows"
        elif "mac" in ua or "darwin" in ua:
            return "macOS"
        elif "linux" in ua:
            return "Linux"
        elif "android" in ua:
            return "Android"
        elif "iphone" in ua or "ipad" in ua:
            return "iOS"
        return None

    async def _serialize_user_out(self, user: dict[str, Any]) -> UserOut:
        if user.get("role") == "admin":
            return UserOut(**(await serialize_admin_user(user, database=self.repository._db)))
        return UserOut(**user_public(user))

    async def register(self, payload: UserCreate) -> UserOut:
        email = payload.email.lower().strip()
        policy = settings.auth_registration_policy
        has_admin = await self.repository.is_any_admin_registered()
        if policy == "bootstrap_strict":
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
        elif policy == "single_admin_open":
            if has_admin and payload.role == "admin":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Self-registration is closed. Contact super admin.",
                )

        extended_roles = payload.extended_roles or []
        if payload.role != "teacher" and extended_roles:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Extended roles are only allowed for teacher accounts",
            )

        if payload.role == "admin":
            admin_type = payload.admin_type or "super_admin"
        else:
            if payload.admin_type is not None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="admin_type is allowed only for admin accounts",
                )
            admin_type = None

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
        try:
            await ensure_student_profile_for_user(created_user)
        except Exception:
            await self.repository.delete_user(result.inserted_id)
            raise
        return await self._serialize_user_out(created_user)

    async def get_bootstrap_status(self) -> BootstrapStatus:
        has_admin = await self.repository.is_any_admin_registered()
        policy = settings.auth_registration_policy
        can_self_register_admin = policy == "open" or not has_admin
        return BootstrapStatus(
            environment=settings.environment,
            auth_registration_policy=policy,
            has_admin=has_admin,
            can_self_register_admin=can_self_register_admin,
            local_auth_recovery_enabled=settings.environment == "development",
        )

    async def bootstrap_or_recover_admin(self, payload: DevBootstrapAdminRequest) -> UserOut:
        if settings.environment != "development":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Local auth recovery is unavailable outside development.",
            )

        email = payload.email.lower().strip()
        existing_user = await self.repository.find_user_by_email(email)
        now = self._utc_now()
        base_updates = {
            "full_name": payload.full_name.strip(),
            "email": email,
            "hashed_password": get_password_hash(payload.password),
            "role": "admin",
            "admin_type": "super_admin",
            "extended_roles": [],
            "role_scope": {},
            "is_active": True,
            "status": "active",
            "must_change_password": False,
            "failed_login_attempts": 0,
            "last_failed_login_at": None,
            "lockout_until": None,
            "updated_at": now,
        }

        if existing_user:
            await self.repository.update_user(existing_user["_id"], base_updates)
            updated_user = await self.repository.find_user_by_id(existing_user["_id"])
            return await self._serialize_user_out(updated_user)

        document = {
            **base_updates,
            "created_at": now,
        }
        result = await self.repository.insert_user(document)
        created_user = await self.repository.find_user_by_id(result.inserted_id)
        return await self._serialize_user_out(created_user)

    @staticmethod
    def _normalize_phone_number(phone_number: str) -> str:
        cleaned = re.sub(r"[^\d+]", "", (phone_number or "").strip())
        if cleaned.startswith("00"):
            cleaned = f"+{cleaned[2:]}"
        if not cleaned.startswith("+"):
            cleaned = f"+{cleaned}"
        digits = re.sub(r"\D", "", cleaned)
        if len(digits) < 10 or len(digits) > 15:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number must be a valid international number",
            )
        return f"+{digits}"

    @staticmethod
    def _mask_phone_number(phone_number: str | None) -> str | None:
        if not phone_number:
            return None
        digits = re.sub(r"\D", "", phone_number)
        if len(digits) <= 4:
            return "*" * len(digits)
        return f"+{'*' * (len(digits) - 4)}{digits[-4:]}"

    @staticmethod
    def _b64url_encode(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")

    @staticmethod
    def _b64url_decode(encoded: str) -> bytes:
        padded = encoded + ("=" * ((4 - len(encoded) % 4) % 4))
        return base64.urlsafe_b64decode(padded.encode("ascii"))

    @staticmethod
    def _extract_webauthn_origin(credential: dict[str, Any]) -> str | None:
        try:
            client_data_json = credential.get("response", {}).get("clientDataJSON")
            if not client_data_json:
                return None
            payload = json.loads(AuthService._b64url_decode(client_data_json).decode("utf-8"))
            origin = payload.get("origin")
            return origin.rstrip("/") if isinstance(origin, str) else None
        except Exception:
            return None

    @staticmethod
    def _is_twilio_configured() -> bool:
        has_sender = bool(settings.twilio_from_number or settings.twilio_messaging_service_sid)
        return bool(settings.twilio_account_sid and settings.twilio_auth_token and has_sender)

    @staticmethod
    def _webauthn_origins() -> list[str]:
        return [origin.rstrip("/") for origin in settings.webauthn_rp_origins if origin]

    def _ensure_webauthn_configured(self) -> None:
        if not WEBAUTHN_AVAILABLE:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="WebAuthn support is not available")
        if not settings.webauthn_rp_id or not self._webauthn_origins():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="WebAuthn relying-party configuration is incomplete",
            )

    @staticmethod
    def _resolve_enabled_mfa_methods(user: dict[str, Any]) -> list[str]:
        methods: list[str] = []
        if user.get("mfa_totp_enabled") and user.get("mfa_totp_secret"):
            methods.append("totp")
        if user.get("mfa_sms_enabled") and user.get("mfa_sms_phone_number") and user.get("mfa_sms_phone_verified_at"):
            methods.append("sms")
        if user.get("mfa_webauthn_enabled") and user.get("mfa_webauthn_credentials"):
            methods.append("webauthn")
        return methods

    @staticmethod
    def _resolve_primary_mfa_method(user: dict[str, Any], methods: list[str]) -> str | None:
        preferred = user.get("mfa_primary_method")
        if preferred in methods:
            return preferred
        return methods[0] if methods else None

    def _build_pending_mfa_token(self, user: dict[str, Any], methods: list[str], primary_method: str | None) -> tuple[str, str, datetime]:
        expires_at = self._utc_now() + timedelta(minutes=settings.mfa_pending_token_expire_minutes)
        jti = uuid4().hex
        payload = {
            "jti": jti,
            "token_type": "mfa_pending",
            "sub": str(user["_id"]),
            "email": user["email"],
            "role": user.get("role"),
            "admin_type": user.get("admin_type"),
            "extended_roles": user.get("extended_roles", []),
            "mfa_methods": methods,
            "mfa_primary_method": primary_method,
            "exp": expires_at,
        }
        token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
        return token, jti, expires_at

    async def _store_pending_mfa_state(
        self,
        user_obj_id,
        *,
        jti: str,
        expires_at: datetime,
        methods: list[str],
        primary_method: str | None,
    ) -> None:
        await self.repository.update_user(
            user_obj_id,
            {
                "mfa_pending_login": {
                    "jti": jti,
                    "expires_at": expires_at,
                    "methods": methods,
                    "primary_method": primary_method,
                    "created_at": self._utc_now(),
                },
                "updated_at": self._utc_now(),
            },
        )

    async def _clear_pending_mfa_state(self, user_obj_id) -> None:
        await self.repository.update_user(
            user_obj_id,
            {
                "mfa_pending_login": None,
                "mfa_sms_login_otp_hash": None,
                "mfa_sms_login_otp_expires_at": None,
                "mfa_sms_login_attempts": 0,
                "mfa_sms_login_pending_jti": None,
                "mfa_webauthn_auth_state": None,
                "updated_at": self._utc_now(),
            },
        )

    async def _load_pending_mfa_user(self, pending_mfa_token: str) -> tuple[dict[str, Any], dict[str, Any]]:
        payload = decode_access_token(pending_mfa_token, expected_type="mfa_pending")
        user_id = payload.get("sub")
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA session")
        pending_state = user.get("mfa_pending_login") or {}
        pending_jti = pending_state.get("jti")
        expires_at = self._normalize_utc(pending_state.get("expires_at"))
        now = self._utc_now()
        if not pending_jti or pending_jti != payload.get("jti"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA session is no longer valid")
        if not expires_at or now > expires_at:
            await self._clear_pending_mfa_state(user["_id"])
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA session has expired")
        pending_methods = pending_state.get("methods") or []
        token_methods = payload.get("mfa_methods") or []
        if pending_methods and sorted(pending_methods) != sorted(token_methods):
            await self._clear_pending_mfa_state(user["_id"])
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA session methods no longer match")
        pending_primary_method = pending_state.get("primary_method")
        token_primary_method = payload.get("mfa_primary_method")
        if pending_primary_method and token_primary_method and pending_primary_method != token_primary_method:
            await self._clear_pending_mfa_state(user["_id"])
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="MFA session is no longer valid")
        if pending_methods:
            payload["mfa_methods"] = pending_methods
        if pending_primary_method:
            payload["mfa_primary_method"] = pending_primary_method
        return payload, user

    async def _issue_authenticated_login(
        self,
        user: dict[str, Any],
        *,
        user_agent: str | None = None,
        ip_address: str | None = None,
        device_fingerprint: str | None = None,
    ) -> Token:
        now = self._utc_now()
        await self.repository.update_user(
            user["_id"],
            {
                "last_active_at": now,
                "updated_at": now,
                "mfa_last_verified_at": now,
            },
        )
        user["last_active_at"] = now
        user["updated_at"] = now

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
            user=await self._serialize_user_out(user),
            anomaly=LoginAnomaly(
                new_device=anomaly.get("new_device", False),
                new_network=anomaly.get("new_network", False),
                message=self._format_anomaly_message(anomaly),
            ) if (anomaly.get("new_device") or anomaly.get("new_network")) else None,
            mfa_required=False,
            pending_mfa_token=None,
            mfa_methods=[],
            mfa_primary_method=None,
            mfa_challenge=None,
        )

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
        enabled_mfa_methods = self._resolve_enabled_mfa_methods(user)
        primary_method = self._resolve_primary_mfa_method(user, enabled_mfa_methods)

        if enabled_mfa_methods:
            pending_mfa_token, pending_jti, pending_expires_at = self._build_pending_mfa_token(
                user,
                enabled_mfa_methods,
                primary_method,
            )
            await self._store_pending_mfa_state(
                user["_id"],
                jti=pending_jti,
                expires_at=pending_expires_at,
                methods=enabled_mfa_methods,
                primary_method=primary_method,
            )

            challenge_payload: dict[str, Any] | None = None
            if primary_method == "sms":
                try:
                    challenge_payload = await self.send_sms_login_challenge(
                        pending_mfa_token=pending_mfa_token,
                        resend=False,
                    )
                except HTTPException as exc:
                    challenge_payload = {
                        "method": "sms",
                        "challenge_sent": False,
                        "error": str(exc.detail),
                    }

            return Token(
                access_token="",
                refresh_token=None,
                user=await self._serialize_user_out(user),
                mfa_required=True,
                pending_mfa_token=pending_mfa_token,
                mfa_methods=enabled_mfa_methods,
                mfa_primary_method=primary_method,
                mfa_challenge=challenge_payload,
            )

        return await self._issue_authenticated_login(
            user,
            user_agent=user_agent,
            ip_address=ip_address,
            device_fingerprint=device_fingerprint,
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
        now = self._utc_now()
        await self.repository.update_user(
            user["_id"],
            {"last_active_at": now, "updated_at": now},
        )
        user["last_active_at"] = now
        user["updated_at"] = now

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
            rotated_at=now,
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
            user=await self._serialize_user_out(user),
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

    # =====================
    # MFA Methods
    # =====================

    @staticmethod
    def _generate_totp_secret() -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()

    @staticmethod
    def _get_totp(secret: str) -> pyotp.TOTP:
        """Get TOTP object from secret."""
        return pyotp.TOTP(secret)

    @staticmethod
    def _generate_otp_code(length: int = 6) -> str:
        return "".join(secrets.choice(string.digits) for _ in range(length))

    @staticmethod
    def _hash_otp(otp: str) -> str:
        return hashlib.sha256(otp.encode()).hexdigest()

    @staticmethod
    def _remaining_backup_codes(backup_codes: list[dict[str, Any]]) -> int:
        return sum(1 for code in backup_codes if not code.get("used"))

    async def _ensure_backup_codes(self, user: dict[str, Any]) -> list[str]:
        existing = user.get("mfa_backup_codes", [])
        if self._remaining_backup_codes(existing) > 0:
            return []

        backup_codes = self._generate_recovery_codes(count=8, code_length=12)
        backup_codes_hashed = [
            {
                "code_hash": self._hash_recovery_code(code),
                "used": False,
                "used_at": None,
            }
            for code in backup_codes
        ]
        now = self._utc_now()
        await self.repository.update_user(
            user["_id"],
            {
                "mfa_backup_codes": backup_codes_hashed,
                "mfa_backup_codes_generated_at": now,
                "updated_at": now,
            },
        )
        return backup_codes

    async def _send_sms_via_twilio(self, phone_number: str, message: str) -> dict[str, Any]:
        if not settings.sms_mfa_enabled:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SMS MFA is disabled in this environment",
            )

        if TwilioClient is None or not self._is_twilio_configured():
            if settings.environment == "production":
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="SMS delivery is not configured. Please contact support.",
                )
            return {"delivered": False, "dev_mode": True}

        try:
            client = TwilioClient(settings.twilio_account_sid, settings.twilio_auth_token)
            payload: dict[str, Any] = {"to": phone_number, "body": message}
            if settings.twilio_messaging_service_sid:
                payload["messaging_service_sid"] = settings.twilio_messaging_service_sid
            else:
                payload["from_"] = settings.twilio_from_number
            twilio_message = client.messages.create(**payload)
            return {"delivered": True, "sid": twilio_message.sid}
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="SMS delivery failed. Please try again.",
            )

    def _validate_sms_send_rate(self, user: dict[str, Any], *, context_prefix: str) -> tuple[datetime, int]:
        now = self._utc_now()
        last_sent = self._normalize_utc(user.get(f"mfa_sms_{context_prefix}_last_sent_at"))
        if last_sent and (now - last_sent).total_seconds() < settings.mfa_sms_send_min_interval_seconds:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {settings.mfa_sms_send_min_interval_seconds} seconds before requesting another code",
            )

        window_started = self._normalize_utc(user.get(f"mfa_sms_{context_prefix}_send_window_started_at"))
        send_count = int(user.get(f"mfa_sms_{context_prefix}_send_count", 0) or 0)
        if not window_started or (now - window_started).total_seconds() > settings.mfa_sms_send_window_seconds:
            return now, 1
        if send_count >= settings.mfa_sms_send_max_per_window:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many SMS code requests. Please try again later.",
            )
        return window_started, send_count + 1

    async def enable_totp(self, user_id: str) -> dict[str, Any]:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        secret = self._generate_totp_secret()
        totp = self._get_totp(secret)
        provisioning_uri = totp.provisioning_uri(name=user["email"], issuer_name="CAPS AI")

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode()

        backup_codes = self._generate_recovery_codes(count=8, code_length=12)
        backup_codes_hashed = [
            {
                "code_hash": self._hash_recovery_code(code),
                "used": False,
                "used_at": None,
            }
            for code in backup_codes
        ]

        await self.repository.save_totp_secret(user["_id"], secret, backup_codes_hashed)

        await log_audit_event(
            actor_user_id=user_id,
            action="totp_enabled_init",
            action_type="mfa_config",
            entity_type="account",
            entity_id=user_id,
            detail="TOTP setup initiated",
            severity="medium",
        )

        return {
            "secret": secret,
            "qr_code": f"data:image/png;base64,{qr_code_base64}",
            "provisioning_uri": provisioning_uri,
            "backup_codes": backup_codes,
            "message": "Save these backup codes safely. Each code can be used once if you lose access to your authenticator app.",
        }

    async def confirm_totp(self, user_id: str, otp_code: str) -> dict[str, Any]:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        secret = user.get("mfa_totp_secret")
        if not secret:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP setup not initiated")

        totp = self._get_totp(secret)
        if not totp.verify(otp_code, valid_window=1):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid OTP code")

        now = self._utc_now()
        await self.repository.update_user(
            user["_id"],
            {
                "mfa_totp_enabled": True,
                "mfa_totp_confirmed_at": now,
                "mfa_primary_method": user.get("mfa_primary_method") or "totp",
                "updated_at": now,
            },
        )

        await log_audit_event(
            actor_user_id=user_id,
            action="totp_confirmed",
            action_type="mfa_config",
            entity_type="account",
            entity_id=user_id,
            detail="TOTP successfully configured",
            severity="high",
        )

        return {"success": True, "message": "TOTP has been successfully enabled for your account"}

    async def disable_totp(self, user_id: str) -> dict[str, Any]:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not user.get("mfa_totp_enabled"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="TOTP is not enabled")

        now = self._utc_now()
        next_primary = None
        if user.get("mfa_sms_enabled"):
            next_primary = "sms"
        elif user.get("mfa_webauthn_enabled") and user.get("mfa_webauthn_credentials"):
            next_primary = "webauthn"

        await self.repository.update_user(
            user["_id"],
            {
                "mfa_totp_enabled": False,
                "mfa_totp_secret": None,
                "mfa_primary_method": next_primary,
                "updated_at": now,
            },
        )

        await log_audit_event(
            actor_user_id=user_id,
            action="totp_disabled",
            action_type="mfa_config",
            entity_type="account",
            entity_id=user_id,
            detail="TOTP has been disabled",
            severity="high",
        )
        return {"success": True, "message": "TOTP has been disabled"}

    async def verify_totp(self, user_id: str, otp_code: str) -> bool:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            return False
        secret = user.get("mfa_totp_secret")
        if not secret or not user.get("mfa_totp_enabled"):
            return False
        return self._get_totp(secret).verify(otp_code, valid_window=1)

    async def send_email_otp(self, user_id: str) -> dict[str, Any]:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        otp_code = self._generate_otp_code()
        otp_hash = self._hash_otp(otp_code)
        expires_at = self._utc_now() + timedelta(minutes=10)
        await self.repository.save_email_otp(user["_id"], otp_hash, expires_at)

        if settings.environment == "development":
            return {
                "success": True,
                "message": "OTP sent to email (development mode)",
                "otp_dev": otp_code,
            }
        return {"success": True, "message": f"OTP sent to {user['email']}"}

    async def verify_email_otp(self, user_id: str, otp_code: str) -> bool:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            return False

        otp_hash = user.get("mfa_email_otp_hash")
        expires_at = self._normalize_utc(user.get("mfa_email_otp_expires_at"))
        if not otp_hash or not expires_at or self._utc_now() > expires_at:
            return False

        attempts = int(user.get("mfa_email_attempts", 0) or 0)
        if attempts >= settings.mfa_sms_verify_max_attempts:
            return False

        input_hash = self._hash_otp(otp_code)
        if input_hash != otp_hash:
            await self.repository.increment_mfa_attempts(user["_id"], "email")
            return False

        await self.repository.clear_mfa_attempts(user["_id"])
        return True

    async def send_sms_enrollment_code(self, user_id: str, phone_number: str) -> dict[str, Any]:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        normalized_phone = self._normalize_phone_number(phone_number)
        window_started, send_count = self._validate_sms_send_rate(user, context_prefix="enroll")

        otp_code = self._generate_otp_code()
        otp_hash = self._hash_otp(otp_code)
        now = self._utc_now()
        expires_at = now + timedelta(seconds=settings.mfa_sms_otp_ttl_seconds)
        delivery = await self._send_sms_via_twilio(
            normalized_phone,
            f"Your CAPS AI verification code is {otp_code}. It expires in {settings.mfa_sms_otp_ttl_seconds // 60} minutes.",
        )

        await self.repository.update_user(
            user["_id"],
            {
                "mfa_sms_enroll_phone_number": normalized_phone,
                "mfa_sms_enroll_otp_hash": otp_hash,
                "mfa_sms_enroll_otp_expires_at": expires_at,
                "mfa_sms_enroll_attempts": 0,
                "mfa_sms_enroll_last_sent_at": now,
                "mfa_sms_enroll_send_window_started_at": window_started,
                "mfa_sms_enroll_send_count": send_count,
                "updated_at": now,
            },
        )

        payload: dict[str, Any] = {
            "success": True,
            "message": "Verification code sent",
            "phone_number_masked": self._mask_phone_number(normalized_phone),
            "expires_in_seconds": settings.mfa_sms_otp_ttl_seconds,
            "resend_after_seconds": settings.mfa_sms_send_min_interval_seconds,
        }
        if delivery.get("dev_mode"):
            payload["otp_dev"] = otp_code
            payload["delivery_mode"] = "development"
        return payload

    async def verify_sms_enrollment_code(self, user_id: str, otp_code: str) -> dict[str, Any]:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        otp_hash = user.get("mfa_sms_enroll_otp_hash")
        phone_number = user.get("mfa_sms_enroll_phone_number")
        expires_at = self._normalize_utc(user.get("mfa_sms_enroll_otp_expires_at"))
        now = self._utc_now()
        if not otp_hash or not phone_number or not expires_at or now > expires_at:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired SMS verification code")

        attempts = int(user.get("mfa_sms_enroll_attempts", 0) or 0)
        if attempts >= settings.mfa_sms_verify_max_attempts:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Maximum SMS verification attempts reached. Request a new code.",
            )

        if self._hash_otp(otp_code) != otp_hash:
            await self.repository.update_user(
                user["_id"],
                {
                    "mfa_sms_enroll_attempts": attempts + 1,
                    "updated_at": now,
                },
            )
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid SMS verification code")

        backup_codes = await self._ensure_backup_codes(user)
        await self.repository.update_user(
            user["_id"],
            {
                "mfa_sms_phone_number": phone_number,
                "mfa_sms_phone_verified_at": now,
                "mfa_sms_enabled": True,
                "mfa_primary_method": user.get("mfa_primary_method") or "sms",
                "mfa_sms_enroll_phone_number": None,
                "mfa_sms_enroll_otp_hash": None,
                "mfa_sms_enroll_otp_expires_at": None,
                "mfa_sms_enroll_attempts": 0,
                "updated_at": now,
            },
        )

        await log_audit_event(
            actor_user_id=user_id,
            action="sms_enabled",
            action_type="mfa_config",
            entity_type="account",
            entity_id=user_id,
            detail="SMS MFA enabled",
            severity="high",
        )

        return {
            "success": True,
            "message": "SMS MFA enabled",
            "phone_number_masked": self._mask_phone_number(phone_number),
            "backup_codes": backup_codes,
        }

    async def disable_sms(self, user_id: str) -> dict[str, Any]:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not user.get("mfa_sms_enabled"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SMS MFA is not enabled")

        now = self._utc_now()
        next_primary = None
        if user.get("mfa_totp_enabled"):
            next_primary = "totp"
        elif user.get("mfa_webauthn_enabled") and user.get("mfa_webauthn_credentials"):
            next_primary = "webauthn"

        await self.repository.update_user(
            user["_id"],
            {
                "mfa_sms_enabled": False,
                "mfa_sms_phone_number": None,
                "mfa_sms_phone_verified_at": None,
                "mfa_primary_method": next_primary,
                "mfa_sms_login_otp_hash": None,
                "mfa_sms_login_otp_expires_at": None,
                "mfa_sms_login_attempts": 0,
                "updated_at": now,
            },
        )

        await log_audit_event(
            actor_user_id=user_id,
            action="sms_disabled",
            action_type="mfa_config",
            entity_type="account",
            entity_id=user_id,
            detail="SMS MFA disabled",
            severity="high",
        )
        return {"success": True, "message": "SMS MFA has been disabled"}

    async def send_sms_login_challenge(self, pending_mfa_token: str, *, resend: bool = True) -> dict[str, Any]:
        payload, user = await self._load_pending_mfa_user(pending_mfa_token)
        methods = payload.get("mfa_methods", [])
        if "sms" not in methods:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SMS is not enabled for this account")

        phone_number = user.get("mfa_sms_phone_number")
        if not phone_number or not user.get("mfa_sms_phone_verified_at"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="SMS is not configured for this account")

        window_started, send_count = self._validate_sms_send_rate(user, context_prefix="login")

        otp_code = self._generate_otp_code()
        otp_hash = self._hash_otp(otp_code)
        now = self._utc_now()
        expires_at = now + timedelta(seconds=settings.mfa_sms_otp_ttl_seconds)
        delivery = await self._send_sms_via_twilio(
            phone_number,
            f"Your CAPS AI login code is {otp_code}. It expires in {settings.mfa_sms_otp_ttl_seconds // 60} minutes.",
        )

        await self.repository.update_user(
            user["_id"],
            {
                "mfa_sms_login_otp_hash": otp_hash,
                "mfa_sms_login_otp_expires_at": expires_at,
                "mfa_sms_login_attempts": 0,
                "mfa_sms_login_pending_jti": payload.get("jti"),
                "mfa_sms_login_last_sent_at": now,
                "mfa_sms_login_send_window_started_at": window_started,
                "mfa_sms_login_send_count": send_count,
                "updated_at": now,
            },
        )

        challenge = {
            "method": "sms",
            "challenge_sent": True,
            "resend": resend,
            "phone_number_masked": self._mask_phone_number(phone_number),
            "expires_in_seconds": settings.mfa_sms_otp_ttl_seconds,
            "resend_after_seconds": settings.mfa_sms_send_min_interval_seconds,
        }
        if delivery.get("dev_mode"):
            challenge["otp_dev"] = otp_code
            challenge["delivery_mode"] = "development"
        return challenge

    async def verify_sms_login_code(self, user: dict[str, Any], pending_jti: str, otp_code: str) -> bool:
        otp_hash = user.get("mfa_sms_login_otp_hash")
        expires_at = self._normalize_utc(user.get("mfa_sms_login_otp_expires_at"))
        challenge_jti = user.get("mfa_sms_login_pending_jti")
        if not otp_hash or not expires_at or self._utc_now() > expires_at:
            return False
        if challenge_jti != pending_jti:
            return False

        attempts = int(user.get("mfa_sms_login_attempts", 0) or 0)
        if attempts >= settings.mfa_sms_verify_max_attempts:
            return False

        if self._hash_otp(otp_code) != otp_hash:
            await self.repository.update_user(
                user["_id"],
                {
                    "mfa_sms_login_attempts": attempts + 1,
                    "updated_at": self._utc_now(),
                },
            )
            return False

        await self.repository.update_user(
            user["_id"],
            {
                "mfa_sms_login_otp_hash": None,
                "mfa_sms_login_otp_expires_at": None,
                "mfa_sms_login_attempts": 0,
                "mfa_sms_login_pending_jti": None,
                "updated_at": self._utc_now(),
            },
        )
        return True

    async def verify_backup_code(self, user_id: str, backup_code: str) -> bool:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            return False

        backup_codes = user.get("mfa_backup_codes", [])
        code_hash = self._hash_recovery_code(backup_code)
        for stored_code in backup_codes:
            if stored_code.get("code_hash") != code_hash:
                continue
            if stored_code.get("used"):
                return False
            return await self.repository.consume_backup_code(user["_id"], code_hash)
        return False

    async def verify_pending_mfa(
        self,
        *,
        pending_mfa_token: str,
        mfa_method: str,
        mfa_code: str,
        user_agent: str | None = None,
        ip_address: str | None = None,
        device_fingerprint: str | None = None,
    ) -> Token:
        payload, user = await self._load_pending_mfa_user(pending_mfa_token)
        method = (mfa_method or "").strip().lower()
        if method not in {"totp", "sms", "backup"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported MFA verification method")

        allowed_methods = payload.get("mfa_methods", [])
        if method not in allowed_methods and method != "backup":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="MFA method is not enabled for this login")

        is_valid = False
        if method == "totp":
            is_valid = await self.verify_totp(str(user["_id"]), mfa_code)
        elif method == "sms":
            is_valid = await self.verify_sms_login_code(user, payload.get("jti"), mfa_code)
        elif method == "backup":
            is_valid = await self.verify_backup_code(str(user["_id"]), mfa_code)

        if not is_valid:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired MFA code")

        await self._clear_pending_mfa_state(user["_id"])
        await log_audit_event(
            actor_user_id=str(user["_id"]),
            action="mfa_login_verified",
            action_type="mfa_verify",
            entity_type="auth",
            entity_id=str(user["_id"]),
            detail=f"MFA login verification succeeded using method={method}",
            severity="medium",
        )
        return await self._issue_authenticated_login(
            user,
            user_agent=user_agent,
            ip_address=ip_address,
            device_fingerprint=device_fingerprint,
        )

    async def begin_webauthn_registration(
        self,
        user_id: str,
        *,
        label: str | None = None,
        authenticator_attachment: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_webauthn_configured()

        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        existing_credentials = user.get("mfa_webauthn_credentials", [])
        exclude_credentials = [
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(credential["credential_id"]))
            for credential in existing_credentials
            if credential.get("credential_id")
        ]

        auth_selection = None
        attachment_value = (authenticator_attachment or "").strip().lower()
        if attachment_value in {"platform", "cross-platform"}:
            auth_selection = AuthenticatorSelectionCriteria(
                authenticator_attachment=(
                    AuthenticatorAttachment.PLATFORM
                    if attachment_value == "platform"
                    else AuthenticatorAttachment.CROSS_PLATFORM
                )
            )

        options = generate_registration_options(
            rp_id=settings.webauthn_rp_id,
            rp_name=settings.webauthn_rp_name,
            user_id=str(user["_id"]).encode("utf-8"),
            user_name=user["email"],
            user_display_name=user.get("full_name") or user["email"],
            exclude_credentials=exclude_credentials,
            user_verification=UserVerificationRequirement.PREFERRED,
            authenticator_selection=auth_selection,
        )
        options_json = json.loads(options_to_json(options))
        now = self._utc_now()
        expires_at = now + timedelta(seconds=settings.webauthn_challenge_ttl_seconds)

        await self.repository.update_user(
            user["_id"],
            {
                "mfa_webauthn_registration_state": {
                    "challenge": options_json.get("challenge"),
                    "expires_at": expires_at,
                    "label": (label or "").strip() or None,
                    "created_at": now,
                },
                "updated_at": now,
            },
        )

        return {
            "options": options_json,
            "expires_at": expires_at,
        }

    async def finish_webauthn_registration(
        self,
        user_id: str,
        *,
        credential: dict[str, Any],
        label: str | None = None,
    ) -> dict[str, Any]:
        self._ensure_webauthn_configured()

        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        registration_state = user.get("mfa_webauthn_registration_state") or {}
        expected_challenge = registration_state.get("challenge")
        expires_at = self._normalize_utc(registration_state.get("expires_at"))
        if not expected_challenge or not expires_at or self._utc_now() > expires_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="WebAuthn registration challenge is missing or expired")

        origin = self._extract_webauthn_origin(credential)
        if not origin or origin not in self._webauthn_origins():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="WebAuthn origin is not allowed")

        try:
            verification = verify_registration_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(expected_challenge),
                expected_rp_id=settings.webauthn_rp_id,
                expected_origin=origin,
                require_user_verification=True,
            )
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="WebAuthn registration verification failed")

        credential_id = self._b64url_encode(verification.credential_id)
        public_key = self._b64url_encode(verification.credential_public_key)
        transports = credential.get("response", {}).get("transports", []) or []
        existing_credentials = [
            c for c in user.get("mfa_webauthn_credentials", []) if c.get("credential_id") != credential_id
        ]

        resolved_label = (
            (label or "").strip()
            or (registration_state.get("label") or "").strip()
            or f"Authenticator {len(existing_credentials) + 1}"
        )
        now = self._utc_now()
        existing_credentials.append(
            {
                "credential_id": credential_id,
                "public_key": public_key,
                "sign_count": int(getattr(verification, "sign_count", 0) or 0),
                "transports": transports,
                "label": resolved_label,
                "created_at": now,
                "last_used_at": None,
                "authenticator_attachment": credential.get("authenticatorAttachment"),
                "device_type": str(getattr(verification, "credential_device_type", "unknown")),
                "backed_up": bool(getattr(verification, "credential_backed_up", False)),
            }
        )

        backup_codes = await self._ensure_backup_codes(user)
        await self.repository.update_user(
            user["_id"],
            {
                "mfa_webauthn_enabled": True,
                "mfa_webauthn_credentials": existing_credentials,
                "mfa_webauthn_registration_state": None,
                "mfa_primary_method": user.get("mfa_primary_method") or "webauthn",
                "updated_at": now,
            },
        )

        await log_audit_event(
            actor_user_id=user_id,
            action="webauthn_credential_registered",
            action_type="mfa_config",
            entity_type="account",
            entity_id=user_id,
            detail="WebAuthn credential registered",
            severity="high",
        )

        return {
            "success": True,
            "message": "WebAuthn authenticator registered",
            "credential_id": credential_id,
            "label": resolved_label,
            "backup_codes": backup_codes,
        }

    async def begin_webauthn_authentication(self, pending_mfa_token: str) -> dict[str, Any]:
        self._ensure_webauthn_configured()

        payload, user = await self._load_pending_mfa_user(pending_mfa_token)
        if "webauthn" not in payload.get("mfa_methods", []):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="WebAuthn is not enabled for this account")

        credentials = user.get("mfa_webauthn_credentials", [])
        if not credentials:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No WebAuthn credentials are registered")

        allow_credentials = [
            PublicKeyCredentialDescriptor(id=base64url_to_bytes(record["credential_id"]))
            for record in credentials
            if record.get("credential_id")
        ]
        options = generate_authentication_options(
            rp_id=settings.webauthn_rp_id,
            allow_credentials=allow_credentials,
            user_verification=UserVerificationRequirement.PREFERRED,
        )
        options_json = json.loads(options_to_json(options))
        now = self._utc_now()
        expires_at = now + timedelta(seconds=settings.webauthn_challenge_ttl_seconds)

        await self.repository.update_user(
            user["_id"],
            {
                "mfa_webauthn_auth_state": {
                    "challenge": options_json.get("challenge"),
                    "expires_at": expires_at,
                    "pending_jti": payload.get("jti"),
                    "allowed_credential_ids": [record.get("credential_id") for record in credentials if record.get("credential_id")],
                    "created_at": now,
                },
                "updated_at": now,
            },
        )
        return {
            "options": options_json,
            "expires_at": expires_at,
        }

    async def finish_webauthn_authentication(
        self,
        *,
        pending_mfa_token: str,
        credential: dict[str, Any],
        user_agent: str | None = None,
        ip_address: str | None = None,
        device_fingerprint: str | None = None,
    ) -> Token:
        self._ensure_webauthn_configured()

        payload, user = await self._load_pending_mfa_user(pending_mfa_token)
        auth_state = user.get("mfa_webauthn_auth_state") or {}
        expected_challenge = auth_state.get("challenge")
        expires_at = self._normalize_utc(auth_state.get("expires_at"))
        pending_jti = auth_state.get("pending_jti")
        allowed_credential_ids = auth_state.get("allowed_credential_ids") or []
        if not expected_challenge or not expires_at or self._utc_now() > expires_at:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="WebAuthn authentication challenge is missing or expired")
        if pending_jti != payload.get("jti"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="WebAuthn challenge does not match this MFA session")

        credential_id = credential.get("id")
        if not credential_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="WebAuthn credential id is required")
        if allowed_credential_ids and credential_id not in allowed_credential_ids:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown WebAuthn credential")

        stored_credentials = user.get("mfa_webauthn_credentials", [])
        existing_record = next((c for c in stored_credentials if c.get("credential_id") == credential_id), None)
        if not existing_record:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unknown WebAuthn credential")

        origin = self._extract_webauthn_origin(credential)
        if not origin or origin not in self._webauthn_origins():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="WebAuthn origin is not allowed")

        try:
            verification = verify_authentication_response(
                credential=credential,
                expected_challenge=base64url_to_bytes(expected_challenge),
                expected_rp_id=settings.webauthn_rp_id,
                expected_origin=origin,
                credential_public_key=base64url_to_bytes(existing_record["public_key"]),
                credential_current_sign_count=int(existing_record.get("sign_count") or 0),
                require_user_verification=True,
            )
        except Exception:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="WebAuthn authentication verification failed")

        now = self._utc_now()
        current_sign_count = int(existing_record.get("sign_count") or 0)
        next_sign_count = int(getattr(verification, "new_sign_count", current_sign_count) or 0)
        if next_sign_count < current_sign_count:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="WebAuthn sign counter regression detected")
        for record in stored_credentials:
            if record.get("credential_id") != credential_id:
                continue
            record["sign_count"] = next_sign_count
            record["last_used_at"] = now
            record["device_type"] = str(getattr(verification, "credential_device_type", record.get("device_type") or "unknown"))
            record["backed_up"] = bool(getattr(verification, "credential_backed_up", record.get("backed_up", False)))
            break

        await self.repository.update_user(
            user["_id"],
            {
                "mfa_webauthn_credentials": stored_credentials,
                "mfa_webauthn_auth_state": None,
                "updated_at": now,
            },
        )
        await self._clear_pending_mfa_state(user["_id"])

        await log_audit_event(
            actor_user_id=str(user["_id"]),
            action="mfa_login_verified",
            action_type="mfa_verify",
            entity_type="auth",
            entity_id=str(user["_id"]),
            detail="MFA login verification succeeded using method=webauthn",
            severity="medium",
        )
        return await self._issue_authenticated_login(
            user,
            user_agent=user_agent,
            ip_address=ip_address,
            device_fingerprint=device_fingerprint,
        )

    async def list_webauthn_credentials(self, user_id: str) -> dict[str, Any]:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        credentials = user.get("mfa_webauthn_credentials", [])
        return {
            "credentials": [
                {
                    "credential_id": record.get("credential_id"),
                    "label": record.get("label") or "Authenticator",
                    "created_at": record.get("created_at"),
                    "last_used_at": record.get("last_used_at"),
                    "transports": record.get("transports", []),
                    "authenticator_attachment": record.get("authenticator_attachment"),
                    "device_type": record.get("device_type"),
                    "backed_up": bool(record.get("backed_up", False)),
                }
                for record in credentials
            ]
        }

    async def remove_webauthn_credential(self, user_id: str, credential_id: str) -> dict[str, Any]:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        credentials = user.get("mfa_webauthn_credentials", [])
        filtered = [record for record in credentials if record.get("credential_id") != credential_id]
        if len(filtered) == len(credentials):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="WebAuthn credential not found")

        now = self._utc_now()
        update_data: dict[str, Any] = {
            "mfa_webauthn_credentials": filtered,
            "mfa_webauthn_enabled": bool(filtered),
            "updated_at": now,
        }
        if not filtered and user.get("mfa_primary_method") == "webauthn":
            update_data["mfa_primary_method"] = "totp" if user.get("mfa_totp_enabled") else "sms" if user.get("mfa_sms_enabled") else None

        await self.repository.update_user(user["_id"], update_data)

        await log_audit_event(
            actor_user_id=user_id,
            action="webauthn_credential_removed",
            action_type="mfa_config",
            entity_type="account",
            entity_id=user_id,
            detail="WebAuthn credential removed",
            severity="high",
        )

        return {
            "success": True,
            "message": "WebAuthn credential removed",
            "remaining_credentials": len(filtered),
        }

    async def disable_webauthn(self, user_id: str) -> dict[str, Any]:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not user.get("mfa_webauthn_enabled") and not user.get("mfa_webauthn_credentials"):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="WebAuthn is not enabled")

        next_primary = "totp" if user.get("mfa_totp_enabled") else "sms" if user.get("mfa_sms_enabled") else None
        await self.repository.update_user(
            user["_id"],
            {
                "mfa_webauthn_enabled": False,
                "mfa_webauthn_credentials": [],
                "mfa_webauthn_registration_state": None,
                "mfa_webauthn_auth_state": None,
                "mfa_primary_method": next_primary,
                "updated_at": self._utc_now(),
            },
        )
        return {"success": True, "message": "WebAuthn MFA has been disabled"}

    async def get_mfa_status(self, user_id: str) -> dict[str, Any]:
        user = await self.repository.find_user_by_id(parse_object_id(user_id))
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        methods = self._resolve_enabled_mfa_methods(user)
        primary_method = self._resolve_primary_mfa_method(user, methods)
        backup_codes = user.get("mfa_backup_codes", [])
        remaining_backup = self._remaining_backup_codes(backup_codes)
        sms_phone = user.get("mfa_sms_phone_number")
        webauthn_credentials = user.get("mfa_webauthn_credentials", [])

        return {
            "mfa_enabled": bool(methods),
            "mfa_methods": methods,
            "methods": methods,
            "primary_method": primary_method,
            "recovery_codes_remaining": remaining_backup,
            "backup_codes_count": remaining_backup,
            "backup_codes_generated_at": user.get("mfa_backup_codes_generated_at"),
            "method_status": {
                "totp": {
                    "enabled": bool(user.get("mfa_totp_enabled")),
                    "ready": bool(user.get("mfa_totp_enabled") and user.get("mfa_totp_secret")),
                },
                "sms": {
                    "enabled": bool(user.get("mfa_sms_enabled")),
                    "ready": bool(user.get("mfa_sms_enabled") and user.get("mfa_sms_phone_verified_at")),
                    "phone_number_masked": self._mask_phone_number(sms_phone),
                    "verified_at": user.get("mfa_sms_phone_verified_at"),
                    "last_sent_at": user.get("mfa_sms_login_last_sent_at") or user.get("mfa_sms_enroll_last_sent_at"),
                    "delivery_configured": self._is_twilio_configured() or settings.environment != "production",
                    "resend_after_seconds": settings.mfa_sms_send_min_interval_seconds,
                    "expires_in_seconds": settings.mfa_sms_otp_ttl_seconds,
                    "send_window_seconds": settings.mfa_sms_send_window_seconds,
                    "send_max_per_window": settings.mfa_sms_send_max_per_window,
                    "provider": "twilio",
                },
                "webauthn": {
                    "enabled": bool(user.get("mfa_webauthn_enabled")),
                    "ready": bool(user.get("mfa_webauthn_enabled") and webauthn_credentials),
                    "credential_count": len(webauthn_credentials),
                    "rp_id": settings.webauthn_rp_id,
                    "allowed_origins": self._webauthn_origins(),
                },
            },
            "webauthn_credentials": [
                {
                    "credential_id": record.get("credential_id"),
                    "label": record.get("label") or "Authenticator",
                    "created_at": record.get("created_at"),
                    "last_used_at": record.get("last_used_at"),
                    "transports": record.get("transports", []),
                    "authenticator_attachment": record.get("authenticator_attachment"),
                    "device_type": record.get("device_type"),
                }
                for record in webauthn_credentials
            ],
            "totp_enabled": bool(user.get("mfa_totp_enabled")),
            "sms_enabled": bool(user.get("mfa_sms_enabled")),
            "webauthn_enabled": bool(user.get("mfa_webauthn_enabled")),
        }

