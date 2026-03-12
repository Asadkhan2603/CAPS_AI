# Legacy Academic Migration Checklist

Reviewed on `2026-03-11`.

This document is the implementation checklist for retiring the legacy academic entities:

- `courses`
- `years`
- `branches`

Public module retirement is now complete for `courses`, `years`, and `branches`. Remaining compatibility is limited to historical data fields such as `branch_name` and read-side translation for older rows.

## Goal

Move all operational academic flows to the canonical hierarchy:

`Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`

Then remove:

- legacy API routes
- legacy frontend pages
- legacy permissions
- legacy tests
- legacy fields where they are no longer needed

## Canonical Replacement Rules

These are the replacement rules to use during migration. They are intentionally conservative.

| Legacy entity | Canonical replacement | Migration note |
|---|---|---|
| `Course` | `Program` | This is the closest primary replacement for the academic offering definition |
| `Year` | `Batch` or `Semester` | No direct 1:1 replacement. Use `Batch` for cohort identity and `Semester` for in-program progression |
| `Branch` | `Specialization` or `Program` | Depends on meaning. If it represents a stream inside a program, use `Specialization`. If it is the whole offering, use `Program` |
| `Class` route alias | `Section` | `/sections` is canonical; `/classes` is not mounted |

## Current Blocking Dependencies

## Backend Surface

- [router.py](/backend/app/api/v1/router.py)
  - no longer mounts `/courses`, `/years`, `/branches`
  - no longer mounts `/classes`; `/sections` is the only public section route

- [permission_registry.py](/backend/app/core/permission_registry.py)
  - no longer defines `courses.manage`, `years.manage`, or `branches.manage`
  - no longer includes `/courses`, `/years`, `/branches`, or `/classes` in `ACADEMIC_ROUTE_PERMISSION_MATRIX`

## Backend Data Contracts

- [class_item.py](/backend/app/schemas/class_item.py)
  - section output still carries `branch_name` for historical rows
  - section create and update payloads no longer accept `course_id`, `year_id`, or `branch_name`
  - canonical fields already exist: `faculty_id`, `department_id`, `program_id`, `specialization_id`, `batch_id`, `semester_id`

- [classes.py](/backend/app/models/classes.py)
  - persisted class model still exposes `branch_name` only as compatibility output for historical rows

## Backend Logic Still Reading Legacy Fields

- [classes.py](/backend/app/api/v1/endpoints/classes.py)
  - active canonical create/update no longer depends on `course_id`, `year_id`, or `branch_name`
  - section list no longer exposes `branch_name` as an active filter

- [analytics.py](/backend/app/api/v1/endpoints/analytics.py)
  - active structure aggregation now builds output using canonical IDs

- [notices.py](/backend/app/api/v1/endpoints/notices.py)
  - notice visibility now uses `batch` scope instead of `year`

- [admin_communication.py](/backend/app/api/v1/endpoints/admin_communication.py)
  - communication preview now resolves class membership by `batch`

- [users.py](/backend/app/api/v1/endpoints/users.py)
  - derived class scope payload now stores `batch_id` and `semester_id`

- [timetables.py](/backend/app/api/v1/endpoints/timetables.py)
  - timetable lookup payload no longer exposes `branch_name`

- [background_jobs.py](/backend/app/services/background_jobs.py)
  - background jobs still fetch classes by `year_id`

## Frontend Surface Still Exposing Legacy Modules

- [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx)
  - `/courses`, `/years`, and `/branches` now redirect to canonical routes

- [navigationGroups.js](/frontend/src/config/navigationGroups.js)
  - no longer includes Courses, Years, or Branches in navigation

- [AcademicStructurePage.jsx](/frontend/src/pages/AcademicStructurePage.jsx)
  - renders only the canonical hierarchy tree

- dedicated legacy CRUD pages have been deleted

## Frontend Logic Still Reading Legacy Fields

- [ClassesPage.jsx](/frontend/src/pages/ClassesPage.jsx)
  - creates canonical sections without `branch_name`

- [AnnouncementsPage.jsx](/frontend/src/pages/Communication/AnnouncementsPage.jsx)
  - no longer loads `/years/`
  - no longer uses `branch_name` in section search text

- [TimetablePage.jsx](/frontend/src/pages/TimetablePage.jsx)
  - no longer depends on timetable lookup `branch_name`

- [TeacherClassTiles.jsx](/frontend/src/components/ui/TeacherClassTiles.jsx)
  - still falls back to `year_id`

- [Sidebar.jsx](/frontend/src/components/layout/Sidebar.jsx)
- [DashboardPage.jsx](/frontend/src/pages/DashboardPage.jsx)
  - no longer renders `branch_name` as a primary academic identity fallback

## Tests Blocking Removal

- [test_auth.py](/backend/tests/test_auth.py)
- [test_timetables.py](/backend/tests/test_timetables.py)
- [test_main_missing_blocks.py](/backend/tests/test_main_missing_blocks.py)
- [test_academic_permissions.py](/backend/tests/test_academic_permissions.py)

These tests now validate canonical setup flows and assert `404` on retired legacy routes.

## Required Migration Order

## Phase 1: Stop Promoting Legacy Setup

Goal: remove legacy modules from primary admin UX without breaking compatibility.

- remove legacy cards from the admin academic structure page
- remove legacy links from the canonical academic structure page
- remove legacy modules from sidebar navigation
- keep only canonical routes; use redirects where needed

This phase is safe now.

## Phase 2: Move Active Reads To Canonical Fields

Goal: make all active workflows read canonical relations first.

Required updates:

- `analytics`
  - replace `course_id` and `year_id` aggregation with `program_id`, `batch_id`, and `semester_id` where applicable

- `notices` and `admin_communication`
  - replace year-based scoping with semester or batch-based scoping
  - decide whether notice visibility should target `semester`, `batch`, or `section`

- `users`
  - remove legacy class scope fields from derived user scope payloads

- `timetables`
  - replace `branch_name` display with `program`, `specialization`, or section label composition

- dashboard and profile widgets
  - stop rendering `branch_name` as a first-class academic identity field

This is the main logic migration step. Legacy routes should not be removed before this phase is complete.

## Phase 3: Clean Section Contracts

Goal: make the section model canonical by default.

Required updates:

- remove `course_id`, `year_id`, and `branch_name` from section create and update payload requirements
- stop validating section creation against legacy `courses` and `years`
- keep compatibility reads only if historical data still needs to be displayed
- backfill any missing canonical IDs on existing `classes` documents if legacy-only rows still exist

Status:
- completed for active create/update/filter flows
- `branch_name` remains read-only compatibility output for historical section rows

Primary file:

- [classes.py](/backend/app/api/v1/endpoints/classes.py)

Supporting files:

- [class_item.py](/backend/app/schemas/class_item.py)
- [classes.py](/backend/app/models/classes.py)
- [ClassesPage.jsx](/frontend/src/pages/ClassesPage.jsx)

## Phase 4: Remove Legacy Frontend Pages And Permissions

Goal: retire direct user-facing access to legacy modules.

Required updates:

- redirect `/courses`, `/years`, `/branches` to canonical routes in [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx)
- remove legacy items from [navigationGroups.js](/frontend/src/config/navigationGroups.js)
- delete legacy pages:
  - `CoursesPage.jsx`
  - `YearsPage.jsx`
  - `BranchesPage.jsx`
- remove legacy feature access entries if they are no longer needed
- remove legacy permission keys and permission matrix rows from [permission_registry.py](/backend/app/core/permission_registry.py)

## Phase 5: Remove Legacy Backend Endpoints

Goal: delete compatibility APIs only after no active caller remains.

Required updates:

- remove legacy route mounts from [router.py](/backend/app/api/v1/router.py)
- delete legacy endpoint files once all callers are gone
- remove legacy domain services that only serve `courses`

## Phase 6: Test And Fixture Cleanup

Goal: make the test suite canonical.

Required updates:

- replace legacy fixture creation in backend tests with canonical setup fixtures
- update permission tests to stop expecting legacy route entries
- update timetable and auth tests to create `program`, `batch`, `semester`, and `section` instead of `course`, `year`, and legacy class relations

## Exit Criteria

Legacy modules can be deleted only when all of the following are true:

- no UI entry point links to `/courses`, `/years`, or `/branches`
- no frontend page fetches `/courses/`, `/years/`, or `/branches/`
- no backend endpoint reads `course_id`, `year_id`, or `branch_name` for current workflows
- section creation and analytics work using canonical IDs only
- permission registry has no legacy academic module keys
- tests no longer require legacy routes
- historical data has either been migrated or is intentionally supported through read-only translation logic

## Recommended Immediate Next Step

Do this next:

1. hide legacy modules from navigation and admin setup pages
2. migrate section-adjacent logic first, because it is the main bridge between legacy and canonical models
3. migrate analytics and communication scopes after section contracts are canonical

That order reduces UI confusion first, then removes the highest-risk backend coupling.


