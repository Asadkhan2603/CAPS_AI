from datetime import datetime

from pydantic import BaseModel, Field


class SectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    program: str = Field(min_length=1, max_length=120)
    academic_year: str = Field(min_length=4, max_length=20)
    semester: int = Field(ge=1, le=12)


class SectionUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    program: str | None = Field(default=None, min_length=1, max_length=120)
    academic_year: str | None = Field(default=None, min_length=4, max_length=20)
    semester: int | None = Field(default=None, ge=1, le=12)
    is_active: bool | None = None


class SectionOut(BaseModel):
    id: str
    name: str
    program: str
    academic_year: str
    semester: int
    is_active: bool = True
    created_at: datetime | None = None
