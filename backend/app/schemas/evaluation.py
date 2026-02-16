from pydantic import BaseModel, Field


class EvaluationInput(BaseModel):
    attendance_percent: int = Field(ge=0, le=100)
    skill: float = Field(ge=0, le=2.5)
    behavior: float = Field(ge=0, le=2.5)
    report: float = Field(ge=0, le=10)
    viva: float = Field(ge=0, le=20)
    final_exam: int = Field(ge=0, le=60)
