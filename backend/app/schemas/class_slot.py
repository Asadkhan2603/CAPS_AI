from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


DayName = Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]


class ClassSlotCreate(BaseModel):
    course_offering_id: str = Field(min_length=1)
    day: DayName
    start_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    end_time: str = Field(pattern=r"^\d{2}:\d{2}$")
    room_code: str = Field(min_length=1, max_length=80)


class ClassSlotUpdate(BaseModel):
    day: DayName | None = None
    start_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    end_time: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    room_code: str | None = Field(default=None, min_length=1, max_length=80)
    is_active: bool | None = None


class ClassSlotOut(BaseModel):
    id: str
    course_offering_id: str
    day: DayName
    start_time: str
    end_time: str
    room_code: str
    is_active: bool = True
    created_at: datetime | None = None
    schema_version: int = 1
