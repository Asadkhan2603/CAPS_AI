from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class GovernancePolicyUpdate(BaseModel):
    two_person_rule_enabled: bool | None = None
    role_change_approval_enabled: bool | None = None
    retention_days_audit: int | None = Field(default=None, ge=30, le=3650)
    retention_days_sessions: int | None = Field(default=None, ge=7, le=3650)


class AdminActionReviewCreate(BaseModel):
    review_type: str = Field(pattern="^(destructive|role_change)$")
    action: str = Field(min_length=2, max_length=100)
    entity_type: str = Field(min_length=2, max_length=100)
    entity_id: str | None = Field(default=None, min_length=3, max_length=128)
    reason: str | None = Field(default=None, max_length=500)
    metadata: dict | None = None


class AdminActionReviewDecision(BaseModel):
    approve: bool
    note: str | None = Field(default=None, max_length=500)


class AdminActionReviewOut(BaseModel):
    id: str
    review_type: str
    action: str
    entity_type: str
    entity_id: str | None = None
    reason: str | None = None
    status: str
    requested_by: str
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    executed_by: str | None = None
    executed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    schema_version: int = 1


class UserSessionOut(BaseModel):
    id: str
    user_id: str | None = None
    user_name: str | None = None
    user_email: str | None = None
    fingerprint: str | None = None
    ip_address: str | None = None
    last_seen_ip: str | None = None
    user_agent: str | None = None
    created_at: datetime | None = None
    last_seen_at: datetime | None = None
    rotated_at: datetime | None = None
    revoked_at: datetime | None = None
    status: str
    schema_version: int = 1
