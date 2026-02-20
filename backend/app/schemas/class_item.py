from datetime import datetime

from pydantic import BaseModel, Field


class ClassCreate(BaseModel):
    course_id: str = Field(min_length=1)
    year_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=100)
    faculty_name: str | None = Field(default=None, max_length=120)
    branch_name: str | None = Field(default=None, max_length=120)
    class_coordinator_user_id: str | None = None


class ClassUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    faculty_name: str | None = Field(default=None, max_length=120)
    branch_name: str | None = Field(default=None, max_length=120)
    class_coordinator_user_id: str | None = None
    is_active: bool | None = None


class ClassOut(BaseModel):
    id: str
    course_id: str
    year_id: str
    name: str
    faculty_name: str | None = None
    branch_name: str | None = None
    class_coordinator_user_id: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
