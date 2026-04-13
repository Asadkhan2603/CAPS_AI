from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.evaluation import RubricCriterion


class AIChatEvaluateRequest(BaseModel):
    teacher_id: str | None = None
    student_id: str
    exam_id: str
    question_id: str | None = None
    teacher_message: str = Field(min_length=1, max_length=2000)
    question_text: str | None = Field(default=None, max_length=4000)
    student_answer: str | None = None
    rubric: str | None = Field(default=None, max_length=4000)
    rubric_criteria: list[RubricCriterion] = Field(default_factory=list)
    submission_id: str | None = None


class AIChatMessageOut(BaseModel):
    role: str
    content: str
    timestamp: datetime
    question_id: str | None = None
    provider_error: str | None = None
    provider: str | None = None
    prompt_version: str | None = None
    runtime_snapshot: dict | None = None


class AIChatThreadOut(BaseModel):
    id: str
    teacher_id: str
    student_id: str
    exam_id: str
    question_id: str | None = None
    messages: list[AIChatMessageOut]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AIChatEvaluateResponse(BaseModel):
    thread: AIChatThreadOut
    ai_response: str
