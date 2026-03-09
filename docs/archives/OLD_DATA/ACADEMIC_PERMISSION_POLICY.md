# Academic Permission Policy

## Scope

This document defines the adopted permission model for the Academic Setup module.

The canonical academic structure remains:

`Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`

Legacy compatibility modules remain:

- `Course`
- `Year`
- `Branch`
- `/classes` as a legacy alias for `/sections`

## Permission Strategy

Read access remains role-based for academic setup listing and detail views:

- `admin`
- `teacher`

Write access now uses entity-level permissions instead of the blanket `academic:manage` permission.

## Admin Type Policy

### Central Academic Governance

These permissions are for central academic administrators:

- `faculties.manage`
- `departments.manage`
- `courses.manage`
- `years.manage`
- `branches.manage`

Allowed admin types:

- `super_admin`
- `admin`
- `academic_admin`

### Canonical Lower-Hierarchy Governance

These permissions are for canonical hierarchy entities managed below the department root:

- `programs.manage`
- `specializations.manage`
- `batches.manage`
- `semesters.manage`
- `sections.manage`

Allowed admin types:

- `super_admin`
- `admin`
- `academic_admin`
- `department_admin`

## Route Matrix

| Route | GET | POST | PUT | DELETE |
| --- | --- | --- | --- | --- |
| `/faculties` | `admin` or `teacher` | `faculties.manage` | `faculties.manage` | `faculties.manage` |
| `/departments` | `admin` or `teacher` | `departments.manage` | `departments.manage` | `departments.manage` |
| `/programs` | `admin` or `teacher` | `programs.manage` | `programs.manage` | `programs.manage` |
| `/specializations` | `admin` or `teacher` | `specializations.manage` | `specializations.manage` | `specializations.manage` |
| `/batches` | `admin` or `teacher` | `batches.manage` | `batches.manage` | `batches.manage` |
| `/semesters` | `admin` or `teacher` | `semesters.manage` | `semesters.manage` | `semesters.manage` |
| `/sections` | `admin` or `teacher` | `sections.manage` | `sections.manage` | `sections.manage` |
| `/classes` | `admin` or `teacher` | `sections.manage` | `sections.manage` | `sections.manage` |
| `/courses` | `admin` or `teacher` | `courses.manage` | `courses.manage` | `courses.manage` |
| `/years` | `admin` or `teacher` | `years.manage` | `years.manage` | `years.manage` |
| `/branches` | `admin` or `teacher` | `branches.manage` | `branches.manage` | `branches.manage` |

## Notes

- `academic:manage` is retained in the registry only for older non-migrated module paths.
- `programs.manage` now governs course-duration editing as well as program CRUD.
- The old program-specific error text about “super admin or department admin” is removed in favor of direct permission enforcement.
- This policy does not yet add department-level data scoping. A `department_admin` can still pass the permission gate globally unless further row-level scope checks are added.
