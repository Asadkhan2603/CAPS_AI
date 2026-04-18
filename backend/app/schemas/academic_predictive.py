from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.student_intervention import StudentInterventionOut


PredictiveRiskLevel = Literal["low", "moderate", "high", "critical"]


class PredictiveEvidenceOut(BaseModel):
    label: str
    value: Any | None = None


class StaffingForecastItemOut(BaseModel):
    section_id: str
    section_name: str
    batch_id: str | None = None
    batch_name: str | None = None
    semester_id: str | None = None
    semester_label: str | None = None
    teacher_user_id: str | None = None
    teacher_name: str | None = None
    risk_level: PredictiveRiskLevel = "low"
    risk_score: int = 0
    reason_codes: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    suggested_action: str | None = None
    evidence: list[PredictiveEvidenceOut] = Field(default_factory=list)


class StudentRiskForecastItemOut(BaseModel):
    student_id: str
    student_name: str
    roll_number: str | None = None
    student_user_id: str | None = None
    section_id: str
    section_name: str
    batch_id: str | None = None
    batch_name: str | None = None
    semester_id: str | None = None
    semester_label: str | None = None
    risk_level: PredictiveRiskLevel = "low"
    risk_score: int = 0
    reason_codes: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    suggested_action: str | None = None
    evidence: list[PredictiveEvidenceOut] = Field(default_factory=list)
    latest_intervention: StudentInterventionOut | None = None


class SectionRiskSummaryItemOut(BaseModel):
    section_id: str
    section_name: str
    batch_id: str | None = None
    batch_name: str | None = None
    semester_id: str | None = None
    semester_label: str | None = None
    risk_level: PredictiveRiskLevel = "low"
    risk_score: int = 0
    total_students: int = 0
    at_risk_students: int = 0
    staffing_pressure: bool = False
    timetable_drift: int = 0
    shortage_risk_count: int = 0
    unreleased_evaluation_count: int = 0
    reason_codes: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    suggested_action: str | None = None


class StaffingForecastResponseOut(BaseModel):
    generated_at: datetime
    summary: dict[str, int] = Field(default_factory=dict)
    items: list[StaffingForecastItemOut] = Field(default_factory=list)


class StudentRiskForecastResponseOut(BaseModel):
    generated_at: datetime
    summary: dict[str, int] = Field(default_factory=dict)
    items: list[StudentRiskForecastItemOut] = Field(default_factory=list)


class SectionRiskSummaryResponseOut(BaseModel):
    generated_at: datetime
    summary: dict[str, int] = Field(default_factory=dict)
    items: list[SectionRiskSummaryItemOut] = Field(default_factory=list)


class PredictiveOverviewOut(BaseModel):
    generated_at: datetime
    summary: dict[str, int] = Field(default_factory=dict)
    staffing_forecast: list[StaffingForecastItemOut] = Field(default_factory=list)
    student_risk: list[StudentRiskForecastItemOut] = Field(default_factory=list)
    section_risk: list[SectionRiskSummaryItemOut] = Field(default_factory=list)
    intervention_queue: list[StudentRiskForecastItemOut] = Field(default_factory=list)
