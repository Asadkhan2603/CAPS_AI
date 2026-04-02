# Hard Blocker Fix Plan

## Purpose

This plan lists the blockers that currently prevent the repo from being fully reproducible, fully documented, or ready for export-safe regeneration.

## Data Model

Blocked areas:

- root documentation validation
- master hierarchy import source
- cleanup of dead runtime artifacts
- migration consistency

## APIs

Blocked or impacted API families:

- master hierarchy setup routes
- student onboarding routes
- admin analytics and system validation

## Workflow

### Blocker 1. Root runtime documentation mismatch

Observed on March 31, 2026:

- `python scripts/check_runtime_matrix.py` fails when root README does not document runtime versions

Fix:

- keep `Python 3.11.x`
- keep `Node.js 20.x`
- update README whenever CI runtime changes

### Blocker 2. Missing workbook source

Observed on March 31, 2026:

- `python backend/scripts/import_master_hierarchy.py --dry-run` fails because `exports/Master_copy.xlsx` is missing

Fix:

- restore the workbook
- or parameterize the import script and document the new canonical input source

### Blocker 3. Compatibility-sensitive migration work

The repo is not ready for blunt removal of:

- `class_id`
- `classes` collection access
- test helpers named `class_*`

Fix:

- complete the migration plan first
- preserve compatibility until all downstream modules are updated

## Dependencies

- `scripts/check_runtime_matrix.py`
- `backend/scripts/import_master_hierarchy.py`
- `docs/migrations/MASTER_HIERARCHY_RUNBOOK.md`
- `docs/roadmap/CLASSES_TO_SECTIONS_MIGRATION_PLAN.md`
