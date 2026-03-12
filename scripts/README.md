# Scripts

Utility scripts for local setup, safety checks, and canonical academic data seeding.

## Inventory

- `python scripts/check_backend_safety.py`
  - Validates safety-critical backend contracts.
  - Current checks include governance delete approval enforcement and protected endpoint expectations.

- `python scripts/seed_medicaps_courses.py`
  - Upserts the legacy course catalog used for compatibility and migration support.
  - This does not restore `/courses` as a public runtime API.

- `python scripts/seed_medicaps_years.py`
  - Seeds legacy year records for compatibility and migration support.
  - This does not restore `/years` as a public runtime API.

- `python scripts/seed_medicaps_departments_branches.py`
  - Seeds faculty, department, and legacy branch-style compatibility data.
  - Public runtime uses `faculties`, `departments`, and `specializations`.

- `powershell -ExecutionPolicy Bypass -File scripts/seed_minimum_stack.ps1`
  - Creates a runnable local dataset for smoke testing.
  - Includes admin, teacher, student, section, subject, enrollment, and timetable baseline data.

- `powershell -ExecutionPolicy Bypass -File scripts/smoke_check_stack.ps1`
  - Runs local smoke checks against a running stack.
  - Covers health, login, `/auth/me`, timetable flows, and student timetable access.

- `python scripts/migrate_academic_soft_delete.py`
  - Normalizes academic collections to canonical soft-delete metadata.
  - Supports dry-run by default and `--apply` for persistence.
  - Target fields: `is_active`, `deleted_at`, `deleted_by`.

- `python scripts/migrate_submission_schema_version.py`
  - Backfills `schema_version` on `submissions`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_evaluation_schema_version.py`
  - Backfills `schema_version` on `evaluations`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_ai_job_schema_version.py`
  - Backfills `schema_version` on `ai_jobs`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_ai_evaluation_run_schema_version.py`
  - Backfills `schema_version` on `ai_evaluation_runs`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

## Usage Notes

- Run Python scripts from the repository root so relative imports and paths resolve correctly.
- Prefer the backend virtualenv interpreter for repeatable results.
- Treat seeding scripts as local/admin utilities, not production migration substitutes.

## Phase 3 Follow-Up

Phase 3 introduces documentation and migration integrity work. Before adding new migration scripts:
- document the target collection shape
- define idempotent behavior
- note rollback expectations in `docs/`
