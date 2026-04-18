from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

UserRole = Literal["admin", "teacher", "student"]
AdminTypeInput = Literal[
    "super_admin",
    "admin",
    "academic_admin",
    "compliance_admin",
    "department_admin",
    "year_admin",
    "hod",
    "dean",
]
UserExtensionRole = Literal["year_head", "class_coordinator", "club_coordinator", "club_president", "class_representative"]


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole
    admin_type: AdminTypeInput | None = None
    extended_roles: list[UserExtensionRole] = Field(default_factory=list)
    role_scope: UserRoleScope | None = None


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


class NotificationScopePreference(BaseModel):
    in_app: bool | None = None
    email_mode: Literal["inherit", "off", "instant", "daily_digest", "weekly_digest"] = "inherit"


class NotificationScopePreferences(BaseModel):
    global_scope: NotificationScopePreference = Field(default_factory=NotificationScopePreference)
    notice: NotificationScopePreference = Field(default_factory=NotificationScopePreference)
    similarity: NotificationScopePreference = Field(default_factory=NotificationScopePreference)
    ai: NotificationScopePreference = Field(default_factory=NotificationScopePreference)
    system: NotificationScopePreference = Field(default_factory=NotificationScopePreference)


class CommunicationDigestPreferences(BaseModel):
    daily_digest_hour_utc: int = Field(default=8, ge=0, le=23)
    weekly_digest_day_of_week: int = Field(default=0, ge=0, le=6)


class CommunicationPreferences(BaseModel):
    announcement_email: bool = True
    club_announcement_email: bool = True
    notification_email: bool = True
    notification_in_app: bool = True
    notification_email_mode: Literal["off", "instant", "daily_digest", "weekly_digest"] = "instant"
    notification_scope_preferences: NotificationScopePreferences = Field(default_factory=NotificationScopePreferences)
    digest_preferences: CommunicationDigestPreferences = Field(default_factory=CommunicationDigestPreferences)


class CommunicationPreferencesUpdate(BaseModel):
    announcement_email: bool | None = None
    club_announcement_email: bool | None = None
    notification_email: bool | None = None
    notification_in_app: bool | None = None
    notification_email_mode: Literal["off", "instant", "daily_digest", "weekly_digest"] | None = None
    notification_scope_preferences: NotificationScopePreferences | None = None
    digest_preferences: CommunicationDigestPreferences | None = None


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


ClassRepresentativeSeat = Literal["cr_1", "cr_2"]


class ClassRepresentativeScope(BaseModel):
    faculty_id: str | None = None
    department_id: str | None = None
    program_id: str | None = None
    specialization_id: str | None = None
    batch_id: str | None = None
    semester_id: str | None = None
    class_id: str | None = None
    seat: ClassRepresentativeSeat | None = None


class UserRoleScope(BaseModel):
    class_coordinator: ClassCoordinatorScope | None = None
    club_president: ClubPresidentScope | None = None
    class_representative: ClassRepresentativeScope | None = None


class UserOut(BaseModel):
    id: str
    full_name: str
    email: str
    role: UserRole
    admin_type: str | None = Field(default=None, max_length=120)
    extended_roles: list[UserExtensionRole] = Field(default_factory=list)
    role_scope: UserRoleScope = Field(default_factory=UserRoleScope)
    is_active: bool = True
    must_change_password: bool = False
    profile: UserProfile = Field(default_factory=UserProfile)
    communication_preferences: CommunicationPreferences = Field(default_factory=CommunicationPreferences)
    avatar_url: str | None = None
    avatar_updated_at: datetime | None = None
    last_active_at: datetime | None = None
    created_at: datetime | None = None
    rbac_role_code: str | None = None
    admin_role: dict[str, Any] | None = None
    permissions: list[str] = Field(default_factory=list)
    permission_overrides: dict[str, Any] = Field(default_factory=lambda: {"allow_permission_keys": [], "deny_permission_keys": []})
    scopes: list[dict[str, Any]] = Field(default_factory=list)
    status: str | None = None
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    last_permission_change_at: datetime | None = None
    last_permission_change_by: str | None = None
    last_status_change_at: datetime | None = None
    last_status_change_by: str | None = None
    schema_version: int = 1


class UserExtensionRolesUpdate(BaseModel):
    extended_roles: list[UserExtensionRole] = Field(default_factory=list)
    role_scope: UserRoleScope | None = None
    change_reason: str | None = Field(default=None, max_length=500)


class UserAdminListItem(BaseModel):
    id: str
    full_name: str
    email: str
    avatar_url: str | None = None
    avatar_updated_at: datetime | None = None
    role: UserRole
    admin_type: str | None = None
    is_active: bool = True
    extended_roles: list[UserExtensionRole] = Field(default_factory=list)
    last_active_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    department: str | None = None
    designation: str | None = None
    last_permission_change_at: datetime | None = None
    last_permission_change_by: str | None = None
    last_status_change_at: datetime | None = None
    last_status_change_by: str | None = None


class UsersAdminListResponse(BaseModel):
    items: list[UserAdminListItem] = Field(default_factory=list)
    page: int = 1
    limit: int = 25
    total: int = 0
    total_pages: int = 0


class UsersAdminCapabilitiesResponse(BaseModel):
    workspace: bool = True
    activity: bool = True
    bulk_operations: bool = True
    permission_templates: bool = True
    invitations: bool = True
    import_export: bool = True
    inline_editing: bool = True
    compact_density: bool = True
    responsive_workflows: bool = True
    table_virtualization: bool = False
    http_cache_validation: bool = False
    rollout_stage: Literal["internal_admins", "super_admins", "all_admins"] = "all_admins"
    rollout_cohort: str = "admin"
    rollout_access: bool = True
    rollout_reason: str | None = None


class UsersAdminTelemetryEvent(BaseModel):
    event: str = Field(min_length=2, max_length=120)
    outcome: Literal["success", "error"] = "success"
    scope: str | None = Field(default=None, max_length=80)
    severity: Literal["low", "medium", "high"] = "low"
    metadata: dict[str, Any] = Field(default_factory=dict)


class UsersAdminDashboardPageSize(BaseModel):
    page_size: int
    count: int = 0


class UsersAdminLatencyDashboardBucket(BaseModel):
    bucket_start: datetime | None = None
    requests: int = 0
    errors: int = 0
    avg_duration_ms: int = 0
    p95_duration_ms: int = 0


class UsersAdminLatencyDashboard(BaseModel):
    request_count: int = 0
    success_count: int = 0
    error_count: int = 0
    error_rate_pct: float = 0.0
    avg_duration_ms: int = 0
    p50_duration_ms: int = 0
    p95_duration_ms: int = 0
    p99_duration_ms: int = 0
    buckets: list[UsersAdminLatencyDashboardBucket] = Field(default_factory=list)


class UsersAdminPaginationDashboard(BaseModel):
    sample_count: int = 0
    avg_page: float = 0.0
    avg_limit: float = 0.0
    empty_page_rate_pct: float = 0.0
    deep_page_rate_pct: float = 0.0
    top_page_sizes: list[UsersAdminDashboardPageSize] = Field(default_factory=list)


class UsersAdminDashboardAlert(BaseModel):
    code: str
    level: Literal["warning", "critical"]
    metric: str
    current_value: float = 0.0
    threshold_value: float = 0.0
    comparison: Literal[">", ">="] = ">"
    message: str


class UsersAdminDashboardResponse(BaseModel):
    window_minutes: int = 60
    bucket_minutes: int = 5
    generated_at: datetime | None = None
    latency: UsersAdminLatencyDashboard = Field(default_factory=UsersAdminLatencyDashboard)
    pagination: UsersAdminPaginationDashboard = Field(default_factory=UsersAdminPaginationDashboard)
    alerts: list[UsersAdminDashboardAlert] = Field(default_factory=list)


class UserStatusUpdate(BaseModel):
    is_active: bool
    reason: str = Field(min_length=3, max_length=500)


class UserBulkStatusUpdate(BaseModel):
    user_ids: list[str] = Field(default_factory=list, min_length=1)
    is_active: bool
    reason: str = Field(min_length=3, max_length=500)


class UserBulkStatusResultItem(BaseModel):
    user_id: str
    success: bool
    message: str | None = None


class UserBulkStatusResponse(BaseModel):
    updated_count: int = 0
    failed_count: int = 0
    results: list[UserBulkStatusResultItem] = Field(default_factory=list)


class UserBulkExtensionUpdateItem(BaseModel):
    user_id: str
    extended_roles: list[UserExtensionRole] = Field(default_factory=list)
    role_scope: UserRoleScope | None = None


class UserBulkExtensionsUpdate(BaseModel):
    updates: list[UserBulkExtensionUpdateItem] = Field(default_factory=list, min_length=1)
    change_reason: str = Field(min_length=3, max_length=500)


class UserBulkExtensionsResultItem(BaseModel):
    user_id: str
    success: bool
    message: str | None = None


class UserBulkExtensionsResponse(BaseModel):
    updated_count: int = 0
    failed_count: int = 0
    results: list[UserBulkExtensionsResultItem] = Field(default_factory=list)


class UserInvitationCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    role: UserRole
    admin_type: AdminTypeInput | None = None
    extended_roles: list[UserExtensionRole] = Field(default_factory=list)
    role_scope: UserRoleScope | None = None
    expires_in_days: int = Field(default=7, ge=1, le=30)


class UserInvitationOut(BaseModel):
    id: str
    full_name: str
    email: str
    role: UserRole
    admin_type: str | None = None
    extended_roles: list[UserExtensionRole] = Field(default_factory=list)
    role_scope: UserRoleScope = Field(default_factory=UserRoleScope)
    status: Literal["pending", "expired", "accepted"] = "pending"
    invitation_link: str
    created_at: datetime | None = None
    expires_at: datetime | None = None


class FilterOptionCount(BaseModel):
    value: str
    count: int = 0


class UsersFilterOptionsResponse(BaseModel):
    roles: list[FilterOptionCount] = Field(default_factory=list)
    admin_types: list[FilterOptionCount] = Field(default_factory=list)
    extensions: list[FilterOptionCount] = Field(default_factory=list)
    departments: list[FilterOptionCount] = Field(default_factory=list)
    status: list[FilterOptionCount] = Field(default_factory=list)


class UserFilterPresetQuery(BaseModel):
    q: str | None = Field(default=None, max_length=100)
    role: str | None = Field(default=None, max_length=50)
    status: Literal["active", "inactive"] | None = None
    admin_type: str | None = Field(default=None, max_length=120)
    extension: str | None = Field(default=None, max_length=120)
    department: str | None = Field(default=None, max_length=120)
    sort_by: str = Field(default="updated_at", max_length=50)
    sort_dir: Literal["asc", "desc"] = "desc"
    limit: int = Field(default=25, ge=10, le=100)


class UserFilterPresetCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    query: UserFilterPresetQuery = Field(default_factory=UserFilterPresetQuery)


class UserFilterPresetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    query: UserFilterPresetQuery | None = None


class UserFilterPresetOut(BaseModel):
    id: str
    name: str
    query: UserFilterPresetQuery = Field(default_factory=UserFilterPresetQuery)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserImportPreviewRow(BaseModel):
    row_number: int
    full_name: str | None = None
    email: str | None = None
    role: str | None = None
    admin_type: str | None = None
    extended_roles: list[str] = Field(default_factory=list)
    valid: bool
    errors: list[str] = Field(default_factory=list)


class UserImportPreviewResponse(BaseModel):
    rows: list[UserImportPreviewRow] = Field(default_factory=list)
    total_rows: int = 0
    valid_rows: int = 0
    invalid_rows: int = 0


class UserImportCommitRow(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    role: UserRole
    admin_type: str | None = None
    extended_roles: list[UserExtensionRole] = Field(default_factory=list)


class UserImportCommitRequest(BaseModel):
    rows: list[UserImportCommitRow] = Field(default_factory=list, min_length=1)
    mode: Literal["invite", "create"] = "invite"
    default_password: str | None = Field(default=None, min_length=8, max_length=128)


class UserImportCommitResponse(BaseModel):
    mode: Literal["invite", "create"]
    created_count: int = 0
    invited_count: int = 0
    skipped_count: int = 0


class PermissionTemplateCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    role: UserRole
    admin_type: str | None = Field(default=None, max_length=120)
    extended_roles: list[UserExtensionRole] = Field(default_factory=list)
    role_scope: UserRoleScope | None = None


class PermissionTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    role: UserRole | None = None
    admin_type: str | None = Field(default=None, max_length=120)
    extended_roles: list[UserExtensionRole] | None = None
    role_scope: UserRoleScope | None = None


class PermissionTemplateOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    role: UserRole
    admin_type: str | None = None
    extended_roles: list[UserExtensionRole] = Field(default_factory=list)
    role_scope: UserRoleScope = Field(default_factory=UserRoleScope)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class UserActivityResponse(BaseModel):
    items: list[dict[str, Any]] = Field(default_factory=list)
    page: int = 1
    limit: int = 25
    total: int = 0
    total_pages: int = 0


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
    communication_preferences: CommunicationPreferencesUpdate | None = None


class UserAdminProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=30)
    department: str | None = Field(default=None, max_length=120)
    designation: str | None = Field(default=None, max_length=120)
    organization: str | None = Field(default=None, max_length=160)
    change_reason: str | None = Field(default=None, max_length=500)
