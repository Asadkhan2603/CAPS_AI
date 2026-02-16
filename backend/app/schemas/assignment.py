from datetime import datetime

from pydantic import BaseModel, Field


class AssignmentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    subject_id: str | None = None
    section_id: str | None = None
    due_date: datetime | None = None
    total_marks: float = Field(default=100, ge=1, le=1000)


class AssignmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    subject_id: str | None = None
    section_id: str | None = None
    due_date: datetime | None = None
    total_marks: float | None = Field(default=None, ge=1, le=1000)


class AssignmentOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    subject_id: str | None = None
    section_id: str | None = None
    due_date: datetime | None = None
    total_marks: float = 100.0
    created_by: str | None = None
    created_at: datetime | None = None
