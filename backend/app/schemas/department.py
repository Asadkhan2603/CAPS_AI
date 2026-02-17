from datetime import datetime

from pydantic import BaseModel, Field


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=60)
    university_name: str | None = Field(default=None, max_length=150)
    university_code: str | None = Field(default=None, max_length=60)


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    code: str | None = Field(default=None, min_length=2, max_length=60)
    university_name: str | None = Field(default=None, max_length=150)
    university_code: str | None = Field(default=None, max_length=60)
    is_active: bool | None = None


class DepartmentOut(BaseModel):
    id: str
    name: str
    code: str
    university_name: str | None = None
    university_code: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
