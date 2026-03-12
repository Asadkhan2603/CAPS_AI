# CLASS / SECTION MODULE MASTER

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
Class / Section Module
|-- Canonical Sections API
|-- Legacy Classes Alias
|-- Coordinator Assignment
|-- Section Archive Flow
`-- Cross-Entity Lineage Validation
```

## Internal Entity And Flow Tree

```text
Section record
|-- Canonical academic linkage
|-- Legacy compatibility linkage
`-- Coordinator and student-facing references
```

## 1. Module Overview

The class/section module is the operational academic container for a teachable student cohort. In the current CAPS AI codebase, the canonical business concept is `Section`, but the underlying implementation still uses legacy `Class` naming in several backend and frontend files.

This module therefore sits at the fault line between:

- the canonical academic hierarchy:
  - `Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`
- the legacy implementation naming:
  - `classes`
  - `ClassCreate`
  - `ClassOut`
  - `ClassesPage.jsx`

The route layer makes the architectural intent explicit:

- `/sections` is canonical
- `/classes` is not mounted and remains a legacy name only

Operationally, this module is important because sections/classes are referenced by:

- enrollments
- class slots
- attendance records
- course offerings
- timetable consumers
- teacher section analytics

## 2. Canonical vs Legacy Model

### 2.1 Canonical model

The canonical model is:

- `Section`

A section belongs to:

- faculty
- department
- program
- specialization
- batch
- semester

and may have:

- `class_coordinator_user_id`

### 2.2 Legacy naming still in use

The actual implementation still uses:

- backend file: [classes.py](/backend/app/api/v1/endpoints/classes.py)
- schema file: [class_item.py](/backend/app/schemas/class_item.py)
- model serializer: [classes.py](/backend/app/models/classes.py)
- frontend page: [ClassesPage.jsx](/frontend/src/pages/ClassesPage.jsx)

The router maps this legacy implementation to:

- canonical route: `/sections`

The backend no longer exposes a `/classes` route, but the naming debt remains in storage and code.

## 3. Database Collection

### 3.1 `classes`

Purpose:

- stores the canonical section record, despite the legacy collection name

Key fields:

- `_id`
- `faculty_id`
- `department_id`
- `program_id`
- `specialization_id`
- `course_id`
- `year_id`
- `batch_id`
- `semester_id`
- `name`
- `faculty_name`
- `branch_name`
- `class_coordinator_user_id`
- `is_active`
- `deleted_at`
- `deleted_by`
- `created_at`

Relations:

- `faculty_id -> faculties._id`
- `department_id -> departments._id`
- `program_id -> programs._id`
- `specialization_id -> specializations._id`
- `course_id -> courses._id` (legacy compatibility)
- `year_id -> years._id` (legacy compatibility)
- `batch_id -> batches._id`
- `semester_id -> semesters._id`
- `class_coordinator_user_id -> users._id`

Important semantic note:

- `course_id` and `year_id` are legacy linkage fields
- `batch_id` and `semester_id` are canonical linkage fields

This means the collection currently supports both academic models at once.

### 3.2 Denormalized display fields

The record also stores:

- `faculty_name`
- `branch_name`

These are display-oriented denormalized fields.

Important issue:

- `branch_name` is currently being populated from program name in the frontend section create flow, which is semantically wrong

## 4. Backend Logic Implemented

Primary backend file:

- [classes.py](/backend/app/api/v1/endpoints/classes.py)

### 4.1 Routing model

The router implementation is mounted once:

- `/sections` as canonical endpoint

There is no `/classes` backend route. This is defined in [router.py](/backend/app/api/v1/router.py).

### 4.2 Section/class list

Endpoint:

- `GET /sections/`

Behavior:

- roles allowed:
  - `admin`
  - `teacher`
- supports filters:
  - `faculty_id`
  - `department_id`
  - `program_id`
  - `specialization_id`
  - `course_id`
  - `year_id`
  - `batch_id`
  - `semester_id`
  - `faculty_name`
  - `branch_name`
  - text query `q`
  - `is_active`
  - `skip`
  - `limit`

Teacher-specific scope:

- teachers only see rows where:
  - `class_coordinator_user_id == current_user._id`
- teachers are additionally forced to:
  - `is_active = true`

This is a strict coordinator-scoped read model.

### 4.3 Get single section/class

Endpoint:

- `GET /sections/{class_id}`

Behavior:

- admin can read any row
- teacher can read only if they are the class coordinator

### 4.4 Create section/class

Endpoint:

- `POST /sections/`

Permission:

- `sections.manage`

Validation implemented:

- if `faculty_id` provided:
  - faculty must exist
- if `department_id` provided:
  - department must exist
  - if faculty present, department must belong to faculty
- if `program_id` provided:
  - program must exist
  - if department present, program must belong to department
- if `specialization_id` provided:
  - specialization must exist
  - if program present, specialization must belong to program
- if `course_id` provided:
  - course must exist
- if `year_id` provided:
  - year must exist
  - if course present, year must belong to course
- if `batch_id` provided:
  - batch must exist
- if `semester_id` provided:
  - semester must exist
  - if batch present, semester must belong to batch

Persisted create state:

- section starts active
- `created_at` is stored

### 4.5 Update section/class

Endpoint:

- `PUT /sections/{class_id}`

Permission:

- `sections.manage`

Validation implemented:

- same cross-entity ownership validation as create
- validates updated target lineage against current stored lineage
- applies state update through shared helper

Important note:

- this backend update capability exists
- current main frontend page does not expose general edit

### 4.6 Delete / archive section/class

Endpoint:

- `DELETE /sections/{class_id}`

Permission:

- `sections.manage`

Governance:

- delete is governance-gated through:
  - `enforce_review_approval(...)`
- accepts:
  - `review_id`

Behavior:

- logs destructive action telemetry at request stage
- enforces governance approval when required
- soft-archives the record using canonical soft-delete helpers
- logs completion telemetry

This is an archive flow, not a hard delete.

## 5. Schemas and Public Contract

Schema file:

- [class_item.py](/backend/app/schemas/class_item.py)

Exposed create/update fields:

- `faculty_id`
- `department_id`
- `program_id`
- `specialization_id`
- `course_id`
- `year_id`
- `batch_id`
- `semester_id`
- `name`
- `faculty_name`
- `branch_name`
- `class_coordinator_user_id`

Output fields:

- all linkage ids
- `name`
- `faculty_name`
- `branch_name`
- `class_coordinator_user_id`
- `is_active`
- `deleted_at`
- `deleted_by`
- `created_at`

Important contract issue:

- there is no separate `section_code`
- the module treats section identity mainly as a freeform `name`

## 6. Frontend Implementation

Primary page:

- [ClassesPage.jsx](/frontend/src/pages/ClassesPage.jsx)

Service wrapper:

- [sectionsApi.js](/frontend/src/services/sectionsApi.js)

Route wiring:

- `/sections` renders `ClassesPage.jsx`

### 6.1 What the page actually does

Despite its filename, the page is the canonical sections UI.

Implemented behavior:

- loads faculties, departments, programs, specializations, batches, semesters
- loads teacher list when admin
- filters section list by canonical hierarchy
- creates section through `/sections/`
- lists section records in a table

### 6.2 Create support

Create form exposes:

- faculty
- department
- program
- specialization
- batch
- semester
- section name
- coordinator

This is aligned with the canonical academic hierarchy.

### 6.3 Read/list support

List columns shown:

- section
- faculty
- department
- program
- specialization
- batch
- semester
- coordinator

### 6.4 Missing edit/delete support

The page currently does not expose:

- section edit
- section archive/delete

This is a major frontend/backend gap because backend fully supports both.

### 6.5 Role behavior in UI

Feature access config allows:

- `admin`
- `teacher`

But page behavior is inconsistent:

- create form is shown only to admin
- teachers can access the page and list sections
- list results for teachers are constrained by backend coordinator scope

This means teachers have a read surface but no create/update UI, even though backend permissioning is based on `sections.manage`.

## 7. Business Rules

### 7.1 Canonical ownership rules

A section may belong to the canonical chain:

- faculty
- department
- program
- specialization
- batch
- semester

Cross-entity validation is enforced so the chain is internally consistent.

### 7.2 Legacy compatibility rules

A section may also still carry:

- `course_id`
- `year_id`

with validation:

- `year_id` must belong to `course_id`

This preserves old integrations, but creates dual-model complexity.

### 7.3 Teacher scope

Teachers are not global section viewers.

They can read only sections where:

- they are the class coordinator

### 7.4 Soft delete rules

Delete archives a section by flipping active state and writing delete metadata rather than removing the record.

### 7.5 Governance rules

Section delete is governance-aware:

- `review_id` may be required depending on governance configuration

## 8. Frontend vs Backend Gaps

### 8.1 Naming mismatch

Frontend route is canonical:

- `/sections`

But implementation names remain legacy:

- `ClassesPage.jsx`

This increases confusion for maintenance and onboarding.

### 8.2 Backend update/delete exists, frontend does not expose them

Backend supports:

- update
- governance-gated archive

Frontend page exposes:

- create
- list

only.

### 8.3 Legacy fields are hidden but still operational

Backend still supports:

- `course_id`
- `year_id`
- `faculty_name`
- `branch_name`

Frontend does not intentionally expose these as editable fields in the main sections page.

That is partly good because it favors the canonical model, but it also means the API contract is broader than the UI contract.

### 8.4 Wrong denormalized field mapping

The create flow sends:

- `branch_name: programNameById[form.program_id]`

This is logically wrong. Program name is not branch name.

## 9. Architectural Issues

### 9.1 Section and class are the same implementation

The system has not actually separated:

- canonical section concept
- legacy class concept

It exposes the same code under two routes.

### 9.2 Dual academic model still present

The same record can carry both:

- canonical chain:
  - `program_id -> specialization_id -> batch_id -> semester_id`
- legacy chain:
  - `course_id -> year_id`

This is the same architectural conflict described in the academic audit.

### 9.3 Collection name is legacy

Canonical sections are stored in:

- `classes`

This is not immediately wrong, but it keeps old semantics embedded in storage and code.

### 9.4 Section identity is weak

There is no dedicated section code or strongly normalized display identity. The record mainly relies on:

- `name`

This may be enough operationally, but it becomes weak for larger-scale administration.

## 10. Downstream Dependencies

The section/class record is used by or referenced from:

- `enrollments`
- `course_offerings`
- `class_slots`
- `attendance_records`
- teacher section analytics

Examples:

- `course_offerings.py` still queries `db.classes`
- analytics exposes teacher sections through:
  - `/analytics/teacher/sections`

This means section/class cleanup must be done carefully because many modules still depend on the legacy collection name.

## 11. Bugs and Risks Identified

### 11.1 Branch name misuse

Frontend create path derives `branch_name` from selected program name.

Risk:

- stored display metadata becomes semantically incorrect

### 11.2 UI permission ambiguity

Feature access allows teachers onto the sections page, but the page exposes no teacher mutation flow.

Risk:

- permission model and operator expectation drift

### 11.3 No DB uniqueness guard for section identity

No unique constraint is visible for combinations such as:

- `semester_id + name`
- `batch_id + semester_id + name`

Risk:

- duplicate section names within the same academic context

### 11.4 Legacy naming may keep old integrations alive indefinitely

Even without a `/classes` route, legacy naming in collections and client code can keep confusion alive unless explicitly addressed.

## 12. Cleanup Strategy

### 12.1 Keep `Section` as the canonical concept

Documentation, UI labels, API clients, and future features should use:

- `Section`

### 12.2 Do not reintroduce `/classes` routes

Make it explicit that new clients must use:

- `/sections`

### 12.3 Remove or quarantine legacy linkage fields

Phase out direct use of:

- `course_id`
- `year_id`
- `branch_name`

from canonical section creation and update flows.

### 12.4 Fix denormalized field mapping

Stop populating `branch_name` from program name in the frontend.

### 12.5 Add full section management UI

The page should eventually expose:

- edit
- governance-aware archive
- optional coordinator reassignment

### 12.6 Normalize filenames over time

Long term, rename:

- `classes.py` -> `sections.py`
- `class_item.py` -> `section.py`
- `ClassesPage.jsx` -> `SectionsPage.jsx`

This is not urgent if the routing and docs are clear, but the current naming debt is real.

## 13. Testing Requirements

### 13.1 Unit tests

- faculty/department lineage validation
- department/program lineage validation
- program/specialization lineage validation
- course/year lineage validation
- batch/semester lineage validation
- teacher read scope for coordinator-only access
- governance-gated delete requiring `review_id`

### 13.2 Integration tests

- canonical `/sections` create/list/get/update/archive flow
- teacher can list only coordinated sections
- admin can create and archive section

### 13.3 Frontend tests

- filter cascade behavior
- create payload correctness
- teacher read-only access behavior
- edit/delete absence documented or intentionally hidden

## 14. Current Module Assessment

The module works, but it is structurally transitional.

Strengths:

- canonical `/sections` route exists
- cross-entity ownership validation is implemented
- teacher coordinator scoping is enforced
- delete is governance-aware and soft-delete based

Weaknesses:

- implementation naming is still legacy
- canonical and legacy academic linkages coexist in one record
- frontend only covers create/list, not full lifecycle
- denormalized `branch_name` handling is logically wrong

As implemented today, this module is usable as the canonical section service, but it still carries the old class model inside it. The next step is not inventing new behavior; it is cleaning up naming, contract scope, and UI parity.

