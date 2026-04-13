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

- `python backend/scripts/seed_program_batches.py`
  - Auto-generates canonical program-level batches and semesters for every active program.
  - Use this after importing `exports/Master_copy.xlsx` when rebuilding a fresh academic hierarchy.

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

- `python scripts/migrate_scheduler_lock_schema_version.py`
  - Backfills `schema_version` on `scheduler_locks`.
- `python scripts/perf_smoke.py`
  - Runs an in-process backend performance smoke gate against `/health`, `/auth/login`, `/admin/system/health`, an authenticated teacher submission-list workflow, an authenticated admin section-list academic workflow, a write-heavy admin student-create academic workflow, and a mixed teacher review workflow (`submissions -> evaluations -> analytics summary`).
- `python scripts/ai_similarity_benchmark.py`
  - Runs an in-process benchmark pass for AI evaluation preview latency, large-assignment similarity candidate-cap behavior, and similarity review-detail load.
  - Writes `artifacts/ai_similarity_benchmark_report.json` with rollout config, provider mode, and measured timings.
- `python scripts/ai_semantic_shadow_calibration.py`
  - Runs semantic shadow calibration cases for exact-match, paraphrase, mixed-language, and unrelated controls.
  - Writes `artifacts/ai_semantic_shadow_calibration_report.json` with rollout thresholds and gate results.
- `python scripts/ai_fairness_regression.py`
  - Runs evaluation fairness regression checks across concise, formula-heavy, multilingual, Unicode-script, short-answer, and rubric-shaped cases.
  - Writes `artifacts/ai_fairness_regression_report.json` with thresholds and drift deltas.
- `python scripts/ai_reviewer_outcome_calibration.py`
  - Summarizes real similarity reviewer outcomes from stored logs to estimate assist-only semantic drift thresholds and promotion readiness.
  - Writes `artifacts/ai_reviewer_outcome_calibration_report.json` with reviewer-status breakdown and rollout guardrails.
- `python scripts/release_gate.py`
  - Runs release-governance health gates against either:
    - an in-process local backend using `TestClient`, or
    - a deployed environment via `--base-url` and `--bearer-token`
  - Fails on critical alerts by default and validates snapshot retention plus alert-routing health.
- `python scripts/canary_rollout.py <backend|frontend> <prepare|promote|rollback|disable> --image <image>`
  - Executes staged Kubernetes rollout control for backend or frontend canary deployments.
  - Uses the dedicated canary deployment/service/ingress manifests and can call `release_gate.py` for remote verification.
  - Supports `--print-only` for command preview without touching a cluster.
- `python scripts/ai_capacity_baseline.py`
  - Emits the current AI and similarity capacity baseline derived from runtime settings and scheduler behavior.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_settings_schema_version.py`
  - Backfills `schema_version` on `settings`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_admin_action_review_schema_version.py`
  - Backfills `schema_version` on `admin_action_reviews`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_analytics_snapshot_schema_version.py`
  - Backfills `schema_version` on `analytics_snapshots`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_user_session_schema_version.py`
  - Backfills `schema_version` on `user_sessions`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_notification_schema_version.py`
  - Backfills `schema_version` on `notifications`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_audit_log_schema_version.py`
  - Backfills `schema_version` on `audit_logs` and `audit_logs_immutable`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_review_ticket_schema_version.py`
  - Backfills `schema_version` on `review_tickets`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_notice_schema_version.py`
  - Backfills `schema_version` on `notices`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_assignment_schema_version.py`
  - Backfills `schema_version` on `assignments`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_club_event_schema_version.py`
  - Backfills `schema_version` on `club_events`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_club_schema_version.py`
  - Backfills `schema_version` on `clubs`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_event_registration_schema_version.py`
  - Backfills `schema_version` on `event_registrations`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_club_member_schema_version.py`
  - Backfills `schema_version` on `club_members`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_club_application_schema_version.py`
  - Backfills `schema_version` on `club_applications`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_similarity_log_schema_version.py`
  - Backfills `schema_version` on `similarity_logs`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_group_schema_version.py`
  - Backfills `schema_version` on `groups`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_subject_schema_version.py`
  - Backfills `schema_version` on `subjects`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_student_schema_version.py`
  - Backfills `schema_version` on `students`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_class_slot_schema_version.py`
  - Backfills `schema_version` on `class_slots`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_course_offering_schema_version.py`
  - Backfills `schema_version` on `course_offerings`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_enrollment_schema_version.py`
  - Backfills `schema_version` on `enrollments`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_attendance_record_schema_version.py`
  - Backfills `schema_version` on `attendance_records`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_internship_session_schema_version.py`
  - Backfills `schema_version` on `internship_sessions`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_faculty_schema_version.py`
  - Backfills `schema_version` on `faculties`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_department_schema_version.py`
  - Backfills `schema_version` on `departments`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_specialization_schema_version.py`
  - Backfills `schema_version` on `specializations`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_branch_schema_version.py`
  - Backfills `schema_version` on legacy `branches`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_program_schema_version.py`
  - Backfills `schema_version` on `programs`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_batch_schema_version.py`
  - Backfills `schema_version` on `batches`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_semester_schema_version.py`
  - Backfills `schema_version` on `semesters`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_class_schema_version.py`
  - Backfills `schema_version` on `classes`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_timetable_schema_version.py`
  - Backfills `schema_version` on `timetables`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_timetable_subject_teacher_map_schema_version.py`
  - Backfills `schema_version` on `timetable_subject_teacher_maps`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

- `python scripts/migrate_user_schema_version.py`
  - Backfills `schema_version` on `users`.
  - Supports dry-run by default and `--apply` for persistence.
  - Current target version: `1`.

## Usage Notes

- Run Python scripts from the repository root so relative imports and paths resolve correctly.
- Prefer the backend virtualenv interpreter for repeatable results.
- Treat seeding scripts as local/admin utilities, not production migration substitutes.

## Academic Rebuild

For a clean academic hierarchy rebuild after a local purge:

1. `python backend/scripts/import_master_hierarchy.py --backup-dir exports`
2. `python backend/scripts/seed_program_batches.py`

That restores the canonical master hierarchy plus program-level batches and semesters. Delivery data such as sections, groups, subjects, course offerings, and class slots remains empty until it is created in CAPS AI.

Current local verification snapshot on April 2, 2026:
- master hierarchy import restored `1` university, `8` faculties, `23` departments, `44` programs, and `35` specializations
- program batch seeding restored `220` batches and `1290` semesters
- non-academic stale-reference audit returned `0` findings across the remaining collections

## Phase 3 Follow-Up

Phase 3 introduces documentation and migration integrity work. Before adding new migration scripts:
- document the target collection shape
- define idempotent behavior
- note rollback expectations in `docs/`
- update `docs/guides/mongo-versioning.md` when the baseline changes materially
- update `audit/roadmap.md` once a migration target or sweep is completed
