# Subject Module Master

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
Subject Module
|-- Subject Catalog
|-- Academic Reference Data
|-- Offering Dependencies
|-- Timetable Dependencies
`-- Assignment And Communication Dependencies
```

## Internal Entity And Flow Tree

```text
Subject
|-- Course offering reference
|-- Timetable and slot reference
|-- Assignment reference
`-- Communication and reporting reference
```

## 1. Module Overview

The Subject module is the academic catalog layer for teachable subjects. It does not define institutional structure such as faculty, department, program, or section. Instead, it defines the reusable subject entities that downstream teaching workflows attach to.

In the current CAPS AI codebase, subjects are referenced by multiple operational modules:

- course offerings
- timetables
- assignments
- announcements and communication targeting
- teacher class tiles and related teaching summaries

That makes the Subject module small in surface area but high in dependency value. If subjects are inconsistent, duplicated, or deleted incorrectly, downstream teaching workflows lose referential integrity quickly.

The current implementation is intentionally simple:

- list subjects
- get a subject by id
- create subject
- update subject
- delete subject

The design is functional, but it is under-governed compared with the recently hardened academic setup module.

## 2. Purpose in the System

The Subject module exists to answer one core question:

"What is the teachable academic unit being delivered?"

A subject in the current system is a reusable catalog record containing:

- a human-readable name
- a unique subject code
- an optional description
- active/inactive state

It is then attached to delivery contexts elsewhere, for example:

- course offering rows that bind a subject to teacher, batch, semester, and group
- timetable slots that refer to a subject by `subject_id`
- assignments that target a subject

This means the module behaves more like a master data catalog than a workflow engine.

## 3. Database Collection

### Primary collection: `subjects`

Primary backend files:

- [subjects.py](/backend/app/api/v1/endpoints/subjects.py)
- [subject.py](/backend/app/schemas/subject.py)
- [subjects.py](/backend/app/models/subjects.py)

Purpose of the collection:

- store reusable academic subject master data
- provide stable ids and codes for downstream academic delivery modules

### Current public shape

The current public subject shape is:

- `id`
- `name`
- `code`
- `description`
- `is_active`
- `created_at`

### Field semantics

#### `name`

Display name of the subject.

Examples:

- Mathematics I
- Database Management Systems
- Python Programming

#### `code`

Operational unique identifier for the subject.

Examples:

- MA1002T
- CS3001P

The backend normalizes codes to uppercase before storage.

#### `description`

Optional human-readable explanatory field.

#### `is_active`

Soft availability flag in the record model. This is supported by schema and update flow and can also be used for filtering on list reads.

#### `created_at`

Creation timestamp.

## 4. Relations

The Subject module does not own the academic hierarchy, but it is referenced by multiple other modules.

### Known downstream relations

#### Assignments

Assignments fetch subjects from `/subjects/` and allow teachers/admins to bind work to a selected subject.

#### Course offerings

Course offerings use subject selection as part of the operational mapping between:

- subject
- teacher
- batch
- semester
- group

#### Timetables

Timetable configuration depends on subject existence and subject selection when assigning a slot to a teachable item.

#### Communication

Announcements and communication flows also query subjects for targeting and contextual filtering.

### Important architectural note

The `subjects` collection is not isolated. It acts as shared master data consumed by multiple modules, but the subject delete flow currently does not protect those relationships.

That is the main system-level risk in this module.

## 5. Backend Logic Implemented

### 5.1 Read operations

#### `GET /subjects/`

Supports:

- text search by name/code through `q`
- active state filtering through `is_active`
- pagination using `skip` and `limit`

Access control:

- `admin`
- `teacher`

This makes subject reads broadly available to operational teaching users.

#### `GET /subjects/{subject_id}`

Returns a single subject by id.

Access control:

- `admin`
- `teacher`

### 5.2 Create operation

#### `POST /subjects/`

Behavior:

- trims subject name
- normalizes subject code to uppercase
- checks uniqueness on code
- inserts a new record with `is_active = true`
- stores `created_at`

Access control:

- `require_permission("academic:manage")`

This is important because it does not align with the frontend route access, which allows teachers to open the page.

### 5.3 Update operation

#### `PUT /subjects/{subject_id}`

Behavior:

- trims name when provided
- normalizes code to uppercase
- checks duplicate code conflict
- rejects empty updates
- supports updating `is_active`

Access control:

- `require_permission("academic:manage")`

### 5.4 Delete operation

#### `DELETE /subjects/{subject_id}`

Behavior:

- performs direct `delete_one(...)`
- returns success if a row was deleted
- returns 404 if subject not found

Access control:

- `require_permission("academic:manage")`

This is a hard delete. There is:

- no soft delete
- no governance review
- no dependency scan
- no telemetry instrumented like the hardened academic setup deletes

## 6. Business Rules

### Rule 1: Subject code must be unique

The backend checks for existing records by normalized uppercase `code`.

### Rule 2: Subject code is normalized

Codes are stored in uppercase even if user input is mixed case.

### Rule 3: Empty update payloads are rejected

If no effective fields are provided on update, the request fails.

### Rule 4: Reads are broader than writes

Teachers can read subjects, but writes require `academic:manage`.

### Rule 5: Subject state can be toggled

`is_active` is supported in `SubjectUpdate` and can be used operationally without deleting the record.

### Rule 6: Delete is destructive

Delete removes the record physically rather than archiving it.

That is a business risk rather than a strength.

## 7. API Endpoints

Base path:

- `/subjects`

### CRUD surface

#### `GET /subjects/`

List subjects.

Query parameters:

- `q`
- `is_active`
- `skip`
- `limit`

#### `GET /subjects/{subject_id}`

Get one subject by id.

#### `POST /subjects/`

Create a subject.

Payload:

- `name`
- `code`
- `description`

#### `PUT /subjects/{subject_id}`

Update a subject.

Payload supports:

- `name`
- `code`
- `description`
- `is_active`

#### `DELETE /subjects/{subject_id}`

Hard delete a subject.

## 8. Frontend Implementation

Frontend page:

- [SubjectsPage.jsx](/frontend/src/pages/SubjectsPage.jsx)

Supporting access and route files:

- [featureAccess.js](/frontend/src/config/featureAccess.js)
- [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx)

### 8.1 UI behavior

The page is implemented with `EntityManager` and currently exposes:

- list
- create
- edit
- delete

### 8.2 Filters

Current frontend filters:

- `q` for name/code search
- `is_active`

### 8.3 Create form

Current create fields:

- `name`
- `code`
- `description`

### 8.4 List columns

Current visible columns:

- `name`
- `code`
- `description`

The page does not currently display:

- `created_at`
The page now also displays:

- `is_active`

## 9. Frontend vs Backend Gaps

### Gap 1: Teachers can open the page, but cannot reliably write

Frontend access config allows:

- `admin`
- `teacher`

But backend write operations require:

- `academic:manage`

If a teacher lacks that permission, the UI still presents create/delete controls and the backend rejects the request.

This is a clear UI-backend contract mismatch.

### Gap 2: Teachers can open the page, but cannot reliably write

The edit and active-filter gaps are now closed in the page itself, but the role/permission mismatch remains.

### Gap 3: Delete is exposed without governance

The page enables delete, but there is:

- no governance review prompt
- no dependency warning
- no destructive telemetry surfaced in UI

## 10. Bugs and Risks Identified

### Risk 1: Hard delete can orphan downstream data

Because subjects are referenced by assignments, course offerings, and timetable-related structures, deleting a subject without dependency protection can break downstream records or leave unresolved references.

### Risk 2: Permission model is inconsistent

Reads use:

- `require_roles(["admin", "teacher"])`

Writes use:

- `require_permission("academic:manage")`

That is not inherently wrong, but the frontend route and page actions do not reflect that split carefully enough.

### Risk 3: Module still uses blanket `academic:manage`

The academic setup hardening moved toward entity-level permissions, but `subjects.py` still uses the older blanket permission model.

### Risk 4: No delete review or safety controls

Delete lacks:

- governance gating
- review id support
- impact preview
- soft-delete fallback

### Risk 5: No dependency-aware archival path

Subjects should usually be retired through inactivation, not hard deletion, but the current delete endpoint allows direct removal.

## 11. Architectural Issues

### Issue 1: Shared master data without shared governance

Subjects are shared master data, but the control level is still lightweight. This is acceptable in a prototype, but weak in a production academic platform.

### Issue 2: Subject lifecycle is underspecified

The module currently supports:

- create
- update
- hard delete

But there is no clear product lifecycle for:

- deprecating a subject
- preserving historical use
- replacing old subject codes
- marking catalog discontinuation safely

### Issue 3: No ownership scope

Teachers can read all subjects, not just subjects they teach.

That may be acceptable if the subject catalog is intentionally global, but it should be a deliberate product decision.

### Issue 4: No canonical relation guardrail on delete

Because subject is used across multiple academic delivery modules, delete should likely be reference-aware and archival by default.

## 12. Recommended Cleanup Strategy

### Short-term

- keep subject reads global for admin/teacher
- hide write controls for users who do not have actual write capability
- prefer `is_active = false` over hard delete for routine retirement

### Medium-term

- replace blanket `academic:manage` with explicit entity permission such as `subjects.manage`
- add dependency checks before delete
- convert delete to soft-delete or archive semantics
- add governance review if delete remains destructive

### Long-term

Treat subjects as protected master data:

- no direct hard delete for normal operations
- archival/inactivation as primary lifecycle
- reference-aware retirement strategy
- migration tooling if subject codes need consolidation

## 13. Recommended Target Model

The stronger target model is:

- `subjects` remains the master catalog
- updates remain allowed to authorized academic operators
- retirement happens by `is_active = false`
- destructive delete is restricted to exceptional governance-approved cleanup

That model protects downstream modules and preserves historical academic records.

## 14. Testing Requirements

Minimum automated coverage should include:

### Unit tests

- subject code normalization to uppercase
- duplicate code rejection
- empty update rejection
- active-state update handling

### API tests

- admin can list and get subjects
- teacher can list and get subjects
- unauthorized write is rejected
- duplicate create fails
- update with duplicate code fails
- delete on missing id returns 404

### Integration tests

- frontend page hides write controls for users who cannot actually write
- frontend edit support is added only if backend update remains intended
- subject deletion behavior is validated against downstream references

### Safety tests that should be added

- delete blocked when subject is still referenced by course offerings
- delete blocked when subject is referenced in timetable or assignments
- governance review required if delete remains destructive

## 15. Final Summary

The Subject module is small, but it is not low impact. It is shared academic master data used by multiple downstream teaching workflows.

Current strengths:

- simple API
- unique code enforcement
- uppercase code normalization
- reusable cross-module catalog

Current weaknesses:

- teachers can access the page but may not be allowed to write
- delete is hard delete with no governance or dependency protection
- the module still uses the older blanket `academic:manage` permission style

From an architectural perspective, the correct direction is clear:

- preserve subjects as master catalog data
- expose update intentionally
- retire via inactive state, not routine hard delete
- protect destructive deletion with dependency and governance controls


