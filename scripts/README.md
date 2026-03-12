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

- `python scripts/migrate_scheduler_lock_schema_version.py`
  - Backfills `schema_version` on `scheduler_locks`.
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

## Phase 3 Follow-Up

Phase 3 introduces documentation and migration integrity work. Before adding new migration scripts:
- document the target collection shape
- define idempotent behavior
- note rollback expectations in `docs/`
- update `docs/guides/mongo-versioning.md` when the baseline changes materially
- update `audit/roadmap.md` once a migration target or sweep is completed
