from fastapi import APIRouter
from app.api.v1.endpoints import (
    analytics,
    assignments,
    audit_logs,
    auth,
    classes,
    courses,
    evaluations,
    notifications,
    section_subjects,
    sections,
    similarity,
    students,
    subjects,
    submissions,
    users,
    years,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(years.router, prefix="/years", tags=["years"])
api_router.include_router(classes.router, prefix="/classes", tags=["classes"])
api_router.include_router(sections.router, prefix="/sections", tags=["sections"])
api_router.include_router(
    section_subjects.router, prefix="/section-subjects", tags=["section-subjects"]
)
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
api_router.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
api_router.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
api_router.include_router(similarity.router, prefix="/similarity", tags=["similarity"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
