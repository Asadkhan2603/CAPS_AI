from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

UserRole = Literal["admin", "teacher", "student"]
TeacherExtensionRole = Literal["year_head", "class_coordinator", "club_coordinator"]


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    extended_roles: list[TeacherExtensionRole] = Field(default_factory=list)


class UserLogin(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: str
    full_name: str
    email: str
    role: UserRole
    extended_roles: list[TeacherExtensionRole] = Field(default_factory=list)
    is_active: bool = True
    created_at: datetime | None = None
