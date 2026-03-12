from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


DayName = Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
SessionType = Literal["theory", "practical", "workshop", "interaction"]
TimetableStatus = Literal["draft", "published"]
ShiftId = Literal["shift_1", "shift_2"]


class TimetableEntryInput(BaseModel):
    day: DayName
    slot_key: str = Field(min_length=1, max_length=60)
    subject_id: str = Field(min_length=1)
    teacher_user_id: str = Field(min_length=1)
    room_code: str = Field(min_length=1, max_length=80)
    session_type: SessionType = "theory"


class TimetableEntryOut(TimetableEntryInput):
    subject_name: str | None = None
    subject_code: str | None = None
    teacher_name: str | None = None


class TimetableSlotOut(BaseModel):
    slot_key: str
    start_time: str
    end_time: str
    is_lunch: bool = False
    is_editable: bool = True
    label: str


class TimetableCreate(BaseModel):
    class_id: str = Field(min_length=1)
    semester: str = Field(min_length=1, max_length=30)
    shift_id: ShiftId
    days: list[DayName] = Field(default_factory=lambda: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])
    entries: list[TimetableEntryInput] = Field(default_factory=list)
    template_timetable_id: str | None = None


class TimetableUpdate(BaseModel):
    days: list[DayName] | None = None
    entries: list[TimetableEntryInput] | None = None


class TimetableOut(BaseModel):
    id: str
    class_id: str
    semester: str
    shift_id: ShiftId
    shift_label: str
    days: list[DayName]
    slots: list[TimetableSlotOut]
    entries: list[TimetableEntryOut]
    status: TimetableStatus
    version: int = 1
    admin_locked: bool = False
    published_at: datetime | None = None
    published_by_user_id: str | None = None
    created_by_user_id: str
    created_at: datetime | None = None
    updated_at: datetime | None = None
    schema_version: int = 1


class TimetablePublishResponse(BaseModel):
    message: str
    timetable: TimetableOut


class TimetableLockRequest(BaseModel):
    admin_locked: bool


class TimetableGenerateRequest(BaseModel):
    shift_id: ShiftId
    days: list[DayName] = Field(default_factory=lambda: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"])

    @model_validator(mode="after")
    def validate_days(self) -> "TimetableGenerateRequest":
        if len(self.days) == 0:
            raise ValueError("At least one day is required")
        return self
