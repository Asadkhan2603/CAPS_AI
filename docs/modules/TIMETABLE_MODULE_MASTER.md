# Timetable Module Master

## Module Tree

```text
Timetable Module
|-- Timetable Planning Records
|-- Runtime Class Slot Layer
|-- Shift And Slot Templates
|-- Teacher And Student Views
`-- Publishing And Display Paths
```

## Internal Entity And Flow Tree

```text
Academic section
|-- Planned timetable
|-- Runtime class slots
`-- Teacher/student timetable views
```

Primary implementation sources:

- `backend/app/api/v1/endpoints/timetables.py`
- `backend/app/api/v1/endpoints/class_slots.py`
- `backend/app/schemas/timetable.py`
- `backend/app/schemas/class_slot.py`
- `frontend/src/pages/TimetablePage.jsx`
- `frontend/src/pages/ClassSlotsPage.jsx`
- `frontend/src/services/timetableApi.js`

Specification reference:

- `docs/archives/OLD_DATA/TIMETABLE_MODULE_GUIDE.md`

This document describes the timetable module as it exists now and identifies where the older specification is only partially implemented.

## 1. Module Overview

The Timetable Module manages academic schedule planning and timetable publication for sections. It supports:

- shift-based timetable generation
- draft and published timetable versions
- class coordinator scoped timetable editing
- teacher and room conflict validation
- student timetable viewing
- lower-level class slot management tied to course offerings

The module is split into two operational layers:

1. `timetables`
   - shift-based, section-level weekly timetable grid
   - intended for timetable planning, allocation, publishing, and student visibility

2. `class_slots`
   - lower-level period records tied to `course_offerings`
   - used directly by students and attendance flows

This is important architecturally:

- the published timetable grid is the planning layer
- `class_slots` is the execution layer currently used by attendance and student daily timetable rendering

## 2. Functional Scope

### Timetable Grid Layer

The `timetables` API supports:

- listing supported shift templates
- generating timetable grids from shift templates
- fetching class/subject/teacher lookup data
- creating timetable drafts
- updating timetable drafts
- publishing timetables
- admin locking and unlocking of published timetables
- fetching student published timetable by enrollment context

### Class Slot Layer

The `class_slots` API supports:

- listing slots
- creating slots
- updating slots
- archiving slots
- student self-view of active class slots

### Downstream Dependencies

The timetable module depends on:

- `classes` for section identity and coordinator ownership
- `subjects` for subject existence and weekly limits
- `users` for teacher assignment
- `enrollments` and `students` for student timetable resolution
- `course_offerings` for class slot ownership and filtering
- `attendance_records` which references `class_slot_id`

## 3. Shift Model

The code currently supports two built-in shift templates.

### `shift_1`

- label: `Shift 1 (Morning)`
- start: `08:30`
- end: `14:20`
- lunch: `12:00` to `12:50`

### `shift_2`

- label: `Shift 2 (Mid)`
- start: `11:20`
- end: `16:50`
- lunch: `12:50` to `13:40`

### Current Shift Rules Enforced

- shift id must be one of:
  - `shift_1`
  - `shift_2`
- grid slots are generated from the selected shift template
- lunch slot is present in generated templates
- lunch slot is non-editable
- timetable entry `slot_key` must belong to the selected shift template
- no duplicate allocation for the same `day + slot_key` in a single timetable
- timetable entries cannot target lunch slots

### Important Current Limitation

The earlier specification called for admin-configurable shift templates. That is not implemented yet.

Current state:

- shift templates are hardcoded in `SHIFT_CONFIG`
- there is no admin API for editing shift templates
- there is no template versioning

## 4. Slot Generation Logic

Generated slots come from `_build_slots(shift_id)` in `timetables.py`.

Current behavior:

- builds timetable slots from shift start to shift end
- inserts one lunch slot at the configured lunch boundary
- uses:
  - `DEFAULT_PERIOD_MINUTES = 50`
  - `MIN_SLOT_MINUTES = 35`
- marks lunch as:
  - `is_lunch = true`
  - `is_editable = false`
- marks lecture periods as:
  - `is_lunch = false`
  - `is_editable = true`

### Implementation Detail

Slot generation is arithmetic rather than institution-template driven.

That means:

- the current grid is generated from time windows
- it does not exactly encode the richer handwritten institutional timetable pattern from the archived guide

This is acceptable for a functional first version, but it is not yet a fully configurable registrar-grade slot engine.

## 5. Database Collections

The timetable module directly or indirectly uses the following collections.

### `timetables`

Purpose:

- stores section-level timetable drafts and published versions

Key fields:

- `_id`
- `class_id`
- `semester`
- `shift_id`
- `days`
- `slots`
- `entries`
- `status`
- `version`
- `admin_locked`
- `published_at`
- `published_by_user_id`
- `created_by_user_id`
- `is_active`
- `created_at`
- `updated_at`

Relations:

- belongs to `classes` via `class_id`
- entry rows reference:
  - `subjects`
  - `users` as teachers

Important status model:

- `draft`
- `published`

Version behavior:

- new timetable draft version increments from previous class + semester + shift history
- publishing archives previous published version for the same class and semester

Indexes present:

- `(class_id, semester, status, is_active)`
- `(entries.teacher_user_id, status)`
- `(entries.room_code, status)`

### `timetable_subject_teacher_maps`

Purpose:

- stores allowed teacher assignments for subjects inside a class timetable context

Key fields:

- `class_id`
- `subject_id`
- `teacher_user_ids`
- `updated_at`

Relations:

- belongs to `classes` via `class_id`
- belongs to `subjects` via `subject_id`
- references `users` by `teacher_user_ids`

Constraint:

- unique on `(class_id, subject_id)`

### `class_slots`

Purpose:

- stores executable schedule slots for individual course offerings

Key fields:

- `_id`
- `course_offering_id`
- `day`
- `start_time`
- `end_time`
- `room_code`
- `is_active`
- `created_by_user_id`
- `created_at`
- `deleted_at`

Relations:

- belongs to `course_offerings` via `course_offering_id`
- consumed by `attendance_records.class_slot_id`

Indexes present:

- `(course_offering_id, day, start_time, is_active)`
- `(day, room_code, is_active)`

### Indirect Collections

The timetable module also reads or validates against:

#### `classes`

Used for:

- class existence
- section identity
- coordinator ownership via `class_coordinator_user_id`

#### `subjects`

Used for:

- subject existence checks
- weekly limit checks
- hydrated display data

#### `users`

Used for:

- teacher assignment
- teacher identity hydration
- teacher role validation

#### `students`

Used for:

- locating student profile by email
- student self-view timetable resolution

#### `enrollments`

Used for:

- resolving a student's enrolled class when loading `/timetables/my`

#### `course_offerings`

Used for:

- class slot ownership
- student filtering of class slot visibility

#### `attendance_records`

Used downstream, not by timetable write logic directly.

It depends on:

- `class_slot_id`

## 6. Backend Logic Implemented

### Class Scope Access

Timetable management is scoped through `_ensure_class_scope_access(...)`.

Behavior:

- admin can access any class timetable
- teacher write access requires:
  - teacher role
  - `class_coordinator` in `extended_roles`
  - class ownership through `class_coordinator_user_id`
- teacher read access is restricted to assigned classes
- students do not use class timetable listing routes; they use `/timetables/my`

This is one of the strongest access-control implementations in the module.

### Grid Validation

`_validate_entries(...)` enforces:

- day must belong to allowed timetable days
- slot key must exist in the selected shift template
- lunch slot cannot be edited
- no duplicate allocation of same day and slot for the class
- subject must exist
- teacher must exist
- assigned teacher role must be `teacher` or `admin`

### Subject Weekly Limit Validation

The backend checks how many times a subject appears in the submitted timetable.

Rule:

- count per subject cannot exceed `subject.weekly_limit`
- if `weekly_limit` is absent, default limit is `6`

### Subject-Teacher Mapping Consistency

If `timetable_subject_teacher_maps` contains mappings for a class:

- a teacher assigned to a timetable entry must belong to the allowed mapped teachers for that subject

This prevents arbitrary teacher allocation where a class-subject teacher map already exists.

### Conflict Validation

The timetable engine validates conflicts against active draft and published timetables of other classes in the same semester.

Conflict types:

- teacher conflict
- room conflict

Conflict logic uses:

- overlapping day
- overlapping time window
- same teacher
- same room

### Draft, Publish, and Lock Logic

#### Draft creation

- creates a new timetable row
- stores generated slots
- stores entries or imports from a template timetable if provided
- increments version based on prior class + semester + shift rows

#### Draft update

- only allowed for active drafts
- blocked if `admin_locked = true`
- blocked if timetable status is already `published`

#### Publish

- revalidates entries
- archives previously published timetable for same class and semester
- marks current row as `published`
- stamps:
  - `published_at`
  - `published_by_user_id`

#### Admin lock

- admin-only
- toggles `admin_locked`

### Student Timetable Resolution

Student published timetable resolution works differently from teacher/admin flows.

`GET /timetables/my`:

- finds student profile by current user email
- fetches enrollment history
- resolves the enrolled class
- returns the latest published timetable for that class

This is the official student grid-based timetable view.

### Class Slot Conflict Logic

`class_slots.py` validates:

- `start_time < end_time`
- teacher conflict by overlapping slot
- room conflict by overlapping slot
- teacher write access via class coordinator ownership of the offering's section

### Student Class Slot View

Students also have `GET /class-slots/my`.

This returns:

- active slots for course offerings of the student's class
- group-aware filtering using `group_id`

In the current frontend, the student timetable page renders from `class_slots/my`, not from the published `timetables/my` grid endpoint.

That is an important implementation split.

## 7. API Endpoints

### Timetable Endpoints

#### `GET /timetables/shifts`

Purpose:

- returns current shift templates and generated slots

Access:

- admin
- teacher
- student

#### `POST /timetables/generate-grid`

Purpose:

- generates timetable grid from shift and day list

Access:

- admin
- teacher

#### `GET /timetables/lookups`

Purpose:

- returns lookup data for timetable creation

Payload includes:

- classes
- subjects
- teachers
- teacher-by-subject map

Access:

- admin
- teacher

#### `POST /timetables/`

Purpose:

- create timetable draft

Access:

- admin
- teacher

#### `GET /timetables/class/{class_id}`

Purpose:

- list timetable versions for a class

Access:

- admin
- teacher

Students are explicitly denied here.

#### `GET /timetables/my`

Purpose:

- return student published timetable by enrollment

Access:

- student

#### `PUT /timetables/{timetable_id}`

Purpose:

- update draft timetable

Access:

- admin
- teacher with class coordinator scope

#### `POST /timetables/{timetable_id}/publish`

Purpose:

- publish timetable

Access:

- admin
- teacher with class coordinator scope

#### `POST /timetables/{timetable_id}/lock`

Purpose:

- lock or unlock timetable

Access:

- admin only

### Class Slot Endpoints

#### `GET /class-slots/`

Purpose:

- list class slots

Access:

- admin
- teacher
- student

Student behavior is internally filtered to their own class and group context.

#### `GET /class-slots/my`

Purpose:

- list current student's active class slots

Access:

- student

#### `POST /class-slots/`

Purpose:

- create class slot

Access:

- admin
- teacher with ownership of offering section

#### `PUT /class-slots/{slot_id}`

Purpose:

- update class slot

Access:

- admin
- teacher with ownership of offering section

#### `DELETE /class-slots/{slot_id}`

Purpose:

- archive class slot

Access:

- admin
- teacher with ownership of offering section

## 8. Frontend Implementation

### `TimetablePage.jsx`

This page supports two distinct experiences.

#### Student mode

Behavior:

- loads `GET /class-slots/my`
- loads `GET /course-offerings/`
- groups rows by day
- renders printable day cards

Important note:

- student mode does not consume the published timetable grid endpoint
- it consumes class slots

#### Admin / Teacher mode

Behavior:

- loads shifts via `getTimetableShifts()`
- loads timetable lookups via `/timetables/lookups`
- loads class timetable versions
- allows:
  - create draft
  - save draft
  - publish timetable
- renders grid with:
  - days as columns
  - slots as rows
  - lunch cells as locked

UI-managed fields:

- class
- semester
- shift
- timetable version
- subject
- teacher
- room
- session type

Visible session types:

- theory
- practical
- workshop
- interaction

### `ClassSlotsPage.jsx`

This page is built with `EntityManager`.

Behavior:

- admin and teacher see CRUD page
- student sees read-only self slots via `/class-slots/my`
- filters:
  - offering
  - day
  - active
- create fields:
  - offering
  - day
  - start time
  - end time
  - room

Current limitations:

- edit is not enabled in the page config even though backend update exists
- student view is simplified and not a timetable grid

### Frontend Feature Access

Feature access currently includes:

- `timetable` for admin, teacher, student

The sidebar exposes:

- `/timetable`
- `/class-slots`

## 9. Implemented vs Intended Specification

The archived timetable guide defines a larger target model. The current implementation only partially matches it.

### Already Implemented

- shift-based timetable model
- two built-in shifts
- lunch lock in generated timetable slots
- grid generation by shift
- teacher and room conflict detection
- published timetable versions
- admin lock/unlock
- coordinator-scoped teacher editing
- student timetable access

### Partially Implemented

- timetable creation currently selects:
  - class
  - semester
  - shift
- the older guide expected:
  - program
  - batch
  - semester
  - section
  - academic year
  - shift

In current code, class encapsulates most of the section context, so the flow is simpler but less explicit.

### Not Yet Implemented

- admin-configurable shift templates
- template versioning for shift definitions
- explicit academic year in timetable entity
- section-level shift binding stored on section itself
- explicit enforcement that a section belongs to one shift permanently
- richer institutional slot template editing

## 10. Architectural Issues

### Two Scheduling Models Exist

The module currently has two timetable representations:

1. `timetables`
   - shift-bound planning grid
   - status/version model
   - publish workflow

2. `class_slots`
   - offering-level executable schedule rows
   - used by student daily timetable and attendance

This creates a product-level ambiguity:

- which one is the authoritative student timetable
- whether publishing a timetable should generate class slots
- whether class slots should instead be derived from published timetable

### Current Reality

Right now:

- timetable planning and publishing exists in `timetables`
- student runtime schedule display depends on `class_slots`
- attendance also depends on `class_slots`

This means the execution layer is not fully unified with the planning layer.

### Shift Template Hardcoding

Shift templates are embedded in backend code.

Consequences:

- no admin configurability
- no template history
- no per-semester schedule evolution

### Missing Academic-Year Dimension

The archived specification expected academic year as a first-class scheduling context.

Current state:

- timetable documents store `semester`
- they do not store `academic_year`

That weakens long-term version traceability across sessions.

## 11. Bugs, Gaps, and Risks

### Student UI Uses Class Slots, Not Published Timetable

This is the most important behavior gap in the module.

Impact:

- student sees active class slot rows
- student does not necessarily consume the published timetable artifact
- publication workflow and student rendering are not fully unified

### `shift_2` Label Drift

Specification language uses `Late Shift`.

Current code label is:

- `Shift 2 (Mid)`

This is a documentation and UX inconsistency.

### Class Slot Edit Capability Exists but UI Does Not Expose It

Backend:

- supports `PUT /class-slots/{slot_id}`

Frontend:

- `ClassSlotsPage.jsx` does not enable edit

### No Governance Workflow on Timetable Destructive Actions

Unlike some academic setup deletes, timetable and class slot destructive operations currently do not use the governance review pattern.

### No Telemetry/Audit Layer Specific to Timetable Publishing

The timetable module does not currently show explicit publish/lock telemetry instrumentation comparable to the academic setup destructive-action telemetry work.

## 12. Cleanup Strategy

### Preferred Target Architecture

The cleaner operating model is:

- `timetables` becomes the authoritative planning and publication artifact
- `class_slots` becomes either:
  - derived runtime rows generated from published timetable, or
  - a lower-level manual override layer with explicit synchronization rules

### Recommended Refactor Sequence

#### Phase 1

Clarify source of truth.

- decide whether students should consume `published timetables` or `class_slots`
- if `class_slots` stays runtime source, document and automate synchronization from published timetable

#### Phase 2

Add missing first-class context.

- add `academic_year` to timetable records
- decide whether section shift should be stored on section entity

#### Phase 3

Externalize shift templates.

- move `SHIFT_CONFIG` into persisted admin-managed configuration
- add template versioning

#### Phase 4

Close UI/backend exposure gaps.

- enable `ClassSlotsPage` edit if intended
- add admin lock UI if needed
- decide whether teachers should create class slots directly or only through timetable publish

#### Phase 5

Add operational observability.

- publish telemetry
- lock/unlock telemetry
- timetable version audit trail

## 13. Testing Requirements

### Backend Tests

- shift template list returns both supported shifts
- lunch slot is generated and locked for each shift
- invalid slot key is rejected
- lunch slot edit is rejected
- duplicate day + slot allocation is rejected
- teacher conflict is rejected
- room conflict is rejected
- subject weekly limit is enforced
- teacher must exist and have valid role
- mapped subject-teacher constraint is enforced
- draft update blocked when published
- draft update blocked when admin locked
- publish archives previous published version for same class and semester
- student timetable lookup resolves by enrollment

### Class Slot Tests

- start time must be before end time
- teacher conflict on overlapping slot is rejected
- room conflict on overlapping slot is rejected
- class coordinator ownership is enforced
- student `my` slot filtering respects group and section context

### Frontend Tests

- timetable page loads shifts and lookups
- lunch cells render locked
- draft creation requires class, semester, and shift
- publish flow persists and refreshes selected timetable
- student page renders grouped day cards from slot data

### Integration Tests

- publishing timetable and student runtime view stay consistent
- teacher role can manage only assigned section timetable
- admin can lock and unlock published timetable
- class slot attendance integration remains valid

## Final Summary

The timetable module is functional, but it is split between:

- a section-level grid planning system
- a class-slot execution system

Its strongest implemented features are:

- shift-based slot generation
- lunch protection
- teacher and room conflict validation
- coordinator-scoped access
- draft and publish workflow

Its main architectural weakness is that the planning artifact and the runtime student-facing artifact are not yet one unified model.

That is the core issue to solve before the timetable module can be considered fully consolidated.