from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

NoticePriority = Literal["normal", "urgent"]
NoticeScope = Literal["college", "year", "class", "subject"]


class NoticeCreate(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    message: str = Field(min_length=2, max_length=2000)
    priority: NoticePriority = "normal"
    scope: NoticeScope = "college"
    scope_ref_id: str | None = None
    expires_at: datetime | None = None


class NoticeOut(BaseModel):
    id: str
    title: str
    message: str
    priority: NoticePriority = "normal"
    scope: NoticeScope = "college"
    scope_ref_id: str | None = None
    expires_at: datetime | None = None
    created_by: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
