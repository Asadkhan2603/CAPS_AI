# Assignment Module Master

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
Assignment Module
|-- Assignment Master Records
|-- Teacher Ownership Rules
|-- Submission Windows
|-- Plagiarism Toggle
`-- Audit Hooks
```

## Internal Entity And Flow Tree

```text
Assignment
`-- Student submission eligibility
    `-- Submission records
        `-- Evaluation workflow
            `-- Review and analytics
```

## 1. Module Overview

The Assignment module manages academic work issued to sections and later consumed by the submission, evaluation, and similarity-check pipelines. It is one of the core teacher workflow modules in CAPS AI.

At a system level, assignments sit between:

- subject master data
- section/class delivery context
- student submission workflows
- teacher evaluation workflows
- plagiarism and similarity analysis

This module is therefore not just CRUD. It is the anchor record for a full academic assessment chain.

Primary backend file:

- [assignments.py](/backend/app/api/v1/endpoints/assignments.py)

Primary frontend page:

- [AssignmentsPage.jsx](/frontend/src/pages/AssignmentsPage.jsx)

## 2. Data Model

Schema/model files:

- [assignment.py](/backend/app/schemas/assignment.py)
- [assignments.py](/backend/app/models/assignments.py)

### Public record shape

Assignments currently expose:

- `id`
- `title`
- `description`
- `subject_id`
- `class_id`
- `due_date`
- `total_marks`
- `status`
- `plagiarism_enabled`
- `created_by`
- `created_at`

### Field semantics

#### `subject_id`

Optional link to `subjects`. This is a catalog relation, not the ownership anchor.

#### `class_id`

Optional link to `classes`, which in current code represents the section delivery unit. This is what student visibility is ultimately scoped through.

#### `status`

Currently a simple literal:

- `open`
- `closed`

#### `plagiarism_enabled`

Boolean toggle controlling whether similarity checks are permitted for submissions under the assignment.

#### `created_by`

Assignment ownership field. This is the main teacher access anchor used by several backend authorization checks.

### Soft-delete semantics

The module uses legacy soft-delete style on delete:

- `is_deleted = true`
- `is_active = false`
- `deleted_at`
- `deleted_by`

Reads filter on `is_deleted`, not the newer canonical academic soft-delete helper contract.

## 3. Backend Logic Implemented

### 3.1 Student visibility

Student assignment visibility is computed through `_student_visible_class_ids(...)`.

The function derives visible class ids from two sources:

- `students.class_id`
- `enrollments.class_id`

This is functional, but it also exposes a duplicated section-membership source of truth in the wider system.

### 3.2 List behavior

#### `GET /assignments/`

Supports filtering by:

- `q`
- `subject_id`
- `class_id`
- `created_by`
- `status`
- `skip`
- `limit`

Access rules:

- admin can list broadly
- teacher sees only assignments where `created_by == current_user._id`
- student sees assignments only for visible classes derived from membership

### 3.3 Get behavior

#### `GET /assignments/{assignment_id}`

Access rules:

- admin can read
- teacher can read only assignments they created
- student can read only if the assignment’s `class_id` is in their visible class set

Deleted assignments return 404.

### 3.4 Create behavior

#### `POST /assignments/`

Access rules:

- `admin`
- `teacher`

Behavior:

- stores title, description, subject, class, due date, marks, status, plagiarism toggle
- writes `created_by = current_user._id`
- writes `created_at`

Important weakness:

- create does not validate that the teacher is entitled to create for the target class
- create does not verify the existence of `subject_id`
- create does not verify the existence of `class_id`

That is weaker than the update/delete ownership model.

### 3.5 Update behavior

#### `PUT /assignments/{assignment_id}`

Access rules:

- admin can update any assignment
- teacher can update only assignments they created

Behavior:

- trims title
- rejects empty updates

### 3.6 Plagiarism toggle

#### `PATCH /assignments/{assignment_id}/plagiarism`

Access rules:

- teacher only, effectively owner only
- admin is explicitly blocked from overriding the plagiarism toggle

This is unusual and intentional:

- admin can update the assignment generally
- admin cannot override the plagiarism-specific toggle

The action is audited via `log_audit_event(...)`.

### 3.7 Delete behavior

#### `DELETE /assignments/{assignment_id}`

Access rules:

- admin can archive any assignment
- teacher can archive only assignments they created

Behavior:

- performs a soft archive using `is_deleted`, `is_active`, `deleted_at`, `deleted_by`
- returns `"Assignment archived"`

Missing from the current delete flow:

- governance review
- destructive telemetry hardening comparable to academic setup deletes
- dependency checks against submissions/evaluations

## 4. Business Rules

### Rule 1: Assignment ownership is creator-based

The main teacher ownership rule is:

- creator teacher can view/update/delete their own assignments

### Rule 2: Student visibility is section-scoped

Students do not browse all assignments. They see only assignments tied to their visible classes.

### Rule 3: Plagiarism toggle is teacher-controlled

Teachers who own the assignment can enable or disable plagiarism checking.

### Rule 4: Admin cannot override plagiarism toggle

This is explicitly enforced in backend logic.

### Rule 5: Deleted assignments are archived, not removed

Delete is soft-delete style rather than hard delete.

### Rule 6: Assignment status is currently binary

Only:

- `open`
- `closed`

There is no draft, scheduled, or published lifecycle state.

## 5. API Endpoints

Base path:

- `/assignments`

### CRUD and control endpoints

#### `GET /assignments/`

List assignments with filters.

#### `GET /assignments/{assignment_id}`

Get one assignment with role-based visibility enforcement.

#### `POST /assignments/`

Create an assignment.

#### `PUT /assignments/{assignment_id}`

Update an assignment.

#### `PATCH /assignments/{assignment_id}/plagiarism`

Toggle plagiarism detection.

#### `DELETE /assignments/{assignment_id}`

Archive an assignment.

## 6. Frontend Implementation

Frontend page:

- [AssignmentsPage.jsx](/frontend/src/pages/AssignmentsPage.jsx)

Route/config:

- [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx)
- [featureAccess.js](/frontend/src/config/featureAccess.js)

### Current page capabilities

The page uses `EntityManager` and currently exposes:

- list
- create
- delete
- plagiarism toggle in-table for teachers

It does not expose:

- edit

Even though backend update exists.

### Lookup dependencies

The page fetches:

- `/subjects/`
- sections via `getSections(...)`

It then resolves ids into display labels.

### Filter support

Frontend filters:

- `q`
- `subject_id`
- `class_id`
- `status`

### Create form support

Frontend create form includes:

- `title`
- `description`
- `subject_id`
- `class_id`
- `due_date`
- `total_marks`
- `status`
- `plagiarism_enabled`

## 7. Frontend vs Backend Gaps

### Gap 1: Backend update exists, UI edit is not enabled

Operators cannot edit through the current page even though the API supports it.

### Gap 2: Create flow may allow invalid references

Frontend offers subject and section selectors, but backend create does not strongly validate those references today.

### Gap 3: Delete is surfaced without review semantics

Assignment archive is available through the shared page, but there is no governance prompt or impact warning.

### Gap 4: Teacher create scope is broader than teacher edit scope

Teachers can create assignments generally, but later mutation is creator-bound.

If teacher creation should also be section-scoped, the current API does not enforce that.

## 8. Cross-Module Dependencies

Assignments are upstream to:

- submissions
- evaluations
- similarity logs
- durable AI jobs scoped by assignment-linked submissions
- notifications generated from similarity alerts
- student history and dashboards
- communication feed

This is why assignment lifecycle control matters. A weak assignment record model creates downstream inconsistency quickly.

## 9. Bugs and Risks Identified

### Risk 1: Teacher create authorization is weaker than later mutation authorization

The system is stricter after creation than during creation. That is not coherent access design.

### Risk 2: No existence validation for `subject_id` and `class_id` on create/update

This can allow orphaned references if bad ids are submitted directly.

### Risk 3: Soft-delete style is legacy, not normalized

Assignments still rely on `is_deleted` semantics rather than the newer canonical soft-delete contract.

### Risk 4: Archive does not check downstream state

Assignments with submissions or evaluations can still be archived without a higher-order workflow or warning.

### Risk 5: Student visibility depends on duplicated section-membership sources

Because student visibility uses both `students.class_id` and `enrollments.class_id`, assignment access can drift if those sources diverge.

## 10. Architectural Issues

### Issue 1: Ownership model is creator-centric, not teaching-allocation-centric

Assignments are primarily controlled by `created_by`, not by:

- course offering ownership
- section coordinator ownership
- timetable allocation

That is simple, but not the strongest academic ownership model.

### Issue 2: Assignment lifecycle is too shallow

Only `open` and `closed` states exist. Real educational workflows usually need richer lifecycle states such as:

- draft
- published
- closed
- archived

### Issue 3: No explicit dependency contract with submissions

Archiving an assignment does not formally address:

- existing submissions
- grading state
- evaluation state

### Issue 4: Governance is not applied to a high-impact academic record

Assignments materially affect students and grading workflows, but delete/archive currently has no governance review.

## 11. Recommended Cleanup Strategy

### Short-term

- add backend validation for `subject_id` and `class_id`
- enable edit in UI if update is meant to be operator-facing
- align teacher create authorization with intended section ownership model

### Medium-term

- normalize assignment delete to a reviewed archival policy if business risk justifies it
- decide whether assignment ownership should stay creator-based or move to section/course-offering-based control
- reduce dependence on duplicated section membership sources for student visibility

### Long-term

Adopt a stronger academic workflow model:

- validated subject and section links
- richer assignment lifecycle
- explicit dependency handling with submissions and evaluations
- audit and governance proportionate to academic impact

## 12. Testing Requirements

Minimum automated coverage should include:

### Unit tests

- student-visible class resolution from both `students.class_id` and `enrollments`
- teacher creator ownership checks
- plagiarism toggle admin restriction
- soft-delete archive metadata write

### API tests

- teacher sees only self-created assignments
- student sees only section-visible assignments
- teacher cannot update another teacher’s assignment
- teacher cannot delete another teacher’s assignment
- admin can update/delete any assignment
- invalid or deleted assignment returns 404

### Safety tests that should be added

- create rejects invalid `subject_id`
- create rejects invalid `class_id`
- archive behavior when submissions already exist
- UI edit alignment if backend update remains supported

## 13. Final Summary

The Assignment module is one of the most operationally important academic workflow modules in CAPS AI. It is already connected to submissions, evaluations, similarity, history, and the communication feed.

Current strengths:

- clear student/teacher/admin read controls
- creator-based teacher ownership for mutation
- soft archive instead of hard delete
- explicit plagiarism toggle with audit logging

Current weaknesses:

- backend create validation is too loose
- UI does not expose edit although backend supports update
- delete/archive is not governance-aware
- visibility still depends on duplicated section membership state elsewhere

From an architecture standpoint, this module should be retained as the assessment anchor, but hardened around:

- better reference validation
- cleaner ownership semantics
- stronger lifecycle states
- safer archival policy


