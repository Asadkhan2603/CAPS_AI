from datetime import datetime

from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    roll_number: str = Field(min_length=1, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    user_id: str | None = None
    class_id: str | None = None
    group_id: str | None = None


class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    roll_number: str | None = Field(default=None, min_length=1, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    user_id: str | None = None
    class_id: str | None = None
    group_id: str | None = None
    is_active: bool | None = None


class StudentOut(BaseModel):
    id: str
    public_id: str | None = None
    display_label: str | None = None
    full_name: str
    roll_number: str
    email: str | None = None
    user_id: str | None = None
    class_id: str | None = None
    group_id: str | None = None
    canonical_class_id: str | None = None
    canonical_group_id: str | None = None
    placement_source: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    schema_version: int = 1


class StudentDuplicateMemberOut(BaseModel):
    id: str
    full_name: str
    roll_number: str | None = None
    email: str | None = None
    user_id: str | None = None
    class_id: str | None = None
    group_id: str | None = None
    is_active: bool = True
    created_at: datetime | None = None


class StudentDuplicateConflictValueOut(BaseModel):
    value: str | None = None
    student_ids: list[str] = Field(default_factory=list)


class StudentDuplicateConflictOut(BaseModel):
    field: str
    values: list[StudentDuplicateConflictValueOut] = Field(default_factory=list)


class StudentMergeReferenceCountOut(BaseModel):
    collection: str
    count: int = 0


class StudentDuplicateCaseOut(BaseModel):
    case_id: str
    member_student_ids: list[str] = Field(default_factory=list)
    matched_by: list[str] = Field(default_factory=list)
    members: list[StudentDuplicateMemberOut] = Field(default_factory=list)
    suggested_primary_student_id: str
    conflicts: list[StudentDuplicateConflictOut] = Field(default_factory=list)
    reference_counts: list[StudentMergeReferenceCountOut] = Field(default_factory=list)


class StudentMergeResolvedProfile(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    roll_number: str = Field(min_length=1, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    user_id: str | None = None
    class_id: str | None = None
    group_id: str | None = None
    is_active: bool = True


class StudentMergePreviewIn(BaseModel):
    seed_student_ids: list[str] = Field(default_factory=list, min_length=1)
    preferred_primary_student_id: str | None = None


class StudentMergePreviewOut(StudentDuplicateCaseOut):
    resolved_profile: StudentMergeResolvedProfile
    hard_delete_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StudentMergeExecuteIn(BaseModel):
    primary_student_id: str = Field(min_length=1)
    duplicate_student_ids: list[str] = Field(default_factory=list, min_length=1)
    resolved_profile: StudentMergeResolvedProfile
    reason: str = Field(min_length=5, max_length=500)
    confirm_hard_delete: bool = True


class StudentMergeExecuteOut(BaseModel):
    merged_student: StudentOut
    deleted_student_ids: list[str] = Field(default_factory=list)
    rewrite_counts: list[StudentMergeReferenceCountOut] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    audit_log_id: str | None = None
