# Backend Analysis

Generated: 2026-03-31

## Validation Summary

- `pytest backend/tests/test_academic_permissions.py -q`: 9 passed
- `python scripts/check_backend_safety.py`: passed
- `python backend/scripts/import_master_hierarchy.py --dry-run`: failed because `exports/Master_copy.xlsx` is missing
- `pytest backend/tests -q`: collection failed from the repo root because two tests import `backend.*`
- `pytest tests -q` from `backend/`: same collection failure for the same import pattern

## Current Strengths

- The backend has a clear layered shape: `main.py` bootstraps middleware, endpoints orchestrate HTTP, services hold business logic, schemas validate contracts, and model serializers shape responses.
- Security middleware is not superficial. The app adds request tracing, security headers, response envelopes, centralized error envelopes, and rate limiting.
- The academic hierarchy is now internally coherent around the canonical model `University -> Faculty -> Department -> Program -> Optional Specialization -> Batch -> Semester -> Section -> Group`.
- The section-mapping and bulk-student-import path is implemented as a real workflow, not just CRUD.
- Admin system health has real depth. The single `/admin/system/health` endpoint aggregates DB ping, scheduler state, snapshot retention, observability, audit-derived slow-query counts, and alert routing.

## Repo-Based Findings

### 1. Full backend test execution is invocation-sensitive

Evidence:

- `pytest backend/tests -q` and `pytest tests -q` both fail collection on `test_academic_setup_rules.py` and `test_master_hierarchy_import.py`
- both failures come from `ModuleNotFoundError: No module named 'backend'`

Impact:

- the suite is not reliably runnable from common local entry points
- local validation is more fragile than CI expectations imply

Recommended fix:

- standardize imports to one convention
- or add a stable test runner entry that sets `PYTHONPATH` explicitly
- update docs and CI comments to match the supported invocation

### 2. Master hierarchy import is implemented but operationally blocked

Evidence:

- `backend/scripts/import_master_hierarchy.py` hardcodes `exports/Master_copy.xlsx`
- the file is absent from the repo
- dry-run import fails immediately on file load

Impact:

- master hierarchy recreation is blocked
- migration and Excel-aligned reconstruction cannot be completed end to end

Recommended fix:

- restore the workbook
- or parameterize the script with an input path and document the replacement source of truth

### 3. Backend architecture still carries placeholder domain packages

Evidence:

- `backend/app/domains/auth/` is the only domain package with real code
- `academic`, `analytics`, `clubs`, `communication`, and `governance` contain only `__init__.py`

Impact:

- the folder structure overstates architectural modularity
- maintainers may assume abstractions exist where they do not

Recommended fix:

- delete placeholder domain packages
- keep only `auth` until more domain packages hold real repository or service abstractions

### 4. Compatibility migration is still active in core flows

Evidence:

- `/sections` is the canonical route
- the implementation still reads and writes the `classes` collection
- downstream records still use `class_id`

Impact:

- naming drift increases maintenance cost
- careless cleanup can break students, enrollments, assignments, and timetables

Recommended fix:

- keep compatibility paths until migration is complete
- continue documenting `section` as canonical and `class_id` as compatibility-only

### 5. A few backend surfaces are oversized and concentration-heavy

Measured file sizes:

- `backend/app/api/v1/endpoints/analytics.py`: 1679 lines
- `backend/tests/test_auth.py`: 3781 lines

Impact:

- high cognitive load
- harder review and higher regression blast radius

Recommended fix:

- split analytics into feed, student-risk, and structure-specific modules
- break the auth test harness into thematic files

## Current Verdict

The backend is functionally strong and safety-aware, but not fully reconstruction-ready yet. The two highest-priority issues are:

1. restore or redefine the master hierarchy workbook source
2. make the full backend test suite path-agnostic for local execution
