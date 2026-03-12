# Documentation Audit Report

Audit date: 2026-03-11

Phase 3 update (2026-03-12):
- actionable `docs/` content is tracked in git again
- root runtime docs (`README.md`, `scripts/README.md`, `backend/app/models/README.md`) were refreshed against current code
- Mongo migration/versioning guidance was added in `docs/guides/mongo-versioning.md`

## Summary

This audit aligns documentation with the current runtime implementation. The backend route graph in `/backend/app/api/v1/router.py` and the frontend navigation in `/frontend/src/routes/AppRoutes.jsx` and `/frontend/src/config/navigationGroups.js` are treated as the runtime source of truth.

Key corrections:

- legacy API routes for `/courses`, `/years`, `/branches`, and `/classes` are retired in the backend
- `/sections` is the only public section route, but section records still live in the `classes` collection
- frontend redirects remain for `/courses`, `/years`, and `/branches`
- documentation links were normalized to repo-relative paths for portability
- module masters now include a standardized section header set for consistent structure

## Runtime-Derived Module Map

### Backend API Families (router-mounted)

- auth: `/auth`
- users: `/users`
- academic setup: `/faculties`, `/departments`, `/programs`, `/specializations`, `/batches`, `/semesters`, `/sections`
- academics: `/students`, `/groups`, `/subjects`, `/course-offerings`, `/class-slots`, `/attendance-records`, `/enrollments`
- assessment and AI: `/assignments`, `/submissions`, `/evaluations`, `/similarity`, `/ai`
- scheduling: `/timetables`
- communication: `/notices`, `/notifications`
- clubs and events: `/clubs`, `/club-events`, `/event-registrations`
- analytics: `/analytics`
- branding: `/branding`
- audit and review: `/audit-logs`, `/review-tickets`
- admin domains: `/admin/system`, `/admin/analytics`, `/admin/communication`, `/admin/governance`, `/admin/recovery`

### Frontend Workspace Routes (navigation groups)

Admin and teacher workspaces:

- admin panel: `/admin/dashboard`, `/admin/governance`, `/admin/analytics`, `/admin/system`, `/admin/recovery`, `/admin/developer`
- overview: `/dashboard`, `/analytics`, `/history`, `/timetable`, `/academic-structure`
- academics: `/students`, `/groups`, `/subjects`, `/course-offerings`, `/class-slots`, `/attendance-records`, `/assignments`, `/submissions`, `/ai-operations`, `/review-tickets`, `/evaluations`, `/enrollments`
- communication: `/communication/feed`, `/communication/announcements`, `/communication/messages`
- clubs: `/clubs`, `/club-events`, `/event-registrations`
- operations: `/audit-logs`, `/developer-panel`, `/users`
- academic setup: `/faculties`, `/departments`, `/programs`, `/specializations`, `/batches`, `/semesters`, `/sections`
- profile: `/profile`

Student workspaces:

- home: `/dashboard`, `/timetable`, `/history`
- academics: `/class-slots`, `/submissions`, `/evaluations`, `/attendance-records`
- notices: `/communication/announcements`, `/notifications`, `/communication/feed`
- clubs: `/clubs`, `/club-events`, `/event-registrations`
- profile: `/profile`

### Frontend Legacy Redirects

- `/courses` -> `/programs`
- `/years` -> `/batches`
- `/branches` -> `/specializations`
- `/notices` -> `/communication/announcements`

## Files Updated

- `/docs/README.md`
- `/docs/guides/module-index.md`
- `/docs/guides/api-contracts.md`
- `/docs/guides/backend-architecture.md`
- `/docs/guides/data-model.md`
- `/docs/guides/governance-workflows.md`
- `/docs/guides/testing.md`
- `/docs/ACADEMIC_SETUP_LOGIC_AUDIT.md`
- `/docs/modules/README.md`
- `/docs/modules/ACADEMIC_MODULE_MASTER.md`
- `/docs/modules/CLASS_SECTION_MODULE_MASTER.md`
- `/docs/modules/ANALYTICS_MODULE_MASTER.md`
- `/docs/modules/RBAC_MODULE_MASTER.md`
- `/docs/modules/GOVERNANCE_MODULE_MASTER.md`
- `/docs/modules/SYSTEM_MODULE_MASTER.md`
- `/docs/modules/RECOVERY_MODULE_MASTER.md`
- standardized section headers inserted into all `*_MODULE_MASTER.md` files
- repo-relative link normalization across `docs/`

## Files Deleted or Archived

- `docs/admin.txt` moved to `docs/archives/OLD_DATA/admin.txt`

## New Documentation Created

- `/docs/DOCUMENTATION_AUDIT_REPORT.md`

## Documentation Bugs Found

- absolute filesystem links made docs non-portable
- multiple references to retired backend routes (`/courses`, `/years`, `/branches`, `/classes`)
- testing guide and CI config drift: CI still references removed endpoints
- module masters lacked a consistent section header structure

## Architecture Observations

- section records are stored in the `classes` collection, but `/sections` is the only public route
- legacy collections (`courses`, `years`, `branches`) remain for data translation and recovery
- admin surface pages are now navigational shells that redirect to canonical modules
- analytics includes a legacy alias at `/analytics/teacher/classes` with a canonical `/analytics/teacher/sections` path

## Recommended Improvements

- update `.github/workflows/ci.yml` to remove references to retired endpoints and match the canonical academic setup routes
- consider renaming legacy storage artifacts (`classes`) once migration risk is reduced
- remove or archive legacy collections after data migration and reporting dependencies are retired
- continue to enforce root-relative links and standardized module sections for new docs
