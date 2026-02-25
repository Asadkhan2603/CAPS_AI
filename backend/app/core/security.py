from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import os
from typing import Callable, Dict, List
from uuid import uuid4

from bson import ObjectId
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.database import db
from app.core.permission_registry import PERMISSION_REGISTRY
from app.core.redis_store import redis_store

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        algorithm, iteration_str, salt_hex, digest_hex = hashed_password.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    try:
        iterations = int(iteration_str)
    except ValueError:
        return False
    computed = hashlib.pbkdf2_hmac(
        "sha256", plain_password.encode("utf-8"), bytes.fromhex(salt_hex), iterations
    ).hex()
    return hmac.compare_digest(computed, digest_hex)


def get_password_hash(password: str) -> str:
    iterations = 390000
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    ).hex()
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest}"


def create_access_token(
    *,
    user_id: str,
    email: str,
    role: str,
    admin_type: str | None = None,
    extended_roles: List[str] | None = None,
    minutes: int | None = None,
) -> str:
    expires_in_minutes = minutes or settings.access_token_expire_minutes
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_in_minutes)
    payload = {
        "jti": uuid4().hex,
        "token_type": "access",
        "sub": user_id,
        "email": email,
        "role": role,
        "admin_type": admin_type,
        "extended_roles": extended_roles or [],
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    *,
    user_id: str,
    email: str,
    role: str,
    admin_type: str | None = None,
    extended_roles: List[str] | None = None,
    days: int | None = None,
) -> str:
    expires_in_days = days or settings.refresh_token_expire_days
    expire = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
    payload = {
        "jti": uuid4().hex,
        "token_type": "refresh",
        "sub": user_id,
        "email": email,
        "role": role,
        "admin_type": admin_type,
        "extended_roles": extended_roles or [],
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str, *, expected_type: str = "access") -> Dict[str, str]:
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    token_type = payload.get("token_type") or "access"
    if token_type != expected_type:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def is_token_blacklisted(jti: str | None) -> bool:
    if not jti:
        return False
    if await redis_store.is_blacklisted(jti):
        return True
    collection = getattr(db, "token_blacklist", None)
    if collection is None:
        return False
    blacklisted = await collection.find_one({"jti": jti})
    return bool(blacklisted)


async def get_current_user(token: str = Depends(oauth2_scheme)) -> Dict[str, str]:
    payload = decode_access_token(token, expected_type="access")
    if await is_token_blacklisted(payload.get("jti")):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing subject",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def require_roles(allowed_roles: List[str]) -> Callable:
    async def role_dependency(
        current_user: Dict[str, str] = Depends(get_current_user),
    ) -> Dict[str, str]:
        if current_user.get("role") not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return role_dependency


def require_teacher_extensions(allowed_extensions: List[str]) -> Callable:
    async def extension_dependency(
        current_user: Dict[str, str] = Depends(get_current_user),
    ) -> Dict[str, str]:
        if current_user.get("role") != "teacher":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Teacher role is required",
            )
        user_extensions = current_user.get("extended_roles", [])
        if not any(role in user_extensions for role in allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Required supervisory role is missing",
            )
        return current_user

    return extension_dependency


def require_admin_or_teacher_extensions(allowed_extensions: List[str]) -> Callable:
    async def dependency(
        current_user: Dict[str, str] = Depends(get_current_user),
    ) -> Dict[str, str]:
        if current_user.get("role") == "admin":
            return current_user
        if current_user.get("role") != "teacher":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin or teacher supervisory role is required",
            )
        user_extensions = current_user.get("extended_roles", [])
        if not any(role in user_extensions for role in allowed_extensions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Required supervisory role is missing",
            )
        return current_user

    return dependency


def _resolved_admin_type(current_user: Dict[str, str]) -> str:
    admin_type = current_user.get("admin_type")
    if admin_type:
        return admin_type
    # Backward compatibility for legacy admin users without admin_type.
    if current_user.get("role") == "admin":
        return "admin"
    return ""


def has_permission(current_user: Dict[str, str], permission: str) -> bool:
    role = current_user.get("role")
    if not role:
        return False

    rule = PERMISSION_REGISTRY.get(permission)
    if not rule:
        return False

    allowed_roles = rule.get("roles", set())
    if role not in allowed_roles:
        return False

    if role == "admin":
        allowed_admin_types = rule.get("admin_types")
        if allowed_admin_types:
            return _resolved_admin_type(current_user) in allowed_admin_types
        return True

    if role == "teacher":
        required_extensions = rule.get("teacher_extensions")
        if required_extensions:
            current_extensions = set(current_user.get("extended_roles") or [])
            return bool(current_extensions.intersection(required_extensions))
        return True

    if role == "student":
        required_extensions = rule.get("student_extensions")
        if required_extensions:
            current_extensions = set(current_user.get("extended_roles") or [])
            return bool(current_extensions.intersection(required_extensions))
        return True

    return False


def require_permission(permission: str) -> Callable:
    async def permission_dependency(
        current_user: Dict[str, str] = Depends(get_current_user),
    ) -> Dict[str, str]:
        if not has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required permission: {permission}",
            )
        return current_user

    return permission_dependency
