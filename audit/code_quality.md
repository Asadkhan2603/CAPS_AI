# CAPS AI Code Quality Audit

## Summary
Codebase is functional and testable, but maintainability is constrained by endpoint bloat, duplicated access logic, naming drift from legacy entities, and inconsistent error handling discipline.

## 1. Code Duplication

### Duplicated Teacher Access Helper
`_teacher_can_access_assignment` appears in four files:
- `backend/app/api/v1/endpoints/ai.py:32`
- `backend/app/api/v1/endpoints/evaluations.py:27`
- `backend/app/api/v1/endpoints/similarity.py:18`
- `backend/app/api/v1/endpoints/submissions.py:28`

Risk:
- Bug fixes/security checks can diverge by module.

Recommendation:
- Move to shared helper/service (e.g., `app/services/access_control.py`) and test once.

## 2. Bad Patterns

### Broad Exception Swallowing
Examples:
- `backend/app/services/audit.py:76`
- `backend/app/services/background_jobs.py:85,93,119`
- `backend/app/api/v1/endpoints/ai.py:62`
- `backend/app/api/v1/endpoints/analytics.py:69,116`

Risk:
- Silent failures and difficult incident triage.

Recommendation:
- Replace with explicit exception handling and structured logging.

### Inconsistent Layering
- Auth has domain service/repository (`backend/app/domains/auth/*`).
- Most other modules query `db` directly from endpoints (`backend/app/api/v1/endpoints/*`).

Risk:
- Harder unit testing and growing endpoint complexity.

Recommendation:
- Gradually introduce service boundaries for academic, AI, and communication modules.

## 3. Dead Code / Low-Value Artifacts
- Placeholder utility with no implementation:
  - `backend/app/utils/text_preprocessing.py:1`
- Unreferenced legacy frontend component:
  - `frontend/src/components/layout/SidebarLegacy.jsx` (no imports found via `rg`)

Recommendation:
- Remove or wire these intentionally; avoid stale artifacts in active tree.

## 4. Overly Complex / Large Files

### Backend (Top hotspots)
- `backend/app/api/v1/endpoints/analytics.py` (752 lines)
- `backend/app/api/v1/endpoints/timetables.py` (578)
- `backend/app/api/v1/endpoints/evaluations.py` (509)
- `backend/app/api/v1/endpoints/clubs.py` (495)
- `backend/app/api/v1/endpoints/ai.py` (409)

### Frontend (Top hotspots)
- `frontend/src/pages/ClubsPage.jsx` (946 lines)
- `frontend/src/components/ui/EntityManager.jsx` (776)
- `frontend/src/pages/DashboardPage.jsx` (607)
- `frontend/src/pages/BatchesPage.jsx` (586)
- `frontend/src/pages/AcademicStructurePage.jsx` (584)

Recommendation:
- Slice by feature subcomponents and extract query/command hooks/services.

## 5. Naming and Domain Inconsistencies
- Canonical routing is sections, but implementation still uses classes module naming:
  - Route mount: `backend/app/api/v1/router.py:52`
  - Handler file: `backend/app/api/v1/endpoints/classes.py`
- Legacy fields still present in schema:
  - `course_id`, `year_id`, `branch_name` in `backend/app/schemas/class_item.py:39-46`
- Frontend redirects legacy paths:
  - `frontend/src/routes/AppRoutes.jsx:201,205,207`

Impact:
- Increased cognitive load and onboarding friction.

## 6. Static Quality Findings
- Current flake8 issues:
  - `backend/app/api/v1/endpoints/course_offerings.py:207` F841 (`merged` unused)
  - `backend/app/api/v1/endpoints/groups.py:8` F401 (unused import)
  - `backend/app/api/v1/endpoints/timetables.py:11` F401 (unused import)
  - `backend/app/api/v1/endpoints/timetables.py:244` F841 (`room_codes` unused)
  - `backend/app/core/indexes.py:4` F401 (unused import)

Recommendation:
- Keep lint clean in main branch; fail CI on full backend flake8, not partial file list.

## 7. Missing Error Handling / Validation Gaps
- Some endpoints/services return generic errors with limited context due broad catches.
- Regex-based queries are used extensively for search:
  - e.g., `backend/app/api/v1/endpoints/classes.py:105`, `students.py:27-29`, `assignments.py:61`

Recommendation:
- Centralize safe search query construction and enforce input normalization rules consistently.

## 8. Logging Review

Strength:
- Structured JSON logging with request/trace IDs:
  - `backend/app/core/observability.py:21-37`
  - `backend/app/main.py:54-101`

Issues:
- Silent exception paths bypass meaningful logs in several modules (see section 2).
- Query string is logged at request start (`backend/app/main.py:61`), which can leak sensitive query parameters if clients misuse URLs.

Recommendation:
- Add query parameter allowlist/masking for logs.

## 9. Testing Audit

### Current
- Backend tests: 10 files, pass (`85 passed`).
  - `backend/tests/test_auth.py`, `test_main_missing_blocks.py`, etc.
- Frontend tests: only one test file:
  - `frontend/src/utils/permissions.test.js`

### Critical Gaps
1. Frontend route protection and auth-refresh flows are not integration-tested.
2. AI module UI flows for teacher/student have minimal automated coverage.
3. No coverage threshold enforcement in CI:
   - Backend step runs `pytest -q` only (`.github/workflows/ci.yml:97`)
   - Frontend step runs `vitest run` only (`.github/workflows/ci.yml:121`)

Recommendation:
- Add coverage reports and minimum thresholds for backend/frontend in CI.

