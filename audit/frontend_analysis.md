# Frontend Analysis

Generated: 2026-03-31

## Validation Summary

- `npm --prefix frontend run typecheck`: passed
- `npm --prefix frontend run test:ci`: 7 files, 26 tests passed
- `npm --prefix frontend run lint`: passed
- `npm --prefix frontend run build`: passed
- `npm --prefix frontend run check:bundle`: passed

## Current Strengths

- The frontend uses a coherent workspace shell with route-level protection, role-aware navigation groups, and an API client that understands backend response envelopes.
- The student onboarding experience is intentionally productized rather than bolted on. `StudentBulkWorkflow` supports preview, commit, lock, unlock, and template download behavior.
- Communication has a real supported product path through announcements, feed, and notifications.
- Admin pages align with live backend surfaces, especially onboarding, analytics, governance, recovery, and system health.

## Repo-Based Findings

### 1. Direct messaging UI exists but is not a live supported route

Evidence:

- `frontend/src/pages/Communication/MessagesPage.jsx` exists
- `ConversationList.jsx` and `ChatWindow.jsx` exist
- route configuration redirects `/communication/messages` to announcements instead of rendering the page

Impact:

- dead or deferred UI code is still shipped in the repo tree
- maintainers may misread this as a supported feature

Recommended fix:

- either remove the deferred messaging UI
- or explicitly re-enable it with a backend contract and route binding

### 2. `Topbar.jsx` is orphaned

Evidence:

- `frontend/src/components/layout/Topbar.jsx` has no imports
- the active layout uses `Header.tsx`, `Sidebar.tsx`, and `AppLayout.tsx`

Impact:

- unnecessary maintenance surface

Recommended fix:

- delete `Topbar.jsx` after approval

### 3. Some key screens are large enough to justify decomposition

Measured file sizes:

- `frontend/src/pages/AcademicStructurePage.jsx`: 998 lines
- `frontend/src/components/students/StudentBulkWorkflow.jsx`: 733 lines

Impact:

- high UI complexity concentrates in a few files
- future behavior changes will be harder to test and review

Recommended fix:

- split `AcademicStructurePage` by hierarchy level or shared manager sections
- split `StudentBulkWorkflow` into destination selection, upload, preview, and commit subpanels

### 4. Bundle budgets pass, but there are a few heavy long-term chunks

Validated bundle results:

- `charts-vendor`: 355.18 KiB against 390 KiB budget
- `react-vendor`: 160.85 KiB against 180 KiB budget
- `motion-vendor`: 124.02 KiB against 140 KiB budget
- `app-entry`: 81.26 KiB against 90 KiB budget
- `total-js`: 1303.18 KiB against 1400 KiB budget

Impact:

- performance is currently within guardrails
- charting and vendor growth have limited headroom before budget breaches

Recommended fix:

- keep analytics and dashboard dependencies from spreading into more routes
- continue route-level lazy loading for admin-heavy surfaces

## Current Verdict

The frontend is healthy and production-shaped. The most important cleanup opportunities are removing deferred or orphaned UI files and reducing page-level complexity in the largest admin flows.
