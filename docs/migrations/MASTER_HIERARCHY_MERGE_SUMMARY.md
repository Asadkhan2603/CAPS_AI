# Master Hierarchy Merge Summary

## Baseline

CAPS AI is now operating on the workbook-backed canonical master hierarchy:

`University -> Faculty -> Department -> Program -> Specialization`

The live workbook import has already been completed and is intentionally not rerun as part of this merge-freeze step.

Imported master counts:

- universities: 1
- faculties: 8
- departments: 23
- programs: 44
- specializations: 35

## Schema Hardening

- Canonical workbook business fields are the official contract for all master entities.
- Legacy `name` and `code` aliases remain available only for backward compatibility.
- Backend import and audit tooling now have explicit fail-fast modes for CI and release verification.
- `openpyxl` is now an explicit backend dependency because the master import tool requires it directly.

## Index And Constraint Model

- Global canonical business ID uniqueness is enforced for:
  - `university_id`
  - `faculty_id`
  - `department_id`
  - `program_id`
  - `specialization_id`
- Scoped uniqueness is enforced where the workbook reuses branch-local codes:
  - `faculty_code` globally
  - `department_code` within faculty
  - `program_code` within department
  - `specialization_code` within program
  - names are scoped to their direct parent branch
- Parent lookup and hierarchy traversal indexes are in place for:
  - `faculties.university_id`
  - `departments.faculty_id`
  - `programs.department_id`
  - `specializations.program_id`

## Mutation Safety Guarantees

- Master entities cannot be deleted while descendants or protected downstream references still exist.
- Faculties, departments, programs, and specializations cannot be re-parented across branches when descendants or dependent operational records exist.
- Manual lineage overrides are rejected; lineage fields are derived from the selected parent record.
- CAPS AI fails fast instead of cascading cross-branch rewrites.

## Canonical Field Contract

Official canonical master fields:

- `universities`: `university_id`, `university_name`
- `faculties`: `faculty_id`, `faculty_code`, `faculty_name`, `university_id`
- `departments`: `department_id`, `department_code`, `department_name`, `faculty_id`
- `programs`: `program_id`, `program_code`, `program_name`, `department_id`, `duration_years`, `total_semesters`, `degree_type`
- `specializations`: `specialization_id`, `specialization_code`, `specialization_name`, `program_id`

See [MASTER_HIERARCHY_FIELD_CONTRACT.md](/d:/VS%20CODE/MY%20PROJECT/CAPS_AI/docs/migrations/MASTER_HIERARCHY_FIELD_CONTRACT.md) for the full contract and compatibility guidance.

## Admin UI Baseline

- Master admin pages use canonical field names in forms and tables.
- Parent selection is lookup-driven instead of free-text lineage entry.
- The university root layer is visible and searchable in the admin flow.
- Hierarchy pages no longer assume the old faculty-first root model.

## Import And Audit Tooling

- `import_master_hierarchy.py` supports:
  - dry-run mode
  - change-plan preview
  - blocker reporting
  - workbook reconciliation reporting
  - optional backup export
  - `--fail-on-change-plan` for merge gates
- `audit_academic_integrity.py` supports:
  - human-readable output
  - JSON output
  - `--fail-on-findings` for merge gates

## CI Protections

The repository CI now includes a dedicated academic hierarchy merge gate that runs:

- `pytest backend/tests/test_master_hierarchy_import.py`
- `pytest backend/tests/test_master_hierarchy_hardening.py`
- `pytest backend/tests/test_academic_setup_rules.py`
- `python -m compileall backend/app backend/scripts`
- `python backend/scripts/import_master_hierarchy.py --no-summary`
- `python backend/scripts/import_master_hierarchy.py --dry-run --no-summary --fail-on-change-plan`
- `python backend/scripts/audit_academic_integrity.py --fail-on-findings`
- `npm --prefix frontend run lint`

The CI import is performed only against an ephemeral MongoDB service, never against live master data.

## Documentation Set

The post-migration documentation set is:

- [MASTER_HIERARCHY_FIELD_CONTRACT.md](/d:/VS%20CODE/MY%20PROJECT/CAPS_AI/docs/migrations/MASTER_HIERARCHY_FIELD_CONTRACT.md)
- [MASTER_HIERARCHY_IMPORT_SUMMARY.md](/d:/VS%20CODE/MY%20PROJECT/CAPS_AI/docs/migrations/MASTER_HIERARCHY_IMPORT_SUMMARY.md)
- [MASTER_HIERARCHY_MUTATION_SAFETY.md](/d:/VS%20CODE/MY%20PROJECT/CAPS_AI/docs/migrations/MASTER_HIERARCHY_MUTATION_SAFETY.md)
- [MASTER_HIERARCHY_RUNBOOK.md](/d:/VS%20CODE/MY%20PROJECT/CAPS_AI/docs/migrations/MASTER_HIERARCHY_RUNBOOK.md)

## Final Verification Status

Verified on the current post-migration baseline:

- `python -m pytest backend/tests/test_master_hierarchy_import.py backend/tests/test_master_hierarchy_hardening.py backend/tests/test_academic_setup_rules.py` -> passed
- `python -m compileall backend/app backend/scripts` -> passed
- `npm run lint` -> passed
- `python backend/scripts/audit_academic_integrity.py --fail-on-findings` -> passed with 0 findings
- `python backend/scripts/import_master_hierarchy.py --dry-run --no-summary --fail-on-change-plan` -> passed with no detected hierarchy changes

## Remaining Risk Profile

- Legacy alias fields still exist for compatibility and should be removed only after downstream consumers are proven to be canonical-field clean.
- Master hierarchy mutations are intentionally conservative; admins must explicitly clean descendants before branch-changing operations.
- The workbook remains the source of truth only for master hierarchy layers. Operational entities remain app-managed by design.
