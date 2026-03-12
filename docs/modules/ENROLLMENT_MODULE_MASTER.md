# Enrollment Module Master

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
Enrollment Module
|-- Enrollment Records
|-- Student To Section Mapping
|-- Teacher-Scoped Enrollment Authority
`-- Student Academic Membership Views
```

## Internal Entity And Flow Tree

```text
Student
`-- Enrollment
    `-- Section membership
        `-- Attendance, timetable, and offering visibility
```

## 1. Module Overview

The Enrollment module is the control point that assigns students to academic sections. In the current CAPS AI implementation, it is the operational bridge between:

- student master records
- academic section ownership
- teacher-managed section access
- downstream student experiences such as timetable visibility and section-scoped academic flows

This module does not define the academic hierarchy itself. That responsibility belongs to the Academic module. Instead, Enrollment binds a student to a concrete teaching unit, represented in the current codebase as a `class_id` pointing to the `classes` collection.

That design matters because several downstream workflows rely on section membership:

- student dashboards
- student timetable visibility
- teacher roster access
- attendance-adjacent section operations
- section-scoped teaching workflows

At present, the Enrollment module is intentionally narrow. It supports:

- listing enrollments
- creating enrollments
- teacher-scoped access for selected teaching roles

It does not currently support:

- enrollment update
- unenrollment
- enrollment archival
- governance-gated destructive review flow

## 2. Position in Academic Architecture

### Canonical intent

The project’s canonical academic hierarchy has been standardized as:

- Faculty
- Department
- Program
- Specialization
- Batch
- Semester
- Section

In that target model, enrollment should bind a student to a canonical Section.

### Current implementation reality

The current implementation still uses `classes` and `class_id` as the enrollment anchor. Functionally, this behaves as the section membership layer, but structurally it is part of the legacy academic path.

Current enrollment path:

- Student
- Class/Section (`class_id` in `classes`)
- Teacher or Admin management scope

This creates an architectural mismatch:

- canonical docs talk about `Section`
- enrollment code still works through `classes`

The module is therefore operationally valid, but not yet fully aligned with the canonical academic naming model.

## 3. Database Collection

### Primary collection: `enrollments`

The module centers on the `enrollments` collection.

Purpose:

- record which student is assigned to which academic class/section
- preserve who performed the assignment
- retain a denormalized roll number for operational lookup

Core fields currently exposed by schema/model:

- `id`
- `class_id`
- `student_id`
- `student_roll_number`
- `assigned_by_user_id`
- `created_at`

### Field semantics

#### `class_id`

References the academic delivery unit in the `classes` collection. In practical usage this behaves like section assignment, even though the collection name is legacy.

#### `student_id`

References the student master record in `students`.

#### `student_roll_number`

Stored as denormalized student identity data. This supports operational lookup and user-facing display without re-resolving the student on every access.

#### `assigned_by_user_id`

Tracks the actor who created the enrollment. This is important because enrollment is a privileged action limited to admins and eligible teachers.

#### `created_at`

Creation timestamp for traceability.

## 4. Relations

The enrollment module depends on three main entity relationships.

### Student relation

- `enrollments.student_id` -> `students._id`

Students may be resolved at input time by:

- Mongo ObjectId
- roll number

The API normalizes that to canonical `student_id` storage.

### Academic delivery relation

- `enrollments.class_id` -> `classes._id`

This is the current section membership anchor.

### Actor relation

- `enrollments.assigned_by_user_id` -> `users._id`

This records which authenticated actor assigned the student.

## 5. Backend Logic Implemented

Backend implementation is in:

- [enrollments.py](/backend/app/api/v1/endpoints/enrollments.py)
- [enrollment.py](/backend/app/schemas/enrollment.py)
- [enrollments.py](/backend/app/models/enrollments.py)

### 5.1 Supported operations

Implemented operations:

- list enrollments
- create enrollment

Not implemented:

- update enrollment
- delete enrollment
- archive enrollment
- recover enrollment

### 5.2 Student identifier resolution

The backend resolves `student_id` input using `_resolve_student_identifier(...)`.

Behavior:

- if the value is a valid Mongo ObjectId, it attempts to find the student by `_id`
- otherwise it falls back to `roll_number`

This is a practical design choice because frontend create flows often work more naturally with roll numbers than raw ObjectIds.

### 5.3 Teacher-scoped class access

Teacher access is not global. The module applies scoped class management rules.

Helper functions:

- `_teacher_manageable_class_ids(...)`
- `_can_manage_class(...)`

Rules implemented:

- admins can manage enrollments broadly
- teachers can manage enrollments only if they carry an approved extension role
- supported teacher extensions are:
  - `year_head`
  - `class_coordinator`

Current scope logic:

- `year_head` can manage all active classes, optionally narrowed by provided `class_id`
- `class_coordinator` can manage only classes where `class_coordinator_user_id == current_user._id`

This is operationally useful, but the `year_head` scope is broader than the role name implies.

### 5.4 Duplicate prevention

Before inserting an enrollment, the backend checks whether the student is already enrolled in the target class.

The duplicate query uses:

- canonical `student_id`
- denormalized `student_roll_number`

This prevents duplicate rows even if earlier data was created using mixed student identifiers.

### 5.5 Audit integration

Enrollment creation writes an audit log entry with:

- `action="enroll_student"`
- `entity_type="enrollment"`

This means enrollment is already operationally auditable even though destructive governance paths are not implemented here.

## 6. Business Rules

### Rule 1: Enrollment is a privileged action

Only these actors can create enrollments:

- admin users
- teachers with `year_head`
- teachers with `class_coordinator`

### Rule 2: Teachers cannot manage arbitrary classes

Teacher actions are constrained to manageable classes defined by role scope.

### Rule 3: Class must exist

Enrollment cannot be created unless the target `class_id` exists.

### Rule 4: Student must exist

Enrollment cannot be created unless the student resolves successfully by ObjectId or roll number.

### Rule 5: Duplicate enrollment is rejected

The same student cannot be enrolled into the same class twice.

### Rule 6: Enrollment is append-only in current implementation

Because update and delete flows do not exist, the module currently behaves as append-only.

This has operational safety benefits, but it also creates cleanup pressure if incorrect assignments are made.

## 7. API Endpoints

Current endpoint base:

- `/enrollments`

### GET `/enrollments/`

Purpose:

- list enrollments
- optionally filter by section/class or student

Supported query parameters:

- `class_id`
- `student_id`
- `skip`
- `limit`

Behavior:

- if `student_id` is provided, backend resolves it by ObjectId or roll number
- if the caller is a scoped teacher, results are restricted to manageable classes
- if the teacher has no manageable classes, the endpoint returns an empty list

### POST `/enrollments/`

Purpose:

- create a new enrollment

Payload schema:

- `class_id`
- `student_id`

Behavior:

- validates class existence
- enforces teacher/admin scope
- resolves the student
- prevents duplicates
- stores canonical `student_id` and denormalized `student_roll_number`
- records `assigned_by_user_id`
- writes audit log

### Missing API operations

These do not currently exist:

- `PUT /enrollments/{id}`
- `PATCH /enrollments/{id}`
- `DELETE /enrollments/{id}`
- archival/recovery endpoints

That absence is an important product constraint and should be treated as an explicit current limitation, not an accidental omission in documentation.

## 8. Frontend Implementation

Frontend implementation is centered on:

- [EnrollmentsPage.jsx](/frontend/src/pages/EnrollmentsPage.jsx)

Supporting configuration:

- [featureAccess.js](/frontend/src/config/featureAccess.js)
- [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx)

### 8.1 Page behavior

The page uses the shared `EntityManager` pattern and supports:

- list enrollments
- create enrollment

It does not expose:

- edit enrollment
- delete enrollment

### 8.2 Supporting data sources

The page fetches:

- sections/classes through `getSections`
- students through `/students/`

The create form uses student `roll_number` as the selection value. That matches backend identifier resolution behavior and avoids forcing frontend operators to work with raw database ids.

### 8.3 Access behavior

Frontend feature access for enrollments currently allows:

- `admin`
- `teacher`

Teacher access is further constrained by required extensions:

- `year_head`
- `class_coordinator`

This generally matches backend policy and is one of the cleaner UI-backend alignments in the current system.

## 9. Frontend vs Backend Gaps

### Gap 1: No unenrollment flow

Backend has no delete/archive flow, and frontend therefore cannot remove mistaken assignments.

### Gap 2: No update flow

If a student is enrolled in the wrong class, there is no direct correction path beyond data intervention or future feature work.

### Gap 3: Canonical naming mismatch

Frontend enrollment UI is conceptually about section membership, but backend and stored fields still use `class_id`.

### Gap 4: No governance path

Because there is no destructive flow, there is also no governance review path. If unenrollment is later added, governance requirements will need to be designed rather than assumed.

### Gap 5: Dual source of truth for section assignment

Student membership is represented in more than one place:

- `students.class_id`
- `enrollments.class_id`

This duplication is a structural risk.

## 10. Strengths of Current Implementation

The module has some good implementation traits despite its narrow scope.

### Good alignment between UI and backend permissions

The feature access configuration broadly matches the backend role model for enrollment management.

### Practical identifier handling

Allowing roll number resolution is operationally correct for academic staff workflows.

### Teacher scoping exists

Teacher access is not open-ended. The system already applies role-based scope, which is important.

### Audit logging exists

Enrollment creation is auditable.

## 11. Bugs, Risks, and Architectural Issues

### Issue 1: Dual membership source of truth

This is the most important architectural problem around enrollment.

Student membership can be inferred from:

- student master record fields
- enrollment records

That creates consistency risk:

- a student could appear assigned in one place and not the other
- downstream modules may rely on different sources

### Issue 2: Legacy `classes` naming in canonical architecture

The system has standardized on `Section`, but enrollment still uses `classes`.

This causes:

- mental model drift
- naming inconsistency in docs and APIs
- avoidable translation overhead in frontend code

### Issue 3: Year head scope is too broad

`year_head` currently maps to all active classes rather than a constrained year/semester/program slice.

That is workable, but semantically weak.

### Issue 4: No corrective lifecycle

There is no safe lifecycle for:

- wrong assignment
- transfer between sections
- temporary removal
- archival of old memberships

### Issue 5: No soft-delete semantics

Unlike recently hardened academic setup entities, enrollment has no canonical archive or soft-delete path.

## 12. Cleanup Strategy

### Short-term

- keep current create/list functionality stable
- document that enrollment is append-only
- avoid introducing ad hoc direct database edits as the normal operator workflow

### Medium-term

- align enrollment naming from `class_id` to canonical `section_id`
- define one authoritative source of student-section membership
- if `enrollments` is retained as the authority, stop duplicating membership in `students.class_id`

### Long-term

Implement a full enrollment lifecycle:

- create enrollment
- transfer enrollment
- archive/unenroll
- recovery if needed
- governance review for destructive changes if policy requires it

That lifecycle should also decide whether enrollment history is:

- mutable current-state only
- or historical and append-only with state transitions

Historical state tracking is the stronger design.

## 13. Recommended Target Model

The clean target model is:

- student master data remains in `students`
- section membership authority lives in `enrollments`
- canonical foreign key becomes `section_id`
- `students.class_id` becomes derived or removed

That design yields:

- clearer ownership
- better auditability
- cleaner transfer history
- stronger alignment with the canonical academic hierarchy

## 14. Testing Requirements

Minimum required automated coverage for the enrollment module should include:

### Unit tests

- student resolution by ObjectId
- student resolution by roll number
- duplicate enrollment rejection
- class existence validation
- teacher scope validation
- year head manageable class resolution
- class coordinator manageable class resolution

### API tests

- admin can list and create enrollments
- class coordinator can create only in owned classes
- teacher without extension role is denied
- invalid student identifier is rejected
- duplicate enrollment returns correct error
- filtered list respects teacher scope

### Integration tests

- student enrolled in section appears in student-facing section-scoped views
- teacher sees only allowed rosters
- timetable/student views use the same membership source consistently

### Future tests if lifecycle expands

- unenrollment review flow
- archival semantics
- section transfer behavior
- membership history preservation

## 15. Final Summary

The Enrollment module is currently a focused operational binding layer between students and sections, implemented through the legacy `classes` model.

It is useful and functional today because it already provides:

- scoped actor permissions
- student resolution by roll number or ObjectId
- duplicate prevention
- audit logging

Its main weaknesses are architectural rather than purely functional:

- section membership is duplicated across data models
- canonical `Section` naming is not yet reflected in the API shape
- there is no correction, transfer, archive, or destructive governance lifecycle

From a system-design perspective, the module should be preserved but normalized:

- keep enrollment as the membership authority
- align it to canonical section terminology
- remove duplicate membership state
- add a controlled lifecycle for change and removal

