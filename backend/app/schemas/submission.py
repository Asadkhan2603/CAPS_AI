from datetime import datetime

from pydantic import BaseModel, Field


class SubmissionOut(BaseModel):
    id: str
    assignment_id: str
    student_user_id: str
    original_filename: str
    stored_filename: str
    file_mime_type: str | None = None
    file_size_bytes: int = 0
    notes: str | None = None
    status: str = 'submitted'
    ai_status: str = 'pending'
    ai_score: float | None = None
    ai_feedback: str | None = None
    ai_provider: str | None = None
    ai_error: str | None = None
    similarity_score: float | None = None
    extracted_text: str | None = None
    created_at: datetime | None = None


class SubmissionUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=50)
    ai_status: str | None = Field(default=None, max_length=50)
    ai_score: float | None = Field(default=None, ge=0, le=10)
    ai_feedback: str | None = Field(default=None, max_length=2000)
    ai_provider: str | None = Field(default=None, max_length=100)
    ai_error: str | None = Field(default=None, max_length=500)
    similarity_score: float | None = Field(default=None, ge=0, le=1)
