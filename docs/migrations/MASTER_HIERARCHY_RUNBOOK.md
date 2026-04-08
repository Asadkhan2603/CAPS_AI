# Master Hierarchy Runbook

## What The Workbook Controls

`exports/Master_copy.xlsx` controls only the master hierarchy:

- University
- Faculty
- Department
- Program
- Specialization

Everything below that is created inside CAPS AI after import:

- batches
- semesters
- sections
- groups
- course offerings
- classes
- teacher/student mappings

## Safe Import Workflow

1. Update `exports/Master_copy.xlsx`.
2. Run a dry run first:

```powershell
python backend/scripts/import_master_hierarchy.py --dry-run
```

3. Review:
- workbook validation errors
- reconciliation entries
- change plan
- downstream blockers

4. If the plan is correct, run the real import with a backup:

```powershell
python backend/scripts/import_master_hierarchy.py --backup-dir exports
```

5. If you are rebuilding a fresh local academic hierarchy after a full academic purge, seed the canonical program batches next:

```powershell
python backend/scripts/seed_program_batches.py
```

That produces the master hierarchy plus program-level batches and semesters. Sections, groups, subjects, course offerings, and class slots are still created inside CAPS AI after the hierarchy rebuild.

## Dry Run Behavior

Dry run:
- validates workbook sheets and normalized hierarchy
- checks ID/code patterns
- builds a change plan against current master records
- reports downstream blockers
- does not mutate master data

For a post-migration stability check, use:

```powershell
python backend/scripts/import_master_hierarchy.py --dry-run --fail-on-change-plan
```

That command fails if the workbook would add, update, or remove master records relative to the current database state.

## Backup Behavior

When `--backup-dir` is provided, the importer writes a JSON snapshot like:

`exports/master_hierarchy_backup_YYYYMMDD_HHMMSS/`

This snapshot is reviewable and can be used for manual rollback planning.

## Reconciliation Cases

The importer may reconcile workbook IDs when the lineage-derived business ID is correct and the workbook row is not.

Example:
- workbook row says `PRG-ENG-CSE-BSC-CS`
- actual parent lineage requires `PRG-SCI-CSE-BSC-CS`

The importer records the change in:
- dry-run output
- markdown summary

Do not ignore repeated reconciliations. Fix the workbook if the mismatch is unexpected.

## Blockers

The importer aborts instead of orphaning downstream records.

Common blockers:
- users still pointing to old faculty/department/program/specialization ObjectIds
- batches or semesters still pointing to old program/specialization ObjectIds
- classes still referencing old hierarchy ObjectIds

Resolve blockers before rerunning the replacement import.

## Merge Gate

The repository CI includes a dedicated academic hierarchy gate that:

- runs the master hierarchy regression tests
- imports the workbook into an ephemeral MongoDB instance
- reruns the importer in dry-run mode with `--fail-on-change-plan`
- runs `audit_academic_integrity.py --fail-on-findings`
- runs backend compile checks and frontend lint

This gate protects the post-migration baseline from silent hierarchy drift.
