from datetime import datetime

from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    roll_number: str = Field(min_length=1, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    class_id: str | None = None


class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    roll_number: str | None = Field(default=None, min_length=1, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    class_id: str | None = None
    is_active: bool | None = None


class StudentOut(BaseModel):
    id: str
    full_name: str
    roll_number: str
    email: str | None = None
    class_id: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
