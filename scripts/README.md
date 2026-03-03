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
- `powershell -ExecutionPolicy Bypass -File scripts/migrate_to_azure_aks.ps1 ...`
  - End-to-end AKS migration automation:
    - optional Azure infrastructure bootstrap (RG + ACR + AKS + attach ACR)
    - optional node-pool hardening (dedicated non-B `System` pool + dedicated `User` pool)
    - Docker build and push to ACR
    - render Azure manifests with real image/domain/secret values
    - deploy and run rollout checks in `caps-ai` namespace
