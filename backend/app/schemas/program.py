from datetime import datetime

from pydantic import BaseModel, Field


class ProgramCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=30)
    department_id: str = Field(min_length=1)
    duration_years: int
    description: str | None = Field(default=None, max_length=500)


class ProgramUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=30)
    department_id: str | None = Field(default=None, min_length=1)
    duration_years: int | None = None
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class ProgramOut(BaseModel):
    id: str
    name: str
    code: str
    department_id: str
    duration_years: int
    total_semesters: int
    description: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
