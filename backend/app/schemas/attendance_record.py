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
    public_id: str | None = None
    display_label: str | None = None
    class_slot_id: str
    student_id: str
    status: AttendanceStatus
    note: str | None = None
    marked_by_user_id: str
    marked_by_label: str | None = None
    marked_at: datetime | None = None
    schema_version: int = 1


class AttendanceRosterStudentOut(BaseModel):
    student_id: str
    student_name: str
    roll_number: str | None = None
    group_id: str | None = None
    group_name: str | None = None
    status: AttendanceStatus | None = None
    note: str | None = None
    attendance_percent: float | None = None


class AttendanceRosterOut(BaseModel):
    class_slot_id: str
    section_id: str | None = None
    section_name: str | None = None
    group_id: str | None = None
    group_name: str | None = None
    subject_name: str | None = None
    teacher_name: str | None = None
    day: str
    start_time: str
    end_time: str
    room_code: str | None = None
    summary: dict[str, int | float | None]
    students: list[AttendanceRosterStudentOut] = Field(default_factory=list)


class AttendanceStudentSummaryOut(BaseModel):
    student_id: str
    student_name: str
    roll_number: str | None = None
    group_id: str | None = None
    group_name: str | None = None
    total_marked_slots: int = 0
    present_like_slots: int = 0
    absent_slots: int = 0
    attendance_percent: float = 0
    shortage_threshold: float = 75
    shortage_risk: bool = False


class AttendanceSectionSummaryOut(BaseModel):
    section_id: str
    section_name: str | None = None
    group_id: str | None = None
    group_name: str | None = None
    total_students: int = 0
    total_slots: int = 0
    total_marked_records: int = 0
    average_attendance_percent: float = 0
    shortage_threshold: float = 75
    shortage_risk_count: int = 0
    students: list[AttendanceStudentSummaryOut] = Field(default_factory=list)


class AttendanceTrendPointOut(BaseModel):
    label: str
    total_marked_slots: int = 0
    attendance_percent: float = 0


class AttendanceSubjectSummaryOut(BaseModel):
    subject_id: str | None = None
    subject_name: str | None = None
    total_marked_slots: int = 0
    present_like_slots: int = 0
    absent_slots: int = 0
    attendance_percent: float = 0
    shortage_risk: bool = False


class AttendanceAnalyticsOut(BaseModel):
    section_id: str
    section_name: str | None = None
    group_id: str | None = None
    group_name: str | None = None
    student_id: str | None = None
    student_name: str | None = None
    roll_number: str | None = None
    range_days: int = 30
    shortage_threshold: float = 75
    average_attendance_percent: float = 0
    present_like_slots: int = 0
    absent_slots: int = 0
    total_marked_slots: int = 0
    shortage_risk: bool = False
    trend: list[AttendanceTrendPointOut] = Field(default_factory=list)
    subjects: list[AttendanceSubjectSummaryOut] = Field(default_factory=list)
