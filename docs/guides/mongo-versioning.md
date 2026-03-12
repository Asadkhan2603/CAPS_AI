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
- academic records may still contain `course_id`, `year_id`, and `branch_name`
- AI documents persist evolving metadata such as `ai_prompt_version` and `ai_runtime_snapshot`

## Strategy

### 1. Add explicit document version fields

For collections with active evolution pressure, introduce:
- `schema_version`
- `migrated_at`
- `migrated_by` when changes are administrative

Initial candidates:
- `classes`
- `submissions`
- `evaluations`
- `similarity_logs`
- `settings`

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

## Immediate Phase 3 Targets

1. Academic legacy normalization
   - continue from `scripts/migrate_academic_soft_delete.py`
   - add version markers where records are normalized
2. Section storage rename planning
   - document the path from `classes` storage to a future canonical `sections` collection, if adopted
3. AI metadata stability
   - keep `ai_prompt_version` and `ai_runtime_snapshot`
   - add version markers if AI payload shape changes materially

## Validation Checklist

- migration script is dry-run safe
- repeated execution is idempotent
- before/after document examples are documented
- affected endpoints still pass tests
- compatibility notes are updated in `README.md` and module docs
