# Analytics And Reporting

## Purpose

This module provides user-facing analytics, admin analytics, activity feed generation, academic structure reporting, and student-risk tracking.

## Data Model

Entities:

- analytics snapshots
- student interventions
- derived feed items
- academic structure aggregates
- platform and audit summaries

## APIs

Primary endpoints:

- `/analytics/summary`
- `/analytics/dashboard`
- `/analytics/feed`
- `/analytics/teacher/sections`
- `/analytics/student-risk`
- `/analytics/student-risk/interventions`
- `/analytics/academic-structure`
- `/admin/analytics/overview`
- `/admin/analytics/platform`
- `/admin/analytics/onboarding-overview`
- `/admin/analytics/snapshots/run-daily`
- `/admin/analytics/snapshots/history`
- `/admin/analytics/audit-summary`

## Workflow

1. analytics endpoints aggregate operational and academic records
2. student-risk panels derive intervention insights
3. admin analytics surfaces onboarding, audit, and platform summary views
4. feed generation publishes a cross-module activity timeline

## Dependencies

- `backend/app/api/v1/endpoints/analytics.py`
- `backend/app/api/v1/endpoints/admin_analytics.py`
- `backend/app/services/analytics_snapshot.py`
- `backend/app/services/system_health_snapshots.py`
- frontend analytics and admin analytics pages
