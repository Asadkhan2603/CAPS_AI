from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


InterventionStatus = Literal["open", "in_progress", "resolved"]
InterventionRiskLevel = Literal["critical", "attention"]


class StudentInterventionCreate(BaseModel):
    student_id: str = Field(min_length=1, max_length=64)
    section_id: str = Field(min_length=1, max_length=64)
    risk_level: InterventionRiskLevel
    note: str = Field(min_length=4, max_length=1500)
    due_date: datetime | None = None
    reason_summary: list[str] = Field(default_factory=list, max_length=10)


class StudentInterventionUpdate(BaseModel):
    status: InterventionStatus
    note: str | None = Field(default=None, max_length=1500)
    due_date: datetime | None = None
    resolution_note: str | None = Field(default=None, max_length=1500)


class StudentInterventionOut(BaseModel):
    id: str
    student_id: str
    student_name: str | None = None
    section_id: str
    section_name: str | None = None
    risk_level: InterventionRiskLevel
    status: InterventionStatus = "open"
    note: str | None = None
    due_date: datetime | None = None
    created_by_user_id: str | None = None
    created_by_name: str | None = None
    owner_user_id: str | None = None
    owner_name: str | None = None
    resolution_note: str | None = None
    resolved_at: datetime | None = None
    resolved_by_user_id: str | None = None
    resolved_by_name: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    reason_summary: list[str] = Field(default_factory=list)
    schema_version: int = 1
