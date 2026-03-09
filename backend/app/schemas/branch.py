from datetime import datetime

from pydantic import BaseModel, Field


class BranchCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=120)
    department_code: str = Field(min_length=2, max_length=60)
    university_name: str | None = Field(default=None, max_length=150)
    university_code: str | None = Field(default=None, max_length=60)


class BranchUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    code: str | None = Field(default=None, min_length=2, max_length=120)
    department_code: str | None = Field(default=None, min_length=2, max_length=60)
    university_name: str | None = Field(default=None, max_length=150)
    university_code: str | None = Field(default=None, max_length=60)
    is_active: bool | None = None


class BranchOut(BaseModel):
    id: str
    name: str
    code: str
    department_name: str | None = None
    department_code: str | None = None
    university_name: str | None = None
    university_code: str | None = None
    is_active: bool = True
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    created_at: datetime | None = None
