from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


OfferingType = Literal["theory", "lab", "elective", "workshop", "club", "interaction"]


class CourseOfferingCreate(BaseModel):
    subject_id: str = Field(min_length=1)
    teacher_user_id: str = Field(min_length=1)
    batch_id: str = Field(min_length=1)
    semester_id: str = Field(min_length=1)
    section_id: str = Field(min_length=1)
    group_id: str | None = None
    academic_year: str = Field(min_length=4, max_length=20)
    offering_type: OfferingType = "theory"


class CourseOfferingUpdate(BaseModel):
    subject_id: str | None = Field(default=None, min_length=1)
    teacher_user_id: str | None = Field(default=None, min_length=1)
    batch_id: str | None = Field(default=None, min_length=1)
    semester_id: str | None = Field(default=None, min_length=1)
    section_id: str | None = Field(default=None, min_length=1)
    group_id: str | None = None
    academic_year: str | None = Field(default=None, min_length=4, max_length=20)
    offering_type: OfferingType | None = None
    is_active: bool | None = None


class CourseOfferingOut(BaseModel):
    id: str
    subject_id: str
    teacher_user_id: str
    batch_id: str
    semester_id: str
    section_id: str
    group_id: str | None = None
    academic_year: str
    offering_type: OfferingType
    subject_name: str | None = None
    subject_code: str | None = None
    teacher_name: str | None = None
    section_name: str | None = None
    group_name: str | None = None
    semester_label: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
