from datetime import datetime
from typing import Any

from pydantic import BaseModel
from pydantic import Field

from app.schemas.user import UserOut


class LoginAnomaly(BaseModel):
    new_device: bool = False
    new_network: bool = False
    message: str | None = None


class Token(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: UserOut
    anomaly: LoginAnomaly | None = None
    mfa_required: bool = False  # If True, user must verify MFA before full access
    pending_mfa_token: str | None = None  # Temporary token for MFA verification
    mfa_methods: list[str] = Field(default_factory=list)
    mfa_primary_method: str | None = None
    mfa_challenge: dict[str, Any] | None = None


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


class LoginHistoryEntry(BaseModel):
    """Login history record for account activity dashboard (Gap-012)"""
    timestamp: datetime
    ip_address: str | None = None
    device_fingerprint: str | None = None
    user_agent: str | None = None
    browser: str | None = None
    os: str | None = None
    device_type: str | None = None  # desktop, mobile, tablet
    location: str | None = None  # approximate location from IP
    success: bool = True
    anomaly: bool = False
    locked_out: bool = False


class LoginHistoryResponse(BaseModel):
    """Response for login history list (Gap-012)"""
    total_count: int
    page: int
    page_size: int
    entries: list[LoginHistoryEntry]


class SessionInfo(BaseModel):
    """Active session info for device management (Gap-015)"""
    session_id: str
    device_fingerprint: str
    device_name: str | None = None
    ip_address: str
    browser: str | None = None
    os: str | None = None
    created_at: datetime
    last_active_at: datetime
    is_current: bool = False


class AccountActivityResponse(BaseModel):
    """Account activity dashboard data (Gap-014)"""
    login_attempts_today: int
    login_attempts_week: int
    unusual_activity: bool
    last_login: datetime | None = None
    total_sessions: int
    active_sessions: list[SessionInfo]
    recent_logins: list[LoginHistoryEntry]


class RecoveryCode(BaseModel):
    code: str = Field(min_length=8, max_length=16)
    used: bool = False
    used_at: datetime | None = None


class RecoveryCodeResponse(BaseModel):
    codes: list[str]
    generated_at: datetime
    message: str = "Store these codes safely. Each code can be used once to recover your account."


class RecoveryCodeVerification(BaseModel):
    recovery_code: str = Field(min_length=8, max_length=16)


class BiometricAuthRequest(BaseModel):
    credential_id: str = Field(min_length=10, max_length=1024)
    authenticator_data: str
    client_data_json: str
    signature: str


class SessionBootstrapResponse(BaseModel):
    user: UserOut
    unread_notice_count: int = 0
    unread_notification_count: int = 0
    branding: SessionBootstrapBranding = Field(default_factory=SessionBootstrapBranding)
    generated_at: str


# ============================================================================
# Phase 5: Multi-Factor Authentication (MFA) Models (Gap-016 to Gap-020)
# ============================================================================

class TOTPSecret(BaseModel):
    """TOTP secret for authenticator app setup (Gap-016)"""
    secret_key: str = Field(min_length=32, max_length=64)
    qr_code_url: str
    verified: bool = False
    created_at: datetime


class MFAPhoneVerification(BaseModel):
    """SMS phone number verification (Gap-017)"""
    phone_number: str = Field(min_length=10, max_length=20, pattern=r'^\+?[\d\-\s\(\)]+$')
    verified: bool = False
    verified_at: datetime | None = None


class MFABackupCode(BaseModel):
    """Backup code for MFA recovery (Gap-020)"""
    code_hash: str = Field(min_length=64, max_length=128)
    used: bool = False
    used_at: datetime | None = None


class UserMFAProfile(BaseModel):
    """User's MFA configuration (Gap-018)"""
    mfa_enabled: bool = False
    primary_method: str | None = None  # "totp" or "sms"
    totp_setup: TOTPSecret | None = None
    sms_phone: MFAPhoneVerification | None = None
    backup_codes: list[MFABackupCode] = []
    created_at: datetime | None = None
    last_verified_at: datetime | None = None


class TOTPSetupRequest(BaseModel):
    """Request to generate TOTP secret (Gap-016)"""
    password: str = Field(min_length=8, max_length=128)  # Require password for security


class TOTPVerificationRequest(BaseModel):
    """Request to verify TOTP code (Gap-016)"""
    secret_key: str = Field(min_length=32, max_length=64)
    totp_code: str = Field(pattern=r'^\d{6}$')  # 6-digit TOTP code


class SMSSetupRequest(BaseModel):
    """Request to setup SMS verification (Gap-017)"""
    phone_number: str = Field(min_length=10, max_length=20, pattern=r'^\+?[\d\-\s\(\)]+$')
    password: str = Field(min_length=8, max_length=128)


class SMSVerificationRequest(BaseModel):
    """Request to verify SMS code (Gap-017)"""
    phone_number: str = Field(min_length=10, max_length=20)
    sms_code: str = Field(pattern=r'^\d{6}$')  # 6-digit SMS code


class MFAVerificationRequest(BaseModel):
    """MFA verification during login (Gap-019)"""
    pending_mfa_token: str = Field(min_length=16, max_length=4096)
    mfa_method: str  # "totp", "sms", "backup", or "webauthn"
    mfa_code: str = Field(min_length=4, max_length=12)  # Code, SMS, or backup code


class MFAVerificationResponse(BaseModel):
    """Response after successful MFA verification (Gap-019)"""
    success: bool
    message: str
    token: Token | None = None


class BackupCodesResponse(BaseModel):
    """Response with generated backup codes (Gap-020)"""
    backup_codes: list[str]
    generated_at: datetime
    message: str = "Store these codes in a safe place. Each code can be used once."
