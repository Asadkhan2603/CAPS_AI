from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EventStatus = Literal["draft", "open", "closed", "completed", "archived"]
EventType = Literal["workshop", "competition", "seminar", "cultural", "internal"]
EventVisibility = Literal["public", "members_only"]


class ClubEventCreate(BaseModel):
    club_id: str = Field(min_length=1)
    title: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    event_type: EventType = "workshop"
    visibility: EventVisibility = "public"
    registration_start: datetime | None = None
    registration_end: datetime | None = None
    event_date: datetime | None = None
    capacity: int = Field(default=100, ge=1, le=5000)
    registration_enabled: bool = True
    approval_required: bool = False
    payment_required: bool = False
    payment_qr_image_url: str | None = Field(default=None, max_length=1200)
    payment_amount: float | None = Field(default=None, ge=0)
    certificate_enabled: bool = False


class ClubEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    event_type: EventType | None = None
    visibility: EventVisibility | None = None
    registration_start: datetime | None = None
    registration_end: datetime | None = None
    event_date: datetime | None = None
    capacity: int | None = Field(default=None, ge=1, le=5000)
    registration_enabled: bool | None = None
    approval_required: bool | None = None
    payment_required: bool | None = None
    payment_qr_image_url: str | None = Field(default=None, max_length=1200)
    payment_amount: float | None = Field(default=None, ge=0)
    certificate_enabled: bool | None = None
    status: EventStatus | None = None
    result_summary: str | None = Field(default=None, max_length=2000)


class ClubEventOut(BaseModel):
    id: str
    club_id: str
    title: str
    description: str | None = None
    event_type: EventType = "workshop"
    visibility: EventVisibility = "public"
    registration_start: datetime | None = None
    registration_end: datetime | None = None
    event_date: datetime | None = None
    capacity: int
    registration_enabled: bool = True
    approval_required: bool = False
    payment_required: bool = False
    payment_qr_image_url: str | None = None
    payment_amount: float | None = None
    certificate_enabled: bool = False
    status: EventStatus = "draft"
    result_summary: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
    schema_version: int = 1
