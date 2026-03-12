from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

AssignmentStatus = Literal["open", "closed"]


class AssignmentCreate(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    subject_id: str | None = None
    class_id: str | None = None
    due_date: datetime | None = None
    total_marks: float = Field(default=100, ge=1, le=1000)
    status: AssignmentStatus = "open"
    plagiarism_enabled: bool = True


class AssignmentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    subject_id: str | None = None
    class_id: str | None = None
    due_date: datetime | None = None
    total_marks: float | None = Field(default=None, ge=1, le=1000)
    status: AssignmentStatus | None = None
    plagiarism_enabled: bool | None = None


class AssignmentOut(BaseModel):
    id: str
    title: str
    description: str | None = None
    subject_id: str | None = None
    class_id: str | None = None
    due_date: datetime | None = None
    total_marks: float = 100.0
    status: AssignmentStatus = "open"
    plagiarism_enabled: bool = True
    created_by: str | None = None
    created_at: datetime | None = None
    schema_version: int = 1


class AssignmentPlagiarismToggle(BaseModel):
    plagiarism_enabled: bool
