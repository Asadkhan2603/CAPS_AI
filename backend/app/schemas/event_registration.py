from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RegistrationStatus = Literal["registered", "pending", "approved", "waitlisted", "rejected", "cancelled"]
AttendanceStatus = Literal["present", "absent"]


class EventRegistrationCreate(BaseModel):
    event_id: str = Field(min_length=1)
    enrollment_number: str | None = Field(default=None, max_length=100)
    full_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    year: str | None = Field(default=None, max_length=100)
    course_branch: str | None = Field(default=None, max_length=200)
    class_name: str | None = Field(default=None, max_length=100)
    phone_number: str | None = Field(default=None, max_length=50)
    whatsapp_number: str | None = Field(default=None, max_length=50)
    payment_qr_code: str | None = Field(default=None, max_length=500)


class EventRegistrationUpdate(BaseModel):
    status: Literal["registered", "pending", "approved", "waitlisted", "rejected", "cancelled"] | None = None
    attendance_status: AttendanceStatus | None = None
    certificate_issued: bool | None = None
    queue_owner_user_id: str | None = Field(default=None, max_length=100)
    coordinator_note: str | None = Field(default=None, max_length=800)


class EventRegistrationBulkUpdate(BaseModel):
    registration_ids: list[str] = Field(min_length=1, max_length=200)
    status: Literal["registered", "pending", "approved", "waitlisted", "rejected", "cancelled"] | None = None
    attendance_status: AttendanceStatus | None = None
    certificate_issued: bool | None = None
    queue_owner_user_id: str | None = Field(default=None, max_length=100)
    coordinator_note: str | None = Field(default=None, max_length=800)


class EventRegistrationReminder(BaseModel):
    event_id: str = Field(min_length=1)
    registration_ids: list[str] = Field(default_factory=list, max_length=200)
    status_filter: Literal["pending", "waitlisted"] | None = None
    message: str | None = Field(default=None, max_length=500)


class EventRegistrationOut(BaseModel):
    id: str
    public_id: str | None = None
    display_label: str | None = None
    event_id: str
    student_user_id: str
    enrollment_number: str | None = None
    full_name: str | None = None
    email: str | None = None
    year: str | None = None
    course_branch: str | None = None
    class_name: str | None = None
    phone_number: str | None = None
    whatsapp_number: str | None = None
    payment_qr_code: str | None = None
    payment_receipt_original_filename: str | None = None
    payment_receipt_stored_filename: str | None = None
    payment_receipt_mime_type: str | None = None
    payment_receipt_size_bytes: int | None = None
    student_name: str | None = None
    student_email: str | None = None
    student_label: str | None = None
    status: RegistrationStatus = "registered"
    queue_owner_user_id: str | None = None
    queue_owner_label: str | None = None
    coordinator_note: str | None = None
    last_touched_by: str | None = None
    last_touched_by_label: str | None = None
    last_touched_at: datetime | None = None
    attendance_status: AttendanceStatus | None = None
    certificate_issued: bool = False
    created_at: datetime | None = None
    schema_version: int = 1
