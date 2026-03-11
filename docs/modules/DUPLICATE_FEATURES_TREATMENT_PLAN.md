# Duplicate Features Treatment Plan

Reviewed on `2026-03-11`.

This document converts the duplicate-feature audit into an execution plan.

Use this together with:

- [DUPLICATE_FEATURES_AND_MODULES_AUDIT.md](/docs/modules/DUPLICATE_FEATURES_AND_MODULES_AUDIT.md)
- [LEGACY_ACADEMIC_MIGRATION_CHECKLIST.md](/docs/modules/LEGACY_ACADEMIC_MIGRATION_CHECKLIST.md)

## Decision Legend

- `Keep`: retain as a first-class surface
- `Keep as alias`: retain temporarily for compatibility only
- `Merge`: fold the surface into another canonical module
- `Retire`: remove after dependencies are cleared

## Treatment Matrix

| Duplicate / Overlap | Current Role | Canonical Target | Decision | Priority |
|---|---|---|---|---|
| `Courses` | legacy academic module | `Programs` | `Retire` | `High` |
| `Years` | legacy academic module | `Batches` and `Semesters` | `Retire` | `High` |
| `Branches` | legacy academic module | `Specializations` or `Programs` | `Retire` | `Completed` |
| `/classes` route | legacy alias | `/sections` | `Retire` | `Completed` |
| `/notices` page identity | redirect wrapper | `/communication/announcements` | `Merge` | `Completed` |
| `AdminAcademicStructurePage` | admin landing shell | canonical academic setup pages | `Merge` | `Completed` |
| `AdminOperationsPage` | admin landing shell | existing operations modules | `Merge` | `Completed` |
| `AdminClubsPage` | admin landing shell | `Clubs` | `Merge` | `Completed` |
| `AdminCommunicationPage` | admin landing shell + preview utility | communication modules | `Keep` if preview remains admin-only, otherwise `Merge` | `Medium` |
| `AdminCompliancePage` | reporting shell | `Audit Logs` + governance/admin analytics | `Keep` or `Merge` | `Medium` |
| `AdminDashboardPage` | control-plane shell | admin metrics surfaces | `Keep` | `Low` |

## Item-by-Item Treatment

## 1. Courses vs Programs

Status:

- `Courses` is a legacy entity
- `Programs` is the canonical academic offering entity

Evidence:

- [router.py](/backend/app/api/v1/router.py)
- [CoursesPage.jsx](/frontend/src/pages/CoursesPage.jsx)
- [ProgramsPage.jsx](/frontend/src/pages/ProgramsPage.jsx)

Treatment:

- stop treating `Courses` as an active module in UX and docs
- remove the legacy `/courses` API surface once active `course_id` flows are gone
- migrate all business logic to `program_id`

Current implementation status:

- frontend `Courses` page has been retired as a first-class surface and deleted
- direct `/courses` frontend navigation now redirects to `/programs`
- backend `/courses` API is no longer mounted
- `courses.manage` has been removed from the permission registry and route matrix
- teacher `class_coordinator` scope no longer writes `course_id` during active updates
- analytics academic-structure now groups by canonical `program -> batch -> semester`
- new canonical section creation no longer persists empty `course_id` / `year_id` fields
- targeted tests no longer seed active `course_id` paths; they only assert legacy-route `404` behavior

Dependencies blocking removal:

- section contracts
- historical model fields on old rows
- dead legacy endpoint files that can be deleted later

Exit condition:

- no frontend page fetches `/courses/`
- no backend logic depends on `course_id`
- no permission entry for `courses.manage`

## 2. Years vs Batches and Semesters

Status:

- `Years` is legacy
- `Batches` and `Semesters` together replace its old responsibilities

Evidence:

- [router.py](/backend/app/api/v1/router.py)
- [YearsPage.jsx](/frontend/src/pages/YearsPage.jsx)
- [BatchesPage.jsx](/frontend/src/pages/BatchesPage.jsx)
- [SemestersPage.jsx](/frontend/src/pages/SemestersPage.jsx)

Treatment:

- use `Batch` for cohort identity
- use `Semester` for progression within a batch
- migrate notice scope, analytics, timetable, and user/class payloads away from `year_id`

Current implementation status:

- frontend `Years` page has been deleted
- direct `/years` frontend navigation now redirects to `/batches`
- backend `/years` API is no longer mounted
- `years.manage` has been removed from the permission registry and route matrix
- notices now use `batch` scope instead of `year`
- admin communication preview resolves `batch` reach instead of `year`
- class creation and update no longer accept active `year_id` linkage in canonical flows
- teacher role scope stores `batch_id` and `semester_id`, not `year_id`
- targeted tests no longer seed active `year_id` flows; they only assert legacy-route `404` behavior

Dependencies blocking removal:

- historical model fields on old rows
- dead legacy endpoint files that can be deleted later

Exit condition:

- no active read of `year_id`
- no `/years` frontend route
- no `/years` backend route

## 3. Branches vs Specializations and Programs

Status:

- `Branches` is legacy
- canonical replacement depends on meaning:
  - stream inside a program -> `Specialization`
  - top-level offering -> `Program`

Evidence:

- [BranchesPage.jsx](/frontend/src/pages/BranchesPage.jsx)
- [SpecializationsPage.jsx](/frontend/src/pages/SpecializationsPage.jsx)
- [LEGACY_ACADEMIC_MIGRATION_CHECKLIST.md](/docs/modules/LEGACY_ACADEMIC_MIGRATION_CHECKLIST.md)

Treatment:

- classify each current `branch` usage by meaning
- replace `branch_name` display and payload use with either `specialization` label or `program` label
- backfill historical rows if reporting still needs readable names

Current implementation status:

- backend `/branches` API is no longer mounted
- frontend `/branches` path now redirects to `/specializations`
- standalone `Branches` page has been deleted
- `branches.manage` has been removed from the permission registry and route matrix
- historical `db.branches` collection support remains only for archive side effects and old data translation

Dependencies blocking removal:

- active `branch_name` display fallback in a few read paths

Exit condition:

- no active `branch_name` usage in current workflows
- `/branches` removed from routes and permissions

## 4. /classes vs /sections

Status:

- `/sections` is canonical
- `/classes` alias has been retired

Evidence:

- [router.py](/backend/app/api/v1/router.py)
- [classes.py](/backend/app/api/v1/endpoints/classes.py)

Treatment:

- keep `/sections` as the only first-class route in frontend and docs
- migrate remaining callers and tests to `/sections`
- remove the alias mount and permission matrix row

Current implementation status:

- backend `/classes` route is no longer mounted
- permission registry no longer includes the `/classes` alias row
- backend test callers were migrated to `/sections`

Dependencies blocking removal:

- external clients outside this repository, if any

Exit condition:

- codebase-wide search shows no `/classes` consumer except migration docs

## 5. /notices vs /communication/announcements

Status:

- the duplicate page has been removed
- `/notices` remains only as a direct route alias to announcements

Canonical target:

- `/communication/announcements`

Treatment:

- stop calling `Notices` a separate module in UX
- keep the route only as a backward-compatible URL alias
- remove the page file and route-level module identity

Current implementation status:

- `NoticesPage.jsx` has been deleted
- `/notices` now redirects directly to `/communication/announcements` from routing

Dependencies blocking removal:

- any old links/bookmarks
- student navigation assumptions if any old path still exists externally

Exit condition:

- route alias removed or clearly documented as alias-only

## 6. Admin Academic Structure Page

Status:

- shell retired
- `/admin/academic-structure` now redirects to `/faculties`

Evidence:

- [AdminAcademicStructurePage.jsx](/frontend/src/pages/Admin/AdminAcademicStructurePage.jsx)

Treatment:

- merge into direct canonical navigation
- retain the admin route only as a redirect target if needed for bookmarks

Current implementation status:

- `AdminAcademicStructurePage.jsx` has been deleted
- the admin route now redirects directly to `/faculties`

## 7. Admin Operations Page

Status:

- shell retired
- `/admin/operations` now redirects to `/students`

Evidence:

- [AdminOperationsPage.jsx](/frontend/src/pages/Admin/AdminOperationsPage.jsx)

Treatment:

- merge into direct canonical navigation
- retain the admin route only as a redirect target if needed for bookmarks

Current implementation status:

- `AdminOperationsPage.jsx` has been deleted
- the admin route now redirects directly to `/students`

## 8. Admin Clubs Page

Status:

- shell retired
- `/admin/clubs` now redirects to `/clubs`

Evidence:

- [AdminClubsPage.jsx](/frontend/src/pages/Admin/AdminClubsPage.jsx)

Treatment:

- merge into `Clubs`
- remove the wrapper when it has no unique admin-only behavior

Current implementation status:

- `AdminClubsPage.jsx` has been deleted
- the admin route now redirects directly to `/clubs`

## 9. Admin Communication Page

Status:

- shell retired
- `/admin/communication` now redirects to `/communication/announcements`

Evidence:

- [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx)

Treatment:

- merge into direct communication navigation
- remove the wrapper when it no longer owns necessary admin-only functionality

Current implementation status:

- `AdminCommunicationPage.jsx` has been deleted
- the admin route now redirects directly to `/communication/announcements`

## 10. Admin Compliance Page

Status:

- shell retired
- `/admin/compliance` now redirects to `/audit-logs`

Evidence:

- [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx)
- [AuditLogsPage.jsx](/frontend/src/pages/AuditLogsPage.jsx)

Treatment:

- merge into audit/governance reporting
- retain the admin route only as a redirect target if needed for bookmarks

Current implementation status:

- `AdminCompliancePage.jsx` has been deleted
- the admin route now redirects directly to `/audit-logs`

## 11. Admin Dashboard Page

Status:

- shell/control-plane page composed from other admin surfaces

Evidence:

- [AdminDashboardPage.jsx](/frontend/src/pages/Admin/AdminDashboardPage.jsx)

Treatment:

- keep as control-plane landing page
- do not count it as a duplicate business module in docs or planning

Recommended treatment:

- keep

Decision:

- `AdminDashboardPage` should stay
- reason: it still owns a unique admin-only overview by combining governance state, system health, and admin analytics on one page instead of acting as a plain link shell

## 12. Permission Duplicates

Status:

- legacy academic permissions still coexist with canonical permissions

Evidence:

- [permission_registry.py](/backend/app/core/permission_registry.py)

Duplicate permission items:

- `courses.manage`
- `years.manage`
- `branches.manage`
- `/classes` legacy route matrix entry

Treatment:

- removed together with the retired legacy routes

Exit condition:

- completed

## Suggested Execution Order

1. Finish canonical migration for `course_id`, `year_id`, and `branch_name`
2. Retire `courses`, `years`, and `branches`
3. Remove `/classes` alias
4. Remove `NoticesPage.jsx` as a separate surface
5. Collapse admin shell pages one by one and keep only the ones with real admin-only value

## Recommended Decisions Summary

### Retire

1. `Courses`
2. `Years`
3. `Branches`
4. `/classes` alias
5. `/notices` page identity

### Keep Temporarily

1. legacy academic permissions until migration is complete
2. admin landing pages that still provide role-specific value

### Merge Or Collapse Later

1. `AdminOperationsPage`
2. `AdminClubsPage`
3. possibly `AdminAcademicStructurePage`
4. possibly `AdminCompliancePage`

## Bottom Line

The project’s duplicate burden is manageable. The real cleanup work is not broad deletion; it is a controlled retirement of:

- legacy academic compatibility modules
- old route aliases
- thin admin wrappers that do not own unique business logic



