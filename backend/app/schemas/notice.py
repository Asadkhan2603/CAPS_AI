from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

NoticePriority = Literal['normal', 'urgent']
NoticeScope = Literal['college', 'year', 'class', 'section', 'subject']


class NoticeCreate(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    message: str = Field(min_length=2, max_length=2000)
    priority: NoticePriority = 'normal'
    scope: NoticeScope = 'college'
    scope_ref_id: str | None = None
    expires_at: datetime | None = None


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
    created_by: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
