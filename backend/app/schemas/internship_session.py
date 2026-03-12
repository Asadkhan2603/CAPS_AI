from datetime import datetime

from pydantic import BaseModel, Field


class InternshipClockInRequest(BaseModel):
    note: str | None = Field(default=None, max_length=300)


class InternshipClockOutRequest(BaseModel):
    note: str | None = Field(default=None, max_length=300)


class InternshipSessionOut(BaseModel):
    id: str
    student_user_id: str
    student_id: str
    status: str
    clock_in_at: datetime
    clock_out_at: datetime | None = None
    total_minutes: int | None = None
    auto_closed: bool = False
    note: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    schema_version: int = 1
