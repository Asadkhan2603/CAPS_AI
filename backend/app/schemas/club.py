from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ClubStatus = Literal["draft", "active", "closed", "suspended", "archived"]
ClubMembershipType = Literal["open", "approval_required"]
ClubMemberRole = Literal["member", "president", "vice_president", "core_member"]
ClubMemberStatus = Literal["active", "inactive", "removed"]
ClubApplicationStatus = Literal["pending", "approved", "rejected"]


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


class ClubOut(BaseModel):
    id: str
    name: str
    slug: str | None = None
    description: str | None = None
    category: str | None = None
    department_id: str | None = None
    academic_year: str | None = None
    coordinator_user_id: str | None = None
    coordinator_name: str | None = None
    coordinator_email: str | None = None
    president_user_id: str | None = None
    president_name: str | None = None
    president_email: str | None = None
    status: ClubStatus = "draft"
    registration_open: bool = False
    membership_type: ClubMembershipType = "approval_required"
    max_members: int | None = None
    member_count: int = 0
    logo_url: str | None = None
    banner_url: str | None = None
    created_by: str | None = None
    updated_at: datetime | None = None
    archived_at: datetime | None = None
    is_active: bool = True
    created_at: datetime | None = None


class ClubMembershipOut(BaseModel):
    id: str
    club_id: str
    student_user_id: str
    student_name: str | None = None
    student_email: str | None = None
    role: ClubMemberRole = "member"
    status: ClubMemberStatus = "active"
    joined_at: datetime | None = None
    left_at: datetime | None = None


class ClubMembershipUpdate(BaseModel):
    role: ClubMemberRole | None = None
    status: ClubMemberStatus | None = None


class ClubApplicationOut(BaseModel):
    id: str
    club_id: str
    student_user_id: str
    student_name: str | None = None
    student_email: str | None = None
    status: ClubApplicationStatus = "pending"
    applied_at: datetime | None = None
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None


class ClubApplicationReview(BaseModel):
    status: Literal["approved", "rejected"]


class ClubAnalyticsOut(BaseModel):
    club_id: str
    total_members: int = 0
    active_members: int = 0
    inactive_members: int = 0
    membership_growth_30d: int = 0
    total_events: int = 0
    upcoming_events: int = 0
    completed_events: int = 0
    average_attendance_pct: float = 0.0
    pending_applications: int = 0
