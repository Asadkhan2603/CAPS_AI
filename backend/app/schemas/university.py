from datetime import datetime

from pydantic import BaseModel, Field


class UniversityCreate(BaseModel):
    university_id: str = Field(min_length=1, max_length=60)
    university_name: str = Field(min_length=2, max_length=200)


class UniversityUpdate(BaseModel):
    university_id: str | None = Field(default=None, min_length=1, max_length=60)
    university_name: str | None = Field(default=None, min_length=2, max_length=200)
    is_active: bool | None = None


class UniversityOut(BaseModel):
    id: str
    university_id: str
    university_name: str
    is_active: bool = True
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    created_at: datetime | None = None
    schema_version: int = 1
