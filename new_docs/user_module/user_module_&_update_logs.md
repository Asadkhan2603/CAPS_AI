# User Module Complete Information

# Admin Users Operational Runbook

Last updated: 2026-04-15

## Purpose

Operate, monitor, and recover the Admin Users modernization stack in production.

## Ownership

- Primary: Admin Platform / Backend API team
- Secondary: Frontend admin workspace team
- Escalation: SRE/on-call lead

## Components Covered

- Backend: `backend/app/api/v1/endpoints/users.py`
- Frontend: `frontend/src/pages/UsersPage.jsx`
- Telemetry store: `users_admin_telemetry` collection
- Capability flags and rollout controls in runtime config

## Critical Endpoints

- `GET /users/admin/list`
- `GET /users/admin/capabilities`
- `POST /users/admin/telemetry`
- `GET /users/admin/dashboard`
- `GET /users/{user_id}/activity`
- `PATCH /users/{user_id}/status`
- `POST /users/bulk/status`
- `PATCH /users/bulk/extensions`

## Rollout Control Variables

- Stage gate:
  - `USERS_ROLLOUT_STAGE` (`internal_admins`, `super_admins`, `all_admins`)
- Internal admin cohort selectors (any match grants internal cohort):
  - `USERS_ROLLOUT_INTERNAL_USER_IDS`
  - `USERS_ROLLOUT_INTERNAL_EMAILS`
  - `USERS_ROLLOUT_INTERNAL_EMAIL_DOMAINS`
  - `USERS_ROLLOUT_INTERNAL_ADMIN_TYPES`
- Verification endpoint:
  - `GET /users/admin/capabilities` exposes `rollout_stage`, `rollout_cohort`, `rollout_access`, `rollout_reason`.

## Day-1 Operational Checks

1. Confirm users page loads for admin users.
2. Confirm `/users/admin/dashboard` returns populated payload.
3. Confirm telemetry writes appear in `users_admin_telemetry`.
4. Confirm capability flags reflect expected rollout state.
5. Confirm rollout stage and cohort behavior via `/users/admin/capabilities` using:
   - one internal-admin identity
   - one super-admin identity
   - one regular-admin identity

## Monitoring Signals

Use the users page "Pagination & API Latency" card and backend logs.

### Latency Signals

- `p95_duration_ms`
- `p99_duration_ms`
- `error_rate_pct`
- bucket-level latency trend

### Pagination Signals

- `avg_page`
- `avg_limit`
- `empty_page_rate_pct`
- `deep_page_rate_pct`
- top page-size distribution

### Telemetry Integrity Signals

- New telemetry rows continuously written during active use.
- No sustained `users.telemetry.persist_failed` log events.

## Initial Alert Thresholds (Recommended)

Tune after baseline is collected.

1. Error-rate warning: `error_rate_pct > 2%` for 15 minutes.
2. Error-rate critical: `error_rate_pct > 5%` for 10 minutes.
3. Latency warning: `p95_duration_ms > 1200` for 15 minutes.
4. Latency critical: `p95_duration_ms > 2500` for 10 minutes.
5. Pagination quality warning: `empty_page_rate_pct > 30%` for 30 minutes.
6. Pagination misuse warning: `deep_page_rate_pct > 40%` for 30 minutes.

## Incident Playbooks

### A) High API Latency

1. Check users dashboard for p95/p99 trend and error rate.
2. Verify database pressure and query performance.
3. Confirm indexes exist and are healthy.
4. Temporarily reduce blast radius:
   - Disable `USERS_CAPABILITY_IMPORT_EXPORT_ENABLED`.
   - Disable `USERS_CAPABILITY_BULK_OPERATIONS_ENABLED` if needed.
5. If still degraded, rollback latest backend/frontend release.

### B) Elevated Error Rate

1. Identify failing endpoint from logs/telemetry metadata.
2. Reproduce with minimal request payload.
3. Disable only impacted capability flag.
4. Validate core workspace still healthy.
5. Patch and redeploy, then re-enable capability.

### C) Pagination Degradation (High Empty/Deep Page Rates)

1. Verify client query synchronization and page reset on filter changes.
2. Check for stale page query params in links/bookmarks.
3. Validate server `total` and `total_pages` correctness.
4. Apply frontend hotfix if query-state bug is confirmed.

### D) Telemetry Ingestion Failure

1. Check for `users.telemetry.persist_failed` logs.
2. Validate DB write access to `users_admin_telemetry`.
3. Confirm index creation did not fail at startup.
4. Keep core features running; telemetry is best-effort.
5. Restore telemetry path and backfill only if required.

### E) Rollout Access Misconfiguration

1. Validate `USERS_ROLLOUT_STAGE` value (must be `internal_admins`, `super_admins`, or `all_admins`).
2. Validate internal cohort env lists for formatting (comma-separated, no whitespace-only values).
3. Call `/users/admin/capabilities` for affected account and inspect:
   - `rollout_cohort`
   - `rollout_access`
   - `rollout_reason`
4. If urgent, temporarily set `USERS_ROLLOUT_STAGE=all_admins` to restore access.
5. Correct selectors and return to intended stage.

## Fast Mitigation via Capability Flags

Disable features without full rollback:

- Workspace: `USERS_CAPABILITY_WORKSPACE_ENABLED`
- Activity: `USERS_CAPABILITY_ACTIVITY_ENABLED`
- Bulk ops: `USERS_CAPABILITY_BULK_OPERATIONS_ENABLED`
- Templates: `USERS_CAPABILITY_PERMISSION_TEMPLATES_ENABLED`
- Invitations: `USERS_CAPABILITY_INVITATIONS_ENABLED`
- Import/export: `USERS_CAPABILITY_IMPORT_EXPORT_ENABLED`
- Inline editing: `USERS_CAPABILITY_INLINE_EDITING_ENABLED`
- Compact mode: `USERS_CAPABILITY_COMPACT_DENSITY_ENABLED`
- Responsive workflows: `USERS_CAPABILITY_RESPONSIVE_WORKFLOWS_ENABLED`
- Telemetry: `USERS_ADMIN_TELEMETRY_ENABLED`
- Rollout cohort gate: `USERS_ROLLOUT_STAGE`

## Rollback Procedure

1. Announce incident and freeze new rollout changes.
2. Roll back cohort exposure first:
   - `all_admins -> super_admins -> internal_admins`
3. Disable impacted capabilities if required.
4. Revert frontend if UI regression is user-blocking.
5. Revert backend if endpoint behavior is unstable.
6. Verify:
   - users page health
   - critical admin actions
   - legacy `GET /users/` consumer behavior
7. Publish status update and next ETA.

## Post-Incident Checklist

- [x] Incident timeline documented.
- [x] Root cause identified.
- [x] Corrective action shipped.
- [x] Alert thresholds updated if needed.
- [x] Runbook updated with new learnings.
- [ ] Rollout resumed only after stable window (production stage gate; execute during live rollout window).

## Incident Record: Users Admin Modernization (2026-04-15)

### Timeline
- 2026-04-15 07:58 UTC (13:28 IST): UI regression confirmed (`Rendered more hooks than during the previous render`) while opening users drawer deep-link.
- 2026-04-15 08:12 UTC (13:42 IST): Root cause isolated to conditional hook-path mismatch during overlay state transitions.
- 2026-04-15 08:34 UTC (14:04 IST): Corrective patch shipped (stable hook ordering + controlled remount + focus-safe drawer lifecycle).
- 2026-04-15 09:02 UTC (14:32 IST): Regression tests and targeted users admin test suite passed; rollout docs updated.

### Root Cause
- Conditional render path in detail overlay created inconsistent hook execution order under rapid selected-user/tab transitions.

### Corrective Action
- Enforced consistent hook ordering and drawer lifecycle hardening.
- Added accessibility and keyboard/focus trap handling to reduce transitional state hazards.
- Added test coverage for users overlay and workspace behavior.

### Prevention Controls
- Users overlay keeps hooks unconditional before return branches.
- Added focused users admin frontend/backend tests in CI surface.
- Added users-admin observability alerts (error-rate, p95 latency, pagination quality) through existing operational routing.

## Planned Improvements

- ✅ Dedicated observability dashboard tiles in admin observability page.
- ✅ Automated alerting rules tied directly to users admin dashboard metrics (reusing existing operational routing/cooldown).

# Class Representative (CR) Operations Runbook

Last updated: 2026-04-16

## What CR Means

- `Class Representative (CR)` is a read-only student leadership permission for a specific section.
- Each section has two neutral seats:
  - `CR-1` (`cr_1` in APIs)
  - `CR-2` (`cr_2` in APIs)
- A CR can view section attendance risk, assignment submission gaps, and authority contacts.
- CRs cannot mark attendance, grade assignments, mutate discipline/status data, or manage other users.

## Who Can Assign CRs

- Admin users can manage CR seats.
- Year Head teachers can manage CR seats through the sections workspace.
- Assignment requires an audit reason.
- Replacement requires explicit confirmation in the UI before mutation.

## How To Assign CR

1. Open `Sections`.
2. Find the target section.
3. Select `Manage CRs`.
4. Choose `CR-1` or `CR-2`.
5. Select an active student from the same section.
6. Enter the reason.
7. Select `Assign Seat`.
8. Verify the seat displays the selected student.

## How To Replace CR

1. Open `Sections`.
2. Select `Manage CRs` for the target section.
3. Pick a new student for the occupied seat.
4. Enter the replacement reason.
5. Select `Review Replace`.
6. Confirm by selecting `Confirm Replace`.
7. Verify the previous student no longer has `class_representative` in `extended_roles`.

## How To Remove CR

1. Open `Sections`.
2. Select `Manage CRs`.
3. Enter the removal reason for the occupied seat.
4. Select `Clear Seat`.
5. Verify the seat becomes empty.
6. Verify the removed student no longer has `role_scope.class_representative`.

## Student CR Workspace

- Route: `/workspace/section-representative`
- Visible only when the student has `extended_roles: ["class_representative"]`.
- Uses `role_scope.class_representative.class_id` as the dashboard section.
- UI highlights read-only access, assigned section/seat, contact coverage, dashboard freshness, and a quick CR action guide.
- Shows:
  - assigned section and seat
  - attendance-risk students
  - missing assignment submissions
  - class coordinator, year head, HOD, dean, and fallback higher-authority contacts when available
- Attendance-risk students are sorted by lowest attendance first and show a compact progress indicator.
- Assignment cards show missing-submission counts and named missing students.

## Section CR Management UI

- `Manage CRs` opens the section governance panel from the `Sections` table.
- The panel shows both seats (`CR-1`, `CR-2`), current holder state, selected candidate preview, and audit reason guidance.
- Assignment buttons stay disabled until a student and reason are provided.
- Replacement uses a two-step flow: `Review Replace` then `Confirm Replace`.
- Clear/remove actions stay disabled until a reason is provided.

## Troubleshooting

### Missing Dashboard Access

1. Confirm the student has `class_representative` in `extended_roles`.
2. Confirm `role_scope.class_representative.class_id` matches the section.
3. Confirm the section is active.
4. Reassign the CR seat if the user binding and section seat are out of sync.

### Missing Authority Contacts

1. Confirm class coordinator is assigned to the section.
2. Confirm active year-head teacher exists.
3. Confirm active HOD/dean admin records exist using current `admin_type` or `rbac_role_code`.
4. Confirm contact phone exists in `profile.phone`.
5. If no direct contact exists, confirm fallback academic/super admin records exist.

## CR Verification Checklist

- [ ] Users admin permission templates include `Class Representative (CR)`.
- [ ] `CR-1` can be assigned with reason.
- [ ] `CR-2` can be assigned with reason.
- [ ] Replacing a CR requires confirmation.
- [ ] Removing a CR clears the student role/scope binding.
- [ ] Assigned CR can open `/workspace/section-representative`.
- [ ] Unassigned student cannot open another section dashboard.
- [ ] Dashboard is read-only.
- [ ] Audit logs include assign/replace/remove events.
- [ ] Telemetry includes CR assign/replace/remove/dashboard events.

# Admin Users Migration Guide

Last updated: 2026-04-15

## Purpose

Migrate `/workspace/administration/users` to the modern admin users stack with zero breakage for legacy `GET /users/` consumers.

## Scope

- Backend admin APIs (`/users/admin/*`, bulk endpoints, invitation/import/export/template endpoints).
- Frontend unified admin users workspace.
- Capability-flag and staged-cohort controlled rollout.
- Telemetry-backed validation (latency and pagination dashboards).

## Compatibility Guarantee

- `GET /users/` remains unchanged and must continue serving existing consumers.
- New admin flows use `/users/admin/list` and related admin endpoints.

## Pre-Deployment Checklist

1. Confirm backend and frontend artifacts are built and versioned.
2. Confirm database connectivity and backup point is available.
3. Confirm startup index creation is enabled in the target environment.
4. Confirm feature flags are present in environment config:
   - `USERS_CAPABILITY_WORKSPACE_ENABLED`
   - `USERS_CAPABILITY_ACTIVITY_ENABLED`
   - `USERS_CAPABILITY_BULK_OPERATIONS_ENABLED`
   - `USERS_CAPABILITY_PERMISSION_TEMPLATES_ENABLED`
   - `USERS_CAPABILITY_INVITATIONS_ENABLED`
   - `USERS_CAPABILITY_IMPORT_EXPORT_ENABLED`
   - `USERS_CAPABILITY_INLINE_EDITING_ENABLED`
   - `USERS_CAPABILITY_COMPACT_DENSITY_ENABLED`
   - `USERS_CAPABILITY_RESPONSIVE_WORKFLOWS_ENABLED`
   - `USERS_ADMIN_TELEMETRY_ENABLED`
5. Confirm staged rollout environment keys are configured:
   - `USERS_ROLLOUT_STAGE` (`internal_admins` | `super_admins` | `all_admins`)
   - `USERS_ROLLOUT_INTERNAL_USER_IDS` (comma-separated user IDs)
   - `USERS_ROLLOUT_INTERNAL_EMAILS` (comma-separated emails)
   - `USERS_ROLLOUT_INTERNAL_EMAIL_DOMAINS` (comma-separated domains)
   - `USERS_ROLLOUT_INTERNAL_ADMIN_TYPES` (comma-separated admin types; default includes `super_admin`)

## Recommended Rollout Sequence

1. Deploy backend first.
2. Validate new endpoints and indexes.
3. Deploy frontend.
4. Start with `USERS_ROLLOUT_STAGE=internal_admins` and baseline-safe capability flags.
5. Promote rollout stage cohort-by-cohort (`super_admins` then `all_admins`) after telemetry validation.
6. Monitor dashboard signals and error telemetry after each cohort step.

## Backend Migration Steps

1. Deploy backend containing:
   - `/users/admin/list`
   - `/users/admin/capabilities`
   - `/users/admin/telemetry`
   - `/users/admin/dashboard`
   - all users admin feature endpoints (activity, status, bulk, invite, import/export, templates).
2. Restart backend services.
3. Verify index initialization succeeded (especially `users_admin_telemetry` indexes).
4. Set initial rollout stage to internal cohort:
   - `USERS_ROLLOUT_STAGE=internal_admins`
5. Verify capability payload includes rollout metadata:
   - `GET /users/admin/capabilities` returns `rollout_stage`, `rollout_cohort`, `rollout_access`, `rollout_reason`.

## Frontend Migration Steps

1. Deploy frontend containing:
   - unified users workspace page
   - capability-aware UI gating
   - telemetry emission for key actions
   - pagination/API latency dashboard card
2. Confirm route loads: `/workspace/administration/users`.

## Smoke Tests (Post-Deploy)

Run these with an admin account that has `users.read` and update rights.

1. Open users page and verify list loads from admin endpoint.
2. Search/filter/sort and verify URL query sync.
3. Open user drawer tabs (`Details`, `Permissions`, `Activity`, `Risk Actions`).
4. Perform status change with reason.
5. Perform one bulk operation with reason.
6. Create invitation.
7. Run import preview and commit on test CSV.
8. Export CSV.
9. Open "Pagination & API Latency" card and confirm metrics populate.
10. Confirm legacy `GET /users/` consumer paths still function.

## Staged Cohort Enablement

Use `USERS_ROLLOUT_STAGE` for cohort gating and capability flags for feature surface.

1. Internal admins:
   - Set `USERS_ROLLOUT_STAGE=internal_admins`.
   - Ensure internal cohort selectors are defined (`INTERNAL_USER_IDS` / `INTERNAL_EMAILS` / `INTERNAL_EMAIL_DOMAINS` / `INTERNAL_ADMIN_TYPES`).
   - Enable `WORKSPACE`, `ACTIVITY`, `TELEMETRY`; keep high-risk features disabled (`BULK`, `IMPORT_EXPORT`) for first pass.
2. Super admins:
   - Set `USERS_ROLLOUT_STAGE=super_admins`.
   - Enable `BULK`, `INVITATIONS`, `INLINE_EDITING`, `PERMISSION_TEMPLATES`.
3. All admins:
   - Set `USERS_ROLLOUT_STAGE=all_admins`.
   - Enable remaining capabilities (`IMPORT_EXPORT`, `COMPACT_DENSITY`, `RESPONSIVE_WORKFLOWS`).

Proceed only if previous cohort has healthy telemetry for at least one observation window (minimum 60 minutes) and no unresolved P1 incidents.

## Success Criteria

- No regressions for legacy `GET /users/` consumers.
- Error rate remains within normal baseline after each rollout step.
- P95/P99 latency on users admin list stable and acceptable for tenant size.
- Audit trail exists for permission/status changes.

## Rollback Plan

1. Immediate mitigation:
   - Move rollout stage one step back (`all_admins -> super_admins -> internal_admins`).
   - Disable impacted capability flags (fastest blast-radius reduction).
2. Functional fallback:
   - Keep legacy consumers on `GET /users/`.
3. If severe:
   - Revert frontend deployment to last stable build.
   - Revert backend deployment if issue is backend-specific.
4. Validate rollback:
   - users page opens without crashes
   - critical admin actions function
   - no elevated 5xx on users endpoints

## Migration Sign-Off Checklist

- [ ] Backend deployed and healthy.
- [ ] Frontend deployed and healthy.
- [ ] New admin endpoints validated.
- [ ] Rollout stage configured for target cohort.
- [ ] Capability flags configured for target cohort.
- [ ] Telemetry ingestion confirmed.
- [ ] Pagination/API latency dashboard populated.
- [ ] Legacy `GET /users/` compatibility verified.
- [ ] Stakeholder approval recorded.

# Admin Users Modernization

Last updated: 2026-04-15

## Implemented Scope

### Backend
- Preserved legacy `GET /users/` response shape for compatibility.
- Added admin contracts:
  - `GET /users/admin/list`
  - `GET /users/filter-options`
  - `GET/POST/PATCH/DELETE /users/filter-presets`
  - `GET /users/export.csv`
  - `GET /users/{user_id}/activity`
  - `PATCH /users/{user_id}/status`
  - `POST /users/bulk/status`
  - `PATCH /users/bulk/extensions`
  - `POST /users/invitations`
  - `GET /users/invitations`
  - `POST /users/import/preview`
  - `POST /users/import/commit`
  - `GET/POST/PATCH/DELETE /users/permission-templates`
- Added admin list envelope and row projection types for scalable table usage.
- Added Phase 6 capability and telemetry contracts:
  - `GET /users/admin/capabilities`
  - `POST /users/admin/telemetry`
  - `GET /users/admin/dashboard`
- Added users-admin dashboard alert evaluation with routed operational alerts:
  - error-rate warning/critical thresholds
  - p95 latency warning/critical thresholds
  - pagination quality warning thresholds (`empty_page_rate_pct`, `deep_page_rate_pct`)
- Added optional HTTP cache validation support for `GET /users/admin/list`:
  - `ETag` response header
  - `If-None-Match` handling with `304 Not Modified`
  - Guarded by `USERS_CAPABILITY_HTTP_CACHE_VALIDATION_ENABLED` (default disabled)
- Added capability-group feature flags in settings:
  - `USERS_CAPABILITY_WORKSPACE_ENABLED`
  - `USERS_CAPABILITY_ACTIVITY_ENABLED`
  - `USERS_CAPABILITY_BULK_OPERATIONS_ENABLED`
  - `USERS_CAPABILITY_PERMISSION_TEMPLATES_ENABLED`
  - `USERS_CAPABILITY_INVITATIONS_ENABLED`
  - `USERS_CAPABILITY_IMPORT_EXPORT_ENABLED`
  - `USERS_CAPABILITY_INLINE_EDITING_ENABLED`
  - `USERS_CAPABILITY_COMPACT_DENSITY_ENABLED`
  - `USERS_CAPABILITY_RESPONSIVE_WORKFLOWS_ENABLED`
  - `USERS_CAPABILITY_TABLE_VIRTUALIZATION_ENABLED`
  - `USERS_CAPABILITY_HTTP_CACHE_VALIDATION_ENABLED`
  - `USERS_ADMIN_TELEMETRY_ENABLED`
- Added users-admin alert threshold config keys:
  - `USERS_ADMIN_ALERT_ERROR_RATE_WARNING_PCT`
  - `USERS_ADMIN_ALERT_ERROR_RATE_CRITICAL_PCT`
  - `USERS_ADMIN_ALERT_P95_LATENCY_WARNING_MS`
  - `USERS_ADMIN_ALERT_P95_LATENCY_CRITICAL_MS`
  - `USERS_ADMIN_ALERT_EMPTY_PAGE_WARNING_PCT`
  - `USERS_ADMIN_ALERT_DEEP_PAGE_WARNING_PCT`
- Added staged rollout execution controls:
  - `USERS_ROLLOUT_STAGE` (`internal_admins`, `super_admins`, `all_admins`)
  - `USERS_ROLLOUT_INTERNAL_USER_IDS`
  - `USERS_ROLLOUT_INTERNAL_EMAILS`
  - `USERS_ROLLOUT_INTERNAL_EMAIL_DOMAINS`
  - `USERS_ROLLOUT_INTERNAL_ADMIN_TYPES`
- Added backend capability guards to users admin endpoints by scope:
  - workspace, activity, bulk operations, permission templates, invitations, import/export, inline editing.
- Added rollout-aware capabilities payload metadata:
  - `rollout_stage`, `rollout_cohort`, `rollout_access`, `rollout_reason`
- Added server telemetry write path (`users_admin_telemetry`) with indexes:
  - `created_at`
  - `(event, outcome, created_at)`
  - `(actor_user_id, created_at)`
- Added audit reason plumbing:
  - Status updates require reason and write audit log entries.
  - Extension updates support `change_reason` and persist audit detail.
- Added `last_active_at` support and auth update hooks.
- Added single-step create/invite scope support:
  - `POST /users/` accepts `role_scope`
  - `POST /users/invitations` accepts `role_scope`
  - Scope compatibility/requirements validated at creation time
  - Role-scope governance metadata persisted on user rows
- Added indexes for user listing, activity queries, invitations, and templates.
- Added indexes for per-admin saved filter presets:
  - `(created_by_user_id, updated_at)`
  - unique `(created_by_user_id, name_normalized)`

### Frontend
- Replaced Users page with a unified admin workspace:
  - Top KPI cards, global search, advanced filters, sort controls.
  - Server-driven table with pagination and row selection.
  - Sticky bulk toolbar for status and extension updates.
  - Action bar for create, invite, import, and export.
- Added table identity enhancement:
  - Profile image shown before user name in list rows.
- Added saved filter preset controls:
  - Save current filter set as preset
  - Apply selected preset to URL/state
  - Update preset with current filters
  - Rename/delete preset
  - Preset is auto-cleared when filters are manually changed
- Added right-side user drawer with tabs:
  - `Details`
  - `Permissions` (extension upgrade cards, template apply, template create/update/delete authoring, scoped role editors, unsaved change warning)
  - `Activity` (audit timeline)
  - `Risk Actions` (activate/deactivate with mandatory reason)
- Added users drawer accessibility hardening:
  - semantic dialog role + labeled title
  - focus trap
  - Escape-to-close
  - focus return to opener
- Improved drawer identity hierarchy:
  - Larger primary name and clearer role/status chips.
- Added create/invite/import flows:
  - Multi-step create wizard (identity -> role -> extensions -> scope -> review)
  - Multi-step invite wizard (identity -> role -> extensions -> scope -> review)
  - Direct create (`POST /users/`) with single-step `role_scope` payload
  - Invite create (`POST /users/invitations`) with single-step `role_scope` payload
  - CSV preview/commit (`/users/import/preview`, `/users/import/commit`)
- Added capability-aware UI gating:
  - Workspace disable state blocks table/filter workspace rendering.
  - Activity tab auto-hides/redirects when disabled.
  - Bulk toolbar and row selection are disabled when bulk operations are off.
  - Invite, import, and export controls are hidden/blocked by capability.
  - Inline editing actions are hidden/blocked when disabled.
  - Density selector is removed when compact-density is disabled.
  - Responsive table mode is controlled by responsive-workflows capability.
- Added frontend key action/error telemetry events for:
  - list/filter loads, profile updates, permission saves, status changes,
  - bulk status/extensions, activity refresh, invitation create,
  - import preview/commit, export CSV.
- Added users admin diagnostics dashboard cards:
  - API latency percentiles (P50/P95/P99), error-rate and request volume.
  - Pagination health (avg page, avg page size, empty-page rate, deep-page rate).
  - Bucketed latency table and top page-size distribution.
- Added users alert-state rendering with threshold comparison (workspace + admin observability views).
- Added row-level governance enrichment in users table:
  - permission last-changed actor/time
  - status last-changed actor/time
- Added optional compact table virtualization path (flagged, default off).

## Stability Fixes

- Resolved runtime crash: `Rendered more hooks than during the previous render`.
- Root cause:
  - Conditional early-return path in `UserDetailOverlay` caused hook-order mismatch when selected user state changed quickly.
- Fix applied:
  - Moved all hooks to execute before any conditional return path.
  - Added a defensive remount key for overlay state transitions in `UsersPage` to prevent stale hook trees during selected-user swaps.

## Guardrails

- Role-extension validation enforced server-side.
- Scope requirements enforced:
  - `class_coordinator` requires `class_coordinator.class_id`
  - `club_president` requires `club_president.club_id`
- Self-deactivation blocked.
- Dangerous status actions require reason text.

## Verification Run

- Backend syntax checks:
  - `python -m py_compile backend/app/api/v1/endpoints/users.py`
  - `python -m py_compile backend/app/schemas/user.py backend/app/models/users.py backend/app/domains/auth/service.py backend/app/core/indexes.py`
- Backend import check:
  - `python -c "from app.api.v1.endpoints import users; print('users-router-ok')"`
- Frontend checks:
  - `npx eslint src/pages/UsersPage.jsx src/pages/users/UserDetailOverlay.jsx src/pages/users/useUsersPageData.js`
  - `npx eslint src/pages/UsersPage.jsx src/pages/users/useUsersPageData.js src/pages/users/UserDetailOverlay.jsx src/pages/users/UserDetailOverlay.test.jsx src/pages/UsersPage.test.jsx`
  - `npm run test -- --run src/pages/UsersPage.test.jsx src/pages/users/UserDetailOverlay.test.jsx src/pages/users/UsersAdminAccessibility.test.jsx`
  - `npm run build`

## Operations Docs

- Consolidated migration guide and operational runbook: `new_docs/user_module/user_module_&_update_logs.md`

## Remaining Items (Planned Follow-up)

- Engineering scope: None for codebase implementation scope in this repo.
- Operational scope:
  - production staged rollout execution (`internal_admins -> super_admins -> all_admins`) with 60-minute stable windows
  - live cohort promotion approvals and final stakeholder sign-off records

# ADMIN USERS PAGE AUDIT

## Date & Time
Baseline audit: 2026-04-14 15:00:39 +05:30 (IST)  
Codebase alignment refresh: 2026-04-15 (synced to current backend/frontend implementation)

---

# 1. CURRENT PAGE ANALYSIS

## Layout Issues
- ✅ Unified single workspace is implemented (global search/filters + one table + KPI cards).
- ✅ Sticky bulk action zone is implemented when rows are selected.
- ✅ Summary context exists via KPI cards and diagnostics panels.
- ✅ Right-side detail drawer with tabbed context is implemented.
- ✅ Responsive table mode is implemented behind `responsive_workflows` capability.
- ✅ Drawer focus/accessibility hardening shipped (dialog semantics, focus trap, Escape, focus return).
- ✅ Row-to-drawer discoverability improved (row click + keyboard Enter open path + explicit tip).

## Feature Placement Issues
- ✅ High-frequency actions are consolidated (global search, filters, presets, row actions).
- ✅ Explicit row actions exist (`Open`, `Activate/Deactivate`, inline safe-field edit).
- ✅ Risk actions are separated in drawer tab with mandatory reason.
- ✅ Refresh and filtering now operate within the unified workspace model.
- ✅ Row-level governance context added in table (`permission/status last changed by/at`).

## Navigation Issues
- ✅ `/workspace/administration/users` now operates as a dedicated admin users workspace.
- ✅ Cross-role comparison is supported in one unified list.
- ✅ Deep-linkable URL state exists (`q`, filters, `page`, `selected`, `tab`, density).
- ✅ Drawer and list are connected via row action + route-state selection.

## UX Problems
- ✅ Cognitive load reduced through unified workspace and consolidated controls.
- ✅ Unsaved permission/scope change indicator is implemented.
- ✅ Guardrails implemented (scope validation + mandatory reason for risk status changes + self-deactivation block).
- ✅ Activity timeline is embedded in drawer.
- ✅ Search + filters + chips + presets implemented.
- ✅ Permission editor now shows `last changed by` and `last changed at` metadata.

---

# 2. ADMIN WORKFLOW ANALYSIS

### Workflows:
- View users
- Add user
- Edit user
- Delete user
- Search/filter user

| Step | Issue | Fix |
|---|---|---|
| View users: open page | ✅ Resolved | Unified table + KPIs + global toolbar shipped |
| View users: inspect a user | ✅ Resolved | Explicit `Open` row action + right drawer shipped |
| Add user | ✅ Resolved | `Add User` and invite flow shipped |
| Add user: assign role/scope | ✅ Resolved | Multi-step create/invite wizard supports extensions + scope assignment before submit |
| Edit user | ✅ Resolved | Safe-field inline editing + diff preview in drawer shipped |
| Delete user | ✅ Resolved (policy path) | Deactivate/reactivate flow shipped with mandatory reason and audit trail |
| Search/filter user | ✅ Resolved | Global search + advanced filters + chips + presets shipped |
| Bulk admin operations | ✅ Resolved | Bulk status and bulk extensions with reason shipped |

---

# 3. FEATURE GAP ANALYSIS

| Feature | Why Needed | Priority |
|---|---|---|
| Bulk actions | Reduces repetitive per-user edits and operational time | ✅ P0 Shipped |
| Advanced filters | Critical for large tenant discoverability and compliance reviews | ✅ P0 Shipped |
| Role management guardrails | Prevents accidental privilege escalation and misconfiguration | ✅ P0 Shipped |
| Activity logs (per user) | Enables traceability for audits and incident response | ✅ P0 Shipped |
| Search improvements | Faster lookup across name/email/id/role/type in one query | ✅ P0 Shipped |
| Add user flow | Core lifecycle action | ✅ P0 Shipped |
| Deactivate/reactivate controls | Safer lifecycle than deletion, required for policy workflows | ✅ P1 Shipped |
| Saved filter presets | Supports repeated admin investigations | ✅ P1 Shipped |
| Permission templates | Speeds standardized access assignment | ✅ P1 Shipped (apply + create/update/delete) |
| CSV export/import | Supports migration, reporting, and recovery workflows | ✅ P1 Shipped |

---

# 4. FEATURE PLACEMENT OPTIMIZATION

| Feature | Current Position | Recommended Position | Reason |
|---|---|---|---|
| Add User | Top action bar | Keep current position | High-priority frequent action |
| Refresh | Workspace table controls | Keep current position | Contextual to data operations |
| Global Search | Unified action bar | Keep current position | Fast first-step for all workflows |
| Role/Status/Admin filters | Unified filter tray + chips | Keep current position | Clear scope control |
| Advanced Filters | Collapsible filter panel | Keep current position | Power without default clutter |
| Bulk Actions | Sticky selection toolbar | Keep current position | Immediate feedback and fewer clicks |
| View/Edit User | Row action + name click + drawer | Keep current position | Discoverable and fast |
| Permission Save | Drawer actions + revert draft | Keep current position | Preserves context while editing |
| Dangerous Actions | Dedicated `Risk Actions` tab | Keep current position | Safe separation of high-impact ops |

Rules applied:
- High priority actions moved to topbar/action bar.
- Frequent actions made visible in primary table context.
- Dangerous actions separated into guarded area with confirmations.

---

# 5. LAYOUT REDESIGN

Define improved structure:

- Grid system
- ✅ Unified workspace structure implemented for desktop/tablet/mobile.
- ✅ Consistent card/table spacing and sticky selection behavior implemented.

- Sections:
  - Topbar
  - ✅ Page title + KPI cards + primary actions (`Add User`, `Export`, `Refresh`)
  - Action bar
  - ✅ Global search, sorting, saved presets, filter chips
  - ✅ Sticky bulk actions when selection > 0
  - Filters
  - ✅ Collapsible advanced filters + inline chips + clear controls
  - Table
  - ✅ Single unified table with pagination/sorting/selection/row actions
  - Side panel (if needed)
  - ✅ Right drawer with `Details`, `Permissions`, `Activity`, `Risk Actions`

---

# 6. RESPONSIVE IMPROVEMENTS

## Mobile (<768px)
| Issue | Fix |
|---|---|
| Long-scroll multi-section user views | ✅ Unified single workspace/table implemented |
| Wide tables hard to scan | ✅ Responsive table mode implemented (capability-gated) |
| Context switching while editing | ✅ Drawer model implemented with route-state persistence |
| Search/filter discoverability | ✅ Global search + filters are centralized |

## Tablet (768px–1024px)
| Issue | Fix |
|---|---|
| Sidebar + content density conflicts | ✅ Single toolbar + filter tray pattern implemented |
| Overlay width consistency | ✅ Drawer layout implemented with persistent context header |
| Repeated controls consuming vertical space | ✅ Consolidated controls in one workspace |

## Desktop (>1024px)
| Issue | Fix |
|---|---|
| Multi-role layout fragmentation | ✅ Unified table + right drawer split view implemented |
| Persistent workflow context | ✅ URL-state + selection persistence implemented |
| High-density admin mode | ✅ Compact density mode implemented behind capability flag |

---

# 7. NEW FEATURE SUGGESTIONS

| Feature | Impact | Complexity |
|---|---|---|
| Last changed by/at in permissions panel | ✅ Implemented | Delivered |
| Permission risk mapping hardening (`low/medium/high` explicit per extension) | ✅ Implemented | Delivered |
| Observability dashboard tiles for users-admin telemetry | ✅ Implemented | Delivered |
| Automated alerting from users-admin telemetry thresholds | ✅ Implemented | Delivered |

---

# 8. PERFORMANCE IMPROVEMENTS

- Large data handling
- ✅ Server pagination/sort/filter via `/users/admin/list` implemented.
- ✅ Debounced search (~300ms) and request cancellation pattern implemented.
- ✅ Optional row virtualization path implemented behind capability flag (default disabled).

- Pagination vs infinite scroll
- ✅ Pagination-first model implemented for admin/compliance workflows.

- API optimization
- ✅ Lightweight list projection + on-demand drawer detail fetch implemented.
- ✅ Bulk status/extension update APIs implemented.
- ✅ Static lookup loading is batched on frontend startup path.
- ✅ Optional `ETag` / `If-None-Match` support implemented for `/users/admin/list` (default disabled).

---

# 9. PRIORITY ACTION PLAN

| Priority | Task | Reason |
|---|---|---|
| ✅ P0 | Unified workspace + global toolbar | Shipped |
| ✅ P0 | Add user lifecycle actions + guardrails | Shipped |
| ✅ P0 | Server pagination/search/filter contracts | Shipped |
| ✅ P0 | Activity timeline + permission/status audit reasoning | Shipped |
| ✅ P1 | Bulk actions + sticky selection toolbar | Shipped |
| ✅ P1 | Responsive workflow + compact density mode | Shipped |
| ✅ P1 | Sorting + saved filter presets | Shipped |
| ✅ P2 | Inline safe-field editing | Shipped |
| ✅ P2 | Export/import + permission template assignment/authoring | Shipped |
| ✅ P2 | Permission editor accountability metadata (`last changed by/at`) | Shipped |

---

# 10. FINAL DESIGN DECISION

Partial redesign

Reason: Core model was retained and the page architecture was modernized into a unified, scalable admin users workspace. Remaining work is operational rollout/checklist execution plus minor UX hardening.

---

# 11. IMPLEMENTATION UPDATE (2026-04-14)

## Completed UI Changes
- Added profile image before each user name in Users tables (Admins, Teachers, Students) with initials fallback when no photo exists.
- Upgraded User Details modal header with larger display name, profile avatar, role/type/status badges, and cleaner identity hierarchy.
- Added a clearer "Extended Role Upgrade" permission section with role-wise descriptions.
- Improved extended role toggles by presenting each permission as a descriptive card instead of plain switches.
- Added unsaved permission change indicator in modal when extension roles or scope are modified.
- Added a quick summary strip in Details tab (current extended roles, permission mode, scope status).
- Added full permission-template authoring in Permissions tab: template library select, `Save As New Template`, `Update Template`, `Delete Template`, and inline validation feedback.
- Added permission-template CRUD wiring in frontend data layer with telemetry events and automatic template list refresh.
- Added focused frontend test coverage for template authoring flow from current permission draft.

## Additional Suggestions For User Details Modal
- ✅ Hardened `Permission Risk Level` tag mapping per extension role (`low`, `medium`, `high`) with explicit values.
- ✅ Added inline `Last changed by` and `Last changed at` metadata inside permission section for accountability.
- ✅ Add preview chip `Effective Access Includes` that expands to real capabilities before save.
- ✅ Add required-scope validation guard (`class_coordinator` must include section, `club_president` must include club) before save action is enabled (server-enforced guardrails).
- ✅ Add `Revert Changes` secondary button to discard local drafts without closing the modal.
- ✅ Add optional `Reason for permission change` textarea and persist it into audit log payload.

---

# 12. IMPLEMENTATION UPDATE (2026-04-15)

## Newly Completed
- ✅ Permission-template authoring is now complete in the Users permissions drawer (`create`, `update`, `delete`, `apply`).
- ✅ Template mutation state and feedback added (`saving` state, inline error messages, success toasts).
- ✅ Template operations now emit frontend telemetry events and refresh template inventory after each mutation.
- ✅ Users create/invite flows upgraded to multi-step wizard with pre-submit scope assignment and review.
- ✅ Backend single-step role-scope submission added to `POST /users/` and `POST /users/invitations`.
- ✅ Users table governance metadata enrichment added (`permission/status last changed by/at`).
- ✅ Users drawer accessibility hardening shipped (dialog semantics, focus trap, Escape, focus return).
- ✅ Admin Observability now includes Users Admin tiles and users-alert state from `/users/admin/dashboard`.
- ✅ Optional scalability enhancements delivered:
  - table virtualization capability path (default off),
  - HTTP cache validation (`ETag`/`If-None-Match`) for `/users/admin/list` (default off).
- ✅ Approved modernization core + enhancement backlog in codebase are complete; remaining items are production rollout execution/sign-off operations.

## Validation Snapshot
- ✅ Frontend lint passed for updated Users workspace and drawer modules.
- ✅ Frontend targeted tests passed (`UsersPage`, `UserDetailOverlay`, `UsersAdminAccessibility`).
- ✅ Frontend production build passed (`vite build`).


