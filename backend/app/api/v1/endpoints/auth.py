from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.models.users import user_public
from app.schemas.auth import ChangePasswordRequest, Token
from app.schemas.user import UserCreate, UserLogin, UserOut, UserProfileUpdate

router = APIRouter()
PROFILE_UPLOAD_DIR = Path("uploads/profiles")
MAX_AVATAR_SIZE = 3 * 1024 * 1024
ALLOWED_AVATAR_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate) -> UserOut:
    email = payload.email.lower().strip()
    extended_roles = payload.extended_roles or []
    if payload.role != "teacher" and extended_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extended roles are only allowed for teacher accounts",
        )

    if payload.role == "admin":
        existing_admin = await db.users.find_one({"role": "admin"})
        if existing_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin account registration is closed",
            )

    existing_user = await db.users.find_one({"email": email})
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered",
        )

    await db.users.create_index("email", unique=True)
    document = {
        "full_name": payload.full_name.strip(),
        "email": email,
        "hashed_password": get_password_hash(payload.password),
        "role": payload.role,
        "extended_roles": extended_roles,
        "is_active": True,
        "must_change_password": False,
        "created_at": datetime.now(timezone.utc),
    }

    try:
        result = await db.users.insert_one(document)
    except Exception as exc:
        if "duplicate key" in str(exc).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered",
            ) from exc
        raise

    created_user = await db.users.find_one({"_id": result.inserted_id})
    return UserOut(**user_public(created_user))


@router.post("/login", response_model=Token)
async def login_user(payload: UserLogin) -> Token:
    email = payload.email.lower().strip()
    user = await db.users.find_one({"email": email})
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not verify_password(payload.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    token = create_access_token(
        user_id=str(user["_id"]),
        email=user["email"],
        role=user["role"],
        extended_roles=user.get("extended_roles", []),
    )
    return Token(access_token=token, user=UserOut(**user_public(user)))


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
