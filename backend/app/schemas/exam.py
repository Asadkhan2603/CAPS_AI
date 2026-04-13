from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ExamStatus = Literal["draft", "scheduled", "completed", "cancelled"]
ExamType = Literal["quiz", "midterm", "final", "practical", "viva", "internal"]


class ExamCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=1000)
    subject_id: str | None = None
    batch_id: str | None = None
    semester_id: str | None = None
    section_id: str | None = None
    assignment_id: str | None = None
    teacher_user_id: str | None = None
    exam_type: ExamType = "internal"
    scheduled_for: datetime | None = None
    duration_minutes: int = Field(default=60, ge=15, le=600)
    room_code: str | None = Field(default=None, max_length=50)
    max_marks: float = Field(default=100, ge=1, le=1000)
    status: ExamStatus = "draft"


class ExamUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    code: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=1000)
    subject_id: str | None = None
    batch_id: str | None = None
    semester_id: str | None = None
    section_id: str | None = None
    assignment_id: str | None = None
    teacher_user_id: str | None = None
    exam_type: ExamType | None = None
    scheduled_for: datetime | None = None
    duration_minutes: int | None = Field(default=None, ge=15, le=600)
    room_code: str | None = Field(default=None, max_length=50)
    max_marks: float | None = Field(default=None, ge=1, le=1000)
    status: ExamStatus | None = None
    is_active: bool | None = None


class ExamOut(BaseModel):
    id: str
    public_id: str | None = None
    display_label: str | None = None
    title: str
    code: str | None = None
    description: str | None = None
    subject_id: str | None = None
    batch_id: str | None = None
    semester_id: str | None = None
    section_id: str | None = None
    assignment_id: str | None = None
    teacher_user_id: str | None = None
    exam_type: ExamType = "internal"
    scheduled_for: datetime | None = None
    duration_minutes: int = 60
    room_code: str | None = None
    max_marks: float = 100
    status: ExamStatus = "draft"
    created_by: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None
    schema_version: int = 1
