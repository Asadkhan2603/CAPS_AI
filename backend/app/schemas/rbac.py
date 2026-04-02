from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class RbacPermissionOut(BaseModel):
    id: str
    key: str
    name: str
    module: str
    module_key: str
    description: str | None = None
    is_system: bool = True
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    schema_version: int = 1


class RbacScopeInput(BaseModel):
    department_id: str | None = None
    year_id: str | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> "RbacScopeInput":
        if not self.department_id and not self.year_id:
            raise ValueError("At least one of department_id or year_id is required")
        return self


class RbacScopeOut(RbacScopeInput):
    id: str
    user_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    schema_version: int = 1


class RbacRoleBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    permission_keys: list[str] = Field(default_factory=list)


class RbacRoleCreate(RbacRoleBase):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Z][A-Z0-9_]*$")


class RbacRoleUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    permission_keys: list[str] | None = None
    is_active: bool | None = None


class RbacRoleOut(BaseModel):
    id: str
    code: str
    name: str
    description: str | None = None
    permission_keys: list[str] = Field(default_factory=list)
    permission_groups: list[str] = Field(default_factory=list)
    is_system: bool = True
    is_active: bool = True
    deleted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    schema_version: int = 1


class RbacRoleSummary(BaseModel):
    id: str
    code: str
    name: str
    description: str | None = None


class RbacPermissionOverrideInput(BaseModel):
    allow_permission_keys: list[str] = Field(default_factory=list)
    deny_permission_keys: list[str] = Field(default_factory=list)


class RbacAdminCreate(RbacPermissionOverrideInput):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role_code: str = Field(min_length=2, max_length=64, pattern=r"^[A-Z][A-Z0-9_]*$")
    scopes: list[RbacScopeInput] = Field(default_factory=list)
    is_active: bool = True


class RbacAdminUpdate(RbacPermissionOverrideInput):
    allow_permission_keys: list[str] | None = None
    deny_permission_keys: list[str] | None = None
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    role_code: str | None = Field(default=None, min_length=2, max_length=64, pattern=r"^[A-Z][A-Z0-9_]*$")
    scopes: list[RbacScopeInput] | None = None
    is_active: bool | None = None


class RbacAdminStatusUpdate(BaseModel):
    is_active: bool


class RbacAdminOut(BaseModel):
    id: str
    full_name: str
    email: str
    role: Literal["admin"]
    admin_type: str | None = None
    admin_role: RbacRoleSummary | None = None
    permissions: list[str] = Field(default_factory=list)
    permission_overrides: dict = Field(default_factory=lambda: {"allow_permission_keys": [], "deny_permission_keys": []})
    scopes: list[RbacScopeOut] = Field(default_factory=list)
    is_active: bool = True
    status: str = "active"
    must_change_password: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    schema_version: int = 1


class RbacDesignOut(BaseModel):
    roles: list[dict]
    permission_groups: list[dict]
    scope_fields: list[str]
