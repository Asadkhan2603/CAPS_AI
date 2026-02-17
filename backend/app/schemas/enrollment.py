from datetime import datetime

from pydantic import BaseModel, Field


class EnrollmentCreate(BaseModel):
    class_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    section_id: str | None = None


class EnrollmentOut(BaseModel):
    id: str
    class_id: str
    student_id: str
    section_id: str | None = None
    assigned_by_user_id: str
    created_at: datetime | None = None
