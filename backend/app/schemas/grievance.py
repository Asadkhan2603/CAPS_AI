from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

GrievanceStage = Literal["coordinator", "hod", "dean"]
GrievanceStatus = Literal["open", "in_progress", "resolved", "reopened", "routing_failed"]
GrievanceTimelineVisibility = Literal["public", "internal"]
GrievanceTimelineKind = Literal[
    "submitted",
    "public_comment",
    "internal_note",
    "forwarded",
    "escalated",
    "resolved",
    "reopened",
    "routing_failed",
    "status_changed",
]
GrievanceManageStatus = Literal["in_progress", "resolved"]
GrievanceInboxView = Literal["coordinator", "hod", "dean", "assigned", "fallback"]


class GrievanceTimelineEntryOut(BaseModel):
    entry_id: str
    kind: GrievanceTimelineKind
    visibility: GrievanceTimelineVisibility = "public"
    message: str
    stage: GrievanceStage | None = None
    actor_user_id: str | None = None
    actor_label: str | None = None
    forwarded_to_user_id: str | None = None
    forwarded_to_label: str | None = None
    created_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class GrievanceCommentCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class GrievanceInternalNoteCreate(BaseModel):
    message: str = Field(min_length=1, max_length=2000)


class GrievanceForwardCreate(BaseModel):
    target_user_id: str = Field(min_length=1)
    note: str | None = Field(default=None, max_length=1000)


class GrievanceStatusUpdate(BaseModel):
    status: GrievanceManageStatus
    resolution_note: str | None = Field(default=None, max_length=2000)


class GrievanceReopenCreate(BaseModel):
    message: str | None = Field(default=None, max_length=2000)


class GrievanceOut(BaseModel):
    id: str
    public_id: str | None = None
    display_label: str | None = None
    category: str
    title: str
    description: str
    student_user_id: str
    student_id: str | None = None
    student_label: str | None = None
    section_id: str | None = None
    section_name: str | None = None
    department_id: str | None = None
    department_name: str | None = None
    current_stage: GrievanceStage
    status: GrievanceStatus
    stage_due_at: datetime | None = None
    resolved_at: datetime | None = None
    resolved_by_user_id: str | None = None
    resolved_by_label: str | None = None
    assigned_resolver_user_id: str | None = None
    assigned_resolver_label: str | None = None
    forwarded_by_user_id: str | None = None
    forwarded_by_label: str | None = None
    forwarded_at: datetime | None = None
    attachment_filename: str | None = None
    attachment_mime_type: str | None = None
    attachment_size_bytes: int | None = None
    attachment_url: str | None = None
    is_overdue: bool = False
    created_at: datetime | None = None
    schema_version: int = 1
    timeline: list[GrievanceTimelineEntryOut] = Field(default_factory=list)
