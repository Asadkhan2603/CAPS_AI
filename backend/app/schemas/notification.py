from datetime import datetime

from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    message: str = Field(min_length=2, max_length=1000)
    priority: str = Field(default="normal", max_length=20)
    scope: str = Field(default="global", max_length=40)
    target_user_id: str | None = None


class NotificationOut(BaseModel):
    id: str
    title: str
    message: str
    priority: str
    scope: str
    target_user_id: str | None = None
    created_by: str | None = None
    is_read: bool = False
    created_at: datetime | None = None
    schema_version: int = 1
