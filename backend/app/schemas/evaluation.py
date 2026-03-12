from datetime import datetime

from pydantic import BaseModel, Field


class EvaluationAIInsight(BaseModel):
    summary: str
    strengths: list[str] = []
    gaps: list[str] = []
    suggestions: list[str] = []
    risk_flags: list[str] = []
    confidence: float = Field(ge=0, le=1)
    status: str = "fallback"
    provider: str | None = None
    prompt_version: str | None = None
    runtime_snapshot: dict | None = None


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


class EvaluationAIPreviewRequest(BaseModel):
    submission_id: str = Field(min_length=1)
    attendance_percent: int = Field(ge=0, le=100)
    skill: float = Field(ge=0, le=2.5)
    behavior: float = Field(ge=0, le=2.5)
    report: float = Field(ge=0, le=10)
    viva: float = Field(ge=0, le=20)
    final_exam: int = Field(ge=0, le=60)
    remarks: str | None = Field(default=None, max_length=1000)


class EvaluationAIPreviewOut(BaseModel):
    submission_id: str
    internal_total: float
    grand_total: float
    grade: str
    ai_score: float | None = None
    ai_feedback: str | None = None
    ai_insight: EvaluationAIInsight


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
    ai_status: str | None = None
    ai_provider: str | None = None
    ai_prompt_version: str | None = None
    ai_runtime_snapshot: dict | None = None
    schema_version: int = 1
    ai_confidence: float | None = Field(default=None, ge=0, le=1)
    ai_risk_flags: list[str] = []
    ai_strengths: list[str] = []
    ai_gaps: list[str] = []
    ai_suggestions: list[str] = []
    remarks: str | None = None
    is_finalized: bool = False
    finalized_at: datetime | None = None
    finalized_by_user_id: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
