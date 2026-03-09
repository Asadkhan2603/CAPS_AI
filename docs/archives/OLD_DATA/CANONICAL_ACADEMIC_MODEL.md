# Canonical Academic Model

## Decision

CAPS AI adopts the following academic hierarchy as the canonical model for all new setup, maintenance, and downstream feature work:

`Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`

This is the authoritative academic tree used by the academic structure UI and should be the default integration target for future modules.

## Legacy Compatibility Modules

The following modules remain available only for backward compatibility and controlled migration:

- `Course`
- `Year`
- `Branch`
- `/classes` API alias for sections

These modules are not part of the canonical academic tree.

## Canonical Routes

Use these routes for new academic structure work:

- `/faculties`
- `/departments`
- `/programs`
- `/specializations`
- `/batches`
- `/semesters`
- `/sections`

## Deprecated Legacy Routes

The following routes remain published but are deprecated in the API metadata:

- `/courses`
- `/years`
- `/branches`
- `/classes`

Expected usage:

- existing clients may continue to use them during migration
- new clients should not model new academic setup on them
- any new hierarchy, reporting, timetable, enrollment, and validation work should prefer the canonical chain

## UI Rules

- `AcademicStructurePage.jsx` represents only the canonical hierarchy
- legacy modules are shown as compatibility links, not as part of the main tree
- admin navigation should visually separate canonical setup from legacy compatibility modules

## Implementation Consequences

- new academic validations should be attached to the canonical chain first
- new UI drill-down flows should terminate at sections under the canonical path
- API consumers should treat legacy modules as transitional or reporting-only unless a documented exception exists
- refactors should move cross-module dependencies away from `course/year/branch` where feasible

## Migration Direction

When replacing legacy usages:

- `Course -> Year -> Section` should be mapped into `Program -> Batch -> Semester -> Section`
- `Department -> Branch` should be treated as compatibility metadata, not as a primary structural axis

This decision does not remove legacy modules immediately. It changes the default model the platform communicates and evolves around.
