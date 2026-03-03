from fastapi import APIRouter
from app.api.v1.endpoints import (
    admin_analytics,
    admin_communication,
    admin_governance,
    admin_recovery,
    admin_system,
    attendance_records,
    ai,
    analytics,
    assignments,
    audit_logs,
    batches,
    branches,
    branding,
    club_events,
    clubs,
    departments,
    faculties,
    enrollments,
    event_registrations,
    auth,
    classes,
    class_slots,
    courses,
    course_offerings,
    evaluations,
    notices,
    notifications,
    review_tickets,
    semesters,
    similarity,
    specializations,
    groups,
    students,
    subjects,
    submissions,
    timetables,
    users,
    years,
    programs,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(courses.router, prefix="/courses", tags=["courses"])
api_router.include_router(programs.router, prefix="/programs", tags=["programs"])
api_router.include_router(departments.router, prefix="/departments", tags=["departments"])
api_router.include_router(faculties.router, prefix="/faculties", tags=["faculties"])
api_router.include_router(branches.router, prefix="/branches", tags=["branches"])
api_router.include_router(specializations.router, prefix="/specializations", tags=["specializations"])
api_router.include_router(years.router, prefix="/years", tags=["years"])
api_router.include_router(batches.router, prefix="/batches", tags=["batches"])
api_router.include_router(semesters.router, prefix="/semesters", tags=["semesters"])
# Canonical section endpoint is /sections.
# /classes is a legacy compatibility alias and should be treated as deprecated for new clients.
api_router.include_router(classes.router, prefix="/classes", tags=["classes"])
api_router.include_router(classes.router, prefix="/sections", tags=["sections"])
api_router.include_router(students.router, prefix="/students", tags=["students"])
api_router.include_router(groups.router, prefix="/groups", tags=["groups"])
api_router.include_router(course_offerings.router, prefix="/course-offerings", tags=["course-offerings"])
api_router.include_router(class_slots.router, prefix="/class-slots", tags=["class-slots"])
api_router.include_router(attendance_records.router, prefix="/attendance-records", tags=["attendance-records"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(assignments.router, prefix="/assignments", tags=["assignments"])
api_router.include_router(submissions.router, prefix="/submissions", tags=["submissions"])
api_router.include_router(timetables.router, prefix="/timetables", tags=["timetables"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
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
api_router.include_router(admin_system.router, prefix="/admin/system", tags=["admin-system"])
api_router.include_router(admin_analytics.router, prefix="/admin/analytics", tags=["admin-analytics"])
api_router.include_router(
    admin_communication.router,
    prefix="/admin/communication",
    tags=["admin-communication"],
)
api_router.include_router(
    admin_governance.router,
    prefix="/admin/governance",
    tags=["admin-governance"],
)
api_router.include_router(admin_recovery.router, prefix="/admin/recovery", tags=["admin-recovery"])
