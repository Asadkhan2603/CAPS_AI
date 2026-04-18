from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from starlette.concurrency import run_in_threadpool

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import USER_SCHEMA_VERSION
from app.core.security import (
    get_current_user,
    oauth2_scheme,
    get_password_hash,
    verify_password,
)
from app.domains.auth.repository import AuthRepository
from app.domains.auth.service import AuthService
from app.api.v1.endpoints.branding import get_logo_meta_payload
from app.api.v1.endpoints.notices import get_unread_notice_count_payload
from app.api.v1.endpoints.notifications import get_unread_notification_count_payload
from app.models.users import normalize_communication_preferences, user_public
from app.schemas.auth import (
    BootstrapStatus,
    ChangePasswordRequest,
    DevBootstrapAdminRequest,
    RefreshTokenRequest,
    SessionBootstrapResponse,
    Token,
)
from app.schemas.user import UserCreate, UserLogin, UserOut, UserProfileUpdate
from app.schemas.user import CommunicationPreferences, CommunicationPreferencesUpdate
from app.services.rbac import serialize_admin_user

router = APIRouter()
session_router = APIRouter()
PROFILE_UPLOAD_DIR = Path("uploads/profiles")
MAX_AVATAR_SIZE = 3 * 1024 * 1024
ALLOWED_AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

auth_service = AuthService(AuthRepository(lambda: db))


async def _serialize_user_response(user: dict) -> UserOut:
    if user.get("role") == "admin":
        return UserOut(**(await serialize_admin_user(user, database=db)))
    return UserOut(**user_public(user))


def _merge_communication_preferences(
    existing: dict | None,
    updates: dict | None,
) -> dict:
    merged = normalize_communication_preferences(existing)
    for key, value in (updates or {}).items():
        if value is None:
            continue
        if key == "notification_scope_preferences" and isinstance(value, dict):
            current_scope_preferences = dict(merged.get("notification_scope_preferences") or {})
            for scope_key, scope_value in value.items():
                if not isinstance(scope_value, dict):
                    continue
                current_scope = dict(current_scope_preferences.get(scope_key) or {})
                for nested_key, nested_value in scope_value.items():
                    if nested_value is not None:
                        current_scope[nested_key] = nested_value
                current_scope_preferences[scope_key] = current_scope
            merged[key] = current_scope_preferences
            continue
        if key == "digest_preferences" and isinstance(value, dict):
            current_digest_preferences = dict(merged.get("digest_preferences") or {})
            for nested_key, nested_value in value.items():
                if nested_value is not None:
                    current_digest_preferences[nested_key] = nested_value
            merged[key] = current_digest_preferences
            continue
        merged[key] = value
    return normalize_communication_preferences(merged)


def _is_loopback_request(request: Request) -> bool:
    host = (request.client.host if request.client else "") or ""
    return host in {"127.0.0.1", "::1", "localhost"}


@router.get("/bootstrap-status", response_model=BootstrapStatus)
async def get_bootstrap_status() -> BootstrapStatus:
    return await auth_service.get_bootstrap_status()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate) -> UserOut:
    return await auth_service.register(payload)


@router.post("/dev/bootstrap-admin", response_model=UserOut)
async def dev_bootstrap_admin(payload: DevBootstrapAdminRequest, request: Request) -> UserOut:
    if not _is_loopback_request(request):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Local auth recovery is available only from the host machine.",
        )
    return await auth_service.bootstrap_or_recover_admin(payload)


@router.post("/login", response_model=Token)
async def login_user(payload: UserLogin, request: Request) -> Token:
    return await auth_service.login(
        payload,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.headers.get("x-forwarded-for") or (request.client.host if request.client else None),
        device_fingerprint=request.headers.get("x-device-fingerprint"),
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(payload: RefreshTokenRequest, request: Request) -> Token:
    return await auth_service.refresh(
        payload.refresh_token,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.headers.get("x-forwarded-for") or (request.client.host if request.client else None),
        device_fingerprint=request.headers.get("x-device-fingerprint"),
    )


@router.post("/logout")
async def logout_user(
    refresh: RefreshTokenRequest | None = None,
    access_token: str = Depends(oauth2_scheme),
    current_user=Depends(get_current_user),
) -> dict:
    refresh_token_value = refresh.refresh_token if refresh else None
    return await auth_service.logout(
        current_user=current_user,
        access_token=access_token,
        refresh_token_value=refresh_token_value,
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user=Depends(get_current_user)) -> UserOut:
    return await _serialize_user_response(current_user)


@session_router.get("/bootstrap", response_model=SessionBootstrapResponse)
async def get_session_bootstrap(
    current_user=Depends(get_current_user),
) -> SessionBootstrapResponse:
    branding = await get_logo_meta_payload()
    unread_notice_count = await get_unread_notice_count_payload(current_user)
    unread_notification_count = await get_unread_notification_count_payload(current_user)
    return SessionBootstrapResponse(
        user=await _serialize_user_response(current_user),
        unread_notice_count=int(unread_notice_count.get("count") or 0),
        unread_notification_count=int(unread_notification_count.get("count") or 0),
        branding=branding,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/change-password", response_model=UserOut)
async def change_password(
    payload: ChangePasswordRequest,
    current_user=Depends(get_current_user),
) -> UserOut:
    if not verify_password(payload.current_password, current_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from current password",
        )

    await db.users.update_one(
        {"_id": current_user["_id"]},
        {
            "$set": {
                "hashed_password": get_password_hash(payload.new_password),
                "must_change_password": False,
                "schema_version": USER_SCHEMA_VERSION,
            }
        },
    )
    updated = await db.users.find_one({"_id": current_user["_id"]})
    return await _serialize_user_response(updated)


@router.patch("/profile", response_model=UserOut)
async def update_profile(
    payload: UserProfileUpdate,
    current_user=Depends(get_current_user),
) -> UserOut:
    update_data = payload.model_dump(exclude_unset=True)
    set_data = {}

    full_name = update_data.pop("full_name", None)
    if full_name is not None:
        set_data["full_name"] = full_name.strip()

    profile_updates = {key: value for key, value in update_data.items()}
    communication_preferences_update = profile_updates.pop("communication_preferences", None)
    if profile_updates:
        existing_profile = dict(current_user.get("profile", {}) or {})
        existing_profile.update(profile_updates)
        set_data["profile"] = existing_profile

    if communication_preferences_update:
        set_data["communication_preferences"] = _merge_communication_preferences(
            current_user.get("communication_preferences"),
            communication_preferences_update,
        )

    if not set_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No profile fields provided")

    set_data["schema_version"] = USER_SCHEMA_VERSION
    await db.users.update_one({"_id": current_user["_id"]}, {"$set": set_data})
    updated = await db.users.find_one({"_id": current_user["_id"]})
    return await _serialize_user_response(updated)


@router.get("/communication-preferences", response_model=CommunicationPreferences)
async def get_communication_preferences(
    current_user=Depends(get_current_user),
) -> CommunicationPreferences:
    return CommunicationPreferences(**normalize_communication_preferences(current_user.get("communication_preferences")))


@router.patch("/communication-preferences", response_model=CommunicationPreferences)
async def update_communication_preferences(
    payload: CommunicationPreferencesUpdate,
    current_user=Depends(get_current_user),
) -> CommunicationPreferences:
    updates = payload.model_dump(exclude_unset=True)
    if not any(value is not None for value in updates.values()):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No communication preference fields provided")

    preferences = _merge_communication_preferences(current_user.get("communication_preferences"), updates)

    await db.users.update_one(
        {"_id": current_user["_id"]},
        {
            "$set": {
                "communication_preferences": preferences,
                "schema_version": USER_SCHEMA_VERSION,
            }
        },
    )
    return CommunicationPreferences(**preferences)


@router.post("/profile/avatar", response_model=UserOut)
async def upload_profile_avatar(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
) -> UserOut:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_AVATAR_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported avatar type")

    content = await file.read()
    size = len(content)
    if size == 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded avatar is empty")
    if size > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Avatar exceeds 3MB limit")

    await run_in_threadpool(PROFILE_UPLOAD_DIR.mkdir, parents=True, exist_ok=True)
    user_id = str(current_user["_id"])
    for existing in await run_in_threadpool(lambda: list(PROFILE_UPLOAD_DIR.glob(f"{user_id}.*"))):
        if await run_in_threadpool(existing.is_file):
            await run_in_threadpool(existing.unlink)

    saved_name = f"{user_id}{suffix}"
    saved_path = PROFILE_UPLOAD_DIR / saved_name
    await run_in_threadpool(saved_path.write_bytes, content)

    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {
            "$set": {
                "avatar_filename": saved_name,
                "avatar_updated_at": now,
                "schema_version": USER_SCHEMA_VERSION,
            }
        },
    )
    updated = await db.users.find_one({"_id": current_user["_id"]})
    return await _serialize_user_response(updated)


@router.get("/profile/avatar/{user_id}")
async def get_profile_avatar(
    user_id: str,
    current_user=Depends(get_current_user),
) -> FileResponse:
    current_user_id = str(current_user["_id"])
    if current_user.get("role") != "admin" and user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this avatar")

    user = await db.users.find_one({"_id": parse_object_id(user_id)})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    file_name = user.get("avatar_filename")
    if not file_name:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar not found")

    file_path = PROFILE_UPLOAD_DIR / file_name
    if not await run_in_threadpool(file_path.exists):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar file missing")
    return FileResponse(
        file_path,
        headers={"Cache-Control": "private, max-age=300, stale-while-revalidate=86400"},
    )


# =====================
# MFA Endpoints (Phase 5)
# =====================

@router.post("/mfa/totp/enable")
async def enable_totp(current_user=Depends(get_current_user)) -> dict:
    """Generate TOTP secret and QR code for enabling TOTP-based MFA."""
    return await auth_service.enable_totp(str(current_user["_id"]))


@router.post("/mfa/totp/confirm")
async def confirm_totp(
    otp_code: str = Body(..., embed=True),
    current_user=Depends(get_current_user),
) -> dict:
    """Confirm TOTP setup by verifying an OTP code."""
    return await auth_service.confirm_totp(str(current_user["_id"]), otp_code)


@router.post("/mfa/totp/disable")
async def disable_totp(current_user=Depends(get_current_user)) -> dict:
    """Disable TOTP for the current user."""
    return await auth_service.disable_totp(str(current_user["_id"]))


@router.post("/mfa/verify")
async def verify_pending_mfa(
    pending_mfa_token: str = Body(..., embed=True),
    mfa_method: str = Body(..., embed=True),
    mfa_code: str = Body(..., embed=True),
    request: Request = None,
) -> Token:
    """Complete login-time MFA verification and issue full session tokens."""
    return await auth_service.verify_pending_mfa(
        pending_mfa_token=pending_mfa_token,
        mfa_method=mfa_method,
        mfa_code=mfa_code,
        user_agent=request.headers.get("user-agent") if request else None,
        ip_address=(request.headers.get("x-forwarded-for") if request else None) or (request.client.host if request and request.client else None),
        device_fingerprint=request.headers.get("x-device-fingerprint") if request else None,
    )


@router.post("/mfa/sms/enroll/send")
async def send_sms_otp(
    phone_number: str = Body(..., embed=True),
    current_user=Depends(get_current_user),
) -> dict:
    """Send SMS OTP for phone enrollment."""
    return await auth_service.send_sms_enrollment_code(str(current_user["_id"]), phone_number)


@router.post("/mfa/sms/enroll/verify")
async def verify_sms_enrollment(
    otp_code: str = Body(..., embed=True),
    current_user=Depends(get_current_user),
) -> dict:
    """Verify SMS enrollment OTP and enable SMS MFA."""
    return await auth_service.verify_sms_enrollment_code(str(current_user["_id"]), otp_code)


@router.post("/mfa/sms/disable")
async def disable_sms_mfa(current_user=Depends(get_current_user)) -> dict:
    """Disable SMS MFA for the current user."""
    return await auth_service.disable_sms(str(current_user["_id"]))


@router.post("/mfa/sms/challenge/send")
async def send_sms_login_challenge(
    pending_mfa_token: str = Body(..., embed=True),
) -> dict:
    """Send SMS challenge for a pending MFA login session."""
    return await auth_service.send_sms_login_challenge(pending_mfa_token, resend=False)


@router.post("/mfa/sms/challenge/resend")
async def resend_sms_login_challenge(
    pending_mfa_token: str = Body(..., embed=True),
) -> dict:
    """Resend SMS challenge for a pending MFA login session."""
    return await auth_service.send_sms_login_challenge(pending_mfa_token, resend=True)


@router.post("/mfa/webauthn/register/begin")
async def begin_webauthn_register(
    label: str | None = Body(default=None, embed=True),
    authenticator_attachment: str | None = Body(default=None, embed=True),
    current_user=Depends(get_current_user),
) -> dict:
    """Begin WebAuthn registration ceremony for account settings."""
    return await auth_service.begin_webauthn_registration(
        str(current_user["_id"]),
        label=label,
        authenticator_attachment=authenticator_attachment,
    )


@router.post("/mfa/webauthn/register/finish")
async def finish_webauthn_register(
    credential: dict = Body(..., embed=True),
    label: str | None = Body(default=None, embed=True),
    current_user=Depends(get_current_user),
) -> dict:
    """Finish WebAuthn registration ceremony and persist credential."""
    return await auth_service.finish_webauthn_registration(
        str(current_user["_id"]),
        credential=credential,
        label=label,
    )


@router.post("/mfa/webauthn/authenticate/begin")
async def begin_webauthn_authentication(
    pending_mfa_token: str = Body(..., embed=True),
) -> dict:
    """Begin WebAuthn authentication ceremony for pending login MFA."""
    return await auth_service.begin_webauthn_authentication(pending_mfa_token)


@router.post("/mfa/webauthn/authenticate/finish")
async def finish_webauthn_authentication(
    pending_mfa_token: str = Body(..., embed=True),
    credential: dict = Body(..., embed=True),
    request: Request = None,
) -> Token:
    """Finish WebAuthn authentication and issue full session tokens."""
    return await auth_service.finish_webauthn_authentication(
        pending_mfa_token=pending_mfa_token,
        credential=credential,
        user_agent=request.headers.get("user-agent") if request else None,
        ip_address=(request.headers.get("x-forwarded-for") if request else None) or (request.client.host if request and request.client else None),
        device_fingerprint=request.headers.get("x-device-fingerprint") if request else None,
    )


@router.get("/mfa/webauthn/credentials")
async def list_webauthn_credentials(current_user=Depends(get_current_user)) -> dict:
    """List registered WebAuthn credentials for the current user."""
    return await auth_service.list_webauthn_credentials(str(current_user["_id"]))


@router.delete("/mfa/webauthn/credentials/{credential_id}")
async def remove_webauthn_credential(
    credential_id: str,
    current_user=Depends(get_current_user),
) -> dict:
    """Remove one registered WebAuthn credential."""
    return await auth_service.remove_webauthn_credential(str(current_user["_id"]), credential_id)


@router.post("/mfa/webauthn/disable")
async def disable_webauthn(current_user=Depends(get_current_user)) -> dict:
    """Disable WebAuthn MFA and remove all credentials for the current user."""
    return await auth_service.disable_webauthn(str(current_user["_id"]))


@router.get("/mfa/status")
async def get_mfa_status(current_user=Depends(get_current_user)) -> dict:
    """Get MFA status for current user."""
    return await auth_service.get_mfa_status(str(current_user["_id"]))


# =============================
# Security Settings Endpoints
# =============================

@router.get("/security-settings/me")
async def get_my_security_settings(current_user=Depends(get_current_user)) -> dict:
    """Get the authenticated user's security settings."""
    return await get_security_settings(str(current_user["_id"]), current_user=current_user)


@router.post("/security-settings/me/mfa/toggle")
async def toggle_my_mfa_method(
    method: str | None = Body(default=None, embed=True),
    current_user=Depends(get_current_user)
) -> dict:
    """Toggle MFA method for the authenticated user."""
    return await toggle_mfa_method(str(current_user["_id"]), method=method, current_user=current_user)


@router.get("/account-activity/me")
async def get_my_account_activity(request: Request, current_user=Depends(get_current_user)) -> dict:
    """Get login history and active sessions for the authenticated user."""
    return await get_account_activity_endpoint(str(current_user["_id"]), request=request, current_user=current_user)


@router.get("/security-settings/{user_id}")
async def get_security_settings(user_id: str, current_user=Depends(get_current_user)) -> dict:
    """Get user's security settings including MFA status and recovery codes."""
    # Keep the literal `/me` route above this dynamic route so FastAPI does not
    # treat "me" as a user id and incorrectly reject self-service requests.
    if str(current_user["_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own security settings",
        )

    mfa_status = await auth_service.get_mfa_status(user_id)
    user = await auth_service.repository.find_user_by_id(parse_object_id(user_id))

    return {
        "mfa_enabled": mfa_status.get("mfa_enabled", False),
        "mfa_methods": mfa_status.get("mfa_methods", mfa_status.get("methods", [])),
        "primary_method": mfa_status.get("primary_method"),
        "method_status": mfa_status.get("method_status", {}),
        "webauthn_credentials": mfa_status.get("webauthn_credentials", []),
        "password_strength": user.get("password_strength", "unknown") if user else "unknown",
        "password_last_changed": user.get("password_updated_at") if user else None,
        "sessions_active": len(await auth_service.repository.find_recent_sessions(user_id, limit=100)),
        "recovery_codes_remaining": mfa_status.get("recovery_codes_remaining", mfa_status.get("backup_codes_count", 0)),
    }


@router.post("/security-settings/{user_id}/mfa/toggle")
async def toggle_mfa_method(
    user_id: str,
    method: str | None = Body(default=None, embed=True),
    current_user=Depends(get_current_user)
) -> dict:
    """Toggle MFA method on/off (totp, sms, webauthn)."""
    # Keep the literal `/me/mfa/toggle` route above this dynamic route so
    # self-service MFA updates are not interpreted as user_id="me".
    if str(current_user["_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only modify your own security settings",
        )

    if not method:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MFA method is required",
        )

    method = method.lower()
    if method not in ["totp", "sms", "webauthn"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid MFA method: {method}. Must be totp, sms, or webauthn",
        )

    try:
        if method == "totp":
            # Check if TOTP is currently enabled
            mfa_status = await auth_service.get_mfa_status(user_id)
            if "totp" in mfa_status.get("methods", []):
                # Disable TOTP
                result = await auth_service.disable_totp(user_id)
            else:
                # Enable TOTP
                result = await auth_service.enable_totp(user_id)
            return result

        elif method == "sms":
            mfa_status = await auth_service.get_mfa_status(user_id)
            if "sms" in mfa_status.get("mfa_methods", mfa_status.get("methods", [])):
                return await auth_service.disable_sms(user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SMS MFA is not enabled. Use /auth/mfa/sms/enroll/send and /auth/mfa/sms/enroll/verify to enable it.",
            )

        elif method == "webauthn":
            mfa_status = await auth_service.get_mfa_status(user_id)
            if "webauthn" in mfa_status.get("mfa_methods", mfa_status.get("methods", [])):
                return await auth_service.disable_webauthn(user_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="WebAuthn is not enabled. Use /auth/mfa/webauthn/register/begin and /auth/mfa/webauthn/register/finish to enable it.",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle MFA method: {str(e)}",
        )


# =============================
# Account Activity Endpoints
# =============================

@router.get("/account-activity/{user_id}")
async def get_account_activity_endpoint(user_id: str, request: Request, current_user=Depends(get_current_user)) -> dict:
    """Get login history and active sessions."""
    # Keep the literal `/me` route above this dynamic route so FastAPI does not
    # treat "me" as a user id and reject the authenticated user's own request.
    if str(current_user["_id"]) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own account activity",
        )

    return await auth_service.get_account_activity(
        user_id,
        current_device_fingerprint=request.headers.get("x-device-fingerprint"),
        current_user_agent=request.headers.get("user-agent"),
        current_ip_address=request.headers.get("x-forwarded-for") or (request.client.host if request.client else None),
    )


@router.post("/sessions/{session_id}/terminate")
async def terminate_session(
    session_id: str,
    request: Request,
    current_user=Depends(get_current_user),
) -> dict:
    """Terminate one non-current active session owned by the authenticated user."""
    return await auth_service.terminate_session(
        current_user=current_user,
        session_id=session_id,
        current_device_fingerprint=request.headers.get("x-device-fingerprint"),
        current_user_agent=request.headers.get("user-agent"),
        current_ip_address=request.headers.get("x-forwarded-for") or (request.client.host if request.client else None),
    )


@router.post("/account/logout-session")
async def logout_from_session(
    request: Request,
    session_id: str = Body(..., embed=True),
    current_user=Depends(get_current_user),
) -> dict:
    """Compatibility wrapper for terminating a specific session."""
    return await auth_service.terminate_session(
        current_user=current_user,
        session_id=session_id,
        current_device_fingerprint=request.headers.get("x-device-fingerprint"),
        current_user_agent=request.headers.get("user-agent"),
        current_ip_address=request.headers.get("x-forwarded-for") or (request.client.host if request.client else None),
    )
