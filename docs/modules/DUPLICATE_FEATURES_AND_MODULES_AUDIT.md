# Duplicate Features And Modules Audit

Reviewed on `2026-03-11`.

This audit identifies duplicate or overlapping features and modules across the project.

Scope reviewed:

- frontend routes and pages
- frontend navigation groups
- backend API router and permissions
- module documentation structure

## Classification

- `Confirmed duplicate`: same entity or workflow exposed twice
- `Legacy duplicate`: deprecated compatibility surface for a canonical module
- `Admin shell overlap`: admin route that mostly wraps or links to existing modules
- `Related overlap`: adjacent surfaces with shared data but still materially different

## Confirmed And Legacy Duplicates

| Area | Duplicate Pair | Type | Evidence | Recommended Action |
|---|---|---|---|---|
| Academic entities | `Courses` vs `Programs` | `Legacy duplicate` | [router.py](/backend/app/api/v1/router.py), [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx), [ProgramsPage.jsx](/frontend/src/pages/ProgramsPage.jsx) | completed: legacy route removed, frontend path now redirects to programs |
| Academic entities | `Years` vs `Batches` / `Semesters` | `Legacy duplicate` | [router.py](/backend/app/api/v1/router.py), [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx), [BatchesPage.jsx](/frontend/src/pages/BatchesPage.jsx) | completed: legacy route removed, frontend path now redirects to batches |
| Academic entities | `Branches` vs `Specializations` / `Programs` | `Legacy duplicate` | [router.py](/backend/app/api/v1/router.py), [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx), [SpecializationsPage.jsx](/frontend/src/pages/SpecializationsPage.jsx) | completed: legacy route removed, frontend path now redirects to specializations |
| Section entity | `/classes` vs `/sections` | `Confirmed duplicate` | [router.py](/backend/app/api/v1/router.py), [classes.py](/backend/app/api/v1/endpoints/classes.py), [test_academic_permissions.py](/backend/tests/test_academic_permissions.py) | completed: `/classes` alias removed; `/sections` is the only public section route |
| Announcements | `/notices` page vs `/communication/announcements` | `Confirmed duplicate` | [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx), [AnnouncementsPage.jsx](/frontend/src/pages/Communication/AnnouncementsPage.jsx) | completed: `/notices` is only a direct route alias to announcements |

## Admin Shell Overlaps

These are not separate business modules. They are admin entry surfaces layered on top of existing modules.

| Admin Surface | Overlapping Real Modules | Type | Evidence | Recommended Action |
|---|---|---|---|---|
| `Admin Academic Structure` | `Faculties`, `Departments`, `Programs`, `Specializations`, `Batches`, `Semesters`, `Sections` | `Admin shell overlap` | [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx) now redirects `/admin/academic-structure` to `/faculties` | completed: shell removed and route collapsed into canonical academic setup |
| `Admin Operations` | `Students`, `Subjects`, `Assignments`, `Submissions`, `Evaluations`, `Review Tickets`, `Enrollments` | `Admin shell overlap` | [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx) now redirects `/admin/operations` to `/students` | completed: shell removed and route collapsed into canonical operations entry |
| `Admin Clubs` | `Clubs` | `Admin shell overlap` | [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx) now redirects `/admin/clubs` to `/clubs` | completed: shell removed and route collapsed into clubs hub |
| `Admin Communication` | `Announcements`, `Feed`, audience preview | `Admin shell overlap` | [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx) now redirects `/admin/communication` to `/communication/announcements` | completed: shell removed and route collapsed into announcements |
| `Admin Compliance` | `Audit Logs`, analytics audit summary | `Admin shell overlap` | [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx) now redirects `/admin/compliance` to `/audit-logs` | completed: shell removed and route collapsed into audit logs |
| `Admin Dashboard` | `Dashboard`, `Admin Analytics`, `Admin System`, governance dashboard | `Admin shell overlap` | [AdminDashboardPage.jsx](/frontend/src/pages/Admin/AdminDashboardPage.jsx) still aggregates governance, system health, and admin analytics into one admin-only control-plane surface | keep: this still has unique control-plane value |

## Related Overlaps, Not Strict Duplicates

These share domain data, but they are not interchangeable yet.

| Area | Surfaces | Type | Why Not A Full Duplicate |
|---|---|---|---|
| Analytics | `Dashboard` vs `Analytics` vs `Admin Analytics` | `Related overlap` | all use summary-style metrics, but audience and scope differ: personal workflow, operational analytics, platform analytics |
| Communication | `Announcements` vs `Notifications` vs `Feed` | `Related overlap` | `Announcements` are authored notices, `Notifications` are alert objects, `Feed` is an aggregated timeline across notices, notifications, assignments, and evaluations |
| Academic overview | `AcademicStructurePage` vs `AdminAcademicStructurePage` | `Related overlap` | one is the canonical hierarchical explorer, the other is an admin landing page for setup modules |
| Clubs | `Clubs`, `Club Events`, `Event Registrations` | `Related overlap` | layered domain flow, not duplicates |

## Permission-Level Duplicates

The permission system still carries duplicate legacy academic controls alongside canonical controls.

Evidence:

- [permission_registry.py](/backend/app/core/permission_registry.py)

Legacy duplicates previously present here have been retired:

- `courses.manage`
- `years.manage`
- `branches.manage`
- `/courses` in `ACADEMIC_ROUTE_PERMISSION_MATRIX`
- `/years` in `ACADEMIC_ROUTE_PERMISSION_MATRIX`
- `/branches` in `ACADEMIC_ROUTE_PERMISSION_MATRIX`
- `/classes` in `ACADEMIC_ROUTE_PERMISSION_MATRIX`

Current status:

- no active permission-level duplicate from the retired academic modules remains

## Documentation Overlaps

These are documentation overlaps, but not necessarily bad duplicates.

| Doc Set | Type | Note |
|---|---|---|
| `AI_MODULE_MASTER.md`, `AI_MODULE_ACTION_PLAN.md`, `AI_MODULE_CONTRACTS.md` | `Intentional companion docs` | same module area, but each has a distinct purpose: master reference, plan, and contracts |
| Admin domain pages vs module masters | `Naming overlap` | several admin pages look like independent modules, but they are mostly shells over existing modules |

## Net Duplicate Inventory

### True duplicates retired

1. `/classes` alias in favor of `/sections`
2. `/notices` page identity in favor of `/communication/announcements`
3. legacy academic modules:
   - `courses`
   - `years`
   - `branches`

### Overlapping shells to treat as navigation, not modules

1. `AdminDashboardPage`

## Recommended Consolidation Order

1. Completed: retire legacy academic modules from public routing and permissions.
2. Completed: remove `/classes` from public routing after migrating callers to `/sections`.
3. Completed: remove `NoticesPage.jsx` as a standalone surface.
4. Completed: collapse `AdminAcademicStructurePage`, `AdminOperationsPage`, and `AdminClubsPage` into canonical routes.
5. Completed: collapse `AdminCommunicationPage` and `AdminCompliancePage` into canonical routes.
6. Decision: keep `AdminDashboardPage` as the admin control-plane landing page because it still combines unique governance, analytics, and system-health signals.

## Bottom Line

The project does not have a large number of random duplicates. It has three concentrated duplication patterns:

1. retired legacy academic compatibility modules
2. retired duplicate route aliases and redirect pages
3. one remaining intentional admin shell page: the control-plane dashboard

That means consolidation is feasible without redesigning the whole system.


