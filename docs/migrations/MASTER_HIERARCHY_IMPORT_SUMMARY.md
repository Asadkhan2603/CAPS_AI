# Master Hierarchy Migration Summary

## Schema Changes
- Added `universities` as a first-class master collection and API.
- Added canonical workbook business fields to master collections while preserving legacy `name` / `code` aliases for compatibility.
- Added master hierarchy indexes for business IDs, business codes, and scoped uniqueness checks.
- Preserved internal ObjectId references for downstream operational entities such as batches, semesters, sections, groups, and course offerings.

## Data Migration Summary
- Workbook counts validated: {"universities": 1, "faculties": 8, "departments": 23, "programs": 44, "specializations": 35}
- Workbook reconciliations applied: 1
- Reconciled `Bachelor of Science in Computer Science` from `PRG-ENG-CSE-BSC-CS` to `PRG-SCI-CSE-BSC-CS` to match its parent faculty/department lineage and the `generic_format` pattern.
- Master collections replaced: specializations, programs, departments, faculties, universities
- Imported counts: {"universities": 1, "faculties": 8, "departments": 23, "programs": 44, "specializations": 35}

## Compatibility Summary
- Downstream operational collections were preserved.
- Replacement is blocked when downstream collections still reference old master ObjectIds.
- Replacement blockers found during this run: 0
- Downstream invalid references after import: 0

## Post-Import Audit
- Master counts: {"universities": 1, "faculties": 8, "departments": 23, "programs": 44, "specializations": 35}
- Duplicate findings total: 0
- Orphan findings total: 0
- Mismatch findings total: 0

## Assumptions
- `exports/Master_copy.xlsx` is the source of truth for the core academic master hierarchy only.
- Operational entities such as batches, semesters, sections, groups, course offerings, staff assignments, and student mappings are intentionally not imported from the workbook.
- Existing downstream records are preserved and must continue to reference valid master ObjectIds; the script aborts instead of orphaning them.

## Runbooks
- Field contract: [MASTER_HIERARCHY_FIELD_CONTRACT.md](/d:/VS%20CODE/MY%20PROJECT/CAPS_AI/docs/migrations/MASTER_HIERARCHY_FIELD_CONTRACT.md)
- Import runbook: [MASTER_HIERARCHY_RUNBOOK.md](/d:/VS%20CODE/MY%20PROJECT/CAPS_AI/docs/migrations/MASTER_HIERARCHY_RUNBOOK.md)
- Mutation safety: [MASTER_HIERARCHY_MUTATION_SAFETY.md](/d:/VS%20CODE/MY%20PROJECT/CAPS_AI/docs/migrations/MASTER_HIERARCHY_MUTATION_SAFETY.md)
