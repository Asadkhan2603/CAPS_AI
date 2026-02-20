from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

EventStatus = Literal["open", "closed", "archived"]


class ClubEventCreate(BaseModel):
    club_id: str = Field(min_length=1)
    title: str = Field(min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    event_date: datetime | None = None
    capacity: int = Field(default=100, ge=1, le=5000)


class ClubEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = Field(default=None, max_length=1000)
    event_date: datetime | None = None
    capacity: int | None = Field(default=None, ge=1, le=5000)
    status: EventStatus | None = None
    result_summary: str | None = Field(default=None, max_length=2000)


class ClubEventOut(BaseModel):
    id: str
    club_id: str
    title: str
    description: str | None = None
    event_date: datetime | None = None
    capacity: int
    status: EventStatus = "open"
    result_summary: str | None = None
    created_by: str | None = None
    created_at: datetime | None = None
