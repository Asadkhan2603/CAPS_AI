from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import db
from app.core.security import (
    create_access_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from app.models.users import user_public
from app.schemas.auth import Token
from app.schemas.user import UserCreate, UserLogin, UserOut

router = APIRouter()


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register_user(payload: UserCreate) -> UserOut:
    email = payload.email.lower().strip()
    extended_roles = payload.extended_roles or []
    if payload.role != "teacher" and extended_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Extended roles are only allowed for teacher accounts",
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
