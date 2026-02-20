from datetime import datetime

from pydantic import BaseModel, Field


class EnrollmentCreate(BaseModel):
    class_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)


class EnrollmentOut(BaseModel):
    id: str
    class_id: str
    student_id: str
    assigned_by_user_id: str
    created_at: datetime | None = None
