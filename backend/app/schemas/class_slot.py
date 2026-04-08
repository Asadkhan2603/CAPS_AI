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
    public_id: str | None = None
    display_label: str | None = None
    course_offering_id: str
    subject_id: str | None = None
    teacher_user_id: str | None = None
    batch_id: str | None = None
    semester_id: str | None = None
    section_id: str | None = None
    group_id: str | None = None
    academic_year: str | None = None
    offering_type: str | None = None
    day: DayName
    start_time: str
    end_time: str
    room_code: str
    subject_name: str | None = None
    subject_code: str | None = None
    teacher_name: str | None = None
    batch_name: str | None = None
    section_name: str | None = None
    group_name: str | None = None
    semester_label: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    schema_version: int = 1
