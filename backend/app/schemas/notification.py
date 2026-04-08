from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.communication_delivery import DeliverySummary


class NotificationCreate(BaseModel):
    title: str = Field(min_length=2, max_length=140)
    message: str = Field(min_length=2, max_length=1000)
    priority: str = Field(default="normal", max_length=20)
    scope: str = Field(default="global", max_length=40)
    target_user_id: str | None = None


class NotificationOut(BaseModel):
    id: str
    public_id: str | None = None
    display_label: str | None = None
    title: str
    message: str
    priority: str
    scope: str
    target_user_id: str | None = None
    target_user_label: str | None = None
    created_by: str | None = None
    created_by_label: str | None = None
    is_read: bool = False
    delivery_summary: DeliverySummary = Field(default_factory=DeliverySummary)
    created_at: datetime | None = None
    schema_version: int = 1
