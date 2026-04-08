from datetime import datetime

from pydantic import BaseModel
from pydantic import Field

from app.schemas.user import UserOut


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: UserOut


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=4096)


class BootstrapStatus(BaseModel):
    environment: str
    auth_registration_policy: str
    has_admin: bool
    can_self_register_admin: bool
    local_auth_recovery_enabled: bool = False


class DevBootstrapAdminRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class SessionBootstrapBranding(BaseModel):
    has_logo: bool = False
    updated_at: datetime | None = None
    filename: str | None = None


class SessionBootstrapResponse(BaseModel):
    user: UserOut
    unread_notice_count: int = 0
    unread_notification_count: int = 0
    branding: SessionBootstrapBranding = Field(default_factory=SessionBootstrapBranding)
    generated_at: str
