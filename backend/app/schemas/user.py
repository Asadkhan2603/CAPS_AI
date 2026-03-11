from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

UserRole = Literal["admin", "teacher", "student"]
AdminType = Literal["super_admin", "admin", "academic_admin", "compliance_admin"]
UserExtensionRole = Literal["year_head", "class_coordinator", "club_coordinator", "club_president"]


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    admin_type: AdminType | None = None
    extended_roles: list[UserExtensionRole] = Field(default_factory=list)


class UserLogin(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class UserProfile(BaseModel):
    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: str | None = Field(default=None, max_length=30)
    gender: str | None = Field(default=None, max_length=30)
    address_line: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, max_length=80)
    postal_code: str | None = Field(default=None, max_length=20)
    bio: str | None = Field(default=None, max_length=1000)
    designation: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    organization: str | None = Field(default=None, max_length=160)
    skills: str | None = Field(default=None, max_length=500)
    linkedin_url: str | None = Field(default=None, max_length=255)
    website_url: str | None = Field(default=None, max_length=255)


class ClassCoordinatorScope(BaseModel):
    faculty_id: str | None = None
    department_id: str | None = None
    program_id: str | None = None
    specialization_id: str | None = None
    department_code: str | None = Field(default=None, max_length=60)
    batch_id: str | None = None
    semester_id: str | None = None
    class_id: str | None = None


class ClubPresidentScope(BaseModel):
    club_id: str | None = None


class UserRoleScope(BaseModel):
    class_coordinator: ClassCoordinatorScope | None = None
    club_president: ClubPresidentScope | None = None


class UserOut(BaseModel):
    id: str
    full_name: str
    email: str
    role: UserRole
    admin_type: AdminType | None = None
    extended_roles: list[UserExtensionRole] = Field(default_factory=list)
    role_scope: UserRoleScope = Field(default_factory=UserRoleScope)
    is_active: bool = True
    must_change_password: bool = False
    profile: UserProfile = Field(default_factory=UserProfile)
    avatar_url: str | None = None
    avatar_updated_at: datetime | None = None
    created_at: datetime | None = None


class UserExtensionRolesUpdate(BaseModel):
    extended_roles: list[UserExtensionRole] = Field(default_factory=list)
    role_scope: UserRoleScope | None = None


class UserProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    date_of_birth: str | None = Field(default=None, max_length=30)
    gender: str | None = Field(default=None, max_length=30)
    address_line: str | None = Field(default=None, max_length=200)
    city: str | None = Field(default=None, max_length=80)
    state: str | None = Field(default=None, max_length=80)
    country: str | None = Field(default=None, max_length=80)
    postal_code: str | None = Field(default=None, max_length=20)
    bio: str | None = Field(default=None, max_length=1000)
    designation: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    organization: str | None = Field(default=None, max_length=160)
    skills: str | None = Field(default=None, max_length=500)
    linkedin_url: str | None = Field(default=None, max_length=255)
    website_url: str | None = Field(default=None, max_length=255)
