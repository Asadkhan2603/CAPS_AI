from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ClubStatus = Literal[
    "draft",
    "pending_activation",
    "active",
    "registration_closed",
    "closed",
    "suspended",
    "archived",
    "dormant",
]
ClubMembershipType = Literal["open", "approval_required"]
ClubMemberRole = Literal["member", "president", "vice_president", "core_member"]
ClubMemberStatus = Literal["active", "inactive", "removed"]
ClubApplicationStatus = Literal["pending", "waitlisted", "approved", "rejected"]


class ClubCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=2, max_length=140)
    description: str | None = Field(default=None, max_length=1000)
    category: str | None = Field(default=None, max_length=120)
    department_id: str | None = None
    academic_year: str | None = Field(default=None, max_length=40)
    coordinator_user_id: str | None = None
    president_user_id: str | None = None
    membership_type: ClubMembershipType = "approval_required"
    registration_open: bool = False
    max_members: int | None = Field(default=None, ge=1, le=10000)
    logo_url: str | None = Field(default=None, max_length=1200)
    banner_url: str | None = Field(default=None, max_length=1200)
    tagline: str | None = Field(default=None, max_length=180)
    achievement_highlights: list[str] = Field(default_factory=list, max_length=8)
    recruitment_headline: str | None = Field(default=None, max_length=180)
    recruitment_cta_label: str | None = Field(default=None, max_length=60)
    public_contact_url: str | None = Field(default=None, max_length=1200)
    sponsorship_target_amount: float | None = Field(default=None, ge=0)
    sponsorship_committed_amount: float | None = Field(default=None, ge=0)
    sponsorship_notes: str | None = Field(default=None, max_length=1200)
    status: ClubStatus = "draft"


class ClubUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=2, max_length=140)
    description: str | None = Field(default=None, max_length=1000)
    category: str | None = Field(default=None, max_length=120)
    department_id: str | None = None
    coordinator_user_id: str | None = None
    president_user_id: str | None = None
    status: ClubStatus | None = None
    registration_open: bool | None = None
    membership_type: ClubMembershipType | None = None
    max_members: int | None = Field(default=None, ge=1, le=10000)
    logo_url: str | None = Field(default=None, max_length=1200)
    banner_url: str | None = Field(default=None, max_length=1200)
    tagline: str | None = Field(default=None, max_length=180)
    achievement_highlights: list[str] | None = Field(default=None, max_length=8)
    recruitment_headline: str | None = Field(default=None, max_length=180)
    recruitment_cta_label: str | None = Field(default=None, max_length=60)
    public_contact_url: str | None = Field(default=None, max_length=1200)
    sponsorship_target_amount: float | None = Field(default=None, ge=0)
    sponsorship_committed_amount: float | None = Field(default=None, ge=0)
    sponsorship_notes: str | None = Field(default=None, max_length=1200)


class ClubOut(BaseModel):
    id: str
    public_id: str | None = None
    display_label: str | None = None
    name: str
    slug: str | None = None
    description: str | None = None
    category: str | None = None
    department_id: str | None = None
    academic_year: str | None = None
    coordinator_user_id: str | None = None
    coordinator_name: str | None = None
    coordinator_email: str | None = None
    coordinator_label: str | None = None
    president_user_id: str | None = None
    president_name: str | None = None
    president_email: str | None = None
    president_label: str | None = None
    status: ClubStatus = "draft"
    registration_open: bool = False
    membership_type: ClubMembershipType = "approval_required"
    max_members: int | None = None
    member_count: int = 0
    logo_url: str | None = None
    banner_url: str | None = None
    tagline: str | None = None
    achievement_highlights: list[str] = Field(default_factory=list)
    recruitment_headline: str | None = None
    recruitment_cta_label: str | None = None
    public_contact_url: str | None = None
    sponsorship_target_amount: float | None = None
    sponsorship_committed_amount: float | None = None
    sponsorship_notes: str | None = None
    created_by: str | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None
    schema_version: int = 1
    is_active: bool = True
    created_at: datetime | None = None


class ClubMembershipOut(BaseModel):
    id: str
    public_id: str | None = None
    display_label: str | None = None
    club_id: str
    student_user_id: str
    student_name: str | None = None
    student_email: str | None = None
    student_label: str | None = None
    role: ClubMemberRole = "member"
    status: ClubMemberStatus = "active"
    joined_at: datetime | None = None
    left_at: datetime | None = None
    schema_version: int = 1


class ClubMembershipUpdate(BaseModel):
    role: ClubMemberRole | None = None
    status: ClubMemberStatus | None = None


class ClubApplicationOut(BaseModel):
    id: str
    public_id: str | None = None
    display_label: str | None = None
    club_id: str
    student_user_id: str
    student_name: str | None = None
    student_email: str | None = None
    student_label: str | None = None
    status: ClubApplicationStatus = "pending"
    queue_owner_user_id: str | None = None
    queue_owner_label: str | None = None
    coordinator_note: str | None = None
    last_touched_by: str | None = None
    last_touched_by_label: str | None = None
    last_touched_at: datetime | None = None
    applied_at: datetime | None = None
    reviewed_by: str | None = None
    reviewed_by_label: str | None = None
    reviewed_at: datetime | None = None
    schema_version: int = 1


class ClubApplicationReview(BaseModel):
    status: Literal["pending", "waitlisted", "approved", "rejected"] | None = None
    queue_owner_user_id: str | None = Field(default=None, max_length=100)
    coordinator_note: str | None = Field(default=None, max_length=800)


class ClubApplicationBulkReview(BaseModel):
    application_ids: list[str] = Field(min_length=1, max_length=200)
    status: Literal["pending", "waitlisted", "approved", "rejected"]


class ClubApplicationReminder(BaseModel):
    application_ids: list[str] = Field(default_factory=list, max_length=200)
    status_filter: Literal["pending", "waitlisted"] | None = None
    message: str | None = Field(default=None, max_length=500)


class ClubEventPerformanceOut(BaseModel):
    event_id: str
    title: str
    status: str = "draft"
    event_date: datetime | None = None
    capacity: int = 0
    confirmed_registrations: int = 0
    pending_registrations: int = 0
    waitlisted_registrations: int = 0
    fill_pct: float = 0.0
    attendance_marked_count: int = 0
    attendance_marked_pct: float = 0.0
    present_count: int = 0
    absent_count: int = 0
    no_show_rate_pct: float = 0.0
    certificate_enabled: bool = False
    certificate_eligible_count: int = 0
    certificate_issued_count: int = 0
    certificate_issuance_pct: float = 0.0
    health_summary: str = "steady"


class ClubEventHistoryEntryOut(BaseModel):
    id: str
    entry_type: Literal["event", "registration", "queue_snapshot"] = "event"
    action: str
    title: str
    detail: str | None = None
    actor_label: str | None = None
    subject_label: str | None = None
    status_label: str | None = None
    attendance_status: str | None = None
    certificate_issued: bool | None = None
    severity: str | None = None
    occurred_at: datetime | None = None


class ClubEventHistoryOut(BaseModel):
    event_id: str
    title: str
    status: str = "draft"
    event_type: str = "event"
    event_date: datetime | None = None
    registration_enabled: bool = True
    approval_required: bool = False
    certificate_enabled: bool = False
    capacity: int = 0
    confirmed_registrations: int = 0
    pending_registrations: int = 0
    waitlisted_registrations: int = 0
    attendance_marked_count: int = 0
    present_count: int = 0
    absent_count: int = 0
    certificates_issued: int = 0
    timeline: list[ClubEventHistoryEntryOut] = Field(default_factory=list)


class ClubTrendSummaryOut(BaseModel):
    key: str
    label: str
    direction: Literal["improving", "steady", "declining"] = "steady"
    current_value: float = 0.0
    previous_value: float = 0.0
    detail: str


class ClubEventTrendPointOut(BaseModel):
    event_id: str
    title: str
    event_date: datetime | None = None
    fill_pct: float = 0.0
    attendance_marked_pct: float = 0.0
    no_show_rate_pct: float = 0.0
    certificate_issuance_pct: float = 0.0
    waitlisted_registrations: int = 0
    health_summary: str = "steady"


class ClubArchiveSeasonSummaryOut(BaseModel):
    season_label: str
    archived_events: int = 0
    confirmed_registrations: int = 0
    attendance_marked_count: int = 0
    attendance_marked_pct: float = 0.0
    no_show_rate_pct: float = 0.0
    certificates_issued: int = 0
    certificate_issuance_pct: float = 0.0


class ClubArchiveCohortOut(BaseModel):
    cohort_key: str
    cohort_label: str
    archived_events: int = 0
    confirmed_registrations: int = 0
    attendance_marked_pct: float = 0.0
    no_show_rate_pct: float = 0.0
    certificate_issuance_pct: float = 0.0
    latest_event_date: datetime | None = None


class ClubArchivalHistoryPointOut(BaseModel):
    period_label: str
    period_start: datetime | None = None
    archived_events: int = 0
    confirmed_registrations: int = 0
    attendance_marked_pct: float = 0.0
    no_show_rate_pct: float = 0.0
    certificate_issuance_pct: float = 0.0


class ClubAnalyticsOut(BaseModel):
    club_id: str
    total_members: int = 0
    active_members: int = 0
    inactive_members: int = 0
    membership_growth_30d: int = 0
    retained_members_90d: int = 0
    departed_members_90d: int = 0
    member_retention_pct_90d: float = 0.0
    member_churn_rate_pct_90d: float = 0.0
    members_with_event_participation: int = 0
    members_with_present_attendance: int = 0
    member_event_conversion_pct: float = 0.0
    member_attendance_conversion_pct: float = 0.0
    recently_engaged_active_members_90d: int = 0
    at_risk_active_members_90d: int = 0
    total_events: int = 0
    upcoming_events: int = 0
    completed_events: int = 0
    average_attendance_pct: float = 0.0
    pending_applications: int = 0
    waitlisted_applications: int = 0
    confirmed_event_registrations: int = 0
    pending_event_registrations: int = 0
    waitlisted_event_registrations: int = 0
    events_at_capacity: int = 0
    attendance_marked_registrations: int = 0
    attendance_marked_pct: float = 0.0
    present_attendance_count: int = 0
    absent_attendance_count: int = 0
    no_show_rate_pct: float = 0.0
    certificate_enabled_events: int = 0
    certificate_eligible_registrations: int = 0
    certificates_issued: int = 0
    certificate_issuance_pct: float = 0.0
    waitlist_pressure_events: int = 0
    archived_events: int = 0
    archived_confirmed_registrations: int = 0
    archived_attendance_marked_pct: float = 0.0
    archived_no_show_rate_pct: float = 0.0
    archived_certificates_issued: int = 0
    archived_certificate_issuance_pct: float = 0.0
    paid_events_count: int = 0
    free_events_count: int = 0
    paid_confirmed_registrations: int = 0
    payment_proof_submitted_count: int = 0
    payment_proof_coverage_pct: float = 0.0
    listed_paid_revenue_inr: float = 0.0
    sponsorship_target_amount: float = 0.0
    sponsorship_committed_amount: float = 0.0
    sponsorship_gap_amount: float = 0.0
    sponsorship_progress_pct: float = 0.0
    event_performance: list[ClubEventPerformanceOut] = Field(default_factory=list)
    trend_summaries: list[ClubTrendSummaryOut] = Field(default_factory=list)
    recent_event_trends: list[ClubEventTrendPointOut] = Field(default_factory=list)
    repeat_attention_events: int = 0
    archive_season_summaries: list[ClubArchiveSeasonSummaryOut] = Field(default_factory=list)
    archive_event_cohorts: list[ClubArchiveCohortOut] = Field(default_factory=list)
    archival_history_points: list[ClubArchivalHistoryPointOut] = Field(default_factory=list)
