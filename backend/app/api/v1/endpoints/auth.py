from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
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

router = APIRouter()
session_router = APIRouter()
PROFILE_UPLOAD_DIR = Path("uploads/profiles")
MAX_AVATAR_SIZE = 3 * 1024 * 1024
ALLOWED_AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

auth_service = AuthService(AuthRepository(lambda: db))


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
    return UserOut(**user_public(current_user))


@session_router.get("/bootstrap", response_model=SessionBootstrapResponse)
async def get_session_bootstrap(
    current_user=Depends(get_current_user),
) -> SessionBootstrapResponse:
    branding = await get_logo_meta_payload()
    unread_notice_count = await get_unread_notice_count_payload(current_user)
    unread_notification_count = await get_unread_notification_count_payload(current_user)
    return SessionBootstrapResponse(
        user=UserOut(**user_public(current_user)),
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
    return UserOut(**user_public(updated))


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
    return UserOut(**user_public(updated))


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
    return UserOut(**user_public(updated))


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
