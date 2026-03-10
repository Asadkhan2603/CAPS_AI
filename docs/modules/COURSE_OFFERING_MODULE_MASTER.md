# COURSE OFFERING MODULE MASTER

## Module Tree

```text
Course Offering Module
|-- Course Offerings
|-- Teacher Assignment Mapping
|-- Section And Group Scope
|-- Student Visibility
`-- Downstream Slot And Attendance Dependents
```

## Internal Entity And Flow Tree

```text
Course offering
|-- Section scope
|-- Optional group scope
|-- Teacher mapping
`-- Downstream class slots and attendance
```

## 1. Module Overview

The course offering module binds a subject to an actual delivery context for a specific academic period and learner cohort. In CAPS AI, a course offering is the bridge between academic structure and operational teaching.

A course offering links:

- subject
- teacher
- batch
- semester
- section
- optional group
- academic year
- offering type

This module is operationally significant because it is the upstream dependency for:

- class slots
- timetable rendering
- attendance marking
- student dashboard teaching tiles

Without course offerings, the system knows that subjects and sections exist, but it does not know which teacher is delivering which subject to which cohort.

## 2. Core Domain Model

### 2.1 Primary entity

The module centers on:

- `course_offerings`

This is not a curriculum design object. It is a delivery-assignment object.

### 2.2 Meaning of a course offering

A single offering represents:

- one subject
- taught by one teacher
- to one section
- in one batch and semester
- in one academic year
- optionally scoped to one group
- for one delivery type

Examples:

- Theory teaching of Mathematics for Section A in Semester 1
- Lab offering of Physics for only Group G1 inside a section
- Club-type or workshop-type offering for special instructional activity

### 2.3 Offering types

The schema allows:

- `theory`
- `lab`
- `elective`
- `workshop`
- `club`
- `interaction`

This means the module is broader than a pure subject timetable binder. It is intended to support multiple instructional modes.

## 3. Database Collection

### 3.1 `course_offerings`

Purpose:

- stores the active teaching assignment contract for a subject-section-period combination

Key fields:

- `_id`
- `subject_id`
- `teacher_user_id`
- `batch_id`
- `semester_id`
- `section_id`
- `group_id`
- `academic_year`
- `offering_type`
- `is_active`
- `created_by_user_id`
- `created_at`
- `deleted_at`

Relations:

- `subject_id -> subjects._id`
- `teacher_user_id -> users._id`
- `batch_id -> batches._id`
- `semester_id -> semesters._id`
- `section_id -> classes._id` even though conceptually this is the canonical section
- `group_id -> groups._id`

Important downstream relation:

- `class_slots.course_offering_id -> course_offerings._id`

### 3.2 Derived/public fields

The list endpoint enriches outputs with:

- `subject_name`
- `subject_code`
- `teacher_name`
- `section_name`
- `group_name`
- `semester_label`

These are response-time enrichments, not stored fields in the base document.

### 3.3 Indexes

Observed indexes in [indexes.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\core\indexes.py):

- `(section_id, semester_id, academic_year, is_active)`
- `(teacher_user_id, is_active)`

These support:

- section-wise offer lookup
- teacher-wise offer lookup

### 3.4 Uniqueness behavior

Application-level duplicate prevention blocks duplicate active offerings for the same:

- `subject_id`
- `teacher_user_id`
- `batch_id`
- `semester_id`
- `section_id`
- `group_id`
- `academic_year`
- `offering_type`

Important limitation:

- this is app-enforced
- no database unique index is visible in the reviewed files

## 4. Backend Logic Implemented

Primary backend file:

- [course_offerings.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\api\v1\endpoints\course_offerings.py)

Supporting files:

- [course_offering.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\schemas\course_offering.py)
- [course_offerings.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\models\course_offerings.py)

### 4.1 Write access model

The backend does not use a dedicated permission string here. It uses role-based access plus section-scoped ownership logic.

Write roles:

- `admin`
- `teacher`

Teacher write constraint:

- teacher can write only if they are the `class_coordinator_user_id` of the target section

Important implication:

- a teacher assigned as `teacher_user_id` on an offering is not, by itself, enough to create or modify offerings
- coordinator authority is stronger than delivery authority here

### 4.2 Payload validation

Shared validator:

- `_validate_payload(...)`

Required fields:

- `section_id`
- `subject_id`
- `teacher_user_id`
- `batch_id`
- `semester_id`
- `academic_year`

Validation performed:

- section must exist and be active
- subject must exist and be active
- teacher must exist, be active, and have role:
  - `teacher`
  - or `admin`
- batch must exist and be active
- semester must exist and be active
- semester must belong to the provided batch
- if `group_id` provided:
  - group must exist and be active
  - group must belong to the provided section

This is strong cross-entity validation for the operational teaching context.

### 4.3 List offerings

Endpoint:

- `GET /course-offerings/`

Roles:

- `admin`
- `teacher`
- `student`

Filters supported:

- `section_id`
- `batch_id`
- `semester_id`
- `group_id`
- `subject_id`
- `teacher_user_id`
- `academic_year`
- `is_active`
- `skip`
- `limit`

Student-specific behavior:

- backend resolves student by:
  - `students.email == current_user.email`
- if no active student row or no `class_id`, returns empty list
- student is then restricted to:
  - their `class_id` as `section_id`
  - either offerings with no `group_id`
  - or offerings matching their own `group_id`

This is one of the cleaner student scoping implementations in the repo.

### 4.4 Create offering

Endpoint:

- `POST /course-offerings/`

Roles:

- `admin`
- `teacher`

Behavior:

- enforces section write access
- validates payload
- blocks duplicates using application-level matching
- stores:
  - `is_active = true`
  - `created_by_user_id`
  - `created_at`

### 4.5 Update offering

Endpoint:

- `PUT /course-offerings/{offering_id}`

Roles:

- `admin`
- `teacher`

Behavior:

- offering must exist
- current user must have section write access based on the current section
- merged payload is validated
- partial update is allowed

Important nuance:

- section write access is checked against the current section before update
- if the section were changed in the update payload, the code validates the new section but the access check originates from the old section

This is not necessarily wrong, but it is a subtle ownership edge case worth noting.

### 4.6 Archive offering

Endpoint:

- `DELETE /course-offerings/{offering_id}`

Roles:

- `admin`
- `teacher`

Behavior:

- offering must exist and be active
- user must have section write access
- soft archives by setting:
  - `is_active = false`
  - `deleted_at`

Important gaps:

- no governance review
- no destructive telemetry
- no audit logging observed in the reviewed file

## 5. Frontend Implementation

Primary page:

- [CourseOfferingsPage.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\CourseOfferingsPage.jsx)

### 5.1 Frontend architecture

The UI uses shared `EntityManager` CRUD scaffolding.

Lookups loaded:

- subjects
- users
- batches
- semesters
- groups
- sections through [sectionsApi.js](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\services\sectionsApi.js)

### 5.2 Create support

Create form exposes:

- subject
- teacher
- batch
- semester
- section
- optional group
- academic year
- offering type

This is close to the full backend contract and is one of the better-aligned CRUD pages in the repo.

### 5.3 Filter support

List filters expose:

- section
- semester
- group
- academic year
- active switch

Backend supports more filters than the current page exposes, such as:

- batch
- subject
- teacher

### 5.4 List support

List columns show:

- subject
- teacher
- section
- group
- batch
- semester
- academic year
- type
- active state

The page now also exposes edit through `EntityManager`, not just create/archive.

### 5.5 Delete support

The page enables delete through `EntityManager`.

Important mismatch:

- delete is available in UI
- backend delete is not governance-gated
- no extra warning exists for downstream class slot dependencies

## 6. Downstream Dependencies

### 6.1 Class slots

`class_slots` are attached to offerings, not directly to sections or subjects.

This means:

- timetable slots depend on offerings existing first
- slot-level conflict checks operate through offerings

Observed in:

- [ClassSlotsPage.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\ClassSlotsPage.jsx)
- [class_slots.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\api\v1\endpoints\class_slots.py)

### 6.2 Attendance

Attendance uses class slot -> course offering -> section/group chain.

Observed in:

- [attendance_records.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\api\v1\endpoints\attendance_records.py)

Attendance validation depends on offering context:

- student must belong to offering section
- if offering has group restriction, student must belong to that group

This makes course offerings a critical access-control and roster boundary.

### 6.3 Student dashboard and timetable views

Student schedule views combine:

- class slots
- course offerings

to render:

- subject
- teacher
- type
- optional group

Observed in:

- [DashboardPage.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\DashboardPage.jsx)
- [TimetablePage.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\TimetablePage.jsx)

## 7. Business Rules

### 7.1 Offering completeness

An offering must always specify:

- section
- subject
- teacher
- batch
- semester
- academic year

### 7.2 Semester ownership

- `semester_id` must belong to `batch_id`

### 7.3 Group ownership

- if `group_id` exists, it must belong to the selected section

### 7.4 Student visibility

Students can see only offerings that belong to:

- their section
- and either:
  - no group restriction
  - or their own group

### 7.5 Write authority

Teacher write authority is based on:

- section coordinator ownership

not on:

- being the assigned teacher in the offering itself

This is a real business rule in the current implementation.

## 8. Frontend vs Backend Gaps

### 8.1 Missing filters

Backend supports filters for:

- batch
- subject
- teacher

Frontend does not expose them.

### 8.2 Delete safety is weak

UI allows delete, but there is no governance review prompt and no explicit warning about linked class slots or attendance implications.

### 8.3 Label quality in dependent UI is weak

`ClassSlotsPage.jsx` labels offerings as:

- `section name | academic_year | offering_type`

instead of using human-friendly:

- subject name
- teacher name

This is better than raw ids, but still weaker than the full enriched data model supports.

### 8.4 No explicit dependency surfacing

The offering page does not surface whether an offering already has:

- class slots
- attendance records

That makes archive decisions opaque.

## 9. Architectural Issues

### 9.1 Write authority is coordinator-centric, not teacher-centric

The assigned teacher on an offering does not automatically control the offering.

This may be operationally acceptable if section coordinators own academic setup, but it is a real architectural choice and should be documented.

### 9.2 Section storage still inherits legacy class naming

Offerings point to `section_id`, but the section is looked up in:

- `db.classes`

This continues the section/class naming debt described in the class-section module.

### 9.3 No dependency-aware archive protection

Offerings can be archived even if they are already referenced by:

- class slots
- attendance records

The reviewed code does not block or warn on these downstream dependencies.

### 9.4 Duplicate prevention is not DB-hard

The duplicate check is useful, but concurrent create requests can still race without a unique index.

## 10. Risks and Bugs Identified

### 10.1 Teacher assignment vs management mismatch

A teacher may be assigned to teach an offering but still be unable to manage it unless they are the section coordinator.

Risk:

- operator confusion
- support burden

### 10.2 Student resolution by email

Student offerings are scoped by finding `students.email == current_user.email`.

Risk:

- identity drift if student master email and auth email diverge

### 10.3 Archive side effects not guarded

Archiving an offering may leave orphaned or semantically invalid downstream scheduling and attendance data unless handled elsewhere.

### 10.4 No governance/audit parity

Compared to hardened academic setup modules, course offerings currently lack:

- governance review gating
- destructive telemetry
- visible audit logging in the endpoint

## 11. Cleanup Strategy

### 11.1 Keep offerings as the delivery contract

This is the right conceptual role for the module and should remain stable.

### 11.2 Decide ownership model explicitly

Choose one of:

- section coordinator owns offerings
- assigned teacher owns offerings
- shared coordinator + teacher ownership

Current code uses the first model.

### 11.3 Add dependency-aware archive checks

Before allowing delete/archive, check for:

- active class slots
- attendance records

and either block or require governance review.

### 11.4 Improve UI filter and labeling quality

Expose:

- subject filter
- teacher filter
- batch filter

and improve downstream offering labels to use human-readable names.

### 11.5 Harden uniqueness at DB level

Add a unique index for active offerings on the effective business key if the product wants duplicate prevention to be race-safe.

## 12. Testing Requirements

### 12.1 Unit tests

- section write access for admin
- section write access for teacher coordinator
- teacher denied if not coordinator
- section existence validation
- subject existence validation
- semester belongs-to-batch validation
- group belongs-to-section validation
- duplicate offering prevention

### 12.2 Integration tests

- create offering
- student list sees only own section offerings
- group-restricted offering hidden from students outside group
- offering archive behavior with existing class slots
- update offering with changed section and ownership constraints

### 12.3 Frontend tests

- create payload formation
- select lookups render correctly
- filter behavior
- delete action availability
- teacher-facing visibility of page actions

## 13. Current Module Assessment

The course offering module is structurally important and reasonably implemented. It is not a placeholder CRUD page. It defines the actual delivery mapping that powers scheduling and attendance.

Strengths:

- strong cross-entity validation
- clear student scoping
- near-complete frontend create UI
- direct integration with class slots and attendance

Weaknesses:

- weak delete safety
- coordinator-centric ownership may not match operator expectations
- duplicate prevention is not database-enforced
- downstream UIs do not exploit enriched metadata well

As implemented today, this module is a core teaching-operations boundary. It should be treated as a protected academic delivery contract, not as simple reference data.
