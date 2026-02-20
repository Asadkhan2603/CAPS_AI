from fastapi import APIRouter
from app.api.v1.endpoints import (
    analytics,
    assignments,
    audit_logs,
    branches,
    branding,
    club_events,
    clubs,
    departments,
    enrollments,
    event_registrations,
    auth,
    classes,
    courses,
    evaluations,
    notices,
    notifications,
    review_tickets,
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
api_router.include_router(departments.router, prefix="/departments", tags=["departments"])
api_router.include_router(branches.router, prefix="/branches", tags=["branches"])
api_router.include_router(years.router, prefix="/years", tags=["years"])
api_router.include_router(classes.router, prefix="/classes", tags=["classes"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
api_router.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
api_router.include_router(evaluations.router, prefix="/evaluations", tags=["evaluations"])
api_router.include_router(similarity.router, prefix="/similarity", tags=["similarity"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(branding.router, prefix="/branding", tags=["branding"])
api_router.include_router(notices.router, prefix="/notices", tags=["notices"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(review_tickets.router, prefix="/review-tickets", tags=["review-tickets"])
api_router.include_router(audit_logs.router, prefix="/audit-logs", tags=["audit-logs"])
api_router.include_router(enrollments.router, prefix="/enrollments", tags=["enrollments"])
api_router.include_router(clubs.router, prefix="/clubs", tags=["clubs"])
api_router.include_router(club_events.router, prefix="/club-events", tags=["club-events"])
api_router.include_router(
    event_registrations.router,
    prefix="/event-registrations",
    tags=["event-registrations"],
)
