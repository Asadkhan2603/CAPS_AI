from datetime import datetime

from pydantic import BaseModel, Field


class SectionSubjectCreate(BaseModel):
    section_id: str = Field(min_length=1)
    subject_id: str = Field(min_length=1)
    teacher_user_id: str | None = None


class SectionSubjectUpdate(BaseModel):
    teacher_user_id: str | None = None
    is_active: bool | None = None


class SectionSubjectOut(BaseModel):
    id: str
    section_id: str
    subject_id: str
    teacher_user_id: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
