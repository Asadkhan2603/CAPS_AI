# Master Hierarchy Field Contract

## Source Of Truth

`exports/Master_copy.xlsx` is the source of truth for CAPS AI master hierarchy data only:

- University
- Faculty
- Department
- Program
- Specialization

Operational entities such as batches, semesters, sections, groups, course offerings, classes, staff assignments, and student academic mappings remain app-managed.

## Canonical Collections

### `universities`
- `university_id`
- `university_name`

### `faculties`
- `faculty_id`
- `faculty_code`
- `faculty_name`
- `university_id`

### `departments`
- `department_id`
- `department_code`
- `department_name`
- `faculty_id`

### `programs`
- `program_id`
- `program_code`
- `program_name`
- `department_id`
- `duration_years`
- `total_semesters`
- `degree_type`

### `specializations`
- `specialization_id`
- `specialization_code`
- `specialization_name`
- `program_id`

## Compatibility Aliases

Legacy aliases are still exposed where older callers depend on them, but new logic must use canonical fields first.

- Faculties:
  - `faculty_name` -> `name`
  - `faculty_code` -> `code`
- Departments:
  - `department_name` -> `name`
  - `department_code` -> `code`
- Programs:
  - `program_name` -> `name`
  - `program_code` -> `code`
- Specializations:
  - `specialization_name` -> `name`
  - `specialization_code` -> `code`

These aliases are compatibility shims, not separate business fields.

## Uniqueness Model

CAPS AI treats workbook business IDs as globally unique canonical identifiers:

- `university_id`
- `faculty_id`
- `department_id`
- `program_id`
- `specialization_id`

Codes and names follow the workbook lineage model:

- `faculty_code` is globally unique
- `department_code` is unique within a faculty
- `program_code` is unique within a department
- `specialization_code` is unique within a program
- `faculty_name` is unique within a university
- `department_name` is unique within a faculty
- `program_name` is unique within a department
- `specialization_name` is unique within a program

This scoped uniqueness is intentional because the workbook legitimately reuses some short codes across different branches.

## Relationship Contract

Master hierarchy:

`University -> Faculty -> Department -> Program -> optional Specialization`

Operational hierarchy:

`Program -> Batch -> Semester -> Section -> optional Group`

Optional specialization branch:

`Program -> Specialization -> Batch -> Semester -> Section -> optional Group`

## Mutation Rules

- A faculty must belong to an existing university.
- A department must belong to an existing faculty.
- A program must belong to an existing department.
- A specialization must belong to an existing program.
- Denormalized lineage fields are derived from parents and must not be edited independently.
- Unsafe re-parenting is rejected when active descendants or dependent operational records exist.
