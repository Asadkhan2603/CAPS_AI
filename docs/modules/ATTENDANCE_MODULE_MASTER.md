# Attendance Module Master

## Module Tree

```text
Attendance Module
|-- Classroom Attendance
|-- Internship Attendance
|-- Attendance Records
|-- Teacher Marking Flows
`-- Student Visibility Flows
```

## Internal Entity And Flow Tree

```text
Class Slot
`-- Attendance session
    `-- Attendance records
        |-- Teacher mark/update
        `-- Student attendance visibility

Internship assignment
`-- Internship attendance records
```

Primary implementation sources:

- `backend/app/api/v1/endpoints/attendance_records.py`
- `backend/app/api/v1/endpoints/class_slots.py`
- `backend/app/schemas/attendance_record.py`
- `backend/app/schemas/class_slot.py`
- `backend/app/schemas/internship_session.py`
- `backend/app/models/attendance_records.py`
- `backend/app/models/class_slots.py`
- `frontend/src/pages/AttendanceRecordsPage.jsx`
- `frontend/src/pages/ClassSlotsPage.jsx`
- `frontend/src/pages/DashboardPage.jsx`
- `frontend/src/config/featureAccess.js`

Related references:

- `docs/modules/TIMETABLE_MODULE_MASTER.md`
- `docs/modules/ACADEMIC_MODULE_MASTER.md`
- `backend/app/core/indexes.py`
- `backend/app/api/v1/router.py`

## 1. Module Overview

The attendance module is the operational execution layer for teaching presence tracking. It is not a standalone academic structure module. It sits on top of:

- section membership from the academic module
- course offerings from the teaching allocation layer
- class slots from the timetable execution layer

The current implementation covers two distinct attendance domains:

1. classroom attendance
   - teacher or coordinator marks a student's presence against a concrete `class_slot`
2. internship attendance
   - student clocks in and clocks out for internship sessions through dashboard actions

That means the current attendance module is partly academic and partly workforce-style session tracking. The code keeps both under `/attendance-records`, which is functionally workable but architecturally mixed.

## 2. Domain Boundaries

### Classroom Attendance Path

The implemented dependency chain is:

`Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section -> Course Offering -> Class Slot -> Attendance Record`

Attendance records are not created directly against section, subject, or timetable documents. They are created against a concrete `class_slot_id`.

### Internship Attendance Path

The internship sub-module does not depend on class slots. It uses:

`Student User -> Student Profile -> Internship Session`

This flow is operationally separate from lecture attendance but currently exposed through the same endpoint file.

## 3. Data Model

### `class_slots`

Purpose:

- stores executable teaching sessions for a course offering
- feeds the student daily schedule view
- acts as the anchor for classroom attendance

Key fields:

- `course_offering_id`
- `day`
- `start_time`
- `end_time`
- `room_code`
- `is_active`
- `created_by_user_id`
- `created_at`
- `deleted_at` on archive path

Relations:

- belongs to one `course_offering`
- indirectly belongs to one `section`
- indirectly belongs to one teacher through `course_offerings.teacher_user_id`
- referenced by `attendance_records.class_slot_id`

Validation implemented:

- `day` must be one of `Monday` to `Saturday`
- `start_time` and `end_time` must match `HH:MM`
- `start_time < end_time`
- no teacher overlap on the same day and time
- no room overlap on the same day and time

Indexes:

- `(course_offering_id, day, start_time, is_active)`
- `(day, room_code, is_active)`

### `attendance_records`

Purpose:

- stores one attendance decision per student per class slot
- supports single mark and bulk mark flows

Key fields:

- `class_slot_id`
- `student_id`
- `status`
- `note`
- `marked_by_user_id`
- `marked_at`

Relations:

- belongs to one `class_slot`
- belongs to one student
- inherits teaching context from the related course offering and section

Status values:

- `present`
- `absent`
- `late`
- `excused`

Write semantics:

- stored by upsert on `(class_slot_id, student_id)`
- a second mark overwrites the previous value instead of creating history rows

Indexes:

- unique `(class_slot_id, student_id)`
- `(student_id, marked_at)`

### `internship_sessions`

Purpose:

- stores student internship clock-in and clock-out state

Key fields:

- `student_user_id`
- `student_id`
- `status`
- `clock_in_at`
- `clock_out_at`
- `total_minutes`
- `auto_closed`
- `note`
- `created_at`
- `updated_at`

Status values observed in code:

- `active`
- `closed`
- `auto_closed`

Indexes:

- `(student_user_id, clock_in_at)`
- `(status, clock_in_at)`

## 4. Backend Logic Implemented

### Student Resolution

`attendance_records.py` accepts `student_id` in two forms:

- Mongo object id
- roll number

Resolution order:

1. try `_id`
2. fallback to `roll_number`

This is practical for UI and manual operations, but it means the API contract is not strictly typed around one identifier.

### Slot + Offering Resolution

Before attendance is marked, the backend resolves:

1. `class_slot`
2. `course_offering` linked from that slot

If either is missing or inactive, the request fails.

This is the core rule that binds attendance to the actual teaching execution layer rather than the broader timetable document.

### Mark Access Enforcement

For classroom attendance:

- `admin` can mark attendance
- `teacher` can mark attendance only when one of these is true:
  - teacher is the mapped offering teacher
  - teacher is the section `class_coordinator_user_id`

Everyone else is denied.

This is one of the stronger access rules in the current codebase because it is row-aware and not just role-aware.

### Cross-Entity Validation

When marking classroom attendance, the backend checks:

- student exists and is active
- student belongs to the same section as the offering
- if the offering is group-specific, student must match that group

This prevents teachers from marking arbitrary students against unrelated sessions.

### Upsert-Based Attendance Write

Attendance is stored with:

- filter: `(class_slot_id, student_id)`
- operation: `$set`
- `upsert=True`

Implication:

- current status is mutable
- there is no built-in version history for status changes
- auditability of attendance changes depends on outer audit infrastructure, not attendance row history

### Bulk Mark Flow

`POST /attendance-records/mark-bulk`:

- resolves and authorizes the shared `class_slot_id` once
- iterates each record
- internally converts each child entry into a single-mark payload
- returns a list of normalized output rows

This is a straightforward implementation with low complexity, but it has no transaction boundary. Partial success behavior would depend on the first validation failure encountered.

### Class Slot Conflict Logic

`class_slots.py` prevents invalid slot scheduling by checking:

- invalid time order
- teacher conflicts
- room conflicts

Conflict checking is performed by:

1. loading all active slots for a given day
2. loading linked offerings to determine teacher ownership
3. comparing overlaps in memory

This works at current scale but does not use a more efficient indexed conflict query strategy.

### Student Slot Visibility

Students do not see arbitrary class slots. Backend filtering restricts them to offerings where:

- `section_id == student.class_id`
- offering is active
- `group_id is None` or matches `student.group_id`

This is used in:

- `GET /class-slots/`
- `GET /class-slots/my`

### Internship Session Logic

Internship attendance includes:

- `clock-in`
- `clock-out`
- `status`
- auto-close after configured hours

Auto-close rule:

- uses `INTERNSHIP_AUTO_LOGOUT_HOURS`
- minimum effective cutoff is 1 hour
- default config value is `9`

When status is queried or clock operations occur:

- active session may be auto-closed first
- then the endpoint returns the latest effective state

This avoids permanently stale active sessions when a student forgets to clock out.

## 5. Business Rules

### Classroom Attendance Rules

1. Attendance must belong to a valid active `class_slot`.
2. Class slot must belong to an active `course_offering`.
3. Only `admin` or an authorized teacher can mark attendance.
4. Student must belong to the offering section.
5. If the offering is group-scoped, student must belong to that group.
6. One student can have at most one current attendance row per class slot.
7. Re-marking updates the same row rather than creating a new one.

### Class Slot Scheduling Rules

1. `start_time` must be before `end_time`.
2. A teacher cannot have overlapping slots on the same day.
3. A room cannot have overlapping slots on the same day.
4. Only `admin` or section `class_coordinator` can create, update, or archive slots.
5. Students can read their own slots but cannot write them.

### Internship Attendance Rules

1. Only students can use internship attendance endpoints.
2. Student profile must exist and be active.
3. Only one active internship session can exist per student.
4. Active internship sessions auto-close after configured hours.
5. Manual clock-out finalizes the session and computes `total_minutes`.

## 6. API Endpoints

### Class Slot Endpoints

Base route: `/class-slots`

#### `GET /class-slots/`

Purpose:

- list class slots

Query parameters:

- `course_offering_id`
- `day`
- `section_id`
- `is_active`
- `skip`
- `limit`

Access:

- `admin`
- `teacher`
- `student`

Behavior:

- students are implicitly restricted to their own eligible offerings

#### `GET /class-slots/my`

Purpose:

- list current student's active class slots

Access:

- `student` only

#### `POST /class-slots/`

Purpose:

- create a class slot

Access:

- `admin`
- `teacher`

Write restrictions:

- teacher must be section coordinator for the related offering section

#### `PUT /class-slots/{slot_id}`

Purpose:

- update day, time, room, active flag

Access:

- `admin`
- `teacher`

Restrictions:

- same section coordinator rule
- conflict validation reruns

#### `DELETE /class-slots/{slot_id}`

Purpose:

- archive class slot

Access:

- `admin`
- `teacher`

Behavior:

- soft archive with `is_active = false`
- sets `deleted_at`

### Attendance Record Endpoints

Base route: `/attendance-records`

#### `GET /attendance-records/`

Purpose:

- list attendance records

Query parameters:

- `class_slot_id`
- `student_id`
- `skip`
- `limit`

Access:

- `admin`
- `teacher`
- `student`

Behavior:

- students are restricted to their own attendance rows

#### `POST /attendance-records/mark`

Purpose:

- mark one attendance record

Access:

- `admin`
- `teacher`

#### `POST /attendance-records/mark-bulk`

Purpose:

- mark multiple students for one class slot

Access:

- `admin`
- `teacher`

### Internship Endpoints

These live under the same attendance router.

#### `POST /attendance-records/internship/clock-in`

Access:

- `student`

#### `POST /attendance-records/internship/clock-out`

Access:

- `student`

#### `GET /attendance-records/internship/status`

Access:

- `student`

Purpose:

- fetch current or latest internship session state
- auto-close an expired active session if required

## 7. Frontend Implementation

### `AttendanceRecordsPage.jsx`

Role behavior:

- admin and teacher:
  - can view attendance records
  - can create via `/attendance-records/mark`
- student:
  - can view only
  - create form is hidden

UI characteristics:

- built on shared `EntityManager`
- supports filters:
  - class slot
  - student
- loads lookup data from:
  - `/class-slots/`
  - `/students/`
- delete is disabled

Important limitation:

- page exposes only single-record mark flow
- bulk attendance exists in backend but not in UI

### `ClassSlotsPage.jsx`

Role behavior:

- admin and teacher:
  - can list, create, and delete
- student:
  - endpoint switches to `/class-slots/my`
  - create is hidden
  - delete is disabled

UI characteristics:

- built on shared `EntityManager`
- filters:
  - section
  - offering
  - day
  - active
- edit is enabled for admin/teacher
- create fields:
  - offering
  - day
  - start time
  - end time
  - room code

Important limitation:

- offering labels are improved to section-aware labels such as:
  - `section name | academic_year | offering_type`
- the page still does not use full enriched offering labels such as subject name and teacher name
- page does not expose conflict visualization before submission

### Dashboard Student Attendance Surface

The student dashboard contains a separate attendance surface:

- internship status widget
- clock-in button
- clock-out button
- auto-close explanation

This means attendance UX is split across:

- `AttendanceRecordsPage`
- `ClassSlotsPage`
- `DashboardPage`

## 8. Frontend Access Control

`FEATURE_ACCESS` currently exposes:

- `classSlots` to `admin`, `teacher`, `student`
- `attendanceRecords` to `admin`, `teacher`, `student`

Frontend route guards are therefore broad. The backend remains the real enforcement layer.

Important consequence:

- a user may be able to navigate to a page because the frontend allows it
- but still be partially blocked by backend write rules tied to section ownership or student identity

This is acceptable from a security perspective, but it produces UX ambiguity because route access is wider than action access.

## 9. Current Strengths

### Strong Integrity Checks

The attendance write path validates:

- slot existence
- offering existence
- teacher ownership or coordinator authority
- student membership in the section
- group compatibility

This is materially stronger than a simple role-only attendance API.

### Concrete Execution Model

Attendance is tied to actual class slot execution rather than abstract semester or subject records. That gives the system:

- time-bound attendance context
- room context
- teacher context
- offering context

### Student Self-Service Internship Flow

Internship attendance is implemented end to end:

- backend endpoints
- auto-close behavior
- dashboard UI

That flow is usable today.

## 10. Current Gaps And Risks

### Attendance History Is Mutable, Not Immutable

Because attendance writes use upsert on the same row:

- the system keeps current truth
- but loses change history at the record level

If a teacher changes a student from `absent` to `present`, the original state is not preserved inside the attendance collection.

### Classroom And Internship Attendance Are Mixed

`attendance_records.py` owns both:

- lecture attendance
- internship sessions

That reduces modular clarity and makes the module harder to reason about.

### No Governance Pattern For Destructive Slot Operations

Unlike hardened academic setup deletes, class slot deletes currently:

- do not request `review_id`
- do not use governance review approval

This may be acceptable for low-risk scheduling edits, but it is a policy inconsistency.

### No Dedicated Bulk Mark UI

Bulk mark exists in backend but not in the main frontend workflow. This forces repetitive single-entry marking for typical classroom use.

### No Attendance Summary / Aggregation API

The module stores raw attendance but does not expose built-in attendance analytics such as:

- per student percentage
- per subject attendance
- low-attendance warnings
- section attendance sheet

Some grade and evaluation services use attendance percentages, but that appears to be separate numeric input rather than derived directly from this module.

### Class Slot Conflict Check Is In-Memory

Conflict detection loads all slots for a day into memory and compares overlaps in Python. This is acceptable for small data volumes but not ideal for large timetable density.

### Soft Delete Semantics For Class Slots Are Not Fully Standardized

Class slot delete sets:

- `is_active = false`
- `deleted_at`

It does not currently set:

- `deleted_by`

That is inconsistent with the newer academic setup delete standard.

## 11. Architectural Issues

### Dual Schedule Representation

Attendance depends on `class_slots`, while the timetable module also has `timetables`.

Current reality:

- `timetables` acts like planning and publication storage
- `class_slots` acts like executable runtime scheduling
- attendance depends on the runtime side only

This creates an architectural split. If published timetable and class slots diverge, attendance follows class slots, not the published timetable grid.

### Section Naming Conflict

The repo still has legacy naming around `classes` and canonical naming around `sections`.

Attendance logic still uses:

- `db.classes`
- offering field `section_id`

This is operationally fine but conceptually mixed.

### Enrollment Dependency Is Implicit

Attendance uses `students.class_id` and optionally `students.group_id`, but the module does not own those assignment rules. It assumes the academic and enrollment layers are already correct.

## 12. Cleanup Strategy

### Phase 1

- split internship attendance into its own endpoint module and master document
- keep classroom attendance focused on `class_slots` and `attendance_records`

### Phase 2

- decide whether `class_slots` is the canonical execution schedule
- if yes, define explicit projection rules from timetable publish to class slots

### Phase 3

- add immutable attendance event history or audit trail for mark changes
- standardize slot delete semantics with `deleted_by`

### Phase 4

- add bulk-mark UI
- add attendance summary and shortage APIs
- add section-wise attendance export

## 13. Testing Requirements

### Class Slot Tests

Required tests:

- create slot with valid offering and coordinator
- reject teacher who is not class coordinator
- reject invalid time order
- reject teacher overlap
- reject room overlap
- student list filtering by section and group
- archive slot behavior

### Attendance Record Tests

Required tests:

- mark single attendance for valid student in section
- reject student from wrong section
- reject wrong group membership
- overwrite existing attendance row for same slot and student
- bulk mark mixed valid records
- student self-view filtering

### Internship Tests

Required tests:

- clock-in success
- reject second active session
- clock-out success
- auto-close after configured hours
- status endpoint returns auto-closed state

### Integration Tests

Required tests:

- student dashboard internship widget matches backend status
- class slot creation followed by attendance marking
- attendance visibility matches offering and section ownership
- frontend route visibility stays aligned with backend role policy

## Final Summary

The attendance module is currently functional and more rigorous than a simple presence table because it ties marking to concrete class slots, teacher ownership, section membership, and group membership.

Its main strengths are:

- strong classroom attendance validation
- usable student internship workflow
- direct linkage to runtime teaching execution

Its main architectural gaps are:

- mixing classroom and internship attendance in one module
- dependency on `class_slots` while timetable planning also exists elsewhere
- mutable attendance history
- missing bulk-mark UI and summary APIs

The correct current interpretation is:

- `class_slots` is the operational attendance anchor
- `attendance_records` stores current classroom attendance state
- `internship_sessions` is a separate attendance concept currently sharing the same router

If the platform is hardened further, the next cleanup should be to separate internship attendance from classroom attendance and make the class slot layer explicitly canonical for runtime teaching operations.
