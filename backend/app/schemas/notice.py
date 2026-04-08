from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.communication_delivery import DeliverySummary

NoticePriority = Literal['normal', 'urgent']
NoticeScope = Literal['college', 'batch', 'class', 'section', 'subject', 'club']


class NoticeCreate(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    message: str = Field(min_length=2, max_length=2000)
    priority: NoticePriority = 'normal'
    scope: NoticeScope = 'college'
    scope_ref_id: str | None = None
    expires_at: datetime | None = None
    is_pinned: bool = False
    template_key: str | None = Field(default=None, max_length=80)


class NoticeUpdate(BaseModel):
    is_pinned: bool | None = None


class NoticeFileOut(BaseModel):
    url: str
    public_id: str
    name: str
    size: int
    mime_type: str | None = None


class NoticeOut(BaseModel):
    id: str
    title: str
    message: str
    priority: NoticePriority = 'normal'
    scope: NoticeScope = 'college'
    scope_ref_id: str | None = None
    expires_at: datetime | None = None
    images: list[NoticeFileOut] = Field(default_factory=list)
    is_pinned: bool = False
    template_key: str | None = None
    scheduled_at: datetime | None = None
    read_count: int = 0
    seen_by: list[str] = Field(default_factory=list)
    is_read: bool = False
    fanout_status: str = 'queued'
    fanout_attempts: int = 0
    fanout_last_attempt_at: datetime | None = None
    fanout_next_retry_at: datetime | None = None
    fanout_count: int = 0
    fanout_dispatched_at: datetime | None = None
    fanout_failed_at: datetime | None = None
    fanout_error: str | None = None
    delivery_summary: DeliverySummary = Field(default_factory=DeliverySummary)
    created_by: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    schema_version: int = 1


class NoticeReadBatchRequest(BaseModel):
    notice_ids: list[str] = Field(default_factory=list)
