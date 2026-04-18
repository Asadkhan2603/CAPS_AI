from datetime import datetime

from pydantic import BaseModel, Field


class RubricCriterion(BaseModel):
    label: str = Field(min_length=1, max_length=200)
    max_score: float = Field(ge=0, le=100)
    keywords: list[str] = Field(default_factory=list)
    notes: str | None = Field(default=None, max_length=500)


class EvaluationCriterionScore(BaseModel):
    label: str
    max_score: float = Field(ge=0)
    awarded_score: float = Field(ge=0)
    evidence_coverage: float = Field(ge=0, le=1)
    rationale: str
    keywords_hit: list[str] = Field(default_factory=list)


class EvaluationAIInsight(BaseModel):
    summary: str
    strengths: list[str] = []
    gaps: list[str] = []
    suggestions: list[str] = []
    risk_flags: list[str] = []
    criterion_scores: list[EvaluationCriterionScore] = []
    criterion_rationales: list[str] = []
    academic_rationale: list[str] = []
    risk_context: list[str] = []
    confidence: float = Field(ge=0, le=1)
    confidence_mode: str | None = None
    status: str = "fallback"
    provider: str | None = None
    prompt_version: str | None = None
    runtime_snapshot: dict | None = None


class EvaluationCreate(BaseModel):
    submission_id: str = Field(min_length=1)
    attendance_percent: int = Field(ge=0, le=100)
    skill: float = Field(ge=0, le=2.5)
    behavior: float = Field(ge=0, le=2.5)
    report: float = Field(ge=0, le=10)
    viva: float = Field(ge=0, le=20)
    final_exam: int = Field(ge=0, le=60)
    remarks: str | None = Field(default=None, max_length=1000)
    rubric_criteria: list[RubricCriterion] = Field(default_factory=list)
    is_finalized: bool = False


class EvaluationUpdate(BaseModel):
    attendance_percent: int | None = Field(default=None, ge=0, le=100)
    skill: float | None = Field(default=None, ge=0, le=2.5)
    behavior: float | None = Field(default=None, ge=0, le=2.5)
    report: float | None = Field(default=None, ge=0, le=10)
    viva: float | None = Field(default=None, ge=0, le=20)
    final_exam: int | None = Field(default=None, ge=0, le=60)
    remarks: str | None = Field(default=None, max_length=1000)
    rubric_criteria: list[RubricCriterion] | None = None
    is_finalized: bool | None = None


class EvaluationAIPreviewRequest(BaseModel):
    submission_id: str = Field(min_length=1)
    attendance_percent: int = Field(ge=0, le=100)
    skill: float = Field(ge=0, le=2.5)
    behavior: float = Field(ge=0, le=2.5)
    report: float = Field(ge=0, le=10)
    viva: float = Field(ge=0, le=20)
    final_exam: int = Field(ge=0, le=60)
    remarks: str | None = Field(default=None, max_length=1000)
    rubric_criteria: list[RubricCriterion] = Field(default_factory=list)


class EvaluationAIPreviewOut(BaseModel):
    submission_id: str
    internal_total: float
    grand_total: float
    grade: str
    ai_score: float | None = None
    ai_feedback: str | None = None
    ai_status: str | None = None
    ai_provider: str | None = None
    ai_confidence: float | None = Field(default=None, ge=0, le=1)
    ai_confidence_mode: str | None = None
    rubric_criteria: list[RubricCriterion] = Field(default_factory=list)
    ai_criterion_scores: list[EvaluationCriterionScore] = Field(default_factory=list)
    ai_criterion_rationales: list[str] = Field(default_factory=list)
    ai_insight: EvaluationAIInsight


class EvaluationOut(BaseModel):
    id: str
    public_id: str | None = None
    display_label: str | None = None
    submission_id: str
    submission_label: str | None = None
    student_user_id: str
    student_label: str | None = None
    teacher_user_id: str
    teacher_label: str | None = None
    attendance_percent: int
    skill: float
    behavior: float
    report: float
    viva: float
    final_exam: int
    internal_total: float
    grand_total: float
    grade: str
    rubric_criteria: list[RubricCriterion] = Field(default_factory=list)
    ai_score: float | None = None
    ai_feedback: str | None = None
    ai_status: str | None = None
    ai_provider: str | None = None
    ai_prompt_version: str | None = None
    ai_runtime_snapshot: dict | None = None
    schema_version: int = 1
    ai_confidence: float | None = Field(default=None, ge=0, le=1)
    ai_confidence_mode: str | None = None
    ai_risk_flags: list[str] = []
    ai_strengths: list[str] = []
    ai_gaps: list[str] = []
    ai_suggestions: list[str] = []
    ai_criterion_scores: list[EvaluationCriterionScore] = []
    ai_criterion_rationales: list[str] = []
    ai_academic_rationale: list[str] = []
    remarks: str | None = None
    is_finalized: bool = False
    finalized_at: datetime | None = None
    finalized_by_user_id: str | None = None
    result_status: str = "draft"
    released_at: datetime | None = None
    released_by_user_id: str | None = None
    result_version: int = 1
    created_at: datetime | None = None
    updated_at: datetime | None = None


class OfficialMarksheetItemOut(BaseModel):
    evaluation_id: str
    submission_id: str
    submission_label: str | None = None
    teacher_user_id: str
    attendance_percent: int
    internal_total: float
    final_exam: int
    grand_total: float
    grade: str
    remarks: str | None = None
    released_at: datetime | None = None
    result_version: int = 1


class OfficialMarksheetOut(BaseModel):
    student_user_id: str
    student_name: str | None = None
    roll_number: str | None = None
    email: str | None = None
    generated_at: datetime
    released_results_count: int = 0
    average_score: float = 0
    items: list[OfficialMarksheetItemOut] = Field(default_factory=list)


class SemesterResultItemOut(BaseModel):
    evaluation_id: str
    submission_id: str
    assignment_id: str | None = None
    assignment_title: str | None = None
    subject_id: str | None = None
    subject_name: str | None = None
    subject_code: str | None = None
    exam_id: str | None = None
    exam_title: str | None = None
    grand_total: float = 0
    grade: str = "Needs Improvement"
    grade_point: float = 0
    released_at: datetime | None = None
    result_version: int = 1


class SemesterResultOut(BaseModel):
    id: str
    student_user_id: str
    student_name: str | None = None
    roll_number: str | None = None
    semester_id: str
    semester_label: str | None = None
    semester_number: int | None = None
    class_id: str | None = None
    class_name: str | None = None
    batch_id: str | None = None
    status: str = "released"
    result_version: int = 1
    released_at: datetime | None = None
    released_by_user_id: str | None = None
    correction_requested_at: datetime | None = None
    correction_requested_by_user_id: str | None = None
    correction_reason: str | None = None
    reopened_at: datetime | None = None
    reopened_by_user_id: str | None = None
    reopen_reason: str | None = None
    result_count: int = 0
    average_score: float = 0
    gpa: float = 0
    items: list[SemesterResultItemOut] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    schema_version: int = 1


class TranscriptSemesterOut(BaseModel):
    result_id: str
    semester_id: str | None = None
    semester_label: str | None = None
    semester_number: int | None = None
    status: str = "released"
    result_version: int = 1
    released_at: datetime | None = None
    result_count: int = 0
    average_score: float = 0
    gpa: float = 0
    cgpa: float = 0


class TranscriptOut(BaseModel):
    student_user_id: str
    student_name: str | None = None
    roll_number: str | None = None
    email: str | None = None
    generated_at: datetime
    semester_count: int = 0
    cgpa: float = 0
    semesters: list[TranscriptSemesterOut] = Field(default_factory=list)


class GradingPolicyOut(BaseModel):
    grade_points: dict[str, float] = Field(default_factory=dict)
    transcript_precision: int = 2


class GradingPolicyUpdate(BaseModel):
    grade_points: dict[str, float] | None = None
    transcript_precision: int | None = Field(default=None, ge=0, le=4)


class SemesterResultReopenRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class SemesterResultCorrectionRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)
