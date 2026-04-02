# Execution Roadmap

## Purpose

This roadmap defines the recommended implementation sequence for stabilizing the repo after audit and documentation reconstruction.

## Data Model

The roadmap is organized around the live data hierarchy and its dependent modules:

- docs and runtime validation
- master hierarchy
- academic operations
- delivery and assessment
- analytics and governance
- export generation

## APIs

Highest-priority route families affected by this roadmap:

- `/auth`, `/users`
- `/universities` through `/sections`
- `/students`, `/enrollments`
- `/subjects`, `/course-offerings`, `/timetables`
- `/assignments`, `/submissions`, `/evaluations`
- `/analytics`
- `/admin/*`

## Workflow

### Phase order after documentation

1. remove or archive confirmed dead modules
2. restore root docs and runtime-matrix health
3. restore or redefine the canonical workbook source for master hierarchy import
4. finish classes-to-sections cleanup without breaking compatibility paths
5. normalize generated outputs and ignore rules
6. rebuild export workbook from canonical docs

### Immediate execution priorities

- fix root documentation so validation scripts pass
- resolve missing `exports/Master_copy.xlsx`
- keep section compatibility bridge intact while refactors continue

## Dependencies

- [README.md](D:/VS%20CODE/MY%20PROJECT/CAPS_AI/README.md)
- [docs/roadmap/HARD_BLOCKER_FIX_PLAN.md](D:/VS%20CODE/MY%20PROJECT/CAPS_AI/docs/roadmap/HARD_BLOCKER_FIX_PLAN.md)
- [docs/roadmap/CLASSES_TO_SECTIONS_MIGRATION_PLAN.md](D:/VS%20CODE/MY%20PROJECT/CAPS_AI/docs/roadmap/CLASSES_TO_SECTIONS_MIGRATION_PLAN.md)
- CI workflow in `.github/workflows/ci.yml`
