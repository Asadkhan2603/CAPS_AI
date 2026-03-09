# Frontend Modernization Plan and Product Cleanup

## Goal
Modernize CAPS AI frontend without breaking current backend contracts, role permissions, or workflows.

## Current Issues Found
- Too many overlapping entry points for the same workflow (Academic Structure + separate setup pages).
- Heavy CRUD-first UX; limited guidance for users (especially teachers/students).
- Low discoverability for critical actions (alerts, deadlines, pending approvals).
- Some admin-only/technical surfaces appear mixed with daily operations.

## Modernization Priorities (Execution Order)
1. App shell modernization (sidebar, topbar, typography, spacing, responsive behavior).
2. Dashboard redesign by role (admin/teacher/student specific KPIs and next actions).
3. Workflow-first pages (Assignments -> Submissions -> Evaluations with guided steps).
4. Data quality UX (empty states, skeleton loaders, clearer error messages).
5. Performance pass (table virtualization/pagination consistency, bundle trims, caching).
6. Accessibility pass (keyboard nav, focus states, ARIA labels, contrast validation).

## New Features to Add
1. Global command palette (`Ctrl/Cmd + K`)
- Fast page/action search: "Create Assignment", "Open Enrollments", "Post Notice".

2. Notification Center v2
- Mark-all-read, filters by module, deep links to affected records.

3. Student Progress Timeline
- Visual timeline per student: assignments, submissions, evaluations, review tickets.

4. Section Health Scorecard
- Per section risk summary: late submissions, low scores, similarity flags.

5. Draft + Schedule for Notices
- Save draft, publish later, preview target audience before publish.

6. Bulk Operations
- Bulk enrollment, bulk assign subject, bulk status updates, CSV import with validation report.

7. Audit Insights
- Not just raw logs; add anomaly indicators (sudden deletions, unusual privilege changes).

8. Personalization
- Pinned modules, last visited pages, role-specific quick actions.

9. Smart Forms
- Auto-suggest values based on context (teacher section, last used subject, current year).

10. In-app Help Layer
- Tooltips + "what this means" info for metrics and governance actions.

## Features to Remove or Simplify
1. Duplicate navigation surfaces
- Keep one canonical path for each domain.
- Recommended: keep `/academic-structure` for overview, keep setup pages for admin only.

2. Legacy naming/aliases in UI
- Keep backend alias compatibility only.
- UI should show one naming standard (Sections, Enrollment Number, etc.).

3. Developer Panel in production navigation
- Hide behind explicit dev flag/env gate.

4. Redundant refresh buttons everywhere
- Replace with auto-refresh + explicit global refresh where needed.

5. Overloaded single-page CRUD blocks
- Split long forms into tabs/steps where workflow is complex.

6. Non-actionable stats
- Remove metrics that do not lead to an action.

## Suggested Route/Product Cleanup
- Keep:
  - `/dashboard`
  - `/academic-structure` (read-focused map)
  - `/sections`, `/students`, `/subjects`, `/assignments`, `/submissions`, `/evaluations`, `/enrollments`
- Admin-only management routes remain but should be grouped under "Administration".
- Remove visible legacy routes from nav (keep redirects for backward compatibility only if needed).

## UX/Design System Upgrades
- Establish tokens for spacing/radius/typography hierarchy.
- Standardize card density and table toolbar patterns.
- Use one icon style and one button hierarchy system.
- Introduce consistent empty/error/success states as shared components.

## Performance and Engineering Upgrades
- Add request caching layer for read-heavy pages.
- Debounce search/filter requests.
- Add optimistic updates for simple toggle actions.
- Add frontend integration tests for role-based route visibility.

## Migration Strategy (Safe)
Phase 1: visual-only shell + shared components (no API changes).
Phase 2: role-specific dashboard modernization.
Phase 3: workflow page redesign (Assignments, Submissions, Evaluations, Enrollments).
Phase 4: remove redundant UI surfaces and hide technical panels.
Phase 5: telemetry + product analytics to validate impact.

## Success Metrics
- 30% reduction in clicks to complete key workflows.
- 40% faster first-action time after login.
- 50% drop in support issues around navigation confusion.
- Stable API error rate (no regression during migration).

## Immediate Next Implementation Sprint (Recommended)
1. Command palette + unified search.
2. Role-based dashboard cards and action queue.
3. Notice scheduler + draft mode.
4. Empty-state and error-state component unification.
