# CLASS SLOT MODULE MASTER

## Module Tree

```text
Class Slot Module
|-- Runtime Teaching Schedule
|-- Teacher Conflict Checks
|-- Room Conflict Checks
|-- Coordinator Slot Management
`-- Student Slot Visibility
```

## Internal Entity And Flow Tree

```text
Course offering
`-- Class slot
    |-- Attendance session anchor
    |-- Timetable visibility anchor
    `-- Teacher and room conflict validation
```

## 1. Module Overview

The class slot module is the runtime scheduling layer for actual teachable time blocks. In CAPS AI, it sits below course offerings and above attendance and student timetable consumption.

A class slot answers a concrete operational question:

- when, on which day, and in which room is a specific course offering delivered?

This is not the same as the higher-level timetable template or shift model. It is a narrower execution-layer schedule record.

The module currently models:

- day of week
- start time
- end time
- room
- linked course offering

and it enforces:

- teacher conflict detection
- room conflict detection

## 2. Core Domain Model

### 2.1 Primary entity

The module centers on:

- `class_slots`

Each slot belongs to:

- exactly one `course_offering`

Through the offering, a slot is indirectly tied to:

- subject
- teacher
- section
- batch
- semester
- optional group
- academic year

### 2.2 Operational role

This module is the actual schedule execution layer used by:

- attendance marking
- student timetable retrieval
- teacher timetable views
- dashboard schedule tiles

That makes it more important than a simple scheduling helper table.

## 3. Database Collection

### 3.1 `class_slots`

Purpose:

- stores concrete scheduled teaching slots for active offerings

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

- `course_offering_id -> course_offerings._id`

Indirect relations via the offering:

- `teacher_user_id`
- `section_id`
- `group_id`
- `subject_id`

### 3.2 Field semantics

- `day` is constrained to:
  - `Monday`
  - `Tuesday`
  - `Wednesday`
  - `Thursday`
  - `Friday`
  - `Saturday`
- `start_time` and `end_time` use `HH:MM`
- `room_code` is freeform text up to 80 chars

### 3.3 Indexes

Observed index in [indexes.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\core\indexes.py):

- `(course_offering_id, day, start_time, is_active)`

This supports:

- per-offering slot lookup
- slot ordering and filtering

Important gap:

- there is no visible unique index preventing exact duplicate room/day/time or offering/day/time rows
- conflict prevention is application-enforced

## 4. Backend Logic Implemented

Primary backend file:

- [class_slots.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\api\v1\endpoints\class_slots.py)

Supporting files:

- [class_slot.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\schemas\class_slot.py)
- [class_slots.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\models\class_slots.py)

### 4.1 Offering dependency

All write operations begin by loading an active course offering.

If the offering does not exist or is inactive:

- write fails with `Course offering not found`

This means class slots cannot exist independently of offerings.

### 4.2 Write access model

Write roles:

- `admin`
- `teacher`

Teacher write constraint:

- teacher must be the `class_coordinator_user_id` of the offering’s section

Important implication:

- the assigned teacher on the offering is not automatically allowed to manage class slots
- slot management is coordinator-centric, not offering-teacher-centric

### 4.3 Conflict validation

Shared validator:

- `_validate_slot_conflicts(...)`

Rules implemented:

- `start_time` must be before `end_time`
- teacher cannot have overlapping slots on the same day
- room cannot have overlapping slots on the same day

How it works:

- loads all active slots for the given day
- resolves their offerings to identify teacher ownership
- compares intervals using overlap logic

Conflict errors returned:

- `Teacher conflict on selected day/time`
- `Room conflict on selected day/time`

### 4.4 List slots

Endpoint:

- `GET /class-slots/`

Roles:

- `admin`
- `teacher`
- `student`

Filters supported:

- `course_offering_id`
- `day`
- `section_id`
- `is_active`
- `skip`
- `limit`

Behavior by role:

- admin and teacher can query directly
- if `section_id` is provided, backend resolves matching active offering ids first
- student path ignores arbitrary broad access and instead derives offerings from the student’s own section/group

### 4.5 Student slot access

Student-specific behavior in list endpoint:

- resolves student by:
  - `students.email == current_user.email`
- requires student to have `class_id`
- loads active offerings where:
  - `section_id == student.class_id`
  - and offering group is either:
    - `null`
    - or equal to student `group_id`

There is also a student convenience endpoint:

- `GET /class-slots/my`

This returns all active slots for the student’s effective offerings.

### 4.6 Create slot

Endpoint:

- `POST /class-slots/`

Roles:

- `admin`
- `teacher`

Behavior:

- validates active offering
- enforces write access
- checks time conflicts
- creates active slot with creator metadata

### 4.7 Update slot

Endpoint:

- `PUT /class-slots/{slot_id}`

Roles:

- `admin`
- `teacher`

Behavior:

- slot must exist
- loads current offering
- enforces write access
- recalculates effective target day/time/room
- revalidates conflicts
- updates mutable fields

### 4.8 Archive slot

Endpoint:

- `DELETE /class-slots/{slot_id}`

Roles:

- `admin`
- `teacher`

Behavior:

- slot must exist and be active
- enforces write access
- soft archives by setting:
  - `is_active = false`
  - `deleted_at`

Important gap:

- no governance review
- no audit event
- no destructive telemetry observed

## 5. Schema Contract

Schema file:

- [class_slot.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\schemas\class_slot.py)

Create contract:

- `course_offering_id`
- `day`
- `start_time`
- `end_time`
- `room_code`

Update contract:

- `day`
- `start_time`
- `end_time`
- `room_code`
- `is_active`

Output contract:

- `id`
- `course_offering_id`
- `day`
- `start_time`
- `end_time`
- `room_code`
- `is_active`
- `created_at`

Important limitation:

- response does not include enriched offering metadata
- clients need a separate offering lookup to show subject, teacher, or section names

## 6. Frontend Implementation

Primary page:

- [ClassSlotsPage.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\ClassSlotsPage.jsx)

### 6.1 Frontend behavior

The page uses shared `EntityManager` CRUD scaffolding.

Lookups loaded:

- active offerings from `/course-offerings/`

Student behavior:

- endpoint switches to:
  - `/class-slots/my`
- create is hidden
- delete is disabled

Admin/teacher behavior:

- endpoint uses:
  - `/class-slots/`
- create is shown
- delete is enabled

### 6.2 Filters exposed in UI

- offering
- day
- active

Backend supports one additional useful filter not exposed prominently:

- `section_id`

### 6.3 Create UI fields

- offering
- day
- start time
- end time
- room/lab

### 6.4 List UI columns

- offering
- day
- start
- end
- room

### 6.5 Label quality issue

Offering labels in the UI are currently built as:

- `section_id | academic_year | offering_type`

This is technically functional but weak for operators.

It should ideally use:

- section name
- subject name
- teacher name

## 7. Downstream Dependencies

### 7.1 Attendance

Attendance records depend directly on class slots.

Observed in:

- [attendance_records.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\api\v1\endpoints\attendance_records.py)

Attendance logic uses:

- class slot
- linked course offering
- section and optional group membership

Attendance marking authority:

- admin
- mapped offering teacher
- class coordinator

This is important because attendance authority is broader than slot management authority.

### 7.2 Student timetable and dashboard

Student schedule views are built from:

- class slots
- joined with course offerings for labels

Observed in:

- [TimetablePage.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\TimetablePage.jsx)
- [DashboardPage.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\DashboardPage.jsx)

### 7.3 Timetable architecture relationship

The class slot module is not the same as the higher-level timetable module.

Current architectural reality:

- `timetables` store broader planning/grid data
- `class_slots` store executable runtime teaching slots tied to offerings

This dual schedule model must be understood clearly to avoid incorrect assumptions.

## 8. Business Rules

### 8.1 Slot validity

- start must be before end
- day must be a valid configured weekday enum

### 8.2 Teacher conflict rule

- one teacher cannot be scheduled in overlapping slots on the same day

### 8.3 Room conflict rule

- one room cannot host overlapping slots on the same day

### 8.4 Student visibility rule

Students can only see slots for offerings in:

- their section
- and, when group-restricted, their own group

### 8.5 Coordinator write rule

Teacher writes are limited to sections they coordinate.

This means:

- class coordinators manage slot structure
- offering teacher identity alone does not grant slot write access

## 9. Frontend vs Backend Gaps

### 9.1 UI does not expose section filter

Backend supports `section_id` filtering, but the main UI does not expose it directly.

### 9.2 UI labels are too technical

Offering labels use ids and offering type rather than enriched names.

### 9.3 No shift-template awareness

The slot module currently accepts freeform start/end times and does not enforce the shift-template timetable model described elsewhere.

This is a significant gap if the institutional timetable is supposed to be shift-driven.

### 9.4 Delete safety is weak

Delete is available in UI and backend, but there is:

- no governance gate
- no warning about existing attendance records

## 10. Architectural Issues

### 10.1 Class slots are more operationally real than timetables in some flows

Attendance and student schedule views depend on class slots, not directly on timetable definitions.

This means class slots are effectively the runtime truth in many workflows.

### 10.2 Slot ownership differs from attendance ownership

Slot writes require section coordinator scope, but attendance marking allows:

- assigned offering teacher
- or class coordinator

This split may be intentional, but it should be explicit because it creates different authority models around the same lesson.

### 10.3 Freeform time slots conflict with shift-template ambition

The module currently allows arbitrary `HH:MM` start/end values.

That conflicts with a stricter institutional model where:

- slots should come from shift templates
- lunch slots are protected
- out-of-shift times are invalid

### 10.4 Conflict detection is app-layer and bounded

Conflict detection loads up to `5000` active day rows and checks overlaps in memory.

This is workable now, but it is not ideal long term for scale.

## 11. Risks and Bugs Identified

### 11.1 No governance or telemetry on slot deletion

Compared to hardened academic setup deletes, slot archive is lightweight and operationally under-protected.

### 11.2 No dependency protection for attendance history

A slot can be archived even if it already has attendance records linked to it.

Risk:

- historical attendance semantics become ambiguous

### 11.3 Identity resolution for students still uses email

Like several student-scoped modules, slot visibility relies on student lookup by email.

Risk:

- auth email drift breaks schedule visibility

### 11.4 Labeling can hide operator mistakes

Because the UI labels offerings poorly, coordinators may create or edit slots against the wrong offering.

## 12. Cleanup Strategy

### 12.1 Keep class slots as runtime schedule truth

This module should remain the executable schedule layer.

### 12.2 Align with shift-template timetable model

If the institutional shift model is mandatory, enforce:

- allowed slot boundaries
- valid shift-specific time windows
- protected lunch slots

at class-slot creation/update time.

### 12.3 Add enriched labels everywhere

Use offering-derived labels like:

- section name
- subject code/name
- teacher name

instead of raw ids.

### 12.4 Add safer archive rules

Before allowing delete/archive, check for:

- attendance records
- published timetable dependencies if applicable

and either block, require governance, or mark as historical-only.

### 12.5 Review authority model

Decide explicitly whether slot management should remain:

- section coordinator only

or expand to:

- assigned offering teacher

## 13. Testing Requirements

### 13.1 Unit tests

- start before end validation
- teacher conflict detection
- room conflict detection
- student offering/group slot filtering
- teacher write access by coordinator scope
- admin write access

### 13.2 Integration tests

- create slot for offering
- student `/class-slots/my` returns only own allowed rows
- slot update revalidates conflicts
- slot archive hides from active queries
- attendance records respect offering/section/group lineage through slot

### 13.3 Frontend tests

- student page uses `/class-slots/my`
- create hidden for students
- delete disabled for students
- offering select renders correctly
- day filter works

## 14. Current Module Assessment

The class slot module is small, but structurally important. It is the runtime scheduling engine that real student and attendance workflows depend on.

Strengths:

- clear dependency on course offerings
- practical teacher and room conflict checks
- student scoping is implemented
- frontend CRUD exists

Weaknesses:

- weak delete safety
- no governance or audit parity
- no shift-template enforcement
- poor operator labeling

As implemented today, the module is usable and operationally meaningful, but it is still a lightweight runtime scheduler rather than a fully policy-driven institutional timetable engine.