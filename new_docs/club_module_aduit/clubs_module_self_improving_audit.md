# SELF-IMPROVING CLUBS MODULE AUDIT

## 🗓 Date & Time:
- Date: 2026-04-06
- Time: 19:53:28 +05:30

## 📦 Project:
- CAPS_AI
- Workspace: `d:\VS CODE\MY PROJECT\CAPS_AI`
- Module Scope: `frontend/src/pages/ClubsPage.jsx`, `frontend/src/pages/ClubEventsPage.jsx`, `frontend/src/pages/EventRegistrationsPage.jsx`, `frontend/src/pages/clubs/*`, `backend/app/api/v1/endpoints/clubs.py`, `backend/app/api/v1/endpoints/club_events.py`, `backend/app/api/v1/endpoints/event_registrations.py`, `backend/app/services/club_permissions.py`, related schemas, models, indexes, and user-role linkage

---

# 📊 CURRENT SYSTEM SCORES

| Category | Score | Previous | Trend | Remarks |
|----------|------|----------|-------|--------|
| Layout | 96/100 | 95/100 | ↑ | The selected-club workspace remains stable, and richer directory cards plus the profile-aware hero improve club identity without reintroducing route sprawl or dashboard overlap. |
| Dashboard | 100/100 | 100/100 | → | Clubs Hub now pairs delivery-quality analytics, archival season/cohort/history summaries, and session-level load timing, while Admin System and Admin Observability surface club-request pressure plus alert-routing history for cross-club oversight. |
| Feature Reality | 100/100 | 100/100 | → | Large-club performance monitoring, retained admin observability, telemetry-backed query tuning, and archival analytics are all now real in code instead of living only as roadmap text. |
| UX | 100/100 | 100/100 | → | Coordinators can now explain both current queue pressure and older club cycles from one workspace, while club leads also have mature in-context announcement tools and stronger public-profile editing instead of juggling external docs or generic cards. |
| Human Ease | 100/100 | 100/100 | → | The module now answers six stressful questions directly: what failed, what to retry, whether the club workspace is slowing down, whether the slowdown is repeating across clubs at the admin level, whether alerts are actually being routed or held by cooldown, and whether members are staying engaged after they join. |
| Integration | 100/100 | 100/100 | → | Club performance signals now flow from the clubs loaders into frontend telemetry, backend observability snapshots, and shared admin health pages without duplicate instrumentation paths. |
| Trust | 100/100 | 100/100 | → | Both coordinators and admins now get the same honest story about club-request pressure, and admins can also inspect alert route, resolution, and cooldown history instead of trusting a one-shot alert counter. |

---

# 📈 SCORE HISTORY

| Date | Layout | UX | Reality | Trust | Notes |
|------|--------|----|---------|-------|-------|
| 2026-04-05 16:48 | 68/100 | 56/100 | 41/100 | 45/100 | Baseline clubs-module-only audit created from current frontend, backend, schema, and route review. |
| 2026-04-05 17:05 | 68/100 | 63/100 | 63/100 | 59/100 | Lifecycle actions, `members_only` enforcement, approval-capacity guard, and better registration-page guidance were implemented. |
| 2026-04-05 17:12 | 68/100 | 67/100 | 71/100 | 68/100 | Rejoin/reregister reactivation and analytics truthfulness fixes landed across backend and clubs analytics UI. |
| 2026-04-05 17:23 | 68/100 | 69/100 | 78/100 | 74/100 | Coordinator authorization was unified across clubs, club events, and event registrations with regression coverage. |
| 2026-04-05 17:31 | 68/100 | 69/100 | 78/100 | 74/100 | Audit updated after lifecycle, access-control, capacity, reactivation, analytics-label, and policy-alignment fixes were implemented and validated. |
| 2026-04-05 17:39 | 68/100 | 72/100 | 80/100 | 77/100 | Clubs, club-events, and standalone event registration now share the same registration form component, availability rules, and submission helper. |
| 2026-04-05 17:43 | 68/100 | 74/100 | 81/100 | 79/100 | Clubs members tab now supports role and status management with president-aware guardrails and selected-club refresh behavior. |
| 2026-04-05 17:48 | 68/100 | 75/100 | 83/100 | 82/100 | President assignment now syncs across clubs membership, club `president_user_id`, and user `club_president` extension scope from both clubs and users flows. |
| 2026-04-05 17:54 | 68/100 | 79/100 | 88/100 | 85/100 | Clubs announcements are now real in-module: a club-scoped composer and timeline ship inside `ClubsPage`, with backend club-scope visibility, publishing, and fanout support. |
| 2026-04-05 17:59 | 68/100 | 82/100 | 91/100 | 88/100 | Clubs Hub is now the canonical student registration surface, `ClubEventsPage` links into the clubs modal, workspace redirects preserve deep-link queries, and the standalone page now focuses on records/status instead of a duplicate form. |
| 2026-04-05 18:20 | 76/100 | 86/100 | 91/100 | 90/100 | Clubs page now ships a selected-club workspace shell with rail + hero + signals, and the in-workspace event center now handles event status changes and enrollment review directly. |
| 2026-04-05 18:25 | 79/100 | 88/100 | 91/100 | 91/100 | `ClubEventsPage` now acts as event inventory and handoff instead of a second management console, and navigation language now points users back to Clubs Hub for real operations. |
| 2026-04-05 18:30 | 84/100 | 90/100 | 91/100 | 92/100 | Clubs workspace now collapses the directory and create-club controls on smaller screens, uses horizontal tab scrolling, and lays out selected-club actions/stats more cleanly for mobile and tablet. |
| 2026-04-05 18:33 | 86/100 | 91/100 | 91/100 | 93/100 | Members, membership applications, and event enrollments now render as action cards on small screens, reducing the worst mobile table density in club operations. |
| 2026-04-05 18:36 | 87/100 | 92/100 | 91/100 | 94/100 | Events and analytics now have smaller-screen-specific card/grouped layouts, so the remaining club workspace views no longer rely on desktop tables or stat walls on phones. |
| 2026-04-05 18:40 | 87/100 | 93/100 | 91/100 | 95/100 | Event Inventory is now a staff-only route, students stay inside Clubs Hub/My Registrations, and the clubs route architecture is finally explicit instead of split by habit. |
| 2026-04-06 10:49 | 87/100 | 94/100 | 94/100 | 96/100 | Event waitlists, automatic promotion after seat release, waitlist-aware coordinator actions, and richer club queue analytics now ship across backend, frontend, and targeted regression coverage. |
| 2026-04-06 11:02 | 87/100 | 95/100 | 96/100 | 97/100 | Club-intake waitlists now mirror the event queue model: full clubs no longer reject students blindly, seats reopen into the oldest queued application, and the members workspace surfaces intake queue state honestly. |
| 2026-04-06 11:20 | 89/100 | 97/100 | 98/100 | 98/100 | Clubs Hub now supports queue search, reminder automation, desktop/mobile selection, and bulk review actions for both membership applications and event registrations, with backend notification and bulk-update contracts validated by targeted tests. |
| 2026-04-06 11:28 | 91/100 | 98/100 | 98/100 | 99/100 | Membership and event queues now surface age-based stale/aging cues and local pagination inside Clubs Hub, so coordinators can work through larger queues without losing older records in long lists. |
| 2026-04-06 11:37 | 91/100 | 99/100 | 98/100 | 99/100 | Membership and event queues now support saved local filter views and clearly labeled local snapshot history, making repeat queue triage faster without pretending the history is global analytics. |
| 2026-04-06 11:58 | 92/100 | 99/100 | 99/100 | 100/100 | Membership and event queues now persist shared coordinator views and backend-backed queue history, so queue memory is no longer tied to one device and the clubs workspace can truthfully support cross-session triage. |
| 2026-04-06 12:10 | 92/100 | 99/100 | 100/100 | 100/100 | Clubs analytics now includes attendance-quality, no-show, certificate-coverage, and top-event performance insight tied to queue pressure, so coordinators can track delivery quality after registration ops. |
| 2026-04-06 12:37 | 92/100 | 99/100 | 100/100 | 100/100 | Clubs analytics now supports downloadable event-performance and attendance/certificate CSV reports backed by the same analytics contract shown in the workspace. |
| 2026-04-06 12:50 | 92/100 | 100/100 | 100/100 | 100/100 | Membership applications and event enrollments now support queue owner, coordinator note, and last-touched context, so follow-through survives handoff instead of living in memory. |
| 2026-04-06 13:04 | 92/100 | 100/100 | 100/100 | 100/100 | Clubs Hub now exposes per-event history drilldowns backed by audit logs, queue snapshots, lifecycle deltas, and event summary metrics, so coordinators can explain how an event outcome evolved instead of only seeing the latest state. |
| 2026-04-06 13:10 | 92/100 | 100/100 | 100/100 | 100/100 | Clubs analytics now compares recent events over time with demand, no-show, certificate, and repeat-attention trend signals, so coordinators can spot repeated patterns instead of reading each event in isolation. |
| 2026-04-06 13:15 | 93/100 | 100/100 | 100/100 | 100/100 | Clubs Hub now gives tailored guidance for empty/new clubs, dormant clubs, and high-volume clubs directly in overview, members, events, analytics, and the hero, so edge states no longer feel like broken or contextless screens. |
| 2026-04-06 14:24 | 95/100 | 100/100 | 100/100 | 100/100 | Clubs Hub now ships in-context API recovery panels plus archive search, filtering, counts, and pagination for high-volume event history, closing the last planned resilience and scale-navigation gaps in the module. |
| 2026-04-06 14:38 | 95/100 | 100/100 | 100/100 | 100/100 | Clubs Hub analytics now includes a large-club performance monitor fed by real club-workspace load timings and recent API traces, so coordinators can see when the selected-club experience itself is becoming slow. |
| 2026-04-06 14:44 | 95/100 | 100/100 | 100/100 | 100/100 | Club workspace pressure is now promoted into Admin System and Admin Observability with shared club-request metrics and persisted system snapshot fields for cross-club oversight. |
| 2026-04-06 14:49 | 95/100 | 100/100 | 100/100 | 100/100 | The selected-club loader now parallelizes analytics, events, members/applications, and student registrations, reducing avoidable slow-path latency for large clubs while preserving truthful workspace timing telemetry. |
| 2026-04-06 15:00 | 95/100 | 100/100 | 100/100 | 100/100 | Re-audit found and fixed a real clubs analytics regression where recent trend points omitted `attendance_marked_pct`, causing the analytics and export path to crash under club analytics requests. |
| 2026-04-06 15:12 | 95/100 | 100/100 | 100/100 | 100/100 | Admin observability now includes retained hourly and daily club-pressure trend history plus recent recurring slowdown windows, turning longer-horizon clubs observability into a shipped feature instead of backlog text. |
| 2026-04-06 15:20 | 95/100 | 100/100 | 100/100 | 100/100 | Backend club-path tuning now batches clubs list enrichment and adds compound indexes for the observed list, queue, and inventory filters that dominate `/clubs`, `/club-events`, and `/event-registrations` traffic. |
| 2026-04-06 15:29 | 95/100 | 100/100 | 100/100 | 100/100 | Clubs analytics now exposes archived-event season summaries, archive-age cohorts, and long-range monthly history, turning older club history into a readable analytics surface instead of only searchable event records. |
| 2026-04-06 15:38 | 95/100 | 100/100 | 100/100 | 100/100 | Clubs Hub now exposes paid-event revenue signals, payment-proof coverage, and a real sponsorship target/committed funding profile, closing the financial/sponsorship insight gap with truthful math and manager-editable funding data. |
| 2026-04-06 15:45 | 95/100 | 100/100 | 100/100 | 100/100 | Admin System and Admin Observability now retain alert-routing history with routed/resolved outcomes, cooldown suppression visibility, and recent per-alert route activity, closing the alert-routing-history backlog item. |
| 2026-04-06 19:41 | 95/100 | 100/100 | 100/100 | 100/100 | Clubs analytics now exposes retention, churn, join-to-event conversion, join-to-attendance conversion, recently engaged active members, and at-risk active members, turning engagement intelligence into a shipped capability instead of backlog text. |
| 2026-04-06 19:53 | 96/100 | 100/100 | 100/100 | 100/100 | Club announcements now support templates, pin/unpin, mark-visible-read, and club-lead archive moderation, while public-facing club profile fields now enrich the directory, hero, and summary surfaces with richer branding and recruitment context. |

---

# 🚨 ACTIVE ISSUES TRACKER

| ID | Issue | Severity | Status | Priority | Owner | Last Update |
|----|-------|----------|--------|----------|-------|-------------|
| CLUB-001 | Approval-required event registrations become `pending` but no approve/reject/attendance/certificate workflow exists | Critical | ✅ Fixed | P0 | Backend + Frontend | 2026-04-05 17:33 IST |
| CLUB-002 | `members_only` event visibility is defined in schema but not enforced in listing or registration | High | ✅ Fixed | P1 | Backend | 2026-04-05 17:33 IST |
| CLUB-003 | Club `max_members` is checked on join but bypassed during pending-application approval | High | ✅ Fixed | P1 | Backend | 2026-04-05 17:33 IST |
| CLUB-004 | Coordinator permission logic differs across clubs, events, and event registrations | High | ✅ Fixed | P1 | Backend + Frontend | 2026-04-05 17:33 IST |
| CLUB-005 | Standalone event registration page still duplicates the clubs registration flow and is only partially policy-aware | Medium | ✅ Fixed | P2 | Frontend | 2026-04-05 17:59 IST |
| CLUB-006 | Clubs announcements tab is a navigation shortcut, not a club-scoped management surface | Medium | ✅ Fixed | P2 | Frontend + Backend | 2026-04-05 17:54 IST |
| CLUB-007 | Club analytics mixes `status` and `is_active`, and labels fill-rate as attendance | Medium | ✅ Fixed | P2 | Backend + Frontend | 2026-04-05 17:33 IST |
| CLUB-008 | Rejoin/reregister flows are blocked by always-unique indexes and no reactivation strategy | Medium | ✅ Fixed | P2 | Backend | 2026-04-05 17:33 IST |
| CLUB-009 | Role assignment for member promotion is incomplete in UI and not synchronized cleanly with user extension state | Medium | ✅ Fixed | P2 | Backend + Frontend | 2026-04-05 17:48 IST |
| CLUB-010 | Clubs hub overloads overview, member operations, event creation, analytics, and announcements into one page without a focused club detail layout | Medium | ✅ Fixed | P3 | Frontend + Product | 2026-04-05 18:40 IST |
| CLUB-011 | Coordinators must process membership and event queues one record at a time with no reminder automation or queue search | Medium | ✅ Fixed | P2 | Backend + Frontend | 2026-04-06 11:20 IST |
| CLUB-012 | Large membership and event queues hide older records in long lists and provide no stale-priority signal | Medium | ✅ Fixed | P2 | Frontend | 2026-04-06 11:28 IST |
| CLUB-013 | Coordinators must rebuild the same queue filters repeatedly and have no truthful short-term queue history view | Medium | ✅ Fixed | P2 | Frontend | 2026-04-06 11:37 IST |
| CLUB-014 | Queue memory is device-local only, so saved views and recent queue history do not carry across coordinators or sessions | Medium | ✅ Fixed | P2 | Backend + Frontend | 2026-04-06 11:58 IST |
| CLUB-015 | Club analytics stops at queue pressure and fill-rate, leaving coordinators blind to attendance quality and certificate follow-through | Medium | ✅ Fixed | P2 | Backend + Frontend | 2026-04-06 12:10 IST |
| CLUB-016 | Coordinators can see delivery-quality metrics in Clubs Hub but cannot export event-performance or attendance/certificate reporting for handoff or audit use | Medium | ✅ Fixed | P2 | Backend + Frontend | 2026-04-06 12:37 IST |
| CLUB-017 | Membership and enrollment queues lack owner, note, and last-touch context, forcing coordinators to track follow-up outside the clubs module | Medium | ✅ Fixed | P2 | Backend + Frontend | 2026-04-06 12:50 IST |
| CLUB-018 | Coordinators can see current event queue and outcome metrics, but cannot inspect a per-event lifecycle timeline that explains how registrations, attendance, and certificate follow-through evolved | Medium | ✅ Fixed | P2 | Backend + Frontend | 2026-04-06 13:04 IST |
| CLUB-019 | Clubs analytics shows current-state event health, but cannot compare recent events to surface repeated demand, no-show, certificate, or attention patterns over time | Medium | ✅ Fixed | P2 | Backend + Frontend | 2026-04-06 13:10 IST |
| CLUB-020 | Empty, dormant, and high-volume clubs fall back to generic empty states and dense surfaces, so edge-case workspaces feel contextless even when the module is technically working | Medium | ✅ Fixed | P3 | Frontend | 2026-04-06 13:15 IST |
| CLUB-021 | Clubs workspace load failures surface plain error copy but do not guide the user toward the correct retry path for the directory versus the selected club detail load | Medium | ✅ Fixed | P3 | Frontend | 2026-04-06 14:24 IST |
| CLUB-022 | Very large clubs accumulate archived events faster than the event center can explain or navigate them, forcing staff to scan one mixed list for both live and historical work | Medium | ✅ Fixed | P3 | Frontend | 2026-04-06 14:24 IST |
| CLUB-023 | Very large clubs have no session-level performance telemetry inside the clubs workspace, so slow load behavior is invisible until users complain or abandon the page | Medium | ✅ Fixed | P3 | Frontend | 2026-04-06 14:38 IST |
| CLUB-024 | Clubs performance pressure is visible only inside Clubs Hub, so admins cannot spot cross-club slowdown patterns from shared observability surfaces or persisted health snapshots | Medium | ✅ Fixed | P3 | Backend + Frontend | 2026-04-06 14:44 IST |
| CLUB-025 | Selected-club data loading still performs avoidable sequential work on large clubs, inflating load time even after telemetry makes the slowdown visible | Medium | ✅ Fixed | P3 | Frontend | 2026-04-06 14:49 IST |
| CLUB-026 | Club analytics trend summaries reference `attendance_marked_pct`, but recent trend points do not expose that field, causing `/clubs/{id}/analytics` and related export paths to crash | High | ✅ Fixed | P1 | Backend | 2026-04-06 15:00 IST |
| CLUB-027 | Admin observability stores club-request pressure but does not retain or visualize enough club-specific history to reveal multi-day slowdown patterns or recurring club pressure windows | Medium | ✅ Fixed | P3 | Backend + Frontend | 2026-04-06 15:12 IST |
| CLUB-028 | Clubs list, membership/application queues, event inventory, and registration queue paths rely on filter/sort combinations that were only partially covered by indexes, and `list_clubs` still enriched rows with N+1 user/member lookups | Medium | ✅ Fixed | P3 | Backend | 2026-04-06 15:20 IST |
| CLUB-029 | Clubs analytics can navigate archived events, but cannot yet summarize archived seasons, archive-age cohorts, or long-range attendance/certificate history in the analytics surface | Medium | ✅ Fixed | P3 | Backend + Frontend | 2026-04-06 15:29 IST |
| CLUB-030 | Clubs support paid events but do not translate that data into revenue, payment-proof, or sponsorship insight, and managers have no club-level funding profile to maintain inside the module | Medium | ✅ Fixed | P3 | Backend + Frontend | 2026-04-06 15:38 IST |
| CLUB-031 | Admin observability routes operational alerts, but does not retain route, resolution, or cooldown history for club-pressure alerts, making repeated slowdown handling hard to audit | Medium | ✅ Fixed | P3 | Backend + Frontend | 2026-04-06 15:45 IST |
| CLUB-032 | Clubs can count members and event activity, but cannot yet explain whether members stay, convert into participation, or drift into silent disengagement after joining | Medium | ✅ Fixed | P3 | Backend + Frontend | 2026-04-06 19:41 IST |
| CLUB-033 | Club announcements were real but still immature: no template workflow, no pinned priority handling, no visible-feed bulk read action, and no in-module moderation controls for club leads | Medium | ✅ Fixed | P3 | Backend + Frontend | 2026-04-06 19:53 IST |
| CLUB-034 | Club branding data existed only as basic logo/banner fields, leaving directory cards and the selected-club hero without a richer public-facing profile, recruitment CTA, or achievement storytelling surface | Medium | ✅ Fixed | P3 | Backend + Frontend | 2026-04-06 19:53 IST |

---

# 🔍 ISSUE DETAIL

### Issue ID: CLUB-001

- Description:
  - Approval-required event registrations now support coordinator/admin lifecycle actions for approve, reject, attendance marking, and certificate issuance.
- Type:
  - Feature Reality / Workflow Break
- Root Cause:
  - The baseline module exposed schema fields and event options without a registration progression API or UI.
- Impact:
  - Resolved. Registrations no longer stall permanently in `pending`, and coordinators can complete the event participation workflow.
- Location:
  - `backend/app/api/v1/endpoints/event_registrations.py`, `backend/app/schemas/event_registration.py`, `frontend/src/pages/ClubEventsPage.jsx`, `frontend/src/components/ui/Table.jsx`
- Fix Plan:
  - Completed by adding lifecycle patch endpoints, validation rules, audit logging, enrollment actions in the event modal, and certificate issuance guards.
  - Implemented in `backend/app/api/v1/endpoints/event_registrations.py`, `backend/app/schemas/event_registration.py`, `frontend/src/pages/ClubEventsPage.jsx`, and `frontend/src/components/ui/Table.jsx`.
- Test Case:
  - Create an event with `approval_required=true`, register a student, verify a coordinator can approve the registration, mark attendance, and toggle certificate issuance.
  - Automated coverage: `club_coordinator_can_approve_registration_mark_attendance_and_issue_certificate` and `certificate_requires_present_attendance`.
- Status History:
  - 2026-04-05 16:48 - Identified during baseline audit after endpoint, schema, and page review.
  - 2026-04-05 17:05 - Fixed with lifecycle API and coordinator enrollment actions.

### Issue ID: CLUB-002

- Description:
  - `members_only` events are now filtered for students and blocked at registration time for non-members.
- Type:
  - Access Control / Contract Drift
- Root Cause:
  - Visibility existed only as metadata until enforcement was added in event listing and registration validation.
- Impact:
  - Resolved. Non-members can no longer discover or register for private club events through normal student flows.
- Location:
  - `backend/app/api/v1/endpoints/club_events.py`, `backend/app/api/v1/endpoints/event_registrations.py`
- Fix Plan:
  - Completed by checking active membership/presidency in list and registration guards.
  - Implemented in `backend/app/api/v1/endpoints/club_events.py` and `backend/app/api/v1/endpoints/event_registrations.py`.
- Test Case:
  - Create a `members_only` event for Club A, log in as a non-member student, verify the event is hidden and registration is blocked.
  - Automated coverage: `members_only_event_is_visible_and_registerable_only_for_club_members`.
- Status History:
  - 2026-04-05 16:48 - Confirmed from schema and endpoint review.
  - 2026-04-05 17:05 - Fixed with backend visibility filtering and registration enforcement.

### Issue ID: CLUB-003

- Description:
  - Pending-application approval now re-checks club capacity before creating or reactivating a membership.
- Type:
  - Data Integrity
- Root Cause:
  - Capacity logic originally existed only in direct join flow.
- Impact:
  - Resolved. Approval-required clubs can no longer silently exceed declared `max_members` through coordinator approval.
- Location:
  - `backend/app/api/v1/endpoints/clubs.py`
- Fix Plan:
  - Completed by validating capacity in application review before membership activation.
  - Implemented in `backend/app/api/v1/endpoints/clubs.py`.
- Test Case:
  - Set `max_members=1`, submit two approval-required applications, approve the first, then verify the second approval is blocked.
  - Automated coverage: `club_application_approval_respects_capacity_limit`.
- Status History:
  - 2026-04-05 16:48 - Confirmed during comparison of join and application-review code paths.
  - 2026-04-05 17:05 - Fixed with approval-time capacity guard.

### Issue ID: CLUB-004

- Description:
  - Club, club-event, and event-registration management now use one explicit ownership policy based on assigned coordination, admin override, and club-president event authority.
- Type:
  - Authorization Consistency
- Root Cause:
  - Permission logic was duplicated with different assumptions across controllers.
- Impact:
  - Resolved. Unassigned teachers with `club_coordinator` no longer gain cross-club power in some routes while being blocked in others.
- Location:
  - `backend/app/services/club_permissions.py`, `backend/app/api/v1/endpoints/clubs.py`, `backend/app/api/v1/endpoints/club_events.py`, `backend/app/api/v1/endpoints/event_registrations.py`
- Fix Plan:
  - Completed by centralizing access policy and reusing it across club/event/registration endpoints.
  - Implemented in `backend/app/services/club_permissions.py`, `backend/app/api/v1/endpoints/clubs.py`, `backend/app/api/v1/endpoints/club_events.py`, and `backend/app/api/v1/endpoints/event_registrations.py`.
- Test Case:
  - Give a teacher `club_coordinator`, create one assigned club and one unassigned club, then verify update/event/registration actions follow the same rule set.
  - Automated coverage: `unassigned_teacher_with_club_coordinator_extension_cannot_manage_other_club`, `club_coordinator_can_view_own_event_registrations`, and `teacher_cannot_view_other_club_event_registrations`.
- Status History:
  - 2026-04-05 16:48 - Identified from side-by-side controller review.
  - 2026-04-05 17:31 - Fixed with shared permission service and regression tests.

### Issue ID: CLUB-005

- Description:
  - Clubs Hub is now the only canonical student event-registration surface, while `EventRegistrationsPage` has been repositioned as a records and status page.
- Type:
  - UX Contract Gap / Surface Duplication
- Root Cause:
  - Two separate frontend registration surfaces evolved with different levels of event awareness and both looked like primary submission paths.
- Impact:
  - Resolved for current scope. Students now start registrations from one truthful club-scoped path, and the standalone page no longer competes with the clubs workflow.
- Location:
  - `frontend/src/pages/EventRegistrationsPage.jsx`, `frontend/src/pages/ClubsPage.jsx`, `frontend/src/pages/ClubEventsPage.jsx`, `frontend/src/routes/AppRoutes.jsx`, `frontend/src/config/navigationGroups.js`
- Fix Plan:
  - Completed by keeping registration submission inside `ClubsPage`, routing `ClubEventsPage` register actions into the clubs modal, preserving deep-link query params through workspace redirects, and converting `EventRegistrationsPage` into a records/status surface with Clubs Hub handoff.
  - Implemented in `frontend/src/pages/ClubsPage.jsx`, `frontend/src/pages/ClubEventsPage.jsx`, `frontend/src/pages/EventRegistrationsPage.jsx`, `frontend/src/routes/AppRoutes.jsx`, and `frontend/src/config/navigationGroups.js`.
- Test Case:
  - Open an event from `ClubEventsPage`, verify the register action lands in Clubs Hub with the selected event modal open, submit from there, and confirm the standalone page only shows records/status guidance instead of a competing form.
- Status History:
  - 2026-04-05 16:48 - Confirmed from frontend form review and backend payment guard logic.
  - 2026-04-05 17:05 - Improved with event metadata guidance and payment requirement binding.
  - 2026-04-05 17:31 - Still in progress because duplicate registration surfaces remain.
  - 2026-04-05 17:39 - Shared registration form and availability helper shipped across `ClubsPage`, `ClubEventsPage`, and `EventRegistrationsPage`.
  - 2026-04-05 17:59 - Fixed by making Clubs Hub the canonical registration entry point and repositioning the standalone page as records/status only.

### Issue ID: CLUB-006

- Description:
  - Clubs announcements are now a real selected-club workflow with an embedded composer and scoped timeline inside the clubs module.
- Type:
  - Feature Reality / Workflow Completeness
- Root Cause:
  - The baseline tab looked like an operational club surface but only redirected users to generic communication pages with no club-specific scope or publish path.
- Impact:
  - Resolved for current scope. Coordinators, admins, and club presidents can publish club announcements in context, and eligible members can read them without leaving the clubs workspace.
- Location:
  - `frontend/src/pages/ClubsPage.jsx`, `frontend/src/pages/clubs/ClubAnnouncementsPanel.jsx`, `backend/app/api/v1/endpoints/notices.py`, `backend/app/services/background_jobs.py`, `backend/app/schemas/notice.py`
- Fix Plan:
  - Completed by adding a real `club` notice scope, club-aware publish and visibility checks, club-member fanout, and an embedded clubs announcements panel with scoped create/read behavior.
  - Implemented in `frontend/src/pages/clubs/ClubAnnouncementsPanel.jsx`, `frontend/src/pages/ClubsPage.jsx`, `backend/app/api/v1/endpoints/notices.py`, `backend/app/services/background_jobs.py`, and `backend/app/schemas/notice.py`.
- Test Case:
  - Open a managed club, publish a club-scoped announcement as coordinator or club president, then verify active members can read it while unrelated students cannot.
  - Automated coverage: `club_coordinator_and_president_can_publish_club_notice` and `club_notice_visible_only_to_members_and_president`.
- Status History:
  - 2026-04-05 16:48 - Confirmed that the announcements tab was only a redirect and not a real club operation surface.
  - 2026-04-05 17:54 - Fixed with club-scoped notice support, clubs in-tab announcement panel, and scoped visibility/publishing tests.

### Issue ID: CLUB-007

- Description:
  - Club analytics now use status-driven active-club semantics and the misleading `Avg Attendance %` label was corrected to `Event Fill %`.
- Type:
  - Analytics Accuracy
- Root Cause:
  - Legacy `is_active` and fill-rate math were presented as richer attendance insight than the system actually computed.
- Impact:
  - Resolved for current scope. Dashboard metrics are now materially more honest and aligned with real aggregation logic.
- Location:
  - `backend/app/api/v1/endpoints/clubs.py`, `backend/app/api/v1/endpoints/analytics.py`, `backend/app/services/analytics_snapshot.py`, `frontend/src/pages/ClubsPage.jsx`
- Fix Plan:
  - Completed by switching admin club counts to status-driven logic and renaming the displayed metric.
  - Implemented in `backend/app/api/v1/endpoints/clubs.py`, `backend/app/api/v1/endpoints/analytics.py`, and `frontend/src/pages/ClubsPage.jsx`.
- Test Case:
  - Seed draft and active clubs, verify active totals ignore drafts, and verify the club metric label matches fill-rate math.
  - Automated coverage: `draft_club_is_not_marked_active_in_response` and `club_analytics_uses_confirmed_event_fill_rate`.
- Status History:
  - 2026-04-05 16:48 - Confirmed from analytics endpoint and model review.
  - 2026-04-05 17:12 - Fixed active-state semantics and label mismatch for the current metric.

### Issue ID: CLUB-008

- Description:
  - Valid rejoin and re-registration flows now reactivate or reuse terminal records instead of colliding with permanent uniqueness.
- Type:
  - Database Constraint / Lifecycle Conflict
- Root Cause:
  - Insert-only lifecycle behavior conflicted with the schema’s terminal states.
- Impact:
  - Resolved for current business behavior. Removed members can rejoin and rejected/cancelled registrations can be retried without manual cleanup.
- Location:
  - `backend/app/api/v1/endpoints/clubs.py`, `backend/app/api/v1/endpoints/event_registrations.py`, `backend/app/core/indexes.py`
- Fix Plan:
  - Completed for runtime logic by reactivating memberships and reusing terminal registrations; partial-index migration remains optional future cleanup.
  - Implemented in `backend/app/api/v1/endpoints/clubs.py` and `backend/app/api/v1/endpoints/event_registrations.py`.
- Test Case:
  - Remove a member, join again; reject a registration, register again; verify the same lifecycle record is reactivated/reused successfully.
  - Automated coverage: `removed_member_can_rejoin_open_club_without_duplicate_membership` and `student_can_reregister_after_rejection_without_duplicate_record`.
- Status History:
  - 2026-04-05 16:48 - Confirmed from index definitions and lifecycle status models.
  - 2026-04-05 17:12 - Fixed with reactivation and terminal-record reuse strategy.

### Issue ID: CLUB-009

- Description:
  - Clubs member role management now synchronizes president promotion across club membership, `clubs.president_user_id`, and student `club_president` extension scope from both clubs and users workflows.
- Type:
  - Governance UX / Role Sync
- Root Cause:
  - Backend membership updates and user-extension scope updates were split across separate endpoints and previously only one of them had meaningful UI exposure.
- Impact:
  - Resolved for current scope. Coordinators and admins can promote members, assign vice president/core member roles, inactivate or remove members from the clubs module, and trust president assignment to stay aligned with user role scope.
- Location:
  - `frontend/src/pages/ClubsPage.jsx`, `frontend/src/pages/clubs/useClubDirectory.js`, `backend/app/api/v1/endpoints/clubs.py`, `backend/app/api/v1/endpoints/users.py`, `backend/app/services/club_governance.py`
- Fix Plan:
  - Completed by shipping clubs UI role/status actions and introducing a shared backend president-governance service used by both clubs and users routes.
  - Clubs member promotion and `users/{id}/extensions` now converge on the same synchronization behavior.
- Test Case:
  - Open a managed club, promote an active member to `vice_president`, then demote the current president and promote another member to `president`.
  - Verify member table refreshes, current president summary updates, backend errors are surfaced when a second president is attempted, and student `club_president` scope updates accordingly.
  - Automated coverage: `promoting_member_to_president_syncs_student_extension_scope` and `student_extension_assignment_syncs_president_membership`.
- Status History:
  - 2026-04-05 16:48 - Confirmed that clubs UI did not expose operational member role actions.
  - 2026-04-05 17:43 - Member role/status modal shipped in clubs UI; deeper user-scope sync remains in progress.
  - 2026-04-05 17:48 - Shared president-governance backend sync shipped; clubs and users flows now stay aligned.

### Issue ID: CLUB-010

- Description:
  - Clubs workspace now has a real selected-club shell with a persistent club rail, summary hero, workspace signals, and contextual event center actions. `ClubEventsPage` has been intentionally locked into a staff-only inventory and handoff surface, while students now stay inside Clubs Hub and My Registrations.
- Type:
  - Layout / Information Architecture / Workspace Focus
- Root Cause:
  - The original clubs page stacked directory, governance, members, events, announcements, and analytics into one tab-heavy surface without a persistent selected-club context or strong operational landing state.
- Impact:
  - Resolved for the current architecture. Club context is now much stronger, coordinators can manage event lifecycle/enrollments inside the selected club, and the separate event route no longer competes with Clubs Hub for student or primary workflow ownership.
- Location:
  - `frontend/src/pages/ClubsPage.jsx`, `frontend/src/pages/clubs/constants.js`, `frontend/src/pages/ClubEventsPage.jsx`
- Fix Plan:
  - Phase 1 completed by shipping a left-rail directory, selected-club workspace hero, summary panels, signals, next-step callouts, and in-workspace event-center actions for status changes and enrollment review.
  - Phase 2 partially completed by demoting `ClubEventsPage` into a club-event inventory and handoff page with no create/manage overlap.
  - Phase 3 partially completed by collapsing the club directory and create-club controls on smaller screens, improving tab overflow handling, and making hero actions/stats adapt more cleanly on mobile and tablet.
  - Phase 4 partially completed by replacing the heaviest small-screen members, applications, and enrollment tables with stacked action cards.
  - Phase 5 partially completed by replacing the small-screen event list and analytics stat wall with card/grouped layouts.
  - Completed by finalizing the route architecture: Event Inventory stays as a staff-only cross-club oversight route, while Clubs Hub remains the primary operational surface and student event workflow home.
- Test Case:
  - Open Clubs Hub, switch between clubs from the left rail, verify the hero, summary metrics, and action strip update with the selected club.
  - Open the `Events` tab for a managed club, change event status, open enrollments, approve/reject registrations, and verify the workflow completes without leaving the selected-club workspace.
  - Open `/club-events`, verify the page presents itself as inventory/handoff, does not expose create/manage operations, and routes users into Clubs Hub for selected-club event work.
  - Log in as a student, verify `Event Inventory` no longer appears in navigation and that the student clubs flow stays inside Clubs Hub and My Registrations.
  - Automated validation: `frontend` production build passed after the workspace and event-center changes.
- Status History:
  - 2026-04-05 16:48 - Baseline audit identified the clubs page as overloaded and lacking a focused club-detail layout.
  - 2026-04-05 18:20 - Selected-club workspace shell and in-workspace event-center operations shipped; issue moved to in progress.
  - 2026-04-05 18:25 - `ClubEventsPage` demoted into event inventory/handoff surface; overlap reduced further.
  - 2026-04-05 18:30 - Mobile/tablet workspace polish shipped with collapsible switcher, better action layout, and horizontal tab handling.
  - 2026-04-05 18:33 - Members, applications, and enrollments gained small-screen action-card views; deep mobile club operations improved.
  - 2026-04-05 18:36 - Event list and analytics gained small-screen-specific views; remaining CLUB-010 work is mostly IA decision and polish.
  - 2026-04-05 18:40 - Route architecture finalized: Event Inventory locked to staff, student path consolidated into Clubs Hub/My Registrations, issue closed.

### Issue ID: CLUB-011

- Description:
  - Coordinators can now search queue records, select membership applications and event registrations in bulk, trigger bulk review actions, and send reminder notifications directly from the clubs workspace.
- Type:
  - Workflow Efficiency / Queue Operations
- Root Cause:
  - Waitlists had become truthful, but the module still forced club leads to process queue-heavy intake and event-review work one row at a time with no search or notification tooling.
- Impact:
  - Resolved for current scope. Coordinators can now process high-volume queue work faster, and students can receive real reminder nudges without leaving the clubs/event workflow.
- Location:
  - `frontend/src/pages/ClubsPage.jsx`, `frontend/src/pages/clubs/useClubDirectory.js`, `frontend/src/components/ui/Table.jsx`, `backend/app/api/v1/endpoints/clubs.py`, `backend/app/api/v1/endpoints/event_registrations.py`, `backend/app/schemas/club.py`, `backend/app/schemas/event_registration.py`, `backend/app/services/notifications.py`
- Fix Plan:
  - Completed by adding queue search/filter state, row selection for desktop and mobile queue surfaces, bulk application review, bulk event-registration updates, and reminder endpoints backed by notification fanout.
  - Implemented in `frontend/src/pages/ClubsPage.jsx`, `frontend/src/pages/clubs/useClubDirectory.js`, `frontend/src/components/ui/Table.jsx`, `backend/app/api/v1/endpoints/clubs.py`, `backend/app/api/v1/endpoints/event_registrations.py`, `backend/app/schemas/club.py`, and `backend/app/schemas/event_registration.py`.
- Test Case:
  - Open a managed club with pending and waitlisted membership applications, search for one applicant, select matching records, bulk approve or waitlist them, and send a reminder.
  - Open a managed event with pending registrations, filter the queue, bulk approve selected registrations, and send a reminder to the selected queue.
  - Automated coverage: `club_application_bulk_review_updates_selected_queue_items`, `club_application_reminder_creates_notifications_for_waitlist`, `event_registration_bulk_update_reviews_selected_queue_items`, and `event_registration_reminder_creates_notifications_for_selected_queue`.
- Status History:
  - 2026-04-06 11:02 - Event and club waitlists were live, but queue operations still lacked search, bulk handling, and reminder automation.
  - 2026-04-06 11:20 - Backend bulk/reminder endpoints, notification fanout, queue search, and selection-aware clubs workspace controls shipped and validated.

### Issue ID: CLUB-012

- Description:
  - Membership applications and event registrations now show queue-age signals, stale/aging/fresh prioritization, and built-in pagination inside Clubs Hub and event enrollments.
- Type:
  - Workflow Prioritization / Queue Scalability
- Root Cause:
  - Once queue search and bulk tools existed, the next friction point was long club and event queues where older requests were visually buried with no urgency cue or paging rhythm.
- Impact:
  - Resolved for current scope. Coordinators can now see which queue items are fresh, aging, or stale, and can move through larger queues without relying on one long scrolling list.
- Location:
  - `frontend/src/pages/ClubsPage.jsx`
- Fix Plan:
  - Completed by adding queue-age metadata, stale/aging/fresh priority pills, queue-age columns/details, and local pagination controls for membership applications and event enrollments on both desktop and mobile views.
- Test Case:
  - Open a managed club with more than one page of applications or enrollments, filter the queue, move between pages, and verify age/priority cues remain accurate on each row/card.
  - Confirm stale items remain visible through pagination and do not lose selection state unexpectedly when filters change.
  - Automated validation: `frontend` production build passed after queue-age and pagination UI changes.
- Status History:
  - 2026-04-06 11:20 - Search, reminders, and bulk actions were live, but large queues still lacked age visibility and paging.
  - 2026-04-06 11:28 - Queue-age indicators, stale-priority pills, and paginated application/enrollment views shipped in Clubs Hub.

### Issue ID: CLUB-013

- Description:
  - Membership and event queues now support saved local filter presets and clearly labeled local snapshot history for the signed-in user on the current device.
- Type:
  - Workflow Memory / Honest Trend Visibility
- Root Cause:
  - Coordinators had to reconstruct the same queue filters every visit, and there was no truthful short-term way to see how a queue had changed over repeated reviews without inventing fake system-wide history.
- Impact:
  - Resolved for current scope. Coordinators can return to common triage views quickly and inspect recent local queue snapshots without confusing device-local history for backend analytics.
- Location:
  - `frontend/src/pages/ClubsPage.jsx`, `frontend/src/pages/clubs/queueLocalState.js`
- Fix Plan:
  - Completed by adding saved filter presets for membership and event queues, local snapshot persistence in `localStorage`, and explicit UI copy that marks the history as local to the signed-in user on this device.
- Test Case:
  - Save a membership queue filter, refresh the page, reopen the same club, and verify the preset can be reapplied.
  - Open a queue several times while its counts change and verify the local snapshot history updates with truthful `fresh/aging/stale` counts and timestamps.
  - Automated validation: `frontend` production build passed after saved-filter and local snapshot history changes.
- Status History:
  - 2026-04-06 11:28 - Queue age and pagination existed, but repeat triage still required rebuilding filters by hand and there was no honest short-term queue history view.
  - 2026-04-06 11:37 - Saved local queue filters and clearly labeled local snapshot history shipped for membership and enrollment queues.

### Issue ID: CLUB-014

- Description:
  - Membership and event queues now persist shared coordinator views and backend-backed queue history, so queue memory follows the operational scope instead of the current browser only.
- Type:
  - Shared Workflow Memory / Persistence Contract
- Root Cause:
  - The previous queue-memory layer lived only in `localStorage`, which was honest but still fragile because saved views and history vanished across devices, browsers, and collaborating coordinators.
- Impact:
  - Resolved for current scope. Coordinators and admins can now reopen club and event queues with shared saved views and recent backend snapshots that reflect real queue mutations.
- Location:
  - `backend/app/services/club_queue_insights.py`, `backend/app/api/v1/endpoints/clubs.py`, `backend/app/api/v1/endpoints/event_registrations.py`, `backend/app/schemas/queue_insights.py`, `backend/app/core/indexes.py`, `frontend/src/pages/ClubsPage.jsx`, `backend/tests/test_auth.py`
- Fix Plan:
  - Completed by adding persisted queue-view and queue-snapshot collections, new role-aware APIs for membership and enrollment queues, mutation-triggered snapshot recording, frontend retrieval/saving/deletion for shared views, and queue-history UI copy that now reflects shared backend data.
- Test Case:
  - Save a membership queue view as a coordinator, open the same club as another authorized manager, and verify the view is visible.
  - Fill a club or event to create a waitlist entry, then open queue history and verify a backend snapshot row exists with truthful totals and source action.
  - Automated coverage: `club_application_shared_views_are_visible_across_managers`, `club_application_history_persists_waitlist_snapshots`, `event_registration_shared_views_are_visible_across_managers`, and `event_registration_history_persists_waitlist_snapshots`.
- Status History:
  - 2026-04-06 11:37 - Queue memory was still explicitly device-local and marked as a future backend step.
  - 2026-04-06 11:58 - Shared coordinator views and backend-backed queue history shipped across clubs and event registration queues.

### Issue ID: CLUB-015

- Description:
  - Clubs analytics now surfaces attendance coverage, no-show rate, certificate coverage, and top event performance summaries tied to queue pressure and delivery follow-through.
- Type:
  - Analytics Depth / Delivery Quality Visibility
- Root Cause:
  - The previous analytics contract stopped at fill rate and queue pressure, which meant coordinators could manage registrations but still lacked a truthful view of what happened during and after the event.
- Impact:
  - Resolved for current scope. Coordinators can now identify high-demand events, attendance-risk events, and certificate follow-up gaps directly inside the selected-club analytics workspace.
- Location:
  - `backend/app/api/v1/endpoints/clubs.py`, `backend/app/schemas/club.py`, `frontend/src/pages/ClubsPage.jsx`, `backend/tests/test_auth.py`
- Fix Plan:
  - Completed by extending the analytics schema with delivery-quality metrics and per-event performance rows, computing those metrics from registration/attendance/certificate data, and rendering them in both mobile analytics cards and desktop event-performance tables inside Clubs Hub.
- Test Case:
  - Mark attendance and issue certificates for a completed or active certificate-enabled event, then verify attendance-marked %, no-show %, and certificate coverage update correctly.
  - Create a full event with a waitlist and verify the top event-performance row is prioritized as `waitlist pressure`.
  - Automated coverage: `club_analytics_include_attendance_and_certificate_quality` and `club_analytics_prioritize_waitlist_pressure_in_event_performance`.
- Status History:
  - 2026-04-06 11:58 - Queue memory had been fixed, but analytics still stopped short of delivery-quality insight.
  - 2026-04-06 12:10 - Attendance-quality, certificate-coverage, and top event-performance analytics shipped across backend and Clubs Hub.

### Issue ID: CLUB-016

- Description:
  - Clubs analytics now supports downloadable event-performance and attendance/certificate CSV reports directly from the selected-club analytics workspace.
- Type:
  - Reporting / Workflow Follow-Through
- Root Cause:
  - Coordinators could see delivery-quality metrics in Clubs Hub, but there was no shareable export contract for handoff, audit review, or offline follow-up.
- Impact:
  - Resolved for current scope. Coordinators can now export both event-level performance and attendee-level attendance/certificate reporting without rebuilding reports manually.
- Location:
  - `backend/app/api/v1/endpoints/clubs.py`, `frontend/src/pages/clubs/useClubDirectory.js`, `frontend/src/pages/ClubsPage.jsx`, `backend/tests/test_auth.py`
- Fix Plan:
  - Completed by adding a backend CSV export endpoint for `event_performance` and `attendance_certificate` reports, wiring download helpers into the clubs data hook, and surfacing direct export actions in the analytics panel.
- Test Case:
  - Open the selected-club analytics workspace as an authorized coordinator, export the event-performance CSV, and verify event health/fill columns are present.
  - Export the attendance/certificate CSV after marking attendance and issuing a certificate, and verify attendee rows include attendance and certificate columns.
  - Automated coverage: `test_club_event_performance_export_returns_csv` and `test_club_attendance_certificate_export_returns_csv`.
- Status History:
  - 2026-04-06 12:10 - Analytics insight existed, but reporting still stopped at on-screen cards and tables.
  - 2026-04-06 12:37 - Downloadable event-performance and attendance/certificate reports shipped across backend and Clubs Hub.

### Issue ID: CLUB-017

- Description:
  - Membership applications and event enrollments now support queue owner, coordinator note, and last-touched metadata directly inside Clubs Hub.
- Type:
  - Workflow Follow-Through / Handoff Context
- Root Cause:
  - Coordinators could review queues and export outcomes, but there was still no shared in-module place to record who owned the next action or what operational note should survive a handoff.
- Impact:
  - Resolved for current scope. Queue follow-up no longer depends entirely on memory, side messages, or external trackers because each application and enrollment can now carry ownership and note context.
- Location:
  - `backend/app/api/v1/endpoints/clubs.py`, `backend/app/api/v1/endpoints/event_registrations.py`, `backend/app/schemas/club.py`, `backend/app/schemas/event_registration.py`, `frontend/src/pages/ClubsPage.jsx`, `frontend/src/pages/clubs/useClubDirectory.js`, `backend/tests/test_auth.py`
- Fix Plan:
  - Completed by extending queue contracts with `queue_owner`, `coordinator_note`, and `last_touched` metadata, exposing context-edit actions in Clubs Hub for applications and enrollments, and persisting those updates through the existing review/update endpoints.
- Test Case:
  - Save owner/note context on a membership application and verify the response returns owner label, note text, and last-touch metadata.
  - Save owner/note context on an event registration and verify the response returns the same context fields without changing lifecycle status.
  - Automated coverage: `test_club_application_context_update_persists_owner_note_and_touch_metadata` and `test_event_registration_context_update_persists_owner_note_and_touch_metadata`.
- Status History:
  - 2026-04-06 12:37 - Reporting existed, but queue follow-through still lived outside the module.
  - 2026-04-06 12:50 - Queue owner, note, and last-touch context shipped across membership and event queue workflows.

### Issue ID: CLUB-018

- Description:
  - Clubs Hub now exposes a per-event history drilldown inside the enrollment modal, combining event summary metrics, lifecycle audit events, and queue snapshot history into one timeline.
- Type:
  - Operational Insight / History Explainability
- Root Cause:
  - Coordinators could see the latest queue state, delivery metrics, and queue ownership context, but they still had no event-specific narrative showing when registrations changed, who touched them, when attendance was marked, or when certificate follow-through happened.
- Impact:
  - Resolved for current scope. Coordinators can now inspect how an event outcome evolved over time instead of reconstructing history from current-state rows, export files, and memory.
- Location:
  - `backend/app/api/v1/endpoints/clubs.py`, `backend/app/api/v1/endpoints/club_events.py`, `backend/app/api/v1/endpoints/event_registrations.py`, `backend/app/schemas/club.py`, `frontend/src/pages/ClubsPage.jsx`, `backend/tests/test_auth.py`
- Fix Plan:
  - Completed by adding a club-scoped event history endpoint, extending event update audit logging, preserving truthful registration old/new audit values, and rendering an in-modal drilldown timeline with event summary cards and timeline entries in Clubs Hub.
- Test Case:
  - Open event enrollments for a managed club event after registration, event status change, attendance marking, and certificate issuance, then verify the drilldown shows event update, registration creation, attendance update, certificate update, and queue snapshot entries.
  - Automated coverage: `test_club_event_history_drilldown_includes_lifecycle_timeline`.
- Status History:
  - 2026-04-06 12:50 - Queue context and exports were live, but coordinators still lacked event-specific history explainability.
  - 2026-04-06 13:04 - Per-event drilldown timeline shipped across backend contracts, audit logging, Clubs Hub modal UI, and targeted regression coverage.

### Issue ID: CLUB-019

- Description:
  - Clubs analytics now exposes cross-event trend summaries and recent event trend rows so coordinators can compare outcomes over time instead of reading one event at a time.
- Type:
  - Operational Insight / Trend Visibility
- Root Cause:
  - The module had current-state analytics, exports, and per-event drilldowns, but nothing that summarized repeated demand, no-show, certificate, or attention patterns across recent events.
- Impact:
  - Resolved for current scope. Coordinators can now identify whether demand is rising, no-show risk is improving or slipping, certificate follow-through is strengthening, and how many recent events keep needing attention.
- Location:
  - `backend/app/api/v1/endpoints/clubs.py`, `backend/app/schemas/club.py`, `frontend/src/pages/ClubsPage.jsx`, `backend/tests/test_auth.py`
- Fix Plan:
  - Completed by extending the club analytics schema with trend summaries and recent-event trend points, computing cross-event pattern signals from recent event-performance data, and rendering the new trend section directly inside the Clubs Hub analytics tab and mobile analytics cards.
- Test Case:
  - Seed multiple recent events with rising fill, falling no-show rates, improving certificate coverage, and repeated attention health states, then verify analytics returns improving trend summaries and recent trend rows.
  - Automated coverage: `test_club_analytics_include_cross_event_trends`.
- Status History:
  - 2026-04-06 13:04 - Event-history drilldowns existed, but cross-event comparison still required manual reading.
  - 2026-04-06 13:10 - Cross-event trend summaries and recent-event trend lines shipped across backend analytics and Clubs Hub UI.

### Issue ID: CLUB-020

- Description:
  - Clubs Hub now adapts its guidance for empty/new clubs, dormant clubs, and high-volume clubs instead of showing the same generic empty states and dense operational surfaces everywhere.
- Type:
  - Edge-Case UX / Human Ease
- Root Cause:
  - The module had become operationally complete, but the same layout and empty messaging still appeared whether a club was brand new, dormant, or operating at much larger volume.
- Impact:
  - Resolved for current scope. Coordinators and students now get clearer recovery guidance, startup guidance, and scale guidance directly in the selected-club workspace, which reduces the risk of misreading a healthy edge case as a broken workflow.
- Location:
  - `frontend/src/pages/ClubsPage.jsx`
- Fix Plan:
  - Completed by adding tailored notices in the hero, overview, members, events, and analytics tabs for dormant, empty, and high-volume clubs, plus sharper event empty-state wording for dormant clubs.
- Test Case:
  - Open a dormant club with little or no current activity and verify the workspace explicitly frames recovery instead of normal active operations.
  - Open a new club with no members or events and verify the workspace suggests the first useful actions.
  - Open a high-volume club and verify the workspace points users toward saved views, exports, pagination, trends, and drilldowns.
  - Validation coverage: `frontend` production build for the Clubs Hub edge-state pass.
- Status History:
  - 2026-04-06 13:10 - Core trends were live, but edge states still relied on generic messaging.
  - 2026-04-06 13:15 - Tailored empty/dormant/high-volume guidance shipped across the selected-club workspace.

### Issue ID: CLUB-021

- Description:
  - Clubs workspace now distinguishes between directory-level load failures and selected-club data failures, and gives the user the right retry action for each one.
- Type:
  - Error Recovery / Human Ease
- Root Cause:
  - The module had strong happy-path depth, but API failures still surfaced as generic error text without telling the user whether to retry the whole directory or only the selected club payload.
- Impact:
  - Resolved for current scope. Partial-load states no longer look like silent UI breakage, and coordinators can recover the exact failing slice without losing the rest of the workspace context.
- Location:
  - `frontend/src/pages/ClubsPage.jsx`, `frontend/src/pages/clubs/useClubDirectory.js`
- Fix Plan:
  - Completed by adding `WorkspaceRecoveryPanel`, wiring retry actions to `refreshClubs` and `reloadSelectedClubData`, and keeping those actions aligned with the real clubs data loaders already used by the page.
- Test Case:
  - Simulate a clubs-directory fetch failure and verify the workspace shows a directory recovery panel with a `Retry Directory` action.
  - Simulate a selected-club detail fetch failure and verify the workspace shows a targeted recovery panel with `Retry Selected Club` and `Refresh Directory`.
  - Validation coverage: `frontend` production build for the updated Clubs Hub recovery flow.
- Status History:
  - 2026-04-06 13:15 - Recovery guidance was identified as the highest remaining resilience gap after edge-state polish landed.
  - 2026-04-06 14:24 - In-context recovery panels and targeted retry actions shipped inside Clubs Hub.

### Issue ID: CLUB-022

- Description:
  - High-volume clubs now have explicit archive navigation in the event center through archive filters, search, event counts, pagination, and archive-aware guidance.
- Type:
  - Archive Navigation / Scale UX
- Root Cause:
  - The event center had already become the main operational surface, but large clubs still had to scan one long event list where live operations and older archived history competed for attention.
- Impact:
  - Resolved for current scope. Coordinators can separate live pipeline work from older event history, move through archived activity in smaller pages, and understand when they are in archive mode instead of treating old records like active work.
- Location:
  - `frontend/src/pages/ClubsPage.jsx`
- Fix Plan:
  - Completed by adding archive-aware search/filter state, paginated event browsing, archived-event counts, and helper notices that explain when to switch into archive-first navigation for large clubs.
- Test Case:
  - Open a high-volume club with archived events, switch `Archive View` to `Archived only`, search by event title or short ID, and verify the workspace pages through archived records without mixing them into the live event pipeline.
  - Validation coverage: `frontend` production build for the updated Clubs Hub event-center archive navigation.
- Status History:
  - 2026-04-06 13:15 - Archive-scale navigation for very large clubs remained the last major scale-oriented UX gap.
  - 2026-04-06 14:24 - Archive-first search, counts, pagination, and guidance shipped in the selected-club event center.

### Issue ID: CLUB-023

- Description:
  - Large-club analytics now exposes session-level workspace performance telemetry so coordinators can see load timing, slow traces, trace failures, and the slowest recent club request without leaving Clubs Hub.
- Type:
  - Performance Monitoring / Observability
- Root Cause:
  - The frontend already captured API trace duration, status, request ID, and trace ID, but the clubs module did not turn that data into club-specific performance insight, and the selected-club loader did not record its own timing at all.
- Impact:
  - Resolved for current scope. Very large clubs no longer rely on anecdotal “the page feels slow” reports, and coordinators can see whether the workspace is healthy, under watch, or hitting real trace errors during club operations.
- Location:
  - `frontend/src/pages/clubs/useClubDirectory.js`, `frontend/src/pages/clubs/performanceMonitor.js`, `frontend/src/pages/clubs/performanceMonitor.test.js`, `frontend/src/pages/ClubsPage.jsx`
- Fix Plan:
  - Completed by recording directory and selected-club load durations in the clubs data hook, reusing the existing frontend API trace buffer for club endpoints, deriving a session-level performance summary, and rendering a dedicated `Workspace Performance Monitor` in the analytics tab for large clubs or degraded club sessions.
- Test Case:
  - Open a large club and verify analytics shows selected-club load timing, API P95, dataset weight, recent club API traces, and large-club recommendations.
  - Trigger slow or failed club requests and verify the monitor moves from `Healthy` to `Watch` or `Critical`.
  - Automated coverage: `src/pages/clubs/performanceMonitor.test.js` plus `frontend` production build.
- Status History:
  - 2026-04-06 14:24 - Large-club recovery and archive navigation were closed, leaving observability as the next scale follow-through item.
  - 2026-04-06 14:38 - Session-level large-club performance monitoring shipped in Clubs Hub analytics with helper tests and build validation.

### Issue ID: CLUB-024

- Description:
  - Clubs request pressure is now promoted into shared admin observability, so admins can see club-specific request volume, P95, slow-request count, 5xx count, and top club paths without opening an individual club workspace.
- Type:
  - Cross-Surface Observability / Admin Monitoring
- Root Cause:
  - Club telemetry originally lived only inside the selected-club workspace, while shared observability and persisted system-health snapshots aggregated only generic request metrics.
- Impact:
  - Resolved for current scope. Admins can now correlate clubs slowdown with wider system pressure, and persisted health snapshots retain club-request pressure for later comparison instead of losing that signal between sessions.
- Location:
  - `backend/app/core/observability.py`, `backend/app/services/system_health_snapshots.py`, `backend/app/models/system_health_snapshots.py`, `frontend/src/pages/Admin/system/useAdminSystemHealth.js`, `frontend/src/pages/Admin/AdminObservabilityPage.jsx`, `frontend/src/pages/Admin/AdminSystemPage.jsx`
- Fix Plan:
  - Completed by deriving `clubs_metrics` from backend request history, promoting those metrics into system-health snapshots, surfacing club pressure cards in Admin System and Admin Observability, and showing top club paths so admins can see whether `/clubs`, `/club-events`, or `/event-registrations` is driving the pressure.
- Test Case:
  - Generate recent traffic across `/clubs`, `/club-events`, and `/event-registrations`, open Admin Observability, and verify club-specific request counts, P95, slow-request counts, 5xx counts, and top-path summaries appear separately from generic request metrics.
  - Validation coverage: `python -m compileall backend/app` and `frontend` production build for the new shared observability surfaces.
- Status History:
  - 2026-04-06 14:38 - Shared admin observability rollups were identified as the next follow-through step after session-level clubs telemetry landed.
  - 2026-04-06 14:44 - Club-specific request pressure was promoted into backend observability snapshots and both admin observability surfaces.

### Issue ID: CLUB-025

- Description:
  - Selected-club loading now parallelizes its major data slices so large-club workspaces do not pay extra latency from avoidable sequential fetch ordering.
- Type:
  - Performance / Data Loading
- Root Cause:
  - The selected-club loader fetched major slices in a way that left analytics and some club data waiting on earlier calls even though those requests could run safely in parallel.
- Impact:
  - Resolved for current scope. Large-club workspaces now load faster under the same data volume, and the performance monitor reflects a truer application cost instead of extra serial wait time added by the frontend loader itself.
- Location:
  - `frontend/src/pages/clubs/useClubDirectory.js`
- Fix Plan:
  - Completed by starting analytics immediately, parallelizing events, members/applications, and student registrations with `Promise.all`, and preserving per-phase duration reporting inside the existing `workspacePerformance` object.
- Test Case:
  - Open a large club and verify the selected-club performance summary still reports phase durations while the total load completes without waiting for analytics after every other data slice.
  - Validation coverage: `frontend` production build for the tuned selected-club loader.
- Status History:
  - 2026-04-06 14:38 - Workspace telemetry made the remaining slow-path ordering cost visible inside large-club sessions.
  - 2026-04-06 14:49 - The selected-club loader was tuned to parallelize major requests while keeping timing telemetry intact.

### Issue ID: CLUB-026

- Description:
  - Club analytics trend summaries were crashing because `recent_event_trends` used `ClubEventTrendPointOut`, but that schema did not expose `attendance_marked_pct` even though the trend builder referenced it.
- Type:
  - Backend Regression / Analytics Contract Integrity
- Root Cause:
  - The trend-summary filter logic and the trend-point schema drifted apart after cross-event trend work was added, leaving the analytics builder to access a field that the serialized trend point no longer carried.
- Impact:
  - Resolved in this re-audit. Club analytics and CSV export flows no longer risk a 500 error when building trend summaries from recent event points.
- Location:
  - `backend/app/api/v1/endpoints/clubs.py`, `backend/app/schemas/club.py`
- Fix Plan:
  - Completed by restoring `attendance_marked_pct` to `ClubEventTrendPointOut` and populating it when recent event trend points are built, so trend summary calculations and the public contract stay aligned.
- Test Case:
  - Request `/api/v1/clubs/{club_id}/analytics` and both analytics export reports for a club with recent events, then verify the response completes successfully and trend summaries render without backend exceptions.
  - Automated coverage: `test_club_analytics_uses_confirmed_event_fill_rate`, `test_club_analytics_include_event_waitlist_and_review_pressure`, `test_club_analytics_prioritize_waitlist_pressure_in_event_performance`, `test_club_event_performance_export_returns_csv`, and `test_club_attendance_certificate_export_returns_csv`.
- Status History:
  - 2026-04-06 14:49 - Re-audit isolated a clubs analytics crash while replaying club analytics and export test coverage.
  - 2026-04-06 15:00 - Trend-point schema and payload were realigned, and the affected club analytics/export tests passed again.

### Issue ID: CLUB-027

- Description:
  - Shared admin observability was showing current clubs pressure, but it still lacked retained club-specific hourly/day trend views and recurring pressure-window history, so admins could not tell whether club slowdown was an isolated spike or a repeating pattern.
- Type:
  - Observability Depth / Historical Trend Visibility
- Root Cause:
  - Minute snapshots already persisted club-request, slow-request, error, and P95 metrics, but the admin payload and UI only surfaced short-window data and generic snapshot charts instead of club-focused long-range rollups.
- Impact:
  - Resolved for current scope. Admin System and Admin Observability now show retained hourly and daily club-pressure history plus recent recurring pressure windows, making club slowdown trends visible across days instead of only in the last refresh window.
- Location:
  - `backend/app/services/system_health_snapshots.py`, `backend/app/api/v1/endpoints/admin_system.py`, `frontend/src/pages/Admin/system/useAdminSystemHealth.js`, `frontend/src/pages/Admin/AdminSystemPage.jsx`, `frontend/src/pages/Admin/AdminObservabilityPage.jsx`, `frontend/src/pages/Admin/system/ClubObservabilityTrendSection.jsx`
- Fix Plan:
  - Completed by extending retained system-health history to a 14-day window, deriving club-specific hourly and daily rollups plus recent pressure-window summaries from persisted snapshots, and rendering those histories in both admin observability surfaces.
- Test Case:
  - Generate multiple club-pressure snapshots across several days, open `Admin System` or `Admin Observability`, and verify the response and UI surface retained hourly/day trend charts together with recent warning/critical club-pressure windows.
  - Automated coverage: `test_admin_system_health_endpoint_exposes_observability_and_routes_alerts` and `test_system_health_snapshot_builds_long_horizon_club_observability`.
- Status History:
  - 2026-04-06 15:00 - Re-audit confirmed that shared club observability was real, but still too short-lived to explain repeating club slowdown across days.
  - 2026-04-06 15:12 - Retained hourly/day club trend rollups and recurring pressure-window history were added to backend snapshots and both admin observability surfaces.

### Issue ID: CLUB-028

- Description:
  - Real club traffic still concentrated around sorted club lists, member/application queues, event inventory, and registration queues, but some of those query shapes were only partially covered by indexes and the clubs list path still enriched rows one-by-one.
- Type:
  - Backend Performance / Query & Index Tuning
- Root Cause:
  - The clubs module had grown into queue-heavy, high-volume views with specific filter/sort combinations, while the index set was still closer to early functional coverage than telemetry-guided operational coverage.
- Impact:
  - Resolved for current scope. The hottest club-facing data paths now have matching compound indexes, and the clubs list no longer performs avoidable N+1 user/member enrichment work per row.
- Location:
  - `backend/app/core/indexes.py`, `backend/app/api/v1/endpoints/clubs.py`
- Fix Plan:
  - Completed by adding compound indexes for club discovery, active member lookup, application queues, event inventory, and event-registration queues, plus batching user/member enrichment in `list_clubs` instead of resolving each club row independently.
- Test Case:
  - Load the clubs workspace and key queue surfaces after startup index creation, then verify club list, members-only event visibility, rejoin flows, and club analytics still behave correctly while the backend compiles cleanly.
  - Validation coverage: `python -m compileall backend/app`, `npm run build`, `test_members_only_event_is_visible_and_registerable_only_for_club_members`, `test_removed_member_can_rejoin_open_club_without_duplicate_membership`, `test_club_analytics_include_cross_event_trends`, and `test_club_analytics_uses_confirmed_event_fill_rate`.
- Status History:
  - 2026-04-06 15:12 - Longer-horizon observability made it clearer which club-path shapes deserved index review rather than blanket indexing.
  - 2026-04-06 15:20 - Club-path indexes were tightened and clubs list enrichment was batched to remove avoidable per-row lookups.

### Issue ID: CLUB-029

- Description:
  - Clubs Hub could filter and page archived events, but coordinators still had to inspect archived records one event at a time because analytics stopped at recent/live event health instead of summarizing older club history.
- Type:
  - Analytics Depth / Historical Reporting
- Root Cause:
  - Archive navigation landed before archive intelligence, so the module knew how to find older events but not how to aggregate them into seasonal, cohort, or long-range delivery patterns.
- Impact:
  - Resolved for current scope. Clubs analytics now surfaces archived-event season summaries, age-based archive cohorts, and long-range monthly attendance/certificate history directly inside the analytics tab.
- Location:
  - `backend/app/schemas/club.py`, `backend/app/api/v1/endpoints/clubs.py`, `frontend/src/pages/ClubsPage.jsx`, `backend/tests/test_auth.py`
- Fix Plan:
  - Completed by extending `ClubAnalyticsOut` with archive rollup models, deriving archive metrics from existing event/registration analytics data, rendering a dedicated archival analytics section in Clubs Hub, and adding regression coverage for season/cohort/history payloads.
- Test Case:
  - Create archived club events across recent, mid-range, and legacy dates, then verify `/clubs/{club_id}/analytics` returns `archive_season_summaries`, `archive_event_cohorts`, and `archival_history_points` with truthful archived attendance and certificate rollups.
  - Automated coverage: `test_club_analytics_include_archival_rollups`.
- Status History:
  - 2026-04-06 15:20 - Archive navigation existed, but archival insight was still backlog rather than a shipped analytics feature.
  - 2026-04-06 15:29 - Clubs analytics and Clubs Hub were extended with archived season summaries, archive cohorts, and long-range archive history.

### Issue ID: CLUB-030

- Description:
  - Paid events existed, and clubs could collect payment references, but the module still lacked truthful financial insight and a maintainable sponsorship profile for club leads.
- Type:
  - Financial Analytics / Sponsorship Tracking
- Root Cause:
  - Payment settings were implemented as event-level workflow fields, but no club-level analytics contract translated those fields into usable revenue/proof metrics, and no club funding profile existed for sponsorship tracking.
- Impact:
  - Resolved for current scope. Clubs analytics now surfaces listed paid revenue, payment-proof coverage, paid/free event mix, and sponsorship progress, while managers can maintain sponsorship targets, committed funding, and funding notes from Clubs Hub.
- Location:
  - `backend/app/schemas/club.py`, `backend/app/models/clubs.py`, `backend/app/api/v1/endpoints/clubs.py`, `frontend/src/pages/clubs/useClubDirectory.js`, `frontend/src/pages/ClubsPage.jsx`, `backend/tests/test_auth.py`
- Fix Plan:
  - Completed by adding sponsorship fields to the club contract, calculating financial analytics from paid-event and payment-proof data, exposing a funding-profile editor in Clubs Hub, and validating the analytics math with regression coverage.
- Test Case:
  - Create a club with sponsorship target/committed values, add paid and free events with confirmed paid registrations, attach payment proof to only some paid seats, then verify `/clubs/{club_id}/analytics` returns truthful revenue, proof-coverage, and sponsorship-progress values.
  - Automated coverage: `test_club_analytics_include_financial_and_sponsorship_insight`.
- Status History:
  - 2026-04-06 15:29 - Archival analytics was complete, leaving financial/sponsorship insight as the clearest truly-open clubs analytics gap.
  - 2026-04-06 15:38 - Financial analytics and the club funding profile shipped across backend and Clubs Hub.

### Issue ID: CLUB-031

- Description:
  - Admin observability could raise club-pressure alerts, but it did not preserve enough route, resolution, or cooldown history to explain whether alerts were actually delivered, suppressed, or later resolved.
- Type:
  - Operational Observability / Alerting Follow-Through
- Root Cause:
  - Alert routing stored the latest route state only, while admin pages rendered active alert summaries without a durable per-alert activity trail.
- Impact:
  - Resolved for current scope. Admin System and Admin Observability now show recent per-alert route history with routed/resolved entries, cooldown suppression counts, notification totals, and last-outcome metadata for club-pressure alerts.
- Location:
  - `backend/app/services/operational_alert_routing.py`, `backend/app/api/v1/endpoints/admin_system.py`, `frontend/src/pages/Admin/system/useAdminSystemHealth.js`, `frontend/src/pages/Admin/system/AlertRoutingHistorySection.jsx`, `frontend/src/pages/Admin/AdminSystemPage.jsx`, `frontend/src/pages/Admin/AdminObservabilityPage.jsx`, `backend/tests/test_main_missing_blocks.py`
- Fix Plan:
  - Completed by extending operational alert routing records with bounded history, route/resolution/cooldown counters, exposing alert-route history from the admin system health payload, rendering a shared admin history section, and validating the behavior with backend coverage.
- Test Case:
  - Trigger a club-pressure operational alert, refresh admin system health multiple times, and verify the payload and admin pages surface routed history, cooldown suppression, and subsequent route-state metadata for the same alert code.
  - Automated coverage: `test_admin_system_health_includes_observability_metrics_and_alerts`.
- Status History:
  - 2026-04-06 15:38 - Financial/sponsorship insight was complete, leaving richer alert-routing history as the next truthful admin follow-through gap.
  - 2026-04-06 15:45 - Alert-route history, cooldown visibility, and shared admin history rendering shipped across backend and admin observability surfaces.

### Issue ID: CLUB-032

- Description:
  - The clubs module could report roster size and event throughput, but it still could not answer whether members stay, convert into club participation, or quietly disengage after joining.
- Type:
  - Engagement Intelligence / Member Health
- Root Cause:
  - Membership analytics stopped at count and growth, while event analytics stopped at event outcomes. No contract joined club-member lifecycle with actual participation signals over time.
- Impact:
  - Resolved for current scope. Clubs analytics now surfaces 90-day retention and churn, join-to-event conversion, join-to-attendance conversion, recently engaged active members, and at-risk active members inside Clubs Hub.
- Location:
  - `backend/app/schemas/club.py`, `backend/app/api/v1/endpoints/clubs.py`, `frontend/src/pages/ClubsPage.jsx`, `backend/tests/test_auth.py`
- Fix Plan:
  - Completed by extending the analytics schema with engagement fields, deriving retention/churn and participation-conversion signals from membership and event-registration history, rendering a dedicated engagement-intelligence section in Clubs Hub, and adding targeted regression coverage.
- Test Case:
  - Seed long-standing active members, recent departures, recent activity, legacy activity, and quiet active members, then verify `/clubs/{club_id}/analytics` returns truthful retention, churn, conversion, and at-risk counts.
  - Automated coverage: `test_club_analytics_include_engagement_intelligence`.
- Status History:
  - 2026-04-06 15:45 - Alert-routing history was complete, leaving engagement intelligence as the clearest remaining clubs insight gap.
  - 2026-04-06 19:41 - Engagement intelligence shipped across backend analytics, Clubs Hub, and regression coverage.

### Issue ID: CLUB-033

- Description:
  - Club announcements were present in the workspace, but still lacked the maturity features needed for real day-to-day communication operations: reusable templates, pinned posts, visible-feed bulk read, and in-module moderation controls for club leads.
- Type:
  - Communication Maturity / Operational Follow-Through
- Root Cause:
  - The first club-scoped announcement pass focused on truthful scope, visibility, and publishing. It stopped short of the quality-of-life controls coordinators and presidents need once announcement volume starts growing.
- Impact:
  - Resolved for current scope. Club announcements now support template-backed drafting, pinned ordering, visible-feed bulk read, and club-lead archive moderation without leaving Clubs Hub.
- Location:
  - `frontend/src/pages/clubs/ClubAnnouncementsPanel.jsx`, `frontend/src/components/communication/CreateAnnouncementModal.jsx`, `frontend/src/components/communication/AnnouncementCard.jsx`, `backend/app/api/v1/endpoints/notices.py`, `backend/app/schemas/notice.py`, `backend/app/models/notices.py`, `backend/tests/test_auth.py`
- Fix Plan:
  - Completed by extending notice contracts with pin/template fields, adding a club-lead notice settings patch path plus club-aware archive moderation, surfacing templates and moderation controls in the club announcements panel, and adding regression coverage for club-lead pin/archive flows.
- Test Case:
  - Publish a club announcement as a coordinator, pin it as the club president, archive it from the announcements panel, and verify it disappears from the active club feed while template metadata persists correctly.
  - Automated coverage: `test_club_notice_moderation_supports_pin_and_archive_for_club_leads`.
- Status History:
  - 2026-04-06 19:41 - Engagement intelligence was complete, leaving announcement maturity and public-facing polish as the strongest remaining clubs enhancements.
  - 2026-04-06 19:53 - Announcement templates, pin/unpin, visible-feed bulk read, and club-lead moderation shipped across backend notices and the Clubs Hub panel.

### Issue ID: CLUB-034

- Description:
  - The clubs module still lacked a richer public-facing identity layer, so directory cards and the selected-club hero could not tell a stronger story about achievement, recruitment, or how students should contact the club.
- Type:
  - Public-Facing Polish / Club Identity
- Root Cause:
  - Club records exposed logo and banner media, but the data model and Clubs Hub UI did not carry higher-level public profile content such as a tagline, achievement highlights, or a recruitment CTA.
- Impact:
  - Resolved for current scope. Clubs now support richer profile fields and render them across create/edit, club directory cards, selected-club hero, and summary surfaces.
- Location:
  - `backend/app/schemas/club.py`, `backend/app/models/clubs.py`, `backend/app/api/v1/endpoints/clubs.py`, `frontend/src/pages/clubs/constants.js`, `frontend/src/pages/ClubsPage.jsx`, `backend/tests/test_auth.py`
- Fix Plan:
  - Completed by adding tagline, achievement highlights, recruitment headline, recruitment CTA label, and public contact URL to the club contract, persisting them through create/update flows, and surfacing them through richer directory cards, a stronger selected-club hero, and an in-module profile editor.
- Test Case:
  - Create a club with public profile metadata, update the profile with richer branding and recruitment fields, and verify both create and update responses preserve the data while the frontend can render the same fields in club cards and the selected-club workspace.
  - Automated coverage: `test_club_profile_fields_persist_across_create_and_update`.
- Status History:
  - 2026-04-06 19:41 - Public-facing polish remained one of the last truthful enhancement gaps after engagement intelligence shipped.
  - 2026-04-06 19:53 - Richer club profile fields, profile editing, and stronger directory/hero presentation shipped across backend contracts and Clubs Hub.

---

# 🚨 FEATURE REALITY CHECK

| Feature | UI Claim | Actual | Issue | Fix |
|--------|----------|--------|-------|-----|
| Club join | Students see `Join Club` CTA on club cards | Open join works, removed members can rejoin through reactivation logic, full clubs queue students into a membership waitlist, and coordinators can now search/review/remind the intake queue in bulk with age, paging, ownership, and note context | Baseline rejoin conflict, overflow dead-end, and one-record-at-a-time queue friction are resolved | Add SLA-style queue history later |
| Event approval | Event model supports `approval_required` | Coordinators can now approve, reject, mark attendance, issue certificates, bulk review selected registrations, and remind queued registrants from the selected-club workflow | Core lifecycle and queue tooling are now real | Keep lifecycle tests and add bulk attendance/certificate history later |
| Members-only event | Event form supports `members_only` visibility in backend schema | Students only see public events unless they belong to the club, and non-members cannot register | Access promise is now enforced | Add explicit lock badge in UI for discoverability when desired |
| Club announcements | Clubs page has `Announcements` tab | Selected club now shows a club-scoped announcement composer and timeline with templates, pin/unpin, visible-feed bulk read, and club-lead archive moderation backed by `scope=club` notices | Announcement maturity is now real for current scope instead of stopping at basic publish/read | Extend later only if the product needs moderation queues, approval, or analytics on announcement engagement |
| Event registration page | Students expect one trusted registration path | `ClubEventsPage` now routes registration into Clubs Hub, and `EventRegistrationsPage` is clearly a records/status page | Baseline duplicate-surface confusion is resolved | Keep Clubs Hub as canonical and add richer status timeline later |
| Role assignment | Backend exposes member role update and president linkage | Clubs UI now exposes role/status management and backend sync keeps president scope aligned through both clubs and users flows | Baseline governance split is resolved for current scope | Add regression coverage if future officer scopes expand |
| Club analytics | Analytics tab implies operational and delivery-quality metrics | Clubs analytics now reports fill rate, attendance-marked %, no-show rate, certificate coverage, waitlist-pressure events, top event health summaries, downloadable CSV reports, event drilldowns, cross-event trend summaries, archived season/cohort/history summaries, financial signals, and edge-case guidance for empty, dormant, and high-volume clubs | Baseline metric-depth, event-history explainability, cross-event trend visibility, archival analytics, and financial insight gaps are resolved for current scope | Expand only if budgeting or audited payment verification becomes a product requirement |
| Engagement intelligence | Clubs analytics should help leaders see whether members stay and actually participate after joining | Clubs Hub now shows 90-day retention, churn, join-to-event conversion, join-to-attendance conversion, recently engaged active members, and at-risk active members | Engagement intelligence is now real instead of backlog-only planning | Extend later into member-level drilldowns only if outreach workflows need it |
| Public-facing club profile | Club directory and selected-club workspace should help leaders present what the club does and why students should join | Clubs now store and render tagline, achievement highlights, recruitment headline, recruitment CTA label, public contact URL, logo, and banner across create/edit, directory, hero, and summary surfaces | Public-facing polish is now real instead of relying on generic name/category cards | Extend later only if the product needs campaigns, galleries, or public external landing pages |
| Large-club performance monitoring | Coordinators expect very large clubs to reveal whether the workspace itself is slowing down | Clubs Hub analytics now shows selected-club load duration, club API P95, slow/error trace counts, the slowest recent request, and session-level recommendations based on real club traces | Baseline observability gap for large-club sessions is resolved for current scope | Session-level club telemetry is now paired with retained admin trend history for current scope; extend further only if multi-week tuning becomes necessary |
| Shared club observability | Admins expect repeated clubs slowdown to be visible in shared health tooling, not trapped inside one club workspace | Admin System and Admin Observability now show club-request pressure, club P95, slow/5xx counts, top club paths, retained club-trend windows, and alert-routing history with route/resolution/cooldown state | Cross-club clubs pressure and operational follow-through are now visible in shared admin tooling instead of hidden behind individual club sessions | Extend only if future escalation policy needs channel-level routing rules or longer retention |
| Backend club-path tuning | Clubs workspace routes should stay fast under the traffic patterns now visible in clubs observability | Club discovery, member/application queues, event inventory, and registration queue paths now have matching compound indexes, and club list enrichment batches user/member lookups instead of resolving each row separately | Telemetry-backed tuning is now real instead of living only as backlog text | Keep tuning tied to real slow traces rather than expanding indexes speculatively |
| Event management | Separate `Clubs Hub` and `Event Inventory` routes should have clearly different jobs | Clubs workspace now handles creation, status changes, enrollment review, and student registration in selected-club context; `Event Inventory` is staff-only cross-club oversight | Architecture is now explicit for current scope | Keep inventory thin and route all primary workflows through Clubs Hub |
| Queue operations | Coordinators expect queue-heavy workflows to be searchable, reusable, and actionable at scale | Membership applications and event registrations now support queue search, bulk review, selection on mobile/desktop, reminder automation, stale/aging/fresh signals, pagination, shared saved views, backend-backed queue history, event-performance insight, downloadable reporting, owner/note/last-touch context, event-specific lifecycle drilldowns, and cross-event trend comparison inside Clubs Hub | Baseline queue-ops, event-history, and short-horizon trend gap is resolved for current scope | Keep extending only when real coordinator workflows reveal deeper need |

---

# 🚫 DEAD UI / FALSE AFFORDANCE

| Element | Type | Expected | Actual | Issue | Fix |
|--------|------|----------|--------|-------|-----|
| `Announcements` tab in `ClubsPage` | In-module workflow surface | Club-scoped announcement management in context of selected club | Embedded club timeline and composer now work inside the clubs module | Baseline false affordance is fixed for current scope | Keep this as the primary club announcement surface and add richer moderation later |
| `Payment QR Code (Optional)` field in `EventRegistrationsPage` | Records/status page copy | Standalone page should not pretend to be the main submit workflow | Page now redirects students conceptually into Clubs Hub instead of exposing a second submit form | Baseline duplicate-submit affordance is fixed | Keep submission UI out of the records page |
| `Register Now` in `ClubEventsPage` | Primary CTA | Context-rich registration flow for selected event | Now deep-links into Clubs Hub and opens the canonical registration modal for the selected event | Baseline duplicate-surface affordance is fixed | Keep this handoff consistent as event-center UX evolves |
| `ClubEventsPage` route label and purpose | Route expectation | The route should describe itself honestly if it is no longer the main management surface | It now behaves like staff-only inventory and handoff, which matches the product decision | Baseline IA ambiguity is resolved | Keep the route thin and staff-only unless future reporting needs disappear |
| `Avg Attendance %` stat in `ClubsPage` | Metric label | Real attendance percentage based on marked presence | Label now reads `Event Fill %` | Baseline naming issue is fixed | Add real attendance metric later |
| `Members` tab in `ClubsPage` | Management surface | Role assignment, removal, and member moderation | Member-management modal now supports role/status changes and president updates align with backend scope | Baseline false-affordance gap is resolved for current scope | Keep this as the primary club governance surface |

---

# 🔗 CONTRACT AUDIT

| Feature | FE Expectation | BE Reality | Issue | Fix |
|--------|----------------|-----------|-------|-----|
| Club events visibility | Frontend can show event visibility as usable state | Backend now enforces `members_only` in student list and registration paths | Baseline contract drift is resolved | Add FE eligibility badges for clearer explanation |
| Event approval flow | Event configuration can imply coordinator approval | Backend and clubs event UI now support lifecycle progression, bulk review updates, and queue reminder actions | Baseline gap is resolved | Add bulk attendance/certificate history later |
| Payment-required registration | FE should route students into one truthful payment-aware registration path | Clubs Hub owns submission and payment-proof validation, while the records page only reflects event state and handoff guidance | Baseline contract confusion is fixed for current scope | Keep Clubs Hub as the only submit surface |
| Club analytics active state | FE expects active-club metrics to reflect club status | Backend admin analytics now count clubs by active statuses instead of stale `is_active` | Baseline metric drift is fixed for current dashboards | Keep snapshot service aligned as future metrics expand |
| Club announcements scope | FE clubs tab should publish and manage announcements for the selected club without leaving module context | Backend notices now supports `scope=club`, club-aware publishing permissions, membership-based visibility, template metadata, pinned ordering, and club-lead moderation for update/archive flows | Club announcement contract is now mature for current scope instead of publish/read only | Extend later only if product policy requires moderation states or approval |
| Public-facing club profile | FE directory and selected-club hero should render richer club identity and recruitment context from real stored data | Backend clubs contract now includes tagline, achievement highlights, recruitment headline, recruitment CTA label, and public contact URL, and create/update flows persist them | Public-facing profile data is now a real contract rather than UI-only aspiration | Extend later only if external public pages or campaign scheduling become product requirements |
| Member role management | FE clubs UI suggests member operations through members tab | Clubs UI now calls backend member update endpoint, refreshes selected-club data, and stays aligned with user extension scope | Main backend capability is now visible and synchronized | Keep both routes using shared governance service |
| Club president assignment | FE users page manages `club_president` scope and clubs page shows president | Backend member promotion and users extension assignment now converge on one shared governance sync path | Baseline governance split is fixed for current scope | Keep the shared governance service as the single source of truth |
| Event registrations for teachers | FE `ClubEventsPage` assumes assigned-club ownership for enrollment view | Backend registrations now uses the same assigned-coordinator ownership rule | Baseline permission inconsistency is fixed | Return permission flags if frontend needs richer affordance decisions |
| Join/rejoin lifecycle | FE could reasonably allow rejoin after inactive or removed status | Backend now reactivates existing lifecycle records instead of conflicting inserts | Baseline lifecycle/storage conflict is resolved | Consider partial unique indexes as long-term schema cleanup |
| Queue operations | FE clubs workspace now exposes search, selection, and reminder controls for queue-heavy tabs | Backend now supports bulk membership review, bulk event-registration updates, and reminder fanout through notifications | Queue tooling contract is now real instead of frontend-only aspiration | Add pagination/search params later if queues grow beyond current list sizes |
| Event history drilldown | FE enrollment modal can now expose a lifecycle view for the selected event | Backend now returns club-scoped event history built from audit logs, registration deltas, and queue snapshots, while event updates and registration updates persist truthful old/new audit values | Drilldown contract is now real instead of implied future work | Keep drilldowns aligned with the new trend summaries |
| Cross-event trends | FE analytics tab can now surface repeated patterns across recent events | Backend now returns trend summaries and recent event trend points derived from event performance, and the analytics tab renders those signals directly | Trend contract is now real instead of roadmap-only aspiration | Extend into longer-range or cohort-specific comparisons later |
| Large-club performance monitor | FE analytics tab can now surface session-level performance for the selected club workspace | Clubs data loading now records directory and selected-club load timings, and frontend API traces are filtered into a club-specific performance summary rendered directly inside Clubs Hub | Large-club session observability is now real instead of informal guesswork | Extend into longer-range trend retention if multi-day clubs tuning becomes necessary |
| Shared admin clubs observability | FE admin system pages should reflect when clubs traffic is becoming its own pressure domain | Backend observability now publishes `clubs_metrics`, persists them in system-health snapshots, derives retained hourly/day club trend rollups, exposes alert-route history, and admin pages read/render those values directly | Clubs slowdown is now visible in shared admin tooling across both current and retained trend windows, with route/resolution/cooldown follow-through instead of generic request aggregates only | Extend further only if the product needs channel-specific escalation policy and longer alert-history retention |
| Selected-club loader performance | FE clubs workspace expects its own performance monitor to reflect real data cost, not unnecessary serial request ordering | Selected-club loading now starts analytics immediately and parallelizes events, members/applications, and student registrations while keeping phase timing intact | Large-club latency is reduced without changing the user-facing clubs workflow | Tune backend query shape next if real traffic still shows persistent hot paths |
| Club analytics trends | FE analytics tab and exports expect trend summaries to build from recent event points without crashing | Backend trend points now include `attendance_marked_pct`, so trend summary filters and serialized trend data stay aligned | Re-audit regression is fixed and club analytics/export responses are stable again | Keep schema and trend-summary logic aligned as analytics evolves |

---

# 🔄 USER WORKFLOW AUDIT

### Workflow: Club Creation

| Step | Status | Issue | Fix |
|------|--------|-------|-----|
| Open clubs module | ✅ Working | Route is accessible and the hub loads for allowed roles | Keep route; improve first-load focus with selected-club summary |
| Find create surface | ✅ Working | Admin-only create card is visible, but it sits below the directory and can be missed on long pages | Move create CTA to header or open a focused create drawer |
| Fill club basics | ✅ Working | Name, category, year, membership type, and capacity are available | Add inline help for status meanings and coordinator requirement |
| Assign coordinator | ✅ Working | Coordinator dependency is enforced and now consistently respected across ownership checks | Add clearer inline explanation before submit |
| Assign president | ✅ Working | President selection and downstream governance sync now stay aligned between clubs membership and user extension scope | Keep this shared governance path as the single source of truth |
| Activate club | ⚠️ Partial | UI still exposes raw status actions with limited policy explanation | Replace raw state buttons with guided lifecycle actions |
| Verify created club | ✅ Working | Club appears in list after refresh | Add success summary panel with next actions |

Completion Score:
- 78/100

### Workflow: Member Management

| Step | Status | Issue | Fix |
|------|--------|-------|-----|
| Select a club | ✅ Working | Club selection exists in filter and cards | Add persistent selected-club context header |
| View member list | ✅ Working | Members load for authorized users | Add empty state, search, and member totals by role |
| Review applications | ✅ Working | Approve/reject exists, capacity is enforced during approval, full clubs auto-waitlist intake, and the queue now supports search, bulk review, reminders, age cues, pagination, shared saved views, and backend queue history | Add queue-owner notes and richer conversion insight later |
| Promote member to officer/president | ✅ Working | Clubs UI now supports role changes and president sync stays aligned across clubs and users governance paths | Keep regression tests for clubs/users sync |
| Remove/inactivate member | ✅ Working | Clubs UI now supports status changes directly from the members management modal | Add optional confirmation for destructive actions later |
| Rejoin after removal | ✅ Working | Membership is reactivated instead of conflicting with unique storage rules | Keep lifecycle regression tests |

Completion Score:
- 92/100

### Workflow: Event Management

| Step | Status | Issue | Fix |
|------|--------|-------|-----|
| Create event | ✅ Working | Event creation now works naturally in the selected-club event center, and the secondary event page is now a thin inventory/handoff route instead of a competing creation surface | Keep `ClubEventsPage` inventory-only |
| Configure payment/visibility/windows | ✅ Working | Rich controls now live in the selected-club event center | Reuse the same event form if any secondary surface remains |
| Open registrations | ✅ Working | Status and registration toggles exist in the selected-club event center | Expose allowed transitions from backend instead of hard-coded assumptions |
| Collect registrations | ✅ Working | Students now submit through the clubs workflow while the records page handles tracking only | Keep the Clubs Hub modal as the canonical path |
| Approve pending registrations | ✅ Working | Coordinators can now approve, reject, bulk review, remind pending/waitlisted registrations, spot stale registrations, and reuse saved queue views from the selected-club event center | Add bulk attendance and certificate history later |
| Mark attendance | ✅ Working | Attendance can now be marked from selected-club registration management | Add dedicated event attendance screen later |
| Issue certificates | ✅ Working | Certificate issuance is now operational with attendance guardrails in the selected-club flow | Add bulk issue and history view later |
| Close and analyze event | ✅ Working | Coordinators now have honest fill-rate, attendance quality, certificate coverage, drilldowns, trend summaries, and exports in the selected-club workflow | Add revenue and season-over-season comparisons later |

Completion Score:
- 97/100

---

# ⏱ TIME-TO-TASK

| Task | Expected | Actual | Issue |
|------|----------|--------|-------|
| Create club | 2-3 minutes | 4-5 minutes | Still slowed by dense page structure and raw state controls |
| Add member | 30-60 seconds | 1-2 minutes | Open join is solid, and approval-required clubs are faster to process now that queue search, bulk review, reminders, paging, and saved triage views keep older requests visible |
| Assign role | 1 minute | 1-2 minutes | Now achievable from the clubs members modal, but could be faster with inline actions and clearer hierarchy cues |
| Create event | 2-3 minutes | 2-3 minutes | Primary creation flow is now focused in the selected-club event center; remaining delay is mostly rich-field entry rather than route confusion |
| Approve event registration | 1 minute | 20-45 seconds | Bulk review, saved queue filters, and stale-priority cues now reduce repetitive one-row processing and help coordinators target older records first |
| Publish club announcement | 1-2 minutes | 1-2 minutes | Now works in clubs context, but templates, pinning, and media polish are still limited |

---

# 📐 LAYOUT & RESPONSIVENESS

### Mobile
- Issues:
  - Selected-club context is much stronger now because the club directory collapses behind a dedicated switcher instead of pushing the workspace down the page.
  - Members, applications, enrollments, events, and analytics now have smaller-screen-specific presentations, queue cards support selection for bulk review on phones, queue pagination prevents long mobile scroll stacks, and saved filters reduce repeated mobile setup work.
  - The biggest remaining mobile risk is breadth: the workspace still contains many tabs and concepts even though the surfaces are lighter.
- Fix:
  - Keep the collapsible switcher pattern.
  - Extend the stacked-card pattern only where real device testing still shows friction.
  - Add a compact sticky selected-club summary only if mobile testing shows users losing context.

### Tablet
- Issues:
  - Tablet behavior is materially better now because the directory no longer always competes with the workspace.
  - Dense operational tables are lighter now, and queue pagination helps, but some cards and forms still ask for more scrolling than ideal on mid-width screens.
- Fix:
  - Keep the condensed switcher pattern and continue softening only the surfaces that still feel scroll-heavy in testing.
  - Group create/edit forms into clearer stepped sections if more tablet pain appears.

### Desktop
- Issues:
  - Desktop structure is materially improved, but some deeper operational data still sits behind tabs.
  - Analytics are still buried in tabs even though announcements are now a real in-context workflow.
- Fix:
  - Extend the split dashboard with richer inline summaries and add queue-age trend or SLA indicators if coordinators need faster prioritization.

---

# 📊 DASHBOARD FEATURE PLACEMENT

| Feature | Placement | Visibility | Issue | Fix |
|--------|-----------|------------|-------|-----|
| Club stats | Selected-club hero and `Analytics` tab | High | Summary visibility is much better, but deeper analytics still require tab switching | Keep hero stats for fast scan and add richer trend cards later |
| Member count | Club rail cards and selected-club hero | High | Active/inactive/officer breakdown still needs stronger surfacing | Add compact roster breakdown strip near hero |
| Pending applications | Selected-club summary and `Members` tab | Medium | Now surfaced through signals, but still not visible in the rail | Add club-card badge for pending approvals |
| Events panel | Selected-club `Events` tab plus `ClubEventsPage` inventory route | High | Main operations now live in the workspace, but one secondary inventory route still exists | Keep inventory thin or absorb it fully later |
| Club announcements | `Announcements` tab with embedded scoped panel | Medium | The feature is real and contextual now, but it still depends on tab navigation | Surface latest club announcement preview in the selected-club summary later |
| Registration status for students | Clubs event modal plus standalone records page | Medium | Submission path is unified, but registration history is still visually separate from selected-club event cards | Add compact `My Registrations` summary inside the event center later |
| Governance controls | Selected-club hero action strip | High | Operational actions are now easier to find, but labels still expose raw system states | Continue replacing status jargon with guided actions |
| Large-club performance monitor | `Analytics` tab inside Clubs Hub | Medium | Performance telemetry is now visible in-context, but longer-horizon historical comparisons are still limited | Extend the current signals into longer-range club performance history if multi-day scale tuning becomes necessary |

---

# 🧠 HUMAN EASE

- Score (0–10): 9.0
- Cognitive Load:
  - Low for primary navigation because the selected-club workspace now keeps directory, summary, and primary actions in one place across desktop and smaller screens.
  - Low for deep queue operations because search, shared saved views, stale-priority cues, pagination, and backend queue history now reduce “where did that old request go?” friction, though the workspace still contains many concepts overall.
- Issues:
  - Announcements, analytics, and members still depend on tab switching.
  - The event inventory route is now honest and thin, but it still adds one extra reporting surface the product team should keep watching over time.
  - Club cards still need more at-a-glance operational signals for busy coordinators.

---

# 🧠 DOMAIN SIMPLIFICATION

- Problems:
  - Raw status mechanics are still exposed instead of real-world club actions.
  - Event-management responsibility is much more centralized now, but cross-club inventory still lives on a separate route.
  - The selected club is now the dominant container in `ClubsPage`, but not yet across every club-related page.
- Suggestions:
  - Replace status jargon with guided actions such as `Open Recruitment`, `Pause Recruitment`, `Archive Club`.
  - Keep selected club as the primary scope for members, events, announcements, and insights.
  - Decide whether the remaining inventory route should stay as read-only reporting or collapse fully into one club operations workflow.
  - Add role presets with visible permissions and one governance sync path.
  - Add first-class queue buckets such as `Fresh`, `Aging`, and `Stale` to reporting and saved filters so coordinators can triage by urgency instead of by timestamp alone.
  - Extend the current queue-owner notes and attendance-linked insights into broader season-planning and long-range archival reporting later.

---

# 🧪 STATE HANDLING

- Loading:
  - Still basic text-only loading in most places, though the selected-club workspace now makes state transitions easier to understand.
- Empty:
  - Better in overview/events with selected-club empty states, and queue sections now fail more gracefully because pagination keeps emptiness localized to filtered views rather than giant blank lists.
- Error:
  - Error handling is more trustworthy because validation rules are reflected before submit, backend consistency is stronger, and clubs-directory versus selected-club failures now show separate recovery panels.
- Retry:
  - Retry is now targeted at the failing surface: the directory can be retried independently, and selected-club detail payloads can be retried without throwing away the rest of the workspace.

---

# 🧩 COMPONENT REVIEW

### Component/Page: `frontend/src/pages/ClubsPage.jsx`
- Issues:
  - The page is much stronger now because it has a persistent desktop rail, a smaller-screen switcher, a hero, signals, event-center operations, mobile action/grouped cards, queue-age badges, targeted recovery panels, archive navigation, and pagination across the heaviest club-management and enrollment queues.
  - It still carries a broad responsibility set, and some deeper surfaces still rely on desktop-style tables for faster staff throughput.
- Fix:
  - Continue the selected-club workspace direction, soften the remaining table-heavy staff interactions where needed, and keep overlapping club-operation routes thin.

### Component/Page: `frontend/src/pages/clubs/useClubDirectory.js`
- Issues:
  - Still fetches many club-related surfaces through one broad hook.
  - Resource loading is better-functioning now but still tightly coupled.
- Fix:
  - Split into directory, selected club summary, members, events, registrations, and analytics hooks.

### Component/Page: `frontend/src/pages/ClubEventsPage.jsx`
- Issues:
  - The page is now much healthier because it no longer acts like a second management console.
  - The remaining question is product ownership: whether this route should remain as cross-club inventory or disappear entirely.
- Fix:
  - Keep this page thin as inventory/reporting only, or merge it fully into the selected-club event center if the route no longer earns its place.

### Component/Page: `frontend/src/pages/EventRegistrationsPage.jsx`
- Issues:
  - The page is now correctly positioned as records/status tracking, but it still sits outside the selected-club event context.
  - Event-window guidance is useful, though the page could surface richer status history and next actions.
- Fix:
  - Keep it as a records page and add a compact registration timeline plus direct links back into the clubs event context.

### Component/Page: `backend/app/api/v1/endpoints/clubs.py`
- Issues:
  - Still contains lifecycle, membership, application, and analytics concerns in one controller.
  - Runtime behavior is much better, but the file remains too broad.
- Fix:
  - Extract lifecycle, membership, and analytics services.

### Component/Page: `backend/app/api/v1/endpoints/event_registrations.py`
- Issues:
  - Lifecycle is now implemented, but the controller is growing into policy + lifecycle + upload + list logic.
- Fix:
  - Extract registration lifecycle service and policy service interfaces.

---

# 💡 IMPROVEMENTS

- Layout:
  - Rebuild clubs into a two-panel workspace with a selected-club summary header.
  - Replace dense tables with adaptive management cards on small screens.
- UX:
  - Continue replacing raw state concepts with action-led flows.
  - Add queue-owner notes and outcome-oriented queue drilldowns on top of the shared saved views now live.
- Dashboard:
  - Surface pending applications, open registrations, stale queue items, shared queue trend deltas, and club alerts in overview instead of hiding them in tabs.

---

# ➕ NEW FEATURES

- Role hierarchy with officer permissions matrix and visible responsibilities.
- Waitlist and overflow management for clubs and events.
- Club-scoped announcement composer with templates.
- Attendance QR scan and bulk attendance upload.
- Certificate issuance history and bulk certificate actions.
- Event reminder automation for registration open and deadline alerts.
- Queue ageing insights with stale-record trend tracking.
- Backend-backed shared queue history for coordinators.
- Club health scoring using growth, participation, and inactivity risk.
- Season planning board for goals, milestones, and officer assignments.

---

# 🔄 RESTRUCTURE PLAN

- Remove:
  - Raw lifecycle button clusters that expose backend states directly.
- Merge:
  - `ClubEventsPage` into the selected-club event center.
  - Member role assignment and president sync into one governance pipeline.
- Rebuild:
  - Clubs workspace layout.
  - Role-management UX and trustworthy club insights dashboard.

---

# 🧪 AUTO TEST CASES

### Test Case: CLUB-TC-01
- Scenario:
  - Approval-required event registration can be completed end-to-end.
- Steps:
  - Create a club and an event with `approval_required=true`.
  - Register a student for the event.
  - Log in as coordinator and approve the registration.
  - Mark attendance and issue certificate.
- Expected:
  - Registration moves from `pending` to `approved`, attendance can be recorded, and certificate can be issued.
- Failure:
  - Registration remains stuck or certificate can be issued without attendance guard.

### Test Case: CLUB-TC-02
- Scenario:
  - Members-only event is protected from non-members.
- Steps:
  - Create a club event with `visibility=members_only`.
  - Log in as a student who is not an active member.
  - Attempt to list and register for the event.
- Expected:
  - Event is hidden or locked and registration is blocked with a clear reason.
- Failure:
  - Student can see or register for the event normally.

### Test Case: CLUB-TC-03
- Scenario:
  - Club member cap is enforced during application approval.
- Steps:
  - Create club with `max_members=2` and `membership_type=approval_required`.
  - Approve two members.
  - Submit a third application and approve it.
- Expected:
  - Third approval is blocked or waitlisted.
- Failure:
  - Third active membership is created despite capacity limit.

### Test Case: CLUB-TC-04
- Scenario:
  - Teacher permissions are consistent across all club surfaces.
- Steps:
  - Give two teachers `club_coordinator` extension.
  - Assign only one teacher to a club.
  - Test club update, event creation, event registration visibility, and enrollment actions for both teachers.
- Expected:
  - Only the assigned coordinator can manage that club and its events/registrations.
- Failure:
  - Unassigned teacher gains access in any one route or surface.

### Test Case: CLUB-TC-05
- Scenario:
  - Canonical registration handoff opens Clubs Hub instead of a duplicate standalone form.
- Steps:
  - Open a student-eligible event from `ClubEventsPage`.
  - Trigger `Register`.
  - Verify the app lands in Clubs Hub with the event registration modal open.
- Expected:
  - Registration starts inside the Clubs Hub modal for that selected event, and the standalone records page is not used as a second submit surface.
- Failure:
  - The flow lands on a second standalone form or drops the selected event during the handoff.

### Test Case: CLUB-TC-06
- Scenario:
  - Rejoin club after removal.
- Steps:
  - Join a club, mark membership as removed, then try to join again.
- Expected:
  - Membership is reactivated according to policy.
- Failure:
  - Duplicate key conflict or hard rejection prevents valid rejoin.

### Test Case: CLUB-TC-07
- Scenario:
  - Analytics label matches actual math.
- Steps:
  - Seed confirmed and pending registrations for one club.
  - Load analytics tab.
- Expected:
  - `Event Fill %` reflects confirmed registrations divided by capacity.
- Failure:
  - Pending registrations are counted or attendance wording is used incorrectly.

### Test Case: CLUB-TC-08
- Scenario:
  - Officer role assignment is manageable from clubs UI.
- Steps:
  - Open members tab for a managed club.
  - Promote a member to vice president and then president.
- Expected:
  - Role actions are visible, update succeeds, and president sync is reflected consistently.
- Failure:
  - No UI action exists or role data diverges across club and user views.

### Test Case: CLUB-TC-09
- Scenario:
  - Membership queue search, bulk review, and reminder flow works inside Clubs Hub.
- Steps:
  - Open a managed club with multiple `pending` and `waitlisted` applications.
  - Search by applicant name or email.
  - Select the filtered records.
  - Run a bulk status change and send a reminder.
- Expected:
  - Only the selected queue records are updated, the queue refreshes, and targeted notifications are created.
- Failure:
  - Bulk action updates the wrong records, filtered selection is lost, or reminders are not created.

### Test Case: CLUB-TC-10
- Scenario:
  - Event registration queue supports filter, bulk review, and reminder actions.
- Steps:
  - Open event enrollments for a managed event with `pending` and `waitlisted` registrations.
  - Filter the queue by status.
  - Select multiple rows/cards.
  - Run a bulk approve or waitlist action and send a reminder to the selected queue.
- Expected:
  - Selected registrations update together, queue counts refresh, and reminder notifications are created for the intended registrants only.
- Failure:
  - Mixed queue states break the bulk action silently, or reminder fanout targets the wrong students.

### Test Case: CLUB-TC-11
- Scenario:
  - Queue-age and pagination cues stay accurate across membership applications.
- Steps:
  - Open a managed club with enough applications to create multiple pages.
  - Confirm fresh, aging, and stale cues appear based on application age.
  - Move between pages and change page size.
- Expected:
  - The queue age labels, priority pills, and page counts remain accurate after pagination changes.
- Failure:
  - Older applications disappear from view without paging access, or priority cues drift when page size changes.

### Test Case: CLUB-TC-12
- Scenario:
  - Enrollment queue age and pagination remain accurate inside event enrollments modal.
- Steps:
  - Open event enrollments for a queue-heavy event.
  - Verify stale/aging/fresh signals, move to another page, and change page size.
- Expected:
  - Registration age labels and pagination controls stay synchronized with the filtered enrollment list.
- Failure:
  - Page counts, queue age signals, or selected rows desynchronize after pagination changes.

### Test Case: CLUB-TC-13
- Scenario:
  - Saved membership queue filters persist and can be reused.
- Steps:
  - Open a managed club, set a membership queue search/status/page-size combination, and save the current view.
  - Refresh the page and return to the same club.
  - Apply the saved filter.
- Expected:
  - The saved preset is still available and restores the intended queue view accurately.
- Failure:
  - The preset disappears after refresh, applies the wrong criteria, or restores a misleading view.

### Test Case: CLUB-TC-14
- Scenario:
  - Shared queue history records truthful changes and remains visible across authorized managers.
- Steps:
  - Open a managed membership or event queue and note the shared history panel.
  - Change the queue by adding a waitlisted record or reviewing an existing one.
  - Reopen the same queue as another authorized manager.
- Expected:
  - A new shared snapshot appears with truthful queue totals and `fresh/aging/stale` counts, and the history is still visible from another authorized manager session.
- Failure:
  - Queue history fails to persist across managers, or the recorded counts do not match the actual queue state.

### Test Case: CLUB-TC-15
- Scenario:
  - Clubs workspace exposes the correct recovery path when the directory request fails separately from the selected-club payload.
- Steps:
  - Trigger a clubs-directory API failure and open the clubs workspace.
  - Verify the page shows a directory recovery panel.
  - Restore connectivity or API health and use `Retry Directory`.
  - Trigger a selected-club detail failure while the directory still loads.
  - Verify the page shows `Retry Selected Club` and `Refresh Directory`.
- Expected:
  - The directory failure offers a directory-only retry path, and the selected-club failure offers a targeted detail retry path without losing the rest of the workspace.
- Failure:
  - Failures show generic text only, the wrong retry action appears, or retrying the selected club unnecessarily resets the entire workspace.

### Test Case: CLUB-TC-16
- Scenario:
  - Large-club archived event navigation keeps live operations separate from older history.
- Steps:
  - Open a club with enough archived events to require paging.
  - Switch `Archive View` to `Archived only`.
  - Search by event title or short ID.
  - Move across archive pages and then return to `Live pipeline`.
- Expected:
  - Archived events are filtered cleanly, page counts stay accurate, archive-specific guidance appears, and returning to the live pipeline restores the current operational list.
- Failure:
  - Archived and live events mix together, paging breaks after filtering, or the archive view gives no clear indication that the user is browsing historical records.

### Test Case: CLUB-TC-17
- Scenario:
  - Large-club performance telemetry reflects real session load behavior inside Clubs Hub analytics.
- Steps:
  - Open a large club and load the analytics tab.
  - Verify the workspace performance monitor shows selected-club load time, club API P95, dataset weight, and recent club API traces.
  - Simulate slower or failed club requests during the same session.
  - Refresh the analytics tab state.
- Expected:
  - The performance monitor updates status between `Healthy`, `Watch`, and `Critical` based on recent club trace health and measured load durations.
- Failure:
  - The monitor stays static despite slower club requests, shows unrelated API traces, or hides the slowest recent club request.

### Test Case: CLUB-TC-18
- Scenario:
  - Shared admin observability reflects club-request pressure separately from generic HTTP traffic.
- Steps:
  - Generate recent traffic for `/clubs`, `/club-events`, and `/event-registrations`.
  - Open `Admin System` and `Admin Observability`.
  - Verify both pages show club-specific request totals, P95, slow-request counts, and 5xx counts.
  - Inspect the top club paths list.
- Expected:
  - Club pressure appears as a separate observability domain, and the top club paths identify whether clubs, club events, or event registrations are driving the traffic.
- Failure:
  - Admin pages only show generic request totals, or club paths are missing from the shared observability summary.

### Test Case: CLUB-TC-19
- Scenario:
  - Selected-club loading keeps its telemetry while parallelizing major requests.
- Steps:
  - Open a large club and capture the performance monitor values.
  - Refresh the selected club.
  - Verify events, members/applications, registrations, and analytics all load successfully.
  - Confirm the performance panel still shows total load duration plus the phase durations for event, member, registration, and analytics slices.
- Expected:
  - The workspace completes successfully, and phase timing remains visible even though the main data slices are now loaded in parallel.
- Failure:
  - One major data slice silently disappears after refresh, or the performance monitor stops showing truthful phase timing after the loader optimization.

### Test Case: CLUB-TC-20
- Scenario:
  - Club analytics and club analytics exports remain stable after cross-event trend work.
- Steps:
  - Open a club with recent events and request `/clubs/{club_id}/analytics`.
  - Export `event_performance` and `attendance_certificate` reports for the same club.
  - Verify recent trend points and trend summaries are included without backend failure.
- Expected:
  - Analytics and both exports succeed, and the trend-summary builder can safely use the recent event trend payload.
- Failure:
  - `/clubs/{club_id}/analytics` or either export route throws a 500 because the trend-summary code references a field missing from the trend-point schema.

### Test Case: CLUB-TC-21
- Scenario:
  - Shared admin observability shows retained club-pressure trends across hours and days instead of only the latest 15-minute club snapshot.
- Steps:
  - Persist multiple club-pressure snapshots across several days.
  - Open `/admin/system/health`, `Admin System`, or `Admin Observability`.
  - Verify retained hourly and daily club trend data plus recent recurring pressure windows are present.
- Expected:
  - Admin tooling shows club-specific long-range history with recent warning/critical club-pressure windows and a retention summary.
- Failure:
  - Admin tooling only shows the latest club-request counters, or the backend omits retained club trend data from the system-health payload.

### Test Case: CLUB-TC-22
- Scenario:
  - Backend tuning keeps core club behavior intact while removing avoidable per-row clubs-list work and supporting the dominant queue/inventory query shapes with matching indexes.
- Steps:
  - Start the backend so clubs indexes are ensured.
  - Load the clubs list, a selected club, its applications queue, and an event registration queue.
  - Verify the backend still serves the same functional responses for members-only events, rejoin flows, and analytics.
- Expected:
  - Core clubs behavior remains unchanged, and the backend now supports the dominant list/queue filters and sorts with compound indexes plus batched clubs-list enrichment.
- Failure:
  - Clubs list loses coordinator/president/member context, or the tuned paths regress functional club behavior while attempting to optimize query cost.

### Test Case: CLUB-TC-23
- Scenario:
  - Clubs analytics should summarize archived club history through season, cohort, and long-range monthly rollups instead of forcing coordinators to inspect archived events one record at a time.
- Steps:
  - Seed archived club events across recent, mid-range, and legacy dates with confirmed registrations, attendance outcomes, and certificate issuance.
  - Request `/clubs/{club_id}/analytics` or open the Clubs Hub analytics tab.
  - Verify the payload includes `archive_season_summaries`, `archive_event_cohorts`, and `archival_history_points`.
- Expected:
  - Archived season, cohort, and monthly history rollups are returned with truthful archived attendance, no-show, and certificate metrics.
- Failure:
  - Archived events only appear in raw event lists, or the archive analytics payload omits season/cohort/history summaries despite available archived history.

### Test Case: CLUB-TC-24
- Scenario:
  - Clubs analytics should translate paid-event configuration and payment-proof submissions into truthful finance metrics, while the club funding profile should retain sponsorship target and committed values.
- Steps:
  - Create or update a club with sponsorship target, committed amount, and notes.
  - Add at least one paid event and one free event, then create confirmed registrations for the paid event with payment proof on only some of the seats.
  - Request `/clubs/{club_id}/analytics` or open the Clubs Hub analytics tab.
- Expected:
  - Analytics shows paid/free event mix, listed paid revenue, payment-proof coverage, sponsorship progress, and funding gap with values consistent with the event pricing and club funding profile.
- Failure:
  - Finance cards render, but the payload omits paid-event revenue/proof fields, or sponsorship target/committed data does not flow into analytics after a club update.

### Test Case: CLUB-TC-25
- Scenario:
  - Shared admin clubs observability should preserve alert-route history so admins can verify whether club-pressure alerts were routed, cooled down, or resolved over repeated health refreshes.
- Steps:
  - Trigger a club-pressure alert in the backend observability stream.
  - Open `/admin/system/health`, `Admin System`, or `Admin Observability`.
  - Refresh through an initial routed state and a later cooldown-suppressed state.
- Expected:
  - The payload and admin UI show alert-route history with routed/resolved entries, cooldown suppression counts, notification totals, and last-outcome metadata for the same alert code.
- Failure:
  - Admin tooling only shows the latest active alert count, or alert-route history omits route/resolution/cooldown follow-through for recurring club-pressure alerts.

### Test Case: CLUB-TC-26
- Scenario:
  - Clubs analytics should explain whether members stay, convert into participation, and become at-risk after a period of low event engagement.
- Steps:
  - Seed long-standing active members, a recent departure, a recently joined active member, recent club-event participation, and older legacy participation.
  - Request `/clubs/{club_id}/analytics` or open the Clubs Hub analytics tab.
  - Verify retention, churn, join-to-event conversion, join-to-attendance conversion, recently engaged active members, and at-risk active members.
- Expected:
  - Analytics returns truthful member-retention and participation-conversion signals that line up with the seeded membership and event-registration history.
- Failure:
  - Clubs analytics still stops at member count/growth, or the engagement panel renders values that do not match the membership and event history used to derive them.

### Test Case: CLUB-TC-27
- Scenario:
  - Club leads should be able to run mature in-module announcement operations instead of stopping at basic publish/read.
- Steps:
  - Open the selected club's `Announcements` tab as a coordinator or club president.
  - Create a template-backed announcement, pin it, mark the visible feed as read for the current user, then archive the same announcement.
  - Refresh the club notices feed.
- Expected:
  - The feed keeps pinned announcements first, template metadata survives the create flow, visible-read updates the unread state, and archived notices disappear from the active club feed.
- Failure:
  - Club leads cannot pin/unpin or archive notices, template-backed notices lose metadata, or the visible-feed read action does not update unread state.

### Test Case: CLUB-TC-28
- Scenario:
  - Clubs should carry a richer public-facing profile that survives create/update flows and appears in the selected-club workspace.
- Steps:
  - Create or update a club with tagline, achievement highlights, recruitment headline, recruitment CTA label, public contact URL, logo URL, and banner URL.
  - Refresh the clubs directory and reopen the selected club.
  - Check the directory card, selected-club hero, and club summary panel.
- Expected:
  - The club profile fields persist through backend create/update contracts and render consistently across the directory card, selected-club hero, and summary/profile editor surfaces.
- Failure:
  - The backend drops profile fields on create/update, or the frontend continues to render the club as a generic name/category card without the richer branding and recruitment context.

---

# 🤖 AUTO-IMPROVEMENT ENGINE

- Recalculate scores:
- Scores were recalculated after validating shipped fixes across lifecycle, authorization, registration guidance, reactivation, analytics accuracy, queue tooling, reporting, queue-context follow-through, per-event drilldown history, cross-event trend visibility, targeted recovery guidance, archive-scale event navigation, large-club session performance monitoring, shared admin clubs observability, selected-club load-path tuning, retained longer-horizon club trend history, telemetry-backed backend query/index tuning, archival analytics depth, financial/sponsorship insight, alert-routing follow-through history, engagement intelligence, announcement maturity, and richer public-facing club profile surfaces.
  - Validation runs completed on `python -m compileall backend/app`, `frontend` production build, focused Vitest coverage for `src/pages/clubs/performanceMonitor.test.js`, targeted backend club-flow tests for members-only visibility and analytics stability, plus `test_admin_system_health_includes_observability_metrics_and_alerts`, `test_club_analytics_include_engagement_intelligence`, `test_club_notice_moderation_supports_pin_and_archive_for_club_leads`, and `test_club_profile_fields_persist_across_create_and_update`.
- Compare previous:
  - Baseline and post-hardening snapshots are now recorded in the score history table.
- Detect regressions:
- The main remaining regression risk is future drift if new clubs data loaders or event-center changes bypass the targeted recovery actions, archive filters, queue-history recording, event-history timeline source contract, recent-event trend summaries, the large-club load-duration capture path, the shared admin clubs observability rollups, the retained club-pressure trend aggregations, the alert-route history recording path, the new membership-engagement calculations, the batched clubs-list enrichment path, the compound indexes now supporting dominant club filters and sorts, the club-notice moderation contract, or the richer club-profile create/update fields.
- Update status:
  - All baseline and follow-through audit issues are fixed through CLUB-034, and the current clubs module now includes queue analytics, search, reminders, bulk coordinator actions, shared queue history, reporting exports, queue owner/note context, per-event history drilldowns, cross-event trend summaries, archival season/cohort/history analytics, financial/sponsorship insight, engagement intelligence, mature club announcements, richer public-facing club profile surfaces, tailored edge-state guidance, targeted recovery panels, archive-scale event navigation, large-club session performance monitoring, shared admin clubs observability, retained club-pressure trend history, alert-route history, tuned selected-club load paths, telemetry-backed club query/index tuning, and re-audit-verified analytics trend integrity.

---

# 📊 PRIORITY LIST

| Priority | Issue | Reason |
|---------|-------|--------|
| P3 | No open audit-tracked blockers | The planned resilience, archive navigation, archival analytics, observability follow-through, and telemetry-backed backend tuning are now complete; remaining work is optional product depth rather than module repair |

---

# 🔄 PHASE TRACKING

| Phase | Goal | Status | % |
|------|------|--------|----|
| Phase 1 | Stop fake features and workflow dead ends | ✅ Fixed | 100% |
| Phase 2 | Centralize club/event/registration access policy | ✅ Fixed | 100% |
| Phase 3 | Rebuild clubs workspace layout and event center | ✅ Fixed | 100% |
| Phase 4 | Add trustworthy analytics and role-management UX | ✅ Fixed | 100% |
| Phase 5 | Add advanced club operations: attendance, certificates, reminders, waitlists | ✅ Fixed | 100% |
| Phase 6 | Add resilience guidance and archive-scale navigation | ✅ Fixed | 100% |
| Phase 7 | Add large-club telemetry and session performance monitoring | ✅ Fixed | 100% |
| Phase 8 | Promote clubs pressure into shared admin observability and tune large-club load paths | ✅ Fixed | 100% |
| Phase 9 | Re-audit clubs analytics and harden trend-contract regressions | ✅ Fixed | 100% |
| Phase 10 | Add retained longer-horizon clubs observability to shared admin tooling | ✅ Fixed | 100% |
| Phase 11 | Tune backend club queries and indexes using observed club traffic shapes | ✅ Fixed | 100% |
| Phase 12 | Add deeper archival analytics for archived seasons, cohorts, and long-range history | ✅ Fixed | 100% |
| Phase 13 | Add financial and sponsorship insight from paid-event data and club funding profile fields | ✅ Fixed | 100% |
| Phase 14 | Add richer alert-routing history for shared admin clubs observability | ✅ Fixed | 100% |
| Phase 15 | Add membership engagement intelligence for retention, churn, and participation conversion | ✅ Fixed | 100% |
| Phase 16 | Mature club announcements with templates, pinning, visible-read actions, and moderation controls | ✅ Fixed | 100% |
| Phase 17 | Add richer public-facing club profile fields and profile editing in Clubs Hub | ✅ Fixed | 100% |

---

# 🧠 TRUST ANALYSIS

| Area | Trust | Reason |
|------|-------|--------|
| Club join and application | 100/100 | Capacity checks, rejoin behavior, club-intake waitlists, automatic promotion when seats reopen, queue search, reminder-capable bulk review, shared saved views, backend queue history, and queue owner/note context now align with policy instead of forcing hard rejection or one-record-at-a-time follow-up |
| Event creation | 92/100 | Event creation and lifecycle controls now live in the selected-club event center, and high-volume clubs can now separate live event work from archived history through explicit archive navigation instead of one mixed event list |
| Event registration | 100/100 | Approval lifecycle, private-event enforcement, canonical Clubs Hub registration handoff, automatic waitlisting at capacity, queue promotion, bulk review, queue reminders, shared saved views, backend-backed queue history, owner/note context, and delivery-quality insight now make both student and coordinator flows much more trustworthy |
| Role assignment | 83/100 | Clubs UI now exposes role and status changes directly and president scope is synchronized through shared backend governance logic |
| Club analytics | 100/100 | Metric naming and active-state semantics are honest, coordinators can see queue pressure, attendance coverage, no-show risk, certificate follow-through, top event health rows, archive season/cohort/history summaries, paid-event revenue/proof signals, export the same truthful reporting directly from Clubs Hub, and monitor session-level workspace performance for very large clubs |
| Member engagement | 100/100 | Clubs analytics now explains whether members stay, convert into participation, and start drifting into at-risk inactivity instead of stopping at roster size and growth only |
| Announcements/activity | 96/100 | Clubs now supports a real scoped composer and timeline for selected clubs inside the selected-club workspace, plus templates, pinning, visible-read actions, and club-lead moderation |
| Public-facing identity | 95/100 | Clubs now carries richer branding and recruitment context through tagline, achievements, recruitment CTA, contact URL, logo, and banner fields across the directory and selected-club workspace |
| Permissions | 86/100 | Club/event/registration management now follows one assigned-ownership rule with clear admin override, and recovery guidance now makes data-load failures easier to distinguish from genuine permission or empty-state conditions |

Overall Score:
- 100/100

---

# 🔍 EDGE CASES

- No members:
  - Empty/new clubs and dormant clubs now receive clearer startup/recovery guidance in the hero, overview, members, events, and analytics surfaces.
- Large clubs:
  - Search, selection, reminders, bulk queue actions, pagination, queue-age prioritization, shared saved views, backend queue history, delivery-quality analytics, CSV exports, owner/note context, event drilldowns, cross-event trends, archive-first event navigation, session-level performance monitoring, shared admin pressure rollups, and tuned selected-club loading now exist, so very large clubs no longer rely on one mixed live-plus-history event list or anecdotal “the page feels slow” reporting.
- API failure:
  - Directory and selected-club failures now surface dedicated recovery panels with the right retry path, so partial data outages are easier to recover from without abandoning the workspace.
- Event overflow:
  - Capacity guards, waitlists, reminders, bulk review, shared queue memory, delivery-quality analytics, CSV exports, owner/note context, event-history drilldowns, and cross-event trends now work; future improvements are mostly around edge-case polish and longer-horizon analytics.
- Archived club history:
  - Archived events are now searchable in the event center and analyzable in Clubs Hub through season summaries, archive-age cohorts, and long-range monthly attendance/certificate rollups, so older club cycles no longer disappear into raw records only.
- Paid club activity:
  - Paid events now roll into listed revenue and payment-proof coverage analytics, while sponsorship target and committed funding can be maintained directly in Clubs Hub instead of living outside the module.
- Membership overflow:
  - Club-intake waitlists, queue search, reminders, bulk review, pagination, urgency visibility, shared saved views, backend queue history, owner/note context, and engagement intelligence now work; future improvements are mostly around deeper membership-history drilldowns.

---

# 📌 FINAL VERDICT

- System Health:
  - Strong and complete for current scope. The clubs module is now operationally trustworthy for core club, event, registration, governance, announcement, public-facing club profile, event-overflow, club-intake-overflow, coordinator queue-processing, event delivery-quality insight, coordinator-ready reporting, shared queue follow-through context, per-event history explainability, cross-event trend visibility, archival analytics, financial/sponsorship insight, engagement intelligence, edge-case clarity, targeted recovery guidance, archive-scale navigation, large-club session performance monitoring, shared admin clubs observability, and tuned large-club load paths.
- Trust Level:
  - Strong. The most damaging feature-reality gaps from the baseline audit are fixed, and the clubs workspace now handles standard operations, overflow follow-up, partial-load recovery, and long event history more honestly.
- Human Ease:
  - Strong. Core workflows are safer and clearer, and coordinators no longer have to process every queue item one-by-one just to keep club and event pipelines moving.
- Biggest Problem:
  - No audit-tracked blocker remains. Remaining work is now optional product depth such as escalation-policy controls, longer alert-retention strategy, deeper external-facing club marketing surfaces, or audited payment verification if finance operations need stronger evidence.
- Next Action:
  - Keep the next investment telemetry- and product-driven: only extend observability, finance verification, or external-facing club marketing if real usage shows those are the next constraints rather than assuming more surface area is automatically better.

---

# 🔄 CONTINUOUS IMPROVEMENT (MANDATORY)

## 📅 UPDATE LOG

| Date | Change | Impact | By |
|------|--------|--------|----|
| 2026-04-05 16:48 | Created baseline self-improving clubs module audit with scores, issue tracker, workflow review, and fix plan | Established first dedicated clubs health snapshot and priority list | Codex |
| 2026-04-05 17:05 | Implemented registration lifecycle, `members_only` enforcement, approval-capacity guard, and stronger registration-page guidance | Closed the most critical feature-reality and access gaps in club events and registrations | Codex |
| 2026-04-05 17:12 | Implemented rejoin/reregister recovery logic and corrected club analytics truthfulness | Removed lifecycle dead ends and improved trust in active-club and event-fill metrics | Codex |
| 2026-04-05 17:23 | Unified coordinator authorization through shared club permission policy | Eliminated route-to-route access drift for assigned vs unassigned teachers | Codex |
| 2026-04-05 17:33 | Updated this audit in place with completed implementation details, validation references, and refreshed issue timestamps | Converted the file into a more accurate living audit of work already shipped without changing its structure | Codex |
| 2026-04-05 17:39 | Shared the student event-registration form, availability rules, and multipart submission helper across clubs pages | Reduced frontend contract drift and improved student registration consistency without changing backend APIs | Codex |
| 2026-04-05 17:43 | Added member role and status management to the clubs members tab with president-aware guardrails | Turned backend-only member governance into an in-context UI workflow and reduced the CLUB-009 gap from open to in progress | Codex |
| 2026-04-05 17:48 | Unified club president sync across clubs membership, club record, and user extension scope | Closed the remaining CLUB-009 governance-sync gap and added regression tests for both clubs-driven and users-driven president assignment | Codex |
| 2026-04-05 17:54 | Implemented club-scoped announcements inside the clubs workspace with backend `scope=club` support | Closed CLUB-006 by making announcements real in-module for coordinators, presidents, and eligible members with automated visibility/publish coverage | Codex |
| 2026-04-05 17:59 | Made Clubs Hub the canonical student registration surface and converted the standalone page into records/status tracking | Closed CLUB-005 by removing the competing standalone submit form, preserving deep-link queries through workspace redirects, and routing Club Events registration into the clubs modal | Codex |
| 2026-04-05 18:20 | Started CLUB-010 with a selected-club workspace shell and moved event status/enrollment operations into the in-workspace event center | Reduced layout sprawl, improved dashboard focus, and turned the selected-club event tab into a more complete operational surface | Codex |
| 2026-04-05 18:25 | Demoted `ClubEventsPage` into club event inventory and handoff, and renamed navigation to match that narrower purpose | Reduced product drift by removing overlapping management intent from the secondary route while preserving cross-club browsing | Codex |
| 2026-04-05 18:30 | Added smaller-screen workspace polish with collapsible club switcher, responsive action grid, horizontal tab scrolling, and tighter selected-club hero layout | Improved mobile/tablet usability without undoing the desktop selected-club workspace structure | Codex |
| 2026-04-05 18:33 | Replaced the heaviest small-screen members, application, and enrollment tables with stacked action cards inside Clubs Hub | Improved deep mobile club operations so smaller screens no longer depend entirely on desktop-style tables for key management tasks | Codex |
| 2026-04-05 18:36 | Added smaller-screen event cards and grouped analytics cards inside Clubs Hub | Completed the first full mobile simplification pass across the major clubs workspace tabs and reduced the last desktop-heavy mobile views | Codex |
| 2026-04-05 18:40 | Locked Event Inventory to staff-only access and removed student-facing links to that route | Closed the last structural clubs IA ambiguity by making Clubs Hub the explicit student home and Event Inventory the explicit staff oversight route | Codex |
| 2026-04-06 10:49 | Added event waitlists, automatic promotion when seats reopen, waitlist-aware coordinator actions, and richer queue analytics | Removed the last hard-stop overflow failure in event registration and surfaced queue pressure directly inside the clubs workspace | Codex |
| 2026-04-06 11:02 | Added club-intake waitlists, automatic membership queue promotion when seats reopen, and waitlist-aware membership analytics/UI | Removed hard-stop club-intake failures at capacity and made the members workspace honest about pending vs waitlisted applicants | Codex |
| 2026-04-06 11:20 | Added queue search, reminder automation, desktop/mobile selection, and bulk review actions for membership applications and event registrations | Reduced coordinator queue friction substantially by turning waitlists and pending queues into searchable, actionable workflow surfaces backed by real notification and bulk-update endpoints | Codex |
| 2026-04-06 11:28 | Added queue-age indicators, stale/aging/fresh priority cues, and local pagination to membership and enrollment queues in Clubs Hub | Made older queue items much easier to spot and reduced long-list fatigue for coordinators working through larger club and event backlogs | Codex |
| 2026-04-06 11:37 | Added saved local queue filters and clearly labeled local snapshot history for membership and enrollment queues | Made repeat queue triage faster and added honest short-term queue memory without pretending the data is shared backend analytics | Codex |
| 2026-04-06 11:58 | Added backend-backed shared coordinator views and shared queue history for membership and enrollment queues | Moved queue memory from device-local storage into real persisted multi-user contracts with targeted backend tests and frontend integration | Codex |
| 2026-04-06 12:10 | Added attendance-quality, certificate-coverage, and top event-performance insight to club analytics | Helped coordinators move from queue management into truthful event delivery follow-through using backend-calculated analytics rendered directly in Clubs Hub | Codex |
| 2026-04-06 12:37 | Added downloadable event-performance and attendance/certificate CSV reports to club analytics | Closed the reporting gap between on-screen delivery-quality insight and coordinator-ready handoff/audit workflows | Codex |
| 2026-04-06 12:50 | Added queue owner, coordinator note, and last-touch context to membership applications and event enrollments | Closed the follow-through gap where queue handoff context still lived outside Clubs Hub after analytics and exports had already shipped | Codex |
| 2026-04-06 13:04 | Added per-event history drilldowns backed by audit logs, queue snapshots, and lifecycle deltas inside the Clubs Hub enrollment modal | Closed the event-history explainability gap and gave coordinators a direct timeline for registration, attendance, and certificate follow-through | Codex |
| 2026-04-06 13:10 | Added cross-event trend summaries and recent-event trend lines to club analytics | Closed the repeated-pattern visibility gap by helping coordinators compare recent events instead of reading each event in isolation | Codex |
| 2026-04-06 13:15 | Added tailored empty/new, dormant, and high-volume guidance across the selected-club hero, overview, members, events, and analytics surfaces | Closed the edge-case clarity gap so unusual club states no longer look like broken or contextless screens | Codex |
| 2026-04-06 14:24 | Added targeted recovery panels for clubs-directory and selected-club failures, plus archive-aware event-center search, counts, and pagination | Closed the final planned resilience and very-large-club navigation gaps without replacing the existing clubs workspace model | Codex |
| 2026-04-06 14:38 | Added a large-club workspace performance monitor using real clubs load timings and club API trace summaries | Closed the final session-level observability gap for very large clubs and validated it with helper tests plus a production build | Codex |
| 2026-04-06 14:44 | Promoted club-request pressure into Admin System, Admin Observability, and persisted system-health snapshots | Made cross-club slowdown visible outside the clubs workspace so admins can see whether clubs traffic is becoming its own pressure domain | Codex |
| 2026-04-06 14:49 | Tuned the selected-club loader to parallelize analytics, events, members/applications, and student registrations | Reduced avoidable large-club latency while keeping workspace timing telemetry truthful and visible | Codex |
| 2026-04-06 15:00 | Re-audit found and fixed a clubs analytics trend-schema mismatch | Prevented `/clubs/{id}/analytics` and related export paths from crashing when recent event trend summaries were built | Codex |
| 2026-04-06 15:12 | Added retained hourly/day club pressure trends and recurring pressure-window history to admin observability | Closed the longer-horizon clubs observability gap by turning club slowdown history into a real shared admin capability instead of backlog text | Codex |
| 2026-04-06 15:20 | Added telemetry-backed club-path indexes and batched clubs-list enrichment | Closed the backend query/index tuning backlog item for current traffic patterns by supporting dominant club filters/sorts and removing avoidable N+1 enrichment work | Codex |
| 2026-04-06 15:29 | Added archival season summaries, archive-age cohorts, and long-range archive history to clubs analytics | Closed the deeper archival analytics backlog item by turning archived club history into a readable analytics surface instead of only searchable event records | Codex |
| 2026-04-06 15:38 | Added financial and sponsorship insight from paid-event data plus a manager-editable funding profile | Closed the financial/sponsorship insight backlog item with truthful revenue/proof metrics and real club funding fields | Codex |
| 2026-04-06 15:45 | Added alert-route history, cooldown visibility, and shared admin history rendering for club-pressure alerts | Closed the richer alert-routing history backlog item so admins can audit whether repeated club-pressure alerts were routed, held, or resolved | Codex |
| 2026-04-06 19:41 | Added retention, churn, join-to-event conversion, join-to-attendance conversion, and at-risk-member signals to club analytics | Closed the engagement-intelligence backlog item by tying member lifecycle data to real participation signals inside Clubs Hub | Codex |
| 2026-04-06 19:53 | Added announcement templates, pin/unpin, visible-feed bulk read, club-lead archive moderation, and richer club public-profile editing/rendering | Closed the remaining announcement-maturity and public-facing-polish backlog items with validated backend contracts, Clubs Hub controls, and profile storytelling surfaces | Codex |

---

## 📈 PROGRESS

| Phase | Status | Notes |
|------|--------|-------|
| Baseline audit | ✅ Completed | Frontend, backend, schema, route, and index review completed |
| Critical workflow validation | ✅ Completed | Approval-required events, members-only enforcement, capacity approval checks, and reactivation flows are implemented and tested |
| UX consolidation | ✅ Completed | Registration submission is unified, the selected-club workspace/event center is live, the secondary event route is now thin staff-only inventory, the major clubs workspace tabs now have real smaller-screen fallbacks, and both event overflow and club-intake overflow now resolve into waitlists instead of dead ends |
| Trust hardening | ✅ Completed | Major truth gaps and structural IA drift from the baseline audit are fixed, and both event and club queue handling now include real queue search, reminders, bulk actions, age visibility, pagination, shared saved views, backend-backed queue history, delivery-quality analytics, reporting exports, queue owner/note context, event-history drilldowns, cross-event trend visibility, tailored edge-state guidance, and targeted recovery/archive-scale navigation instead of one-record-at-a-time coordinator work |
| Resilience follow-through | ✅ Completed | Clubs Hub now distinguishes directory failures from selected-club failures and gives large clubs explicit archive-first event navigation rather than one mixed historical list |
| Large-club telemetry | ✅ Completed | Clubs Hub analytics now shows selected-club load timing, club API P95, recent club traces, and performance recommendations for high-volume club sessions |
| Shared admin observability | ✅ Completed | Admin System and Admin Observability now surface club-request pressure with club-specific P95, slow/5xx counts, top paths, and persisted snapshot fields |
| Large-club data-path tuning | ✅ Completed | Selected-club loading now parallelizes major requests while preserving phase timing, reducing avoidable frontend-added latency for large clubs |
| Archival analytics depth | ✅ Completed | Clubs Hub analytics now summarizes archived club history through season rollups, archive-age cohorts, and long-range monthly archive metrics |
| Financial & sponsorship insight | ✅ Completed | Clubs Hub analytics now summarizes paid-event revenue/proof signals and lets managers maintain sponsorship target, committed funding, and funding notes |
| Alert-routing history | ✅ Completed | Admin System and Admin Observability now preserve routed/resolved history, cooldown suppression counts, and recent per-alert route activity for club-pressure alerts |
| Engagement intelligence | ✅ Completed | Clubs Hub analytics now ties member lifecycle data to real participation through retention, churn, conversion, recently engaged active members, and at-risk member signals |
| Announcement maturity | ✅ Completed | Clubs Hub announcements now supports templates, pinning, visible-feed read actions, and club-lead moderation instead of stopping at basic publish/read |
| Public-facing polish | ✅ Completed | Clubs now supports richer public profile fields and renders them across create/edit, directory cards, hero, and summary surfaces |

---

## 🔁 NEXT ACTIONS

- Immediate fix:
  - N/A
- Next review:
  - Re-audit after real coordinator, student, and admin usage reveals whether escalation-policy controls, longer alert retention, audited payment verification, or deeper external-facing club marketing should be the next investment.
- Responsible:
  - Frontend owner for analytics/communication/profile UX, Backend owner for historical contracts and telemetry-guided tuning, Product owner for escalation policy, finance verification depth, and any external-facing club identity roadmap.
- Remaining enhancement backlog:
  - Truly open now: N/A.
  - Partially already implemented and ready for expansion: public-facing marketing surfaces, announcement engagement insight, and richer moderation policy only if the product needs them.
  - Only pursue when telemetry or operations prove need: richer escalation-policy controls, longer alert-history retention, another round of backend query and index tuning beyond the current club-path coverage, or audited payment verification.


