# Mongo Versioning And Migration Strategy

This guide defines the Phase 3 strategy for MongoDB data-shape changes in CAPS AI.

## Goals

- make schema evolution explicit
- keep compatibility with legacy academic artifacts during transition
- ensure migrations are idempotent and reviewable

## Current Reality

The application uses MongoDB collections directly with serializer helpers and service-level shaping. This means schema evolution must be controlled by convention and scripted migrations rather than by an ORM migration framework.

Compatibility examples already present in runtime:
- `classes` collection backs the canonical `/sections` API
- academic records may still contain legacy compatibility fields such as `branch_name` on historical section rows
- AI documents persist evolving metadata such as `ai_prompt_version` and `ai_runtime_snapshot`

## Strategy

### 1. Add explicit document version fields

For collections with active evolution pressure, introduce:
- `schema_version`
- `migrated_at`
- `migrated_by` when changes are administrative

Current status:
- the active collection-target sweep is complete for current write-path collections
- new writes now stamp `schema_version`
- dry-run and `--apply` backfill scripts exist under `scripts/`
- versioned collections now include academic setup, academics, AI, governance, communication, clubs, timetables, and users

### 2. Use idempotent migration scripts

Migration scripts should:
- support dry-run by default
- support `--apply` for persistence
- log counts for scanned, changed, skipped, and failed documents
- only mutate records that are below the target `schema_version`

### 3. Keep runtime readers backward-compatible during rollout

Until migration completion is verified:
- readers should accept both old and new fields
- writers should persist the new canonical shape
- docs should identify compatibility-only fields explicitly

### 4. Retire compatibility fields in a second phase

Field removal should happen only after:
- migration scripts have completed
- smoke tests and targeted regression checks pass
- docs and dashboards stop depending on the old shape

## Suggested Script Contract

Each migration script should document:
- target collections
- source fields and destination fields
- version bump rule
- dry-run output example
- rollback expectations

Recommended output fields:
- `collection`
- `target_version`
- `scanned`
- `updated`
- `skipped`
- `failed`

## Current Runtime Baseline

Completed baseline:
1. Version markers exist across the active write-path sweep
2. Collection-specific backfill scripts are documented in [scripts/README.md](/scripts/README.md)
3. Legacy academic compatibility remains read-oriented only where still needed for historical rows

Remaining follow-up work:
1. decide whether the `classes` collection should stay as the long-term storage name for canonical sections
2. introduce `schema_version` increments above `1` only when a collection shape actually changes again
3. keep compatibility readers narrow and explicitly documented

## Validation Checklist

- migration script is dry-run safe
- repeated execution is idempotent
- before/after document examples are documented
- affected endpoints still pass tests
- compatibility notes are updated in `README.md` and module docs
- scripts inventory is updated in `scripts/README.md`
