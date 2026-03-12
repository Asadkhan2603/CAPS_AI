from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AttendanceStatus = Literal["present", "absent", "late", "excused"]


class AttendanceRecordCreate(BaseModel):
    class_slot_id: str = Field(min_length=1)
    student_id: str = Field(min_length=1)
    status: AttendanceStatus
    note: str | None = Field(default=None, max_length=300)


class AttendanceRecordBulkCreate(BaseModel):
    class_slot_id: str = Field(min_length=1)
    records: list[AttendanceRecordCreate] = Field(default_factory=list)


class AttendanceRecordOut(BaseModel):
    id: str
    class_slot_id: str
    student_id: str
    status: AttendanceStatus
    note: str | None = None
    marked_by_user_id: str
    marked_at: datetime | None = None
    schema_version: int = 1
