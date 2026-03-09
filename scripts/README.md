Utility scripts for local development and setup.

Available scripts:

- `python scripts/seed_medicaps_courses.py`
  - Upserts Medi-Caps course catalog and deactivates non-catalog courses.
- `python scripts/seed_medicaps_years.py`
  - Creates year records for active courses based on duration rules.
- `python scripts/seed_medicaps_departments_branches.py`
  - Upserts Medi-Caps departments/faculties and their branches/specializations.
- `powershell -ExecutionPolicy Bypass -File scripts/seed_minimum_stack.ps1`
  - Creates/updates a minimum runnable stack dataset:
    - admin, class coordinator teacher, student
    - course/year/section, subject
    - enrollment and published timetable baseline
- `powershell -ExecutionPolicy Bypass -File scripts/smoke_check_stack.ps1`
  - Validates backend smoke flow:
    - health check
    - login + `/auth/me`
    - timetable shifts/lookups
    - student `/timetables/my`
- `python scripts/migrate_academic_soft_delete.py`
  - Dry-run migration for academic setup collections to canonical soft-delete metadata:
    - `is_active`
    - `deleted_at`
    - `deleted_by`
  - Run with `--apply` to persist the normalization.
