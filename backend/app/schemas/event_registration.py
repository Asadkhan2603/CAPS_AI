from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

RegistrationStatus = Literal["registered", "cancelled"]


class EventRegistrationCreate(BaseModel):
    event_id: str = Field(min_length=1)
    enrollment_number: str | None = Field(default=None, max_length=100)
    full_name: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    year: str | None = Field(default=None, max_length=100)
    course_branch: str | None = Field(default=None, max_length=200)
    section: str | None = Field(default=None, max_length=100)
    phone_number: str | None = Field(default=None, max_length=50)
    whatsapp_number: str | None = Field(default=None, max_length=50)
    payment_qr_code: str | None = Field(default=None, max_length=500)


class EventRegistrationOut(BaseModel):
    id: str
    event_id: str
    student_user_id: str
    enrollment_number: str | None = None
    full_name: str | None = None
    email: str | None = None
    year: str | None = None
    course_branch: str | None = None
    section: str | None = None
    phone_number: str | None = None
    whatsapp_number: str | None = None
    payment_qr_code: str | None = None
    payment_receipt_original_filename: str | None = None
    payment_receipt_stored_filename: str | None = None
    payment_receipt_mime_type: str | None = None
    payment_receipt_size_bytes: int | None = None
    student_name: str | None = None
    student_email: str | None = None
    status: RegistrationStatus = "registered"
    created_at: datetime | None = None

