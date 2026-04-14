from datetime import datetime

from pydantic import BaseModel, Field


class SubmissionOut(BaseModel):
    id: str
    public_id: str | None = None
    display_label: str | None = None
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
    ai_prompt_version: str | None = None
    ai_runtime_snapshot: dict | None = None
    schema_version: int = 1
    similarity_score: float | None = None
    extracted_text: str | None = None
    extraction_quality: float | None = Field(default=None, ge=0, le=1)
    ocr_attempted: bool | None = None
    ocr_provider: str | None = None
    ocr_chars_added: int | None = None
    page_count: int | None = None
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    low_text_reason: str | None = None
    ocr_result_state: str | None = None
    ocr_retry_count: int | None = None
    ocr_timeout_seconds: int | None = None
    ocr_error: str | None = None
    ocr_retry_guidance: str | None = None
    created_at: datetime | None = None


class SubmissionUpdate(BaseModel):
    notes: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=50)
    ai_status: str | None = Field(default=None, max_length=50)
    ai_score: float | None = Field(default=None, ge=0, le=10)
    ai_feedback: str | None = Field(default=None, max_length=2000)
    ai_provider: str | None = Field(default=None, max_length=100)
    ai_error: str | None = Field(default=None, max_length=500)
    ai_prompt_version: str | None = Field(default=None, max_length=100)
    similarity_score: float | None = Field(default=None, ge=0, le=1)
