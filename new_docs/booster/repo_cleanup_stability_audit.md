# Repository Cleanup & Stability Audit

**Date & Time:** 2026-04-14 11:55:34 +05:30 (Asia/Calcutta)

**Audit Scope:** Full repository scan of tracked source/config/docs plus local runtime/cache/build directories (`.runlogs`, `.pytest_cache`, `frontend/node_modules`, `backend/.venv311`, `frontend/dist-verification*`, `out`, `test-results`).

**Validation Signals Captured During Audit:**
- `frontend`: `npm run lint` passed.
- `frontend`: `npm run build` passed (bundle output captured).
- `backend`: `pytest -q tests/test_health.py` passed with FastAPI deprecation warnings for `@app.on_event` usage.

## Repository Health Score

| Category | Score | Remarks |
|----------|------|--------|
| Code Cleanliness | 5/10 | Multiple very large files (frontend pages and backend endpoints), legacy mock components still present, mixed active/inactive modules. |
| Dead Code | 4/10 | Multiple high-confidence unreferenced source files in both frontend and backend; test-only helper in production tree. |
| File Structure | 4/10 | Build verification artifacts (`frontend/dist-verification*`) are tracked in repo with redundant copies. |
| Performance | 5/10 | Large chunks/components, repeated request patterns (`Promise.all` over row-level updates), and oversized modules indicate scaling risk. |
| Dependency Health | 6/10 | Frontend dependencies are actively used; backend has runtime requirements with no code usage (`httpx`, `nltk`) and test dep (`pytest`) in runtime file. |
| Logging & Debug | 7/10 | Production UI still has direct console logging in error and governance paths; script logging is mostly appropriate for CLI tools. |
| Cache Handling | 3/10 | Large untracked runtime/cache directories not ignored (`.runlogs`, `backend/.venv311`), plus tracked generated verification builds. |
| Stability | 6/10 | Core checks pass, but deprecated FastAPI lifecycle hooks and risky cleanup zones require controlled refactoring. |

---

# Unused File Detection

| File/Folder | Reason Unused | Risk | Action |
|-------------|---------------|------|--------|
| `frontend/src/components/analytics/StudentRiskPanel.jsx` | No inbound references found in `frontend/src`; component only references itself. | Low | Safe-remove candidate after route-level smoke test. |
| `frontend/src/components/communication/ChatWindow.jsx` | No inbound references; mock component never mounted. | Low | Remove with snapshot/visual check on communication pages. |
| `frontend/src/components/communication/ConversationList.jsx` | No inbound references; mock-only UI path. | Low | Remove after `npm run lint && npm run build`. |
| `frontend/src/components/layout/Topbar.jsx` | Not referenced by active layout stack (`DashboardLayout -> AppLayout -> Header`); legacy topbar path. | Medium | Remove together with dependent `noticeReadTracker` only after header behavior parity check. |
| `frontend/src/pages/NavigationGroupPage.jsx` | Not routed in `AppRoutes`; no imports found. | Low | Remove after route crawl (`/workspace/*`) sanity test. |
| `frontend/src/pages/clubs/queueLocalState.js` | No references in app/tests; dead local-storage queue helper set. | Low | Safe-remove candidate; validate clubs queue persistence still server-driven. |
| `frontend/src/pages/timetablePage.helpers.js` | Used only by `timetablePage.helpers.test.js`, not by runtime pages. | Medium | Move to test utilities folder or remove and inline in tests. |
| `backend/app/services/pdf_report.py` | `build_evaluation_report` has zero references in `backend/app`, tests, and scripts. | Medium | Remove only after verifying no external invocation contract exists. |
| `backend/app/services/student_bulk_import.py` | Entire module unreferenced; no imports of `parse_bulk_upload_rows` or helpers. | Medium | Remove after API grep and endpoint smoke for student workflows. |
| `backend/app/utils/text_preprocessing.py` | Placeholder-only file with no callable code and no imports. | Low | Remove immediately (safe), run compile/test smoke. |
| `frontend/admin-role-matrix.spec.js`, `frontend/admin-role-smoke.spec.js`, `frontend/teacher-role-matrix.spec.js` | Playwright specs exist, but no Playwright dependency/scripts wired in `frontend/package.json` or CI. | Medium | Either wire Playwright into toolchain or archive/move these specs out of active tree. |
| `frontend/dist-verification*` (6 directories) | No code references; generated build artifacts are tracked in git. 498 files, ~9.36 MB. | Medium | Keep only latest snapshot (or none) with release-note link; remove historical copies by PR. |
| `package-lock.json` (repo root) | No root `package.json`; lock file contains empty packages object only. | Medium | Remove after updating CI path filters that currently watch this file. |
| `test-results/.last-run.json` | Generated test artifact tracked in repository. | Low | Stop tracking and ignore `test-results/` outputs. |

---

# Dead Code Detection

| File | Code Block | Issue | Fix |
|------|------------|-------|-----|
| `frontend/src/components/analytics/StudentRiskPanel.jsx` | `StudentRiskPanel`, `Metric`, `toneForLevel`, `toneForInterventionStatus` | Full component tree is unreachable from routes/layout imports. | Remove module or re-introduce via explicit analytics route integration. |
| `frontend/src/components/communication/ChatWindow.jsx` | `ChatWindow` + `MOCK_MESSAGES` | Legacy mock chat implementation not used by current `MessagesPage`. | Delete module or replace `MessagesPage` placeholder with this component if intended. |
| `frontend/src/components/communication/ConversationList.jsx` | `ConversationList` + `MOCK_THREADS` | Unmounted legacy mock thread list. | Remove or intentionally wire into communication roadmap implementation. |
| `frontend/src/components/layout/Topbar.jsx` | `Topbar` | Legacy layout component superseded by `Header.tsx`. | Remove with paired removal of dead utility dependency chain. |
| `frontend/src/utils/noticeReadTracker.js` | `unreadNoticeCount` utility | Referenced only by dead `Topbar`. | Remove together with `Topbar`, or re-home to active header if needed. |
| `frontend/src/pages/NavigationGroupPage.jsx` | `NavigationGroupPage`, `describeGroup` | Route not mounted anywhere in `AppRoutes`. | Remove page or add intended route mapping. |
| `frontend/src/pages/clubs/queueLocalState.js` | `listSavedQueueFilters`, `saveQueueFilter`, `removeQueueFilter`, `listQueueSnapshots`, `recordQueueSnapshot` | Entire helper file has zero call sites. | Remove module or explicitly adopt for offline queue behavior. |
| `frontend/src/pages/timetablePage.helpers.js` | `groupStudentTimetableByDay` | Test-only helper stored in production path; runtime does not import it. | Move to `__tests__/helpers` or keep in runtime page and import there. |
| `backend/app/services/pdf_report.py` | `build_evaluation_report` | No imports/callers discovered; dead report generator. | Remove or expose via endpoint/job if report generation is planned. |
| `backend/app/services/student_bulk_import.py` | `parse_bulk_upload_rows` + helper constants/functions | Standalone bulk import parsing service not wired to endpoints/services. | Remove if superseded; otherwise integrate into student ingestion endpoint and add tests. |
| `backend/app/utils/text_preprocessing.py` | Placeholder comment only | Non-functional placeholder with no references. | Delete immediately. |

---

# Logging & Debug Cleanup

| File | Log Type | Issue | Fix |
|------|----------|-------|-----|
| `frontend/src/components/system/ErrorBoundary.jsx` | `console.error` | Raw browser console logging in production error boundary. | Route to centralized telemetry service and gate console logging by environment. |
| `frontend/src/components/ui/entityManager/useDeleteGovernance.js` | `console.warn`, `console.error` | Governance failures and blocked deletes leak to console only; no structured observability contract. | Replace with API-backed audit/telemetry event + user-safe toast messaging. |
| `scripts/migrate_*_schema_version.py` (40 files) | Frequent `print(...)` | High console verbosity is acceptable for CLI, but no common logging abstraction across migration scripts. | Keep `print` for CLI mode, but standardize output schema and add `--json`/`--quiet` flags. |
| `scripts/*` audit/smoke utilities | `print(...)` status streams | Expected for one-shot CLI tools; not a production runtime concern. | No deletion; classify as acceptable operational logging. |

---

# Cache & Build Artifact Audit

| Item | Issue | Impact | Fix |
|------|-------|--------|-----|
| `backend/.venv311` (~381.84 MB, untracked) | Local virtualenv directory not covered by `.gitignore` (`.venv/` exists, but `.venv311` does not). | High disk churn, accidental commit risk. | Add `backend/.venv*/` ignore rule and keep venv outside repo root when possible. |
| `.runlogs` (~204.09 MB, untracked) | Runtime DB/log directory not ignored; includes large WiredTiger logs (2 x 100 MB). | Local storage pressure and accidental commit risk. | Add `.runlogs/` to `.gitignore`; document cleanup command for stale runlogs. |
| `frontend/node_modules` (~206.36 MB, untracked) | Expected local cache, but doubles with root `node_modules`. | Workspace bloat and slower file indexing. | Keep only per-project install; remove stray root modules when idle. |
| `frontend/dist-verification*` (tracked, ~9.36 MB, 498 files) | Generated bundles checked in as historical snapshots. | Repo noise, PR diff noise, stale binary-like JS assets. | Stop tracking generated verification builds or retain a single archived snapshot outside main tree. |
| `.pytest_cache` | Standard cache present; currently ignored correctly. | Minimal. | Keep ignored; periodic cleanup optional. |
| `out/` | Generated scripts output folder (ignored). | Minimal. | Keep ignored; prune as needed. |
| `test-results/.last-run.json` (tracked) | Generated test-run metadata tracked in repo. | Non-deterministic diffs and stale metadata. | Remove from git and add/keep ignore for `test-results/`. |
| Root `node_modules` | Secondary install footprint in monorepo root. | Confusion and potential dependency drift. | Remove root install artifacts and enforce package-manager working dirs. |

---

# Unused Dependencies

| Package | Used? | Issue | Fix |
|---------|-------|-------|-----|
| `frontend` runtime deps (`axios`, `clsx`, `framer-motion`, `lucide-react`, `react`, `react-dom`, `react-router-dom`, `recharts`) | Yes | Import hits found across `frontend/src`; no immediate cleanup target. | No action required. |
| `backend/requirements.txt -> httpx==0.27.2` | No in-repo code usage | Declared runtime dependency without app/scripts/tests imports. | Remove from runtime requirements or justify and add usage. |
| `backend/requirements.txt -> nltk==3.9.3` | No in-repo code usage | Unused runtime package increases install time and vulnerability surface. | Remove from runtime requirements unless pending feature branch depends on it. |
| `backend/requirements.txt -> pytest==8.3.3` | Test-only | Testing framework is in runtime dependency file. | Move `pytest` to `requirements-dev.txt`; keep runtime lean. |
| `backend/requirements-dev.txt` toolchain deps | Yes (CI/lint/type/audit workflow) | Actively aligned with CI (`flake8`, `mypy`, `bandit`, `pytest-cov`, `pip-audit`). | Keep as-is. |

---

# Duplicate & Redundant Code

| Location | Duplicate Type | Issue | Fix |
|----------|----------------|-------|-----|
| `frontend/dist-verification`, `dist-verification-2`, `-3`, `-4`, `-5`, `-6` | Repeated generated bundles | Same vendor chunks repeated across six snapshots (hash-identical assets observed). | Keep one canonical artifact (if needed) or remove all generated snapshots from git history going forward. |
| `backend/app/services/academic_students.py`, `communication_deliveries.py`, `student_profiles.py`, `student_bulk_import.py`, `scripts/sync_student_profiles_from_users.py` | Repeated email normalization helpers | Multiple local implementations of `normalize_email` / `_normalize_email`. | Extract shared normalization utility in `app/utils` and reuse across modules/scripts. |
| `scripts/migrate_*_schema_version.py` (40 files) | Boilerplate migration scaffolding | High structural duplication across schema migration scripts increases maintenance effort. | Introduce common migration runner/template to reduce repeated argument parsing and reporting logic. |
| `frontend/src/components/layout/Topbar.jsx` vs active `Header.tsx` | Legacy UI overlap | Two top navigation implementations, one dead, one active. | Remove dead topbar path and consolidate notification/profile logic in active header only. |
| `export/` + `exports/` output strategy | Redundant artifact destinations | `generate_academic_export.py` writes duplicate datasets to two directories by default. | Keep dual-write only if backward compatibility is mandatory; otherwise deprecate one path with migration notice. |

---

# Performance Bottlenecks

| Area | Issue | Impact | Fix |
|------|-------|--------|-----|
| `frontend/src/pages/ClubsPage.jsx` (4044 lines) | Monolithic page with many effects/state transitions and multiple API surfaces in one component. | Higher rerender complexity, harder memoization, slower onboarding/debugging. | Split into domain hooks + leaf components (applications, events, registrations, analytics). |
| `frontend/src/pages/NotificationsPage.jsx` (2600 lines) | Large all-in-one page handling CRUD, reports, digests, incidents, preferences. | High interaction latency risk and maintainability drag. | Extract report/digest/admin sections into lazy-loaded subcomponents. |
| `frontend/src/pages/NotificationsPage.jsx:818` | `Promise.all(unreadRows.map(...patch...))` sends one request per visible unread row. | Request burst spikes for large tables and potential rate-limit/backpressure issues. | Add batch mark-read endpoint and send one bulk payload. |
| `frontend/src/pages/ClubsPage.jsx:334` and `:361` | Effects depend on `applications`/`enrollments`, triggering repeated fetches beyond key identity changes. | Excess network traffic and redundant state churn. | Narrow dependencies to stable IDs/timestamps and debounce refresh triggers. |
| Frontend build output (`npm run build`) | Heavy bundles (`charts-vendor` ~363.70 kB, `react-vendor` ~164.71 kB, `ClubsPage` chunk ~155.89 kB, `NotificationsPage` chunk ~74.42 kB). | Slower first-load and route transition payloads on low bandwidth. | Adopt route/component level lazy boundaries and on-demand chart imports; enforce bundle budgets in CI. |
| `backend/app/api/v1/endpoints/clubs.py` (2026 lines) | Oversized endpoint module with broad responsibilities. | Increased CPU path complexity and regression risk under change. | Decompose into subrouters/services by responsibility (membership, governance, analytics, queue views). |
| `backend/app/main.py:177` and `:186` | Deprecated FastAPI lifecycle hooks (`@app.on_event`) detected via test warnings. | Future framework upgrade break risk and lifecycle management fragility. | Migrate to lifespan context manager pattern. |

---

# Risky Cleanup Areas

| Item | Risk | Why | Safe Approach |
|------|------|-----|---------------|
| `frontend/dist-verification*` removal | Medium | Could be used as manual QA snapshots outside code references. | Confirm release/QA process owner, archive one signed snapshot, then delete others in one PR. |
| `package-lock.json` (root) removal | Medium | CI change filters currently include this file path. | Remove file together with CI `paths` update to avoid silent trigger behavior change. |
| Migration script pruning (`scripts/migrate_*`) | High | Historical operational scripts may be required for rollback/data repair. | Never hard-delete without migration inventory, runbook mapping, and archival policy. |
| `backend/app/services/student_bulk_import.py` deletion | Medium | Could represent pending feature integration not yet wired. | Validate product backlog/roadmap owner before deletion; preserve in feature branch if planned. |
| `backend/app/services/pdf_report.py` deletion | Medium | Could be called by external/manual scripts not tracked in repo. | Search deployment scripts/docs, verify no external contract, then remove. |
| `frontend/src/components/system/ErrorBoundary.jsx` console logging removal | Medium | May reduce immediate incident visibility if telemetry replacement not ready. | Replace console with structured telemetry first, then strip raw logs. |
| `export/` directory cleanup | Medium | Export generator currently writes to both `export/` and `exports/`. | Deprecate one path in two-step release: dual-write -> monitor -> single-write. |

---

# Safe Deletion Plan (Critical)

| Item | Step-by-Step Action | Validation |
|------|---------------------|------------|
| `frontend/src/components/analytics/StudentRiskPanel.jsx` | 1) Create cleanup branch. 2) Remove file. 3) Run lint/build. 4) Navigate analytics routes manually. 5) Merge if no regressions. | `npm --prefix frontend run lint`, `npm --prefix frontend run build`, route smoke `/analytics`. |
| `frontend/src/components/communication/ChatWindow.jsx` + `ConversationList.jsx` | 1) Remove both files. 2) Run communication page smoke tests. 3) Confirm placeholders still render as expected. | `npm --prefix frontend run lint`, `npm --prefix frontend run build`, manual `/communication/messages`. |
| `frontend/src/components/layout/Topbar.jsx` + `frontend/src/utils/noticeReadTracker.js` | 1) Confirm no imports remain via grep. 2) Remove both. 3) Validate header notifications/profile interactions. | `git grep -n "Topbar\|unreadNoticeCount" -- frontend/src`, UI smoke across header flows. |
| `frontend/src/pages/NavigationGroupPage.jsx` | 1) Remove file. 2) Verify workspace routes still redirect/render. | Manual test `/workspace/:groupKey/*`, `npm --prefix frontend run build`. |
| `frontend/src/pages/clubs/queueLocalState.js` | 1) Remove file. 2) Validate clubs queue save/history behavior (server-backed endpoints). | Clubs page regression pass, no missing import build errors. |
| `frontend/src/pages/timetablePage.helpers.js` | 1) Move to test utilities or remove. 2) Update test imports. | `npm --prefix frontend run test:ci` for timetable tests. |
| `backend/app/utils/text_preprocessing.py` | 1) Remove file. 2) Compile backend modules. 3) Run backend health test. | `python -m compileall backend/app backend/scripts`, `pytest -q backend/tests/test_health.py`. |
| `backend/app/services/pdf_report.py` | 1) Verify no external references in docs/deploy scripts. 2) Remove module. 3) Run smoke tests. | `git grep -n "build_evaluation_report\|pdf_report" -- .`, backend smoke tests from CI list. |
| `backend/app/services/student_bulk_import.py` | 1) Confirm no usage in endpoints/jobs. 2) Remove file. 3) Run student workflows smoke tests. | `git grep -n "parse_bulk_upload_rows\|student_bulk_import" -- backend`, targeted student API tests. |
| `frontend/dist-verification*` | 1) Select retention policy (keep latest only or archive externally). 2) Delete obsolete dirs. 3) Update `.gitignore` to block reintroduction. | `git ls-files "frontend/dist-verification*"` returns intended retained set only. |
| Root `package-lock.json` | 1) Remove stale lock file. 2) Update CI path filters removing root lock dependency. 3) Re-run CI. | CI workflow diff review + PR run green. |
| `test-results/.last-run.json` | 1) Untrack generated test metadata. 2) Ensure ignore rule covers file/folder. | `git ls-files test-results/.last-run.json` should return empty. |

---

# Cleanup Execution Plan

## Phase 1: Safe Removals
- Remove high-confidence dead UI files: `StudentRiskPanel.jsx`, `ChatWindow.jsx`, `ConversationList.jsx`, `NavigationGroupPage.jsx`, `queueLocalState.js`.
- Remove backend placeholder: `backend/app/utils/text_preprocessing.py`.
- Untrack generated metadata: `test-results/.last-run.json`.
- Add ignore rules for `.runlogs/`, `backend/.venv*/`, and build verification outputs.

## Phase 2: Code Cleanup
- Remove legacy layout chain (`Topbar.jsx` + `noticeReadTracker.js`) after header parity check.
- Remove dead backend service modules (`pdf_report.py`, `student_bulk_import.py`) after contract validation.
- Consolidate duplicate normalization helpers into shared utility.
- Start splitting monolith files (`ClubsPage.jsx`, `NotificationsPage.jsx`, `clubs.py`) into smaller modules.

## Phase 3: Dependency Cleanup
- Update backend requirements:
  - Remove `httpx` (unused).
  - Remove `nltk` (unused).
  - Move `pytest` from `requirements.txt` to `requirements-dev.txt`.
- Keep frontend dependency set unchanged (all runtime deps currently in use).

## Phase 4: Performance Fix
- Implement notification bulk mark-read endpoint to replace per-row request fan-out.
- Narrow `ClubsPage` effect dependencies to reduce redundant refetches.
- Add and enforce bundle budgets in CI (script exists: `frontend/scripts/checkBundleBudgets.mjs`).
- Migrate FastAPI lifecycle hooks to lifespan API to eliminate deprecation path.

---

# Impact Analysis

| Change | Expected Benefit |
|--------|------------------|
| Remove dead frontend/backend files | Smaller surface area, lower cognitive load, fewer stale references. |
| Remove tracked generated verification bundles | Cleaner diffs, faster code review, lower repo bloat. |
| Ignore `.runlogs` and `.venv311` | Prevent accidental large commits and reduce local disk churn risk in version control. |
| Prune unused backend dependencies | Faster installs, reduced CVE exposure, leaner runtime container images. |
| Refactor heavy pages/endpoints | Better maintainability, reduced rerender/query overhead, easier targeted testing. |
| Batch notification mark-read API | Reduced network request bursts and improved UI responsiveness under large unread sets. |
| Replace deprecated FastAPI lifecycle hooks | Improved forward compatibility and lower framework upgrade risk. |

---

# Final Verdict

- Repo Health: **Moderate, cleanup overdue**
- Stability Risk: **Medium**
- Cleanup Urgency: **High for artifact/cache hygiene; Medium for dead code removal; Medium-High for performance refactor**
- Biggest Problem: **Generated/legacy code coexistence (tracked build artifacts + dead modules + monolithic hot files)**
- Recommended Action: **Execute phased cleanup with strict validation gates, starting with low-risk dead file/artifact removal and ignore-rule hardening, then dependency/performance refactors.**
