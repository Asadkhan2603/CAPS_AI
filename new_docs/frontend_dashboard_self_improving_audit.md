# SELF-IMPROVING FRONTEND + DASHBOARD AUDIT SYSTEM

## 🗓 Current Audit Date:
2026-04-02 17:35:54 IST (UTC+05:30)

## 📦 Project:
CAPS AI

## Update History

| Timestamp | Update | Source |
|----------|--------|--------|
| 2026-04-02 17:35:54 IST (UTC+05:30) | Initial living frontend/dashboard audit created from route inspection, API contract review, frontend build, typecheck, and vitest results. | Codex Audit System |

---

# 📊 CURRENT SYSTEM SCORES

| Category | Score | Previous Score | Trend ↑↓ | Remarks |
|----------|------|---------------|----------|--------|
| Layout | 63/100 | N/A | Baseline | Core shell is polished, but route/page mismatches and unreachable setup screens weaken structure clarity. |
| Dashboard | 44/100 | N/A | Baseline | Dashboard loads and refreshes, but the trend chart is labeled live while using hardcoded data. |
| Feature Reality | 28/100 | N/A | Baseline | Multiple prominent workflows exist as UI files or tests without real routing or backend support. |
| UX | 47/100 | N/A | Baseline | Primary tasks are discoverable, but false affordances and broken admin flows hurt confidence. |
| Human Ease | 41/100 | N/A | Baseline | Non-technical admins face too much ambiguity across sections, onboarding, RBAC, and bulk operations. |
| Integration | 31/100 | N/A | Baseline | Frontend routes, navigation tests, and backend mounts are materially out of sync. |
| Trust | 33/100 | N/A | Baseline | Build and typecheck pass, but fake/live claims, dead workflows, and failing tests reduce product trust. |

---

# 📈 SCORE EVOLUTION HISTORY

| Date | Layout | UX | Reality | Trust | Notes |
|------|--------|----|--------|-------|------|
| 2026-04-02 17:35:54 IST | 63 | 47 | 28 | 33 | Baseline created. `npm run build` and `npm run typecheck` passed. `npm run test:ci` failed on navigation drift, missing auth helpers, and missing Playwright dependency. |

---

# 🚨 ACTIVE ISSUES TRACKER

| ID | Issue | Severity | Status | Phase | Owner | Last Update |
|----|------|----------|--------|-------|-------|------------|
| FD-001 | `/sections` still resolves to legacy classes experience and legacy backend router | High | ❌ Open | Phase 2 | Frontend + Backend | 2026-04-02 17:35 IST |
| FD-002 | Admin onboarding wizard exists in code but is not routed and its API contract is missing | High | ❌ Open | Phase 1 | Frontend + Backend | 2026-04-02 17:35 IST |
| FD-003 | RBAC control center exists in UI code but backend router is not mounted and imports are broken | Critical | ❌ Open | Phase 2 | Backend + Admin Frontend | 2026-04-02 17:35 IST |
| FD-004 | Student bulk onboarding and section mapping are mostly unreachable and unsupported | Critical | ❌ Open | Phase 2 | Frontend + Backend | 2026-04-02 17:35 IST |
| FD-005 | Dashboard trend card claims live analytics while rendering static chart data | High | ❌ Open | Phase 1 | Frontend + Analytics | 2026-04-02 17:35 IST |
| FD-006 | Header quick search is a false affordance with no behavior | Medium | ❌ Open | Phase 1 | Frontend | 2026-04-02 17:35 IST |
| FD-007 | Navigation rules, route surface, and test expectations are drifting | High | ❌ Open | Phase 2 | Frontend | 2026-04-02 17:35 IST |
| FD-008 | UI crash handling stops at `console.error` with no reporting path | Medium | ❌ Open | Phase 4 | Frontend + Platform | 2026-04-02 17:35 IST |

Statuses:
- ❌ Open
- ⚠️ In Progress
- ✅ Fixed
- 🔁 Reopened

---

# 🔍 ISSUE DETAIL (FOR EACH ISSUE)

### Issue ID: FD-001

- Description: The product exposes a "Sections" concept, but the active route and active API mount still point to the older classes implementation.
- Type: Layout / Dashboard / UX / Reality / Integration
- Root Cause: Frontend route aliasing and backend router mounting were not cut over to the newer section contract.
- Impact: Admins reach the wrong management surface, section-locking and sync-group capabilities stay unavailable, and future fixes risk landing in the wrong code path.
- Affected Pages: `/sections`, `/academic-structure`, any workflow that depends on section lock state or sync-groups.
- Fix Plan: Route `/sections` to `SectionsPage`, mount `backend.app.api.v1.endpoints.sections` at `/sections`, keep temporary compatibility aliases only for migrated callers, and retire the legacy classes-first ownership model.
- Linked Test Case: `TC-FD-001 Sections Surface Uses Canonical Contract`
- Status History:
  - 2026-04-02 17:35 IST -> ❌ Open (baseline audit created)

---

### Issue ID: FD-002

- Description: An admin onboarding wizard page exists, but it is not part of the route graph and it calls an endpoint that is not implemented by the mounted admin analytics API.
- Type: Dashboard / UX / Reality / Integration
- Root Cause: Product surface was designed ahead of contract delivery and never gated behind route availability checks.
- Impact: The product promises setup guidance it cannot currently deliver, which damages first-run trust for admins.
- Affected Pages: `AdminOnboardingPage`, admin analytics navigation expectations, onboarding-related test expectations.
- Fix Plan: Either add route and backend endpoint parity immediately or remove/hide the wizard until the real onboarding contract is ready.
- Linked Test Case: `TC-FD-002 Onboarding Wizard Reachability`
- Status History:
  - 2026-04-02 17:35 IST -> ❌ Open (baseline audit created)

---

### Issue ID: FD-003

- Description: The RBAC management UI is implemented in the frontend, but the backend router is not mounted and the backend module imports `check_role`, which is not available in the security module.
- Type: Dashboard / UX / Reality / Integration
- Root Cause: Frontend admin tooling shipped before backend mount/boot verification was completed.
- Impact: Role governance is effectively fake from a product perspective and can mislead super admins during audits or demos.
- Affected Pages: `AdminRbacPage`, admin governance flows, admin navigation tests, RBAC service layer.
- Fix Plan: Replace the invalid guard import, mount `/admin/rbac`, add route entries for the page, and verify the full admin CRUD flow with API-backed smoke coverage.
- Linked Test Case: `TC-FD-003 RBAC Control Center Is Operational`
- Status History:
  - 2026-04-02 17:35 IST -> ❌ Open (baseline audit created)

---

### Issue ID: FD-004

- Description: Student bulk onboarding and coordinator section mapping are implemented as standalone UI files, but they are not part of the active route surface, depend on unsupported endpoints, and reference missing section API exports.
- Type: Layout / UX / Reality / Integration
- Root Cause: High-value workflow UI was developed outside the active module graph, which also allowed contract defects to hide from the production build.
- Impact: Large-scale student onboarding remains blocked, and operations teams are pushed toward manual entry or unsupported processes.
- Affected Pages: `StudentBulkImportPage`, `CoordinatorStudentMappingPage`, `StudentBulkWorkflow`, student onboarding operations.
- Fix Plan: Add canonical routes, implement `/students/bulk-import/preview` and `/students/bulk-import/commit`, export section lock/unlock helpers, and validate both admin and coordinator workflows end to end.
- Linked Test Case: `TC-FD-004 Bulk Onboarding And Mapping Flow`
- Status History:
  - 2026-04-02 17:35 IST -> ❌ Open (baseline audit created)

---

### Issue ID: FD-005

- Description: The main dashboard trend card is labeled "Live Analytics" but renders static `performanceData`.
- Type: Dashboard / UX / Reality
- Root Cause: Placeholder visualization was left in place after real dashboard summary loading was added.
- Impact: Users can interpret sample trends as live operational insight, which is a direct trust risk.
- Affected Pages: `/dashboard`
- Fix Plan: Replace chart data with API-backed metrics from the dashboard analytics contract or relabel the card as sample/demo data until real metrics exist.
- Linked Test Case: `TC-FD-005 Dashboard Trend Integrity`
- Status History:
  - 2026-04-02 17:35 IST -> ❌ Open (baseline audit created)

---

### Issue ID: FD-006

- Description: The header exposes a quick search input with no handlers, results, shortcut, or navigation behavior.
- Type: UX / Reality
- Root Cause: Search affordance was added to the layout shell before a real search experience was implemented.
- Impact: Users are invited into a dead interaction that quietly lowers trust in the rest of the interface.
- Affected Pages: Global header across authenticated screens.
- Fix Plan: Either wire the input to the existing quick-search utility and result surface or remove the control until it has real behavior.
- Linked Test Case: `TC-FD-006 Header Search Has Real Behavior`
- Status History:
  - 2026-04-02 17:35 IST -> ❌ Open (baseline audit created)

---

### Issue ID: FD-007

- Description: Navigation configuration, route availability, and test expectations do not match, and frontend CI also fails because `apiClient` test helpers are missing while Playwright-based role specs require an uninstalled dependency.
- Type: Layout / UX / Reality / Integration
- Root Cause: Navigation and auth contracts evolved without keeping tests and package setup aligned.
- Impact: CI signal is unreliable, role-based navigation confidence is low, and product expectations drift faster than the shipped surface.
- Affected Pages: Workspace navigation, role-based landing flows, frontend CI.
- Fix Plan: Make route registry the source of truth for navigation, align tests to shipped routes, restore or remove tested auth helper exports, and explicitly install or exclude Playwright specs from Vitest runs.
- Linked Test Case: `TC-FD-007 Navigation Contract Matches Tests`
- Status History:
  - 2026-04-02 17:35 IST -> ❌ Open (baseline audit created)

---

### Issue ID: FD-008

- Description: The global error boundary only logs crashes to the console and offers a reload button.
- Type: UX / Integration / Trust
- Root Cause: Crash reporting integration was deferred.
- Impact: Production crashes can disappear without actionable telemetry, making trust recovery and debugging slower.
- Affected Pages: Entire authenticated app shell.
- Fix Plan: Connect the error boundary to a real reporting sink with route, user, and release context, and add a user-facing fallback path for known recoverable failures.
- Linked Test Case: `TC-FD-008 Crash Reporting Is Captured`
- Status History:
  - 2026-04-02 17:35 IST -> ❌ Open (baseline audit created)

---

# 🚨 FEATURE REALITY CHECK (AUTO-UPDATING)

| Feature | Status (Real/Fake/Partial) | Last Checked | Fix Progress |
|---------|----------------------------|--------------|-------------|
| Dashboard summary cards from `/analytics/dashboard` | Partial | 2026-04-02 17:35 IST | Data loads, but the trend card still uses static chart data. |
| Dashboard trend analytics | Fake | 2026-04-02 17:35 IST | Replace static `performanceData` or relabel as sample data. |
| Sections management | Partial | 2026-04-02 17:35 IST | Active route and backend mount still use legacy classes behavior. |
| Section lock/unlock controls | Fake | 2026-04-02 17:35 IST | UI depends on non-exported frontend helpers and non-mounted backend endpoints. |
| Admin onboarding wizard | Fake | 2026-04-02 17:35 IST | Page exists off-route and calls a missing endpoint. |
| RBAC control center | Fake | 2026-04-02 17:35 IST | Frontend exists, backend router not mounted, backend import broken. |
| Student bulk onboarding | Fake | 2026-04-02 17:35 IST | UI exists outside route graph and backend endpoints are absent. |
| Coordinator section mapping | Fake | 2026-04-02 17:35 IST | Depends on inactive route surface and missing contract support. |
| Header quick search | Fake | 2026-04-02 17:35 IST | Search field has no behavior. |
| Crash reporting | Partial | 2026-04-02 17:35 IST | Local fallback exists, telemetry integration does not. |

⚠️ Update this whenever feature status changes

---

# 🔄 USER WORKFLOW TRACKER

### Workflow: Admin First-Time Setup

| Step | Status | Issue | Fix | Last Updated |
|------|--------|------|-----|-------------|
| Open admin entry point | Partial | Admin dashboard is reachable, but onboarding wizard is not part of the route surface | Add a real `/admin/onboarding` route or remove the promise from tests and nav | 2026-04-02 17:35 IST |
| Review setup progress | Fake | Wizard calls missing `/admin/analytics/onboarding-overview` | Implement endpoint or hide the workflow | 2026-04-02 17:35 IST |
| Jump to required next action | Fake | Next-step contract depends on missing wizard data | Gate CTA generation behind a working contract | 2026-04-02 17:35 IST |

Completion Score: 20/100

---

### Workflow: RBAC Governance

| Step | Status | Issue | Fix | Last Updated |
|------|--------|------|-----|-------------|
| Discover RBAC workspace | Fake | No active route exposes the page | Add route and navigation entry | 2026-04-02 17:35 IST |
| Load role catalog | Fake | Backend router is not mounted | Mount `/admin/rbac` | 2026-04-02 17:35 IST |
| Create/update admin role | Fake | Backend boot path is broken by invalid security import | Replace invalid guard and verify boot | 2026-04-02 17:35 IST |

Completion Score: 10/100

---

### Workflow: Student Bulk Onboarding

| Step | Status | Issue | Fix | Last Updated |
|------|--------|------|-----|-------------|
| Open bulk onboarding screen | Fake | Screen exists in source but is not routed | Register canonical routes | 2026-04-02 17:35 IST |
| Upload roster and preview | Fake | `/students/bulk-import/preview` is not available | Implement preview endpoint | 2026-04-02 17:35 IST |
| Commit valid rows | Fake | `/students/bulk-import/commit` is not available | Implement commit endpoint | 2026-04-02 17:35 IST |
| Lock target section after mapping | Fake | Frontend helper exports and mounted backend endpoints are missing | Ship lock/unlock contract end to end | 2026-04-02 17:35 IST |

Completion Score: 5/100

---

### Workflow: Sections Management

| Step | Status | Issue | Fix | Last Updated |
|------|--------|------|-----|-------------|
| Navigate to sections | Partial | User lands on legacy classes experience | Route to `SectionsPage` | 2026-04-02 17:35 IST |
| Manage advanced section operations | Fake | Sync-group and mapping lock flows are not active at runtime | Mount new sections router | 2026-04-02 17:35 IST |
| Keep navigation and tests aligned | Partial | Nav/tests still expect pages not in route graph | Generate nav from route registry | 2026-04-02 17:35 IST |

Completion Score: 35/100

---

# ⏱ TIME-TO-TASK TRACKER

| Task | Previous Time | Current Time | Improvement | Status |
|------|--------------|-------------|------------|-------|
| Reach working sections manager | N/A | 2 to 4 minutes plus wrong page detour | Baseline | Needs contract cutover |
| Verify admin onboarding progress | N/A | Blocked | Baseline | Broken |
| Create or adjust RBAC roles | N/A | Blocked | Baseline | Broken |
| Bulk onboard a student cohort | N/A | Blocked | Baseline | Broken |
| Read a real dashboard trend | N/A | Under 1 minute, but trust is low because data is static | Baseline | Misleading |

---

# 📐 LAYOUT & RESPONSIVENESS TRACKER

| Area | Issue | Status | Fix Applied | Verified |
|------|------|--------|-------------|----------|
| Global header | Quick search field is visually present but functionally dead | ❌ Open | No | Code audit |
| Workspace route shell | Several feature pages exist outside the active route graph | ❌ Open | No | Code audit |
| Sections surface | `/sections` resolves to legacy page ownership | ❌ Open | No | Code audit |
| Modal system | Shared modal lacks a hardened accessibility contract for admin workflows | ❌ Open | No | Code audit |
| Student bulk workflow layout | Rich UI exists, but not in the active experience users can reach | ❌ Open | No | Code audit |

---

# 📊 DASHBOARD FEATURE TRACKER

| Feature | Placement | Status | Improvement | Verified |
|--------|----------|--------|------------|----------|
| Summary cards | Main dashboard hero | Partial | Real API summary exists; keep aligned to available permissions | Frontend runtime contract review |
| Trend chart | Main analytics card | ❌ Misleading | Replace static chart data or rename it | Code audit |
| Refresh Insights | Dashboard side card | Partial | Refreshes summary payload but not the hardcoded trend dataset | Code audit |
| Urgent notices | Dashboard content panel | Real | Keep current API linkage | Code audit |
| Student timetable/deadlines | Student dashboard | Partial | Works from dashboard payload, but still needs broader workflow validation | Code audit |

---

# 🧠 HUMAN EASE TRACKER

| Page | Score (Before) | Score (After) | Improvement | Notes |
|------|---------------|--------------|------------|------|
| Dashboard | N/A | 55/100 | Baseline | Fast to scan, but "Live Analytics" overstates reality. |
| Sections | N/A | 42/100 | Baseline | Naming and routing ambiguity make the feature harder than it should be. |
| Admin onboarding | N/A | 15/100 | Baseline | Promise exists, working flow does not. |
| RBAC admin | N/A | 10/100 | Baseline | Complex UI exists off-route and without a stable contract. |
| Student bulk onboarding | N/A | 8/100 | Baseline | High-effort UI cannot currently translate into a working task. |

---

# 🧪 AUTO TEST CASE GENERATION (MANDATORY)

### Test Case: TC-FD-001 Sections Surface Uses Canonical Contract

- Scenario: An admin opens the sections area and should land on the canonical sections experience backed by the canonical sections API.
- Steps:
  1. Sign in as an admin user with section permissions.
  2. Navigate to `/sections`.
  3. Trigger a list fetch and open any advanced section action.
- Expected Result: `SectionsPage` loads, section rows come from the mounted sections router, and advanced section actions such as lock/sync are available when permitted.
- Failure Condition: User lands on the legacy classes page or advanced section actions are unavailable because the wrong router is mounted.

---

### Test Case: TC-FD-002 Onboarding Wizard Reachability

- Scenario: An admin should be able to access the onboarding wizard only if the supporting API contract exists.
- Steps:
  1. Sign in as an admin.
  2. Navigate to `/admin/onboarding` from nav or direct URL.
  3. Observe the network call for onboarding overview.
- Expected Result: The page is routed, returns data from `/admin/analytics/onboarding-overview`, and shows next-step guidance.
- Failure Condition: Route is missing, page is unreachable, or the API call 404s.

---

### Test Case: TC-FD-003 RBAC Control Center Is Operational

- Scenario: A super admin opens RBAC and manages roles through a real API surface.
- Steps:
  1. Sign in as a super admin.
  2. Open `/admin/rbac`.
  3. Load design, permissions, roles, and admins.
  4. Create a test role and update an admin assignment.
- Expected Result: All RBAC endpoints respond successfully and UI state refreshes from backend data.
- Failure Condition: Route is missing, requests 404, or backend startup fails on the RBAC module.

---

### Test Case: TC-FD-004 Bulk Onboarding And Mapping Flow

- Scenario: Admin bulk onboarding and coordinator mapping should both run through a safe preview-and-commit contract.
- Steps:
  1. Sign in as an admin and open `/students/bulk-import`.
  2. Upload a valid template file and request preview.
  3. Commit valid rows.
  4. Sign in as a coordinator and open `/students/section-mapping`.
  5. Lock and unlock a permitted section after mapping.
- Expected Result: Both routes are reachable, preview and commit endpoints respond, and section mapping lock state updates correctly.
- Failure Condition: Routes are unreachable, endpoints are missing, or section lock/unlock helpers fail.

---

### Test Case: TC-FD-005 Dashboard Trend Integrity

- Scenario: Dashboard trend visualization must match real backend metrics or be clearly marked as sample data.
- Steps:
  1. Sign in to the dashboard.
  2. Record chart values before and after a data refresh.
  3. Compare rendered trend data with the backend analytics payload.
- Expected Result: Chart data comes from the backend or is explicitly labeled as sample/demo.
- Failure Condition: Card claims live analytics while rendering hardcoded values.

---

### Test Case: TC-FD-006 Header Search Has Real Behavior

- Scenario: Header quick search should perform a visible search action.
- Steps:
  1. Open any authenticated screen.
  2. Enter a query in the header search input.
  3. Submit or pause for results.
- Expected Result: Search results, navigation suggestions, or a search overlay appear.
- Failure Condition: Input accepts text but nothing happens.

---

### Test Case: TC-FD-007 Navigation Contract Matches Tests

- Scenario: Navigation visibility and route availability should match the automated tests and installed toolchain.
- Steps:
  1. Run `npm run test:ci`.
  2. Inspect role-based navigation expectations.
  3. Verify every asserted route exists in the route graph.
  4. Verify Playwright specs are either supported or excluded from the Vitest run.
- Expected Result: Frontend CI passes without missing route assertions, missing exports, or missing Playwright dependency errors.
- Failure Condition: Tests fail because the route surface and test expectations drift apart.

---

### Test Case: TC-FD-008 Crash Reporting Is Captured

- Scenario: A UI crash should create a structured observability event.
- Steps:
  1. Trigger a controlled render error inside the authenticated app.
  2. Observe the error boundary response.
  3. Check the reporting sink for a captured event.
- Expected Result: User sees the fallback UI and an error event is recorded with route and user context.
- Failure Condition: Error is only printed to the browser console.

---

# 🤖 AUTO-IMPROVEMENT ENGINE

After every audit/update:

1. Recalculate ALL scores using shipped route reachability, backend contract availability, build health, test health, and feature truthfulness.
2. Compare with previous scores. Current report is the baseline, so previous values are `N/A`.
3. Highlight improvements/regressions.
   Improvement signal: `npm run build` passed.
   Improvement signal: `npm run typecheck` passed.
   Regression signal: `npm run test:ci` failed.
   Regression signal: prominent admin and onboarding workflows are still not real.
4. Update issue statuses.
   Current status: all tracked issues remain `❌ Open`.
5. Suggest next priority actions.
   Immediate focus: remove fake admin surfaces or finish the missing contracts behind them.

---

# 📊 PRIORITY ENGINE

Automatically rank:

| Priority | Issue | Reason |
|----------|------|--------|
| P0 | FD-003 RBAC control center is not operational | High-risk admin governance surface is fake and backend boot path is broken. |
| P0 | FD-004 Student bulk onboarding and section mapping are unsupported | Core operational workflow for scale is blocked end to end. |
| P1 | FD-001 Sections contract cutover is incomplete | Canonical academic structure flow is split across legacy and new implementations. |
| P1 | FD-005 Dashboard trend integrity | "Live" claim with static data is a direct trust issue. |
| P2 | FD-007 Navigation/test drift | CI noise and route drift will keep reintroducing false product promises. |
| P2 | FD-006 Header quick search false affordance | Smaller than contract bugs, but visible on every authenticated page. |
| P2 | FD-008 Missing crash telemetry | Limits operational recovery and learning from frontend failures. |

---

# 🔄 PHASE TRACKING SYSTEM

| Phase | Goal | Status | Completion % | Notes |
|------|------|--------|-------------|------|
| Phase 1 | Remove fake UI | ⚠️ In Progress | 20% | Fake dashboard/live claims and dead search remain visible. |
| Phase 2 | Fix contracts | ⚠️ In Progress | 15% | Sections, RBAC, onboarding, and bulk import contracts are still misaligned. |
| Phase 3 | Fix layout | ⚠️ In Progress | 30% | Core shell works, but route/page ownership is still inconsistent. |
| Phase 4 | Improve UX | ⚠️ In Progress | 18% | Some polished surfaces exist, but trust and clarity gaps remain. |
| Phase 5 | Add features | ❌ Open | 5% | New features should pause until current promises are made real. |

---

# 📅 CONTINUOUS UPDATE LOG

| Date | Change | Impact | Updated By |
|------|-------|--------|-----------|
| 2026-04-02 17:35:54 IST | Created living frontend/dashboard audit baseline | Established tracked scores, active issues, workflow completion, and trust baseline | Codex Audit System |
| 2026-04-02 17:35:54 IST | Validated frontend health with build, typecheck, and vitest | Build confidence is moderate, but CI trust remains low because tests fail | Codex Audit System |

---

# 🔁 NEXT ACTIONS (AUTO-GENERATED)

- Highest priority fix: Finish or hide RBAC and bulk onboarding before any new admin UX work continues.
- Quick wins: Remove the "Live Analytics" badge or wire the chart to real data, and hide or implement header quick search.
- Risk areas: Admin trust, student onboarding at scale, route/test drift, and silent frontend crashes.
- Next audit trigger: Any route-map change, admin feature release, bulk import API implementation, or CI status improvement.

---

# 🧠 PRODUCT TRUST MONITOR

| Area | Trust Before | Trust Now | Change |
|------|-------------|-----------|--------|
| Dashboard analytics honesty | N/A | Low | Baseline |
| Admin governance confidence | N/A | Very Low | Baseline |
| Academic setup guidance | N/A | Very Low | Baseline |
| Student onboarding reliability | N/A | Very Low | Baseline |
| Global shell polish | N/A | Medium | Baseline |
| Frontend CI confidence | N/A | Low | Baseline |

---

# 📌 FINAL SYSTEM STATE

- System Health: Average
- Trend: Stable
- Deployment Readiness: No

