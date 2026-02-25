from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import (
    get_current_user,
    oauth2_scheme,
    get_password_hash,
    verify_password,
)
from app.domains.auth.repository import AuthRepository
from app.domains.auth.service import AuthService
from app.models.users import user_public
from app.schemas.auth import ChangePasswordRequest, RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserLogin, UserOut, UserProfileUpdate

router = APIRouter()
PROFILE_UPLOAD_DIR = Path("uploads/profiles")
MAX_AVATAR_SIZE = 3 * 1024 * 1024
ALLOWED_AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

auth_service = AuthService(AuthRepository(lambda: db))


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate) -> UserOut:
    return await auth_service.register(payload)


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
    if profile_updates:
        existing_profile = dict(current_user.get("profile", {}) or {})
        existing_profile.update(profile_updates)
        set_data["profile"] = existing_profile

    if not set_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No profile fields provided")

    await db.users.update_one({"_id": current_user["_id"]}, {"$set": set_data})
    updated = await db.users.find_one({"_id": current_user["_id"]})
    return UserOut(**user_public(updated))


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

    PROFILE_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    user_id = str(current_user["_id"])
    for existing in PROFILE_UPLOAD_DIR.glob(f"{user_id}.*"):
        if existing.is_file():
            existing.unlink()

    saved_name = f"{user_id}{suffix}"
    saved_path = PROFILE_UPLOAD_DIR / saved_name
    saved_path.write_bytes(content)

    now = datetime.now(timezone.utc)
    await db.users.update_one(
        {"_id": current_user["_id"]},
        {"$set": {"avatar_filename": saved_name, "avatar_updated_at": now}},
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
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Avatar file missing")
    return FileResponse(file_path)
