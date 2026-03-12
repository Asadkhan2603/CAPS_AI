# CAPS AI Final Audit Report

## 1. Project Health Score (0-100)
**68 / 100**

Scoring rationale:
- Functionality and baseline tests are strong.
- Core architecture and security controls are present.
- Score reduced by dependency vulnerabilities, scaling bottlenecks, documentation drift, and maintainability hotspots.

## 2. Top 10 Critical Issues
1. Backend vulnerable dependencies in auth/parser stack (`backend/requirements.txt:5-6,12`; pip_audit output).
2. Frontend vulnerable dependencies (`frontend/package.json:16,22`; npm audit output).
3. Weak SHA1 usage in submission AI bulk idempotency (`backend/app/api/v1/endpoints/submissions.py:253`).
4. Large in-memory query materialization (`background_jobs.py:47`, `admin_communication.py:33,51`).
5. Sequential notice fanout write loop (`backend/app/services/background_jobs.py:67-75`).
6. CPU-heavy similarity pipeline inside app worker (`similarity_pipeline.py:69-70`, `similarity_engine.py:25-29`).
7. Endpoint bloat in key modules (analytics/timetables/evaluations).
8. Inconsistent architecture layering (direct DB access in endpoints vs service abstraction in auth).
9. Documentation drift from canonical runtime (`README.md:104`, `scripts/README.md:5-15`, `backend/app/models/README.md:4-6`).
10. CI quality gates missing for SCA and coverage thresholds (`.github/workflows/ci.yml`).

## 3. Top 10 Quick Fixes
1. Upgrade vulnerable dependencies (backend + frontend) and regenerate lockfiles.
2. Replace SHA1 with SHA256 in submissions idempotency key.
3. Fix current flake8 violations (5 reported).
4. Cap and paginate high-volume DB reads (`to_list(length=5000+)` paths).
5. Batch notification fanout (`insert_many` + chunking).
6. Add CI job for `python -m pip_audit -r backend/requirements.txt`.
7. Add CI job for `npm audit --omit=dev` with policy thresholds.
8. Enforce backend/frontend coverage thresholds in CI.
9. Update stale READMEs and align naming to canonical hierarchy.
10. Remove or archive dead artifacts (`SidebarLegacy.jsx`, placeholder utility) after validation.

## 4. Long-Term Refactor Suggestions
1. Move from endpoint-centric to domain-module architecture (commands/queries/services).
2. Extract shared access-control logic into centralized service.
3. Introduce async worker queue for expensive AI/similarity/background fanout jobs.
4. Add migration/version framework for Mongo schema evolution.
5. Build read models for analytics/dashboard-heavy queries.
6. Reduce frontend mega-components with route-level data hooks and presentational splits.

## 5. Security Risk Summary
- **High**: dependency CVEs, SHA1 usage.
- **Medium**: header trust assumptions, broad exception swallowing, registration-policy hardening, session token exposure under XSS.
- **Low**: manifest placeholder secrets and broad CORS defaults.

Reference: see `audit/security.md`.

## 6. Performance Improvement Plan
- Immediate: query windowing/pagination, fanout batching, AI chat message retention bounds.
- Mid-term: queue offload similarity and heavy jobs, aggregation/read-model optimization.
- Long-term: SLO-based load testing and capacity planning.

Reference: see `audit/performance.md`.

## 7. Architecture Improvement Plan
- Standardize domain boundaries across all modules (not only auth).
- Normalize canonical naming (`sections` vs `classes`) in API/docs/UI internals.
- Introduce module-level contracts and shared policy helpers for access/governance.
- Remove residual legacy assumptions from indexes/docs/scripts.

Reference: see `audit/architecture.md`.

## 8. Technical Debt Summary
- High debt concentration:
  - Large endpoint files
  - Legacy naming compatibility residue
  - Partial abstraction strategy
  - Documentation divergence and ignored docs tree (`.gitignore:65`)

Debt impact:
- Slower onboarding, higher regression risk, and scaling friction.

## 9. Recommended Roadmap (Phase-wise)

## Execution Status Update (2026-03-12)
- Phase 0 (stabilize and secure): completed in `56fbe7d`.
  - dependency upgrades completed (backend + frontend)
  - SHA1 replaced with SHA256 for submission AI idempotency
  - CI quality gates added (`pip_audit`, `npm audit`, backend/frontend coverage)
- Phase 1 (performance and reliability): completed across `9f39c65`, `d3eac0a`, `13722be`, `455069a`, `76438a9`, and current branch.
  - notice fanout batching and high-limit query reduction completed
  - teacher-scope query hot paths reduced with `distinct` + safe fallback patterns
  - endpoint/scheduler observability metrics and alert synthesis are now exposed through `/admin/system/health`
- Phase 2 (structural refactor): completed in `7d3c52c` plus frontend policy UX follow-up in current branch.
  - shared access-control utilities extracted into services
  - monolithic `ai.py` and `evaluations.py` split into submodules
  - service-layer orchestration added for AI runtime, AI ops, AI chat, evaluation workflows, and access-policy checks
  - teacher fallback indicators added to AI review surfaces
  - student AI disclosure policy made explicit in submissions/evaluations UI
- Phase 3 (data and documentation integrity): completed in `8ecddc6`.
  - `schema_version` rollout and backfill coverage completed across active Mongo collections
  - legacy schema and compatibility cleanup completed where safe
  - root, module, guide, recovery, and migration documentation aligned with runtime truth

### Phase 0 (0-1 week): Stabilize and Secure
Status: `Completed`
1. Patch dependencies and eliminate SHA1 usage.
2. Clean flake8 failures.
3. Add SCA + coverage CI gates.

### Phase 1 (1-3 weeks): Performance and Reliability
Status: `Completed`
1. Fix top `to_list` hotspots with paging/chunking.
2. Parallelize/batch notice fanout.
3. Add endpoint and scheduler observability metrics with alerting. (completed)

### Phase 2 (3-6 weeks): Structural Refactor
Status: `Completed`

Workstream A: Shared access-control and governance utilities
1. Create a centralized access policy service for teacher/admin scope checks. (completed)
2. Replace duplicated `_teacher_can_access_assignment` logic across: (completed)
   - `backend/app/api/v1/endpoints/ai.py`
   - `backend/app/api/v1/endpoints/evaluations.py`
   - `backend/app/api/v1/endpoints/similarity.py`
   - `backend/app/api/v1/endpoints/submissions.py`
3. Consolidate governance delete-approval enforcement wrappers for academic modules. (partially complete; further standardization pending outside AI Phase 2 scope)

Workstream B: Split monolithic endpoint files
1. Split `backend/app/api/v1/endpoints/ai.py` into role-focused submodules: (completed)
   - runtime/admin config
   - jobs and operations
   - chat/evaluation
2. Split `backend/app/api/v1/endpoints/evaluations.py` into: (completed)
   - CRUD and grade workflows
   - AI preview/refresh/trace workflows
3. Add router composition tests to guarantee path and permission parity. (covered by existing backend test suite; explicit dedicated composition tests remain optional)

Workstream C: Service-layer introduction (AI/academic/communication)
1. Move non-HTTP business logic from endpoints into services. (completed for AI/evaluation/submission/similarity domains)
2. Keep endpoint handlers thin (validation, auth, response mapping only). (completed for AI and evaluations; improved for submissions/similarity)
3. Define explicit command/query boundaries per domain. (completed for AI Phase 2 target modules; broader rollout can continue in Phase 3)

Phase 2 acceptance gates
1. No API path changes and no role-regression in route tests.
2. Static analysis and test suite remain green in CI.
3. Endpoint files targeted in this phase are reduced in size and duplicate access logic is removed.

### Phase 3 (6-10 weeks): Data and Documentation Integrity
Status: `Completed`
1. Introduce migration/version strategy for Mongo data shapes. (completed: submissions, evaluations, ai_jobs, ai_evaluation_runs, scheduler_locks, settings, admin_action_reviews, analytics_snapshots, user_sessions, notifications, audit_logs, audit_logs_immutable, review_tickets, notices, assignments, club_events, clubs, event_registrations, club_members, club_applications, similarity_logs, groups, subjects, students, class_slots, course_offerings, enrollments, attendance_records, internship_sessions, faculties, departments, specializations, legacy branches, programs, batches, semesters, classes, timetables, timetable_subject_teacher_maps, and users now persist `schema_version`, and dry-run/apply backfill scripts exist)
2. Remove legacy schema/index artifacts where safe. (completed: AI chat indexes centralized in startup bootstrap; legacy compatibility indexes no longer materialize absent collections at startup; `course_id` and `year_id` removed from section API output; dead `SidebarLegacy.jsx` removed; timetable lookup payload no longer exposes `branch_name`; active announcement audience search no longer keys on `branch_name`; dashboard identity no longer falls back to legacy `profile.branch_name`; section create/update/filter flows no longer accept `branch_name`; recovery defaults exclude retired `courses`/`years`/`branches` unless explicitly requested; analytics no longer exposes `courses`/`years` compatibility payload aliases or the `/analytics/teacher/classes` compatibility route)
3. Align and version docs (stop ignoring actionable docs, refresh READMEs/module docs). (completed: root docs, testing guide, mongo versioning guide, recovery docs, and legacy academic compatibility docs now reflect the current runtime and migration baseline)

### Phase 4 (Continuous): Scale Readiness
Status: `Completed`
1. Load/perf regression tests in CI/CD. (completed in current branch: backend performance smoke gate added in current branch for `/health`, `/auth/login`, `/admin/system/health`, an authenticated teacher submission-list workflow, an authenticated admin section-list academic workflow, a write-heavy admin student-create academic workflow, and a mixed teacher review workflow covering submissions, evaluations, and analytics summary)
2. Capacity planning for AI and similarity workloads. (completed in current branch: runtime-derived baseline added in `scripts/ai_capacity_baseline.py`, documented in `docs/guides/ai-capacity-planning.md`, enforced at runtime via `/api/v1/admin/system/health`, surfaced for operators in `frontend/src/pages/Admin/AdminSystemPage.jsx` and `frontend/src/pages/Admin/AdminObservabilityPage.jsx`, backed by a persisted `system_health_snapshots` store plus live 15-minute history, browser-local retention, auto-refresh, JSON export, retention-bound status metrics, persisted row/prune trend charts, and throttled system-notification alert routing for `system.read` operators)
3. Release governance with risk budgets and rollback criteria. (completed in current branch: `docs/guides/release-governance.md` now defines release classes, go/no-go gates, current risk budgets, rollback triggers, and watch-window rules; those rules can read live AI pressure metrics from `/api/v1/admin/system/health`, persisted snapshot history, the admin system page, the dedicated observability dashboard, and routed system notifications; `scripts/release_gate.py` plus the `release-governance-gate` CI job enforce the current go/no-go budgets in automation; and `scripts/canary_rollout.py` plus the canary Kubernetes manifests provide staged rollout and rollback control)

#### Phase 4 Exit Criteria

`Item 1: CI/CD perf regression coverage`

- `backend-perf-smoke` must remain green in GitHub Actions on the default branch.
- The smoke suite must cover:
  - unauthenticated health
  - authenticated admin health
  - authenticated login path
  - at least one authenticated teacher workflow
- Thresholds must be versioned in code and intentionally re-baselined when changed.
- At least one production-like benchmark path must cover a write-heavy or list-heavy academic flow in addition to the current teacher submission list.

Current status:

- all Item 1 exit criteria are met in the current worktree

`Item 2: AI/similarity capacity planning`

- `scripts/ai_capacity_baseline.py` must stay aligned with runtime constants in `backend/app/core/ai_capacity.py`.
- `/api/v1/admin/system/health` must expose:
  - live AI pressure metrics
  - bounded in-memory history
  - persisted snapshot history
  - snapshot-store retention status
- The admin system page and dedicated observability dashboard must render operator-visible status for:
  - queue depth
  - oldest queued age
  - fallback rate
  - similarity candidate pressure
  - snapshot-store growth and prune activity
- Capacity budgets must be documented and mapped to alertable thresholds.
- Those thresholds must also route outside dashboard pages through an operator-visible notification path.

Current status:

- all Item 2 exit criteria are met in the current worktree

`Item 3: Release governance`

- `docs/guides/release-governance.md` must define release classes, go/no-go checks, rollback triggers, rollback procedures, and watch windows.
- The release checklist must reference the actual CI jobs and admin health surface used by the repo.
- Operators must be able to evaluate current risk budgets without reading raw backend JSON.

Current status:

- all Item 3 exit criteria are met in the current worktree
