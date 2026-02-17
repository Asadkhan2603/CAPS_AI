from datetime import datetime

from pydantic import BaseModel, Field


class EvaluationCreate(BaseModel):
    submission_id: str = Field(min_length=1)
    attendance_percent: int = Field(ge=0, le=100)
    skill: float = Field(ge=0, le=2.5)
    behavior: float = Field(ge=0, le=2.5)
    report: float = Field(ge=0, le=10)
    viva: float = Field(ge=0, le=20)
    final_exam: int = Field(ge=0, le=60)
    remarks: str | None = Field(default=None, max_length=1000)
    is_finalized: bool = False


class EvaluationUpdate(BaseModel):
    attendance_percent: int | None = Field(default=None, ge=0, le=100)
    skill: float | None = Field(default=None, ge=0, le=2.5)
    behavior: float | None = Field(default=None, ge=0, le=2.5)
    report: float | None = Field(default=None, ge=0, le=10)
    viva: float | None = Field(default=None, ge=0, le=20)
    final_exam: int | None = Field(default=None, ge=0, le=60)
    remarks: str | None = Field(default=None, max_length=1000)
    is_finalized: bool | None = None


class EvaluationOut(BaseModel):
    id: str
    submission_id: str
    student_user_id: str
    teacher_user_id: str
    attendance_percent: int
    skill: float
    behavior: float
    report: float
    viva: float
    final_exam: int
    internal_total: float
    grand_total: float
    grade: str
    ai_score: float | None = None
    ai_feedback: str | None = None
    remarks: str | None = None
    is_finalized: bool = False
    created_at: datetime | None = None
