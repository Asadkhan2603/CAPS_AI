from datetime import datetime

from pydantic import BaseModel, Field


class SectionCreate(BaseModel):
    faculty_id: str | None = None
    department_id: str | None = None
    program_id: str | None = None
    specialization_id: str | None = None
    batch_id: str | None = None
    semester_id: str | None = None
    name: str = Field(min_length=1, max_length=100)
    faculty_name: str | None = Field(default=None, max_length=120)
    class_coordinator_user_id: str | None = None


class SectionUpdate(BaseModel):
    faculty_id: str | None = None
    department_id: str | None = None
    program_id: str | None = None
    specialization_id: str | None = None
    batch_id: str | None = None
    semester_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    faculty_name: str | None = Field(default=None, max_length=120)
    class_coordinator_user_id: str | None = None
    is_active: bool | None = None


class SectionOut(BaseModel):
    id: str
    public_id: str | None = None
    display_label: str | None = None
    faculty_id: str | None = None
    department_id: str | None = None
    department_name: str | None = None
    program_id: str | None = None
    program_name: str | None = None
    specialization_id: str | None = None
    specialization_name: str | None = None
    batch_id: str | None = None
    batch_name: str | None = None
    semester_id: str | None = None
    semester_label: str | None = None
    name: str
    faculty_name: str | None = None
    branch_name: str | None = Field(
        default=None,
        description="Legacy compatibility field returned only for historical rows.",
    )
    class_coordinator_user_id: str | None = None
    class_coordinator_name: str | None = None
    mapping_locked: bool = False
    mapping_locked_by_user_id: str | None = None
    mapping_locked_by_name: str | None = None
    mapping_locked_by_email: str | None = None
    mapping_locked_at: datetime | None = None
    mapping_lock_reason: str | None = None
    is_active: bool = True
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    created_at: datetime | None = None
    schema_version: int = 1


# Compatibility aliases kept for tests and older internal imports while the
# public route and current docs standardize on sections.
ClassCreate = SectionCreate
ClassUpdate = SectionUpdate
ClassOut = SectionOut


class SectionLockRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=300)


class SectionOperationalSummaryOut(BaseModel):
    section_id: str
    section_name: str
    student_count: int = 0
    legacy_profile_only_count: int = 0
    active_offering_count: int = 0
    pending_evaluation_count: int = 0
    unreleased_evaluation_count: int = 0
    latest_timetable_status: str | None = None
    latest_timetable_sync_status: str | None = None
    latest_timetable_drift_count: int = 0
    average_attendance_percent: float | None = None
    shortage_risk_count: int = 0


class SectionDashboardResponse(BaseModel):
    total_sections: int = 0
    total_students: int = 0
    total_active_offerings: int = 0
    total_pending_evaluations: int = 0
    total_unreleased_evaluations: int = 0
    sections_with_drift: int = 0
    sections_with_attendance_risk: int = 0
    global_unmapped_students: int = 0
    sections: list[SectionOperationalSummaryOut] = Field(default_factory=list)
