# Academic Module Master

## Module Overview
This section provides a standardized summary for the module. Refer to the detailed sections below for full context.

## Responsibilities
- Core responsibilities are described in the detailed sections below.

## Components
- Primary backend endpoints, schemas, and UI surfaces are listed below.

## API Endpoints
- Refer to the API endpoint inventory in this document.

## Data Models
- Refer to the data model details in this document.

## Workflows
- Refer to the workflow and lifecycle sections below.

## Dependencies
- Refer to dependency notes in this document.

## Known Limitations
- Refer to current limitations described below.

## Improvements
- Refer to improvement opportunities listed below.


## Module Tree

```text
Academic Module
|-- Canonical Hierarchy
|   |-- Faculty
|   |-- Department
|   |-- Program
|   |-- Specialization
|   |-- Batch
|   |-- Semester
|   `-- Section
|-- Legacy Compatibility
|   |-- Branch
|   |-- Course
|   |-- Year
|   `-- Class naming compatibility
`-- Cross-Cutting Controls
    |-- Permissions
    |-- Governance delete gates
    |-- Soft delete semantics
    `-- Validation and telemetry
```

## Internal Entity And Flow Tree

```text
Faculty
`-- Department
    `-- Program
        `-- Specialization
            `-- Batch
                `-- Semester
                    `-- Section

Legacy compatibility path:
Department -> Branch -> Course -> Year -> Section/Class
```

Source of truth: `docs/ACADEMIC_SETUP_LOGIC_AUDIT.md`

This document is the operational reference for the Academic Module in CAPS AI. It documents the module as it exists in the current codebase, not as a theoretical future design.

## 1. Module Overview

The Academic Module is the structural core of the university system. It defines how the institution's academic organization is modeled, validated, exposed in the backend, and operated in the frontend.

Its primary role is to provide the canonical academic hierarchy that all downstream academic workflows depend on, including:

- section creation
- enrollment alignment
- subject and timetable attachment
- academic duration planning
- semester derivation
- teacher-scoped class access
- administrative governance for setup changes

In the current platform, the Academic Module is not just a set of CRUD pages. It already contains real academic business rules, particularly around:

- program duration
- semester generation
- batch structure
- section integrity
- teacher visibility boundaries

The system now explicitly adopts one canonical academic model:

`Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`

At the same time, the codebase still contains legacy compatibility entities:

- `Course`
- `Year`
- `Branch`

These remain operational, but they are no longer the primary hierarchy for the platform.

## 2. Academic Hierarchy

### Canonical Hierarchy

The currently adopted hierarchy is:

1. Faculty
2. Department
3. Program
4. Specialization
5. Batch
6. Semester
7. Section (stored in backend collection `classes`)

### Relationship Model

#### Faculty

Faculty is the top-level academic grouping. It represents the broad institutional academic division.

Examples:

- Faculty of Engineering
- Faculty of Commerce
- Faculty of Arts

#### Department

Department belongs to a Faculty.

Relationship:

- one faculty can contain many departments
- one department belongs to at most one faculty

#### Program

Program belongs to a Department.

Relationship:

- one department can contain many programs
- one program belongs to one department

Program is the most important rule-bearing entity in the module because it defines:

- `duration_years`
- `total_semesters`

#### Specialization

Specialization belongs to a Program.

Relationship:

- one program can contain many specializations
- one specialization belongs to one program

This entity refines the academic track within a program.

#### Batch

Batch belongs to a Program and may optionally belong to a Specialization.

Relationship:

- one program can contain many batches
- one specialization can be associated with many batches
- one batch belongs to one program
- one batch may optionally reference one specialization

Batch is the operational cohort entity. It materializes the duration defined by the program into actual semester rows.

#### Semester

Semester belongs to a Batch.

Relationship:

- one batch can contain many semesters
- one semester belongs to one batch

Semester count is derived from Program duration through Batch creation and Program duration updates.

#### Section

Section is the bottom node of the canonical hierarchy.

In the backend it is stored in collection `classes` and exposed through:

- canonical route: `/sections`
- storage collection: `classes` (no `/classes` route)

Section can reference:

- faculty
- department
- program
- specialization
- batch
- semester

Section is where operational teaching, teacher assignment, enrollment linkage, and timetable usage typically converge.

### Legacy Compatibility Hierarchy

The repository also still contains a second, older hierarchy:

`Course -> Year -> Section`

And a side relation:

`Department -> Branch`

These models still exist in code and data contracts, but they are no longer the preferred academic structure.

## 3. Database Collections

The Academic Module currently uses the following collections.

### `faculties`

Purpose:

- stores top-level academic divisions

Key fields:

- `_id`
- `name`
- `code`
- `university_name`
- `university_code`
- `is_active`
- `deleted_at`
- `deleted_by`
- `created_at`

Relations:

- referenced by `departments.faculty_id`

Unique constraints:

- faculty `code` must be unique

### `departments`

Purpose:

- stores departments under faculties

Key fields:

- `_id`
- `name`
- `code`
- `faculty_id`
- `university_name`
- `university_code`
- `is_active`
- `deleted_at`
- `deleted_by`
- `created_at`

Relations:

- belongs to `faculties` by `faculty_id`
- referenced by `programs.department_id`
- legacy `branches` denormalize department data from this entity

Unique constraints:

- department `code` must be unique

### `programs`

Purpose:

- stores academic programs under departments
- acts as the configuration source for duration and semester count

Key fields:

- `_id`
- `name`
- `code`
- `department_id`
- `duration_years`
- `total_semesters`
- `description`
- `is_active`
- `deleted_at`
- `deleted_by`
- `created_at`

Relations:

- belongs to `departments` by `department_id`
- referenced by `specializations.program_id`
- referenced by `batches.program_id`
- referenced by `classes.program_id`

Unique constraints:

- program `code` must be unique

### `specializations`

Purpose:

- stores specialized tracks under programs

Key fields:

- `_id`
- `name`
- `code`
- `program_id`
- `description`
- `is_active`
- `deleted_at`
- `deleted_by`
- `created_at`

Relations:

- belongs to `programs` by `program_id`
- referenced by `batches.specialization_id`
- referenced by `classes.specialization_id`

Unique constraints:

- specialization `code` must be unique

### `batches`

Purpose:

- stores academic cohorts for a program
- materializes program duration into actual semesters

Key fields:

- `_id`
- `program_id`
- `specialization_id`
- `name`
- `code`
- `start_year`
- `end_year`
- `is_active`
- `deleted_at`
- `deleted_by`
- `created_at`

Relations:

- belongs to `programs` by `program_id`
- may belong to `specializations` by `specialization_id`
- referenced by `semesters.batch_id`
- referenced by `classes.batch_id`

Unique constraints:

- batch `code` is currently enforced within the same `program_id` + `specialization_id` scope

### `semesters`

Purpose:

- stores semester rows under a batch

Key fields:

- `_id`
- `batch_id`
- `semester_number`
- `label`
- `is_active`
- `deleted_at`
- `deleted_by`
- `created_at`

Relations:

- belongs to `batches` by `batch_id`
- referenced by `classes.semester_id`

Unique constraints:

- uniqueness of `(batch_id, semester_number)`

### `classes`

Purpose:

- stores sections or classes
- acts as the operational bottom node of the academic structure

Key fields:

- `_id`
- `name`
- `faculty_id`
- `department_id`
- `program_id`
- `specialization_id`
- `batch_id`
- `semester_id`
- `course_id`
- `year_id`
- `faculty_name`
- `branch_name`
- `class_coordinator_user_id`
- `is_active`
- `deleted_at`
- `deleted_by`
- `created_at`

Relations:

- canonical relations to faculty, department, program, specialization, batch, semester
- legacy compatibility relations to course and year
- teacher scope via `class_coordinator_user_id`

Unique constraints:

- no explicit uniqueness guarantee is documented in the audit for section naming

### `courses`

Purpose:

- legacy academic entity used in the older hierarchy

Key fields:

- `_id`
- `name`
- `code`
- `description`
- `is_active`
- `deleted_at`
- `deleted_by`
- `created_at`

Relations:

- referenced by `years.course_id`
- may be referenced by `classes.course_id`

Unique constraints:

- course `code` must be unique

### `years`

Purpose:

- legacy academic year entity under course

Key fields:

- `_id`
- `course_id`
- `year_number`
- `label`
- `is_active`
- `deleted_at`
- `deleted_by`
- `created_at`

Relations:

- belongs to `courses` by `course_id`
- may be referenced by `classes.year_id`

Unique constraints:

- uniqueness of `(course_id, year_number)`

### `branches`

Purpose:

- legacy academic branch entity
- kept as compatibility structure connected to department

Key fields:

- `_id`
- `name`
- `code`
- `department_code`
- `department_name`
- `university_name`
- `university_code`
- `is_active`
- `deleted_at`
- `deleted_by`
- `created_at`

Relations:

- belongs to department by `department_code`, not `department_id`
- denormalizes department and university metadata

Unique constraints:

- branch `code` must be unique

## 4. Backend Logic Implemented

### Program Duration Rules

Programs contain the academic duration rule engine.

Implemented logic:

- validates minimum duration
- validates maximum duration
- computes `total_semesters`
- blocks duration changes when students already exist in dependent semesters
- triggers semester synchronization when duration changes

This makes Program the true source of truth for academic duration.

### Semester Auto Generation

Semester rows are generated automatically in two places:

- when a Batch is created
- when a Program duration change requires synchronization

Implemented behaviors:

- create missing semesters
- reactivate required inactive semesters
- archive semesters that exceed the new configured total

### Batch Creation Logic

Batch creation is not free-form.

The backend performs:

- program validation
- specialization validation
- specialization ownership validation against program
- year range derivation or validation
- semester generation based on program duration
- program creation also auto-seeds base program batches from `2022` through the current year

This means batch creation operationalizes academic structure rather than only saving a row.

### Semester Uniqueness

Semesters are unique by:

- `batch_id`
- `semester_number`

The backend rejects duplicates inside the same batch.

### Cross-Entity Validation

Sections are strongly validated. The backend checks:

- department belongs to faculty
- program belongs to department
- specialization belongs to program
- year belongs to course
- semester belongs to batch

This prevents invalid cross-tree data attachment.

### Teacher Scoped Class Access

Teachers do not get broad access to all sections.

Implemented behavior:

- teacher list access is filtered by `class_coordinator_user_id`
- teacher single-record access is denied if the section is not assigned to the logged-in teacher

This is real data scoping logic, not only frontend hiding.

### Governance-Gated Destructive Actions

Protected delete flows currently exist for:

- departments
- branches
- years
- courses
- classes or sections

Governance flow behavior:

- backend can require an approved `review_id`
- the two-person rule can block destructive actions
- approved reviews are executed and tracked
- missing or invalid governance review blocks the delete

### Destructive Action Telemetry

The module now emits structured telemetry for destructive operations.

Tracked dimensions include:

- actor user id
- entity type
- entity id
- action
- stage
- whether `review_id` was supplied
- whether governance completed

Telemetry stages include:

- `requested`
- `completed`
- `governance_blocked`
- `governance_completed`

## 5. Business Rules

### Program Rules

- `duration_years` must be between 3 and 5
- if `duration_years < 3`, reject with:
  `Course duration must be at least 3 years.`
- if `duration_years > 5`, reject with:
  `Course duration cannot exceed 5 years.`
- `total_semesters = duration_years * 2`

Examples:

- 3 years -> 6 semesters
- 4 years -> 8 semesters
- 5 years -> 10 semesters

### Program Change Protection

- program duration cannot be changed if students are already enrolled in existing semesters for that program

### Batch Rules

- batch must belong to a valid program
- specialization, if supplied, must belong to the selected program
- if only `start_year` is given, `end_year` is auto-derived as the pass-out year
- if only `end_year` is given, `start_year` is auto-derived from the pass-out year
- if both are given, the span must match program duration
- for a 4-year program, `2022 -> 2026` is valid batch notation

### Semester Rules

- semester number must be unique within a batch
- batch must exist before semester creation

### Section Rules

- faculty, department, program, specialization, batch, semester ownership must be consistent
- invalid cross-entity combinations are rejected
- teacher visibility is constrained to assigned classes

### Delete Rules

- soft delete is canonical
- canonical delete fields are:
  - `is_active = false`
  - `deleted_at`
  - `deleted_by`
- some entities require governance review depending on policy

## 6. API Endpoints

Academic routes are mounted under the API router. The operational surface is:

### Canonical Endpoints

#### `/faculties`

Operations:

- `GET /faculties`
- `GET /faculties/{faculty_id}`
- `POST /faculties`
- `PUT /faculties/{faculty_id}`
- `DELETE /faculties/{faculty_id}`

#### `/departments`

Operations:

- `GET /departments`
- `GET /departments/{department_id}`
- `POST /departments`
- `PUT /departments/{department_id}`
- `DELETE /departments/{department_id}`

#### `/programs`

Operations:

- `GET /programs`
- `GET /programs/{program_id}`
- `POST /programs`
- `PUT /programs/{program_id}`
- `DELETE /programs/{program_id}`

Important behavior:

- `POST /programs` now auto-creates base batches from `2022` through the current year for that program
- `POST /programs/seed-batches` backfills missing base batches for existing active programs

#### `/specializations`

Operations:

- `GET /specializations`
- `GET /specializations/{specialization_id}`
- `POST /specializations`
- `PUT /specializations/{specialization_id}`
- `DELETE /specializations/{specialization_id}`

#### `/batches`

Operations:

- `GET /batches`
- `GET /batches/{batch_id}`
- `POST /batches`
- `PUT /batches/{batch_id}`
- `DELETE /batches/{batch_id}`

#### `/semesters`

Operations:

- `GET /semesters`
- `GET /semesters/{semester_id}`
- `POST /semesters`
- `PUT /semesters/{semester_id}`
- `DELETE /semesters/{semester_id}`

#### `/sections`

Canonical route for sections. Section records are stored in the legacy-named `classes` collection, but there is no `/classes` backend route.

Operations:

- `GET /sections`
- `GET /sections/{section_id}`
- `POST /sections`
- `PUT /sections/{section_id}`
- `DELETE /sections/{section_id}`

### Legacy Compatibility Endpoints

Legacy academic routes are no longer mounted in the backend:

- `/courses` -> frontend redirect to `/programs`
- `/years` -> frontend redirect to `/batches`
- `/branches` -> frontend redirect to `/specializations`

### API Status Notes

- `/sections` is canonical
- `/classes` is not mounted (storage-only legacy name)
- `/courses`, `/years`, and `/branches` are retired routes with frontend redirects only

## 7. Frontend Implementation

The frontend uses two major patterns:

- generic CRUD pages built on `EntityManager`, now using header icons plus overlay-based search and create or edit flows
- custom academic hierarchy and class pages

### Page Coverage

| Page | Create | Edit | Delete | Notes |
|---|---|---|---|---|
| `FacultiesPage.jsx` | Yes | Yes | Yes | one of the most complete pages |
| `DepartmentsPage.jsx` | Yes | Yes | Yes | exposes university metadata |
| `ProgramsPage.jsx` | Yes | Yes | Yes | includes duration logic awareness and base batch auto-seeding |
| `SpecializationsPage.jsx` | Yes | No | Yes | backend update exists, UI edit missing |
| `BatchesPage.jsx` | Yes | Yes | Yes | specialization filtered by program; base batches are auto-seeded from program create, can be backfilled from the page, and now support active-state edit |
| `SemestersPage.jsx` | Yes | No | Yes | backend update exists |
| `ClassesPage.jsx` | Yes | Partial/custom | Partial/custom | custom cascading form, not a standard EntityManager page |
| Legacy `/courses` | - | - | - | frontend redirect only; no dedicated page |
| Legacy `/years` | - | - | - | frontend redirect only; no dedicated page |
| Legacy `/branches` | - | - | - | frontend redirect only; no dedicated page |

### Academic Structure Pages

#### `AdminAcademicStructurePage.jsx`

Purpose:

- acts as a navigation launcher
- separates canonical setup modules from legacy compatibility modules

#### `AcademicStructurePage.jsx`

Purpose:

- renders the lazy drill-down academic hierarchy

Implemented behavior:

- starts at faculties
- loads children on expansion
- supports expand and collapse
- supports animation
- supports search over loaded nodes
- supports super-admin in-tree edit

Included in tree:

- faculties
- departments
- programs
- specializations
- batches
- semesters
- sections

Excluded from tree:

- courses
- years
- branches

This confirms the frontend hierarchy aligns to the canonical model, not the legacy model.

## 8. Frontend vs Backend Gaps

Several capabilities already exist in backend but are not fully exposed in frontend.

### Backend Supports Update, UI Does Not

- `specializations` update exists, but page edit is missing
- `semesters` update exists, but page edit is missing
- `years` update exists, but page edit is missing
- `branches` update exists, but page edit is missing
- `courses` full CRUD exists, but page is effectively read-only

### Backend Fields Exist, UI Uses Only Part

- sections support `course_id` and `year_id`, but the canonical setup UI does not expose them
- sections support `faculty_name` and `branch_name`, but naming usage is inconsistent
- batches are auto-seeded by program, but the batch page still keeps a manual create form for exceptional cases

### Governance UI Coverage Is Partial

- shared `EntityManager` pages can pass `review_id`
- custom delete UIs still need the same governance flow wiring
- `ClassesPage.jsx` is still a gap here

### Scope Enforcement Gap

- UI permission exposure is aligned better than before
- backend still lacks true row-level scope enforcement for `department_admin`

## 9. Bugs Identified

This section documents audit-identified defects and operational inconsistencies. Some have already been hardened in code, but they remain important for module history and regression awareness.

### Unreachable Code In `departments.py`

The audit identified unreachable validation code in the department delete flow. This was a maintainability bug because intended validation logic was positioned after a terminal return path.

Current status:

- identified during hardening
- fixed by moving validation to the proper update path
- should remain documented because the safety pipeline now explicitly guards against similar issues

### Permission Mismatch

The module previously mixed:

- granular entity permissions in the registry
- blanket `academic:manage` in route handlers

This created policy drift.

Current status:

- academic setup routes now use entity-level permissions
- remaining risk is row-level scope, not permission-key naming

### Governance Delete Without `review_id`

The audit identified that governance-protected destructive operations could fail at runtime if UI flows did not pass `review_id`.

Current status:

- shared CRUD UI can now prompt for and pass `review_id`
- custom delete UIs still require explicit wiring

### Denormalized Branch Relations

Branches still attach to departments via `department_code`, not `department_id`.

Impact:

- weaker relational integrity
- extra propagation logic on department updates
- higher risk of drift than id-based relations

## 10. Architectural Issues

### Dual Academic Model Conflict

The repository still carries two overlapping models.

#### Canonical Model

`Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`

#### Legacy Compatibility Model

`Department -> Branch -> Course -> Year -> Section`

This creates ambiguity in:

- section identity
- cohort modeling
- subject allocation
- enrollment semantics
- timetable integration
- reporting consistency

### Why This Is a Real Architectural Problem

The issue is not that the module lacks logic. The issue is that logic exists in two different structural interpretations:

- one modern id-based hierarchy
- one older compatibility chain

As long as both remain alive, the system has to answer difficult questions repeatedly:

- which hierarchy is authoritative for section creation
- whether course/year should still matter once program/batch/semester already exists
- whether branch should continue as a first-class academic setup entity

## 11. Cleanup Strategy

### Canonical Direction

Keep the canonical structure as:

`Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`

### Legacy Entities

Treat the following as legacy compatibility modules unless a strong business case re-promotes them:

- `courses`
- `years`
- `branches`
- `classes` as a storage-only legacy collection name

### Simplification Strategy

#### Phase 1: Make the Canonical Model Explicit Everywhere

- keep documentation aligned with the canonical hierarchy
- keep `/sections` as the primary section route
- treat legacy routes as retired, with frontend redirects only

#### Phase 2: Remove UI Ambiguity

- do not present legacy entities as co-equal academic roots
- keep them clearly labeled as compatibility or migration modules

#### Phase 3: Reduce Dual References In Sections

- minimize operational dependence on `course_id` and `year_id`
- prefer faculty/department/program/specialization/batch/semester in new flows

#### Phase 4: Normalize Relations

- replace branch-to-department code linkage with id-based linkage if branch remains
- remove denormalized propagation requirements where possible

#### Phase 5: Finish Governance And Scope Hardening

- complete review-aware delete flow in custom pages
- add row-level scope enforcement for `department_admin`

#### Phase 6: Close UI/Backend Exposure Gaps

- expose edit only where intended
- hide unsupported fields intentionally
- document any backend-only fields explicitly

## 12. Testing Requirements

The Academic Module needs both business-rule tests and architecture-safety tests.

### Required Backend Unit Tests

- program duration lower bound validation
- program duration upper bound validation
- `total_semesters` derivation
- batch creation auto-generates semesters
- semester uniqueness within a batch
- specialization must belong to selected program
- department must belong to selected faculty
- program must belong to selected department
- specialization must belong to selected program for section creation
- semester must belong to selected batch
- year must belong to selected course in legacy flows
- teacher scoped class access behavior

### Required Governance Tests

- delete blocked when governance requires `review_id`
- delete proceeds when approved review exists
- governance review cannot be self-approved
- governance completion emits telemetry
- destructive action request and completion emit telemetry

### Required Permission Tests

- entity-level route permissions enforce correct admin types
- `department_admin` can use lower-hierarchy canonical routes where intended
- `department_admin` is denied for central setup entities where intended
- UI feature-access configuration matches backend permission expectations

### Required Integration Tests

- program duration update synchronizes dependent semesters
- batch creation persists batch and semester rows consistently
- section creation rejects invalid cross-entity ownership
- admin recovery restores archived academic entities correctly
- governance-gated delete flow works from frontend request format

### Required Static Safety Checks

- unreachable code detection
- delete endpoint governance contract checks
- linting on safety-critical module paths
- typing checks on governance-sensitive delete flows

### Existing Test Assets Already In Repo

- `backend/tests/test_academic_setup_rules.py`
- `backend/tests/test_departments.py`
- `backend/tests/test_academic_permissions.py`
- `backend/tests/test_destructive_action_telemetry.py`
- `frontend/src/utils/permissions.test.js`

## Final Summary

The Academic Module already has substantial implemented logic. Its strongest current design line is:

- program defines duration
- duration defines total semesters
- batch creation materializes semesters
- section creation validates cross-entity ownership

The main problem is not missing logic. The main problem is coexistence of:

- a strong canonical hierarchy
- legacy compatibility entities
- frontend exposure that does not fully match backend capability
- partial governance and scope wiring in some UI areas

The right direction is consolidation, not reinvention.
