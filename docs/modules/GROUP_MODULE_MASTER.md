# GROUP MODULE MASTER

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
Group Module
|-- Section-Scoped Groups
|-- Group Membership Anchors
|-- Offering Scope Controls
|-- Slot Visibility Controls
`-- Attendance Eligibility Controls
```

## Internal Entity And Flow Tree

```text
Section
`-- Group
    |-- Student grouping
    |-- Course offering scope
    `-- Class slot and attendance scope
```

## 1. Module Overview

The group module partitions a section into smaller instructional sub-cohorts. In CAPS AI, groups are not decorative labels. They are operational routing units used to restrict course offerings, class slots, attendance eligibility, and student-visible schedules.

A group always belongs to a single section. Through that section, it is indirectly tied to:

- faculty
- department
- program
- specialization
- batch
- semester

This module is therefore a sub-section segmentation layer inside the canonical academic model.

## 2. Core Domain Model

### 2.1 Primary entity

The module centers on:

- `groups`

Each group represents a named and coded subset of a section.

Typical use cases:

- lab groups
- tutorial groups
- elective split groups
- practical section subdivisions

### 2.2 Why groups matter

Groups are used downstream in multiple operational rules:

- a course offering may be restricted to one group
- a class slot inherits that restriction through its course offering
- attendance marking rejects students outside the offering group
- student timetable and dashboard visibility hide group-scoped sessions not assigned to the student

That makes groups a real access and scheduling primitive.

## 3. Database Collection

### 3.1 `groups`

Purpose:

- stores section-scoped subgroups

Key fields:

- `_id`
- `section_id`
- `name`
- `code`
- `description`
- `is_active`
- `created_at`
- `deleted_at`

Relations:

- `section_id -> classes._id` even though conceptually this is the canonical section entity

Important note:

- the module still depends on the legacy `classes` collection name because canonical sections are stored there

### 3.2 Uniqueness behavior

The backend enforces active uniqueness for:

- `section_id + code`

Observed supporting indexes in [indexes.py](/backend/app/core/indexes.py):

- `(section_id, code, is_active)`
- `(section_id, is_active)`

This is one of the cleaner indexing stories in the academic-operations area.

## 4. Backend Logic Implemented

Primary backend file:

- [groups.py](/backend/app/api/v1/endpoints/groups.py)

Supporting files:

- [group_item.py](/backend/app/schemas/group_item.py)
- [groups.py](/backend/app/models/groups.py)

### 4.1 Section access model

Shared helper:

- `_ensure_section_access(...)`

Behavior:

- section must exist and be active
- admin can always proceed
- teacher:
  - read is allowed for section access
  - write requires the teacher to be the `class_coordinator_user_id`
- student:
  - cannot write
  - read is permitted only through student-scoped query shaping

This means group write authority is section-coordinator based.

### 4.2 List groups

Endpoint:

- `GET /groups/`

Roles:

- `admin`
- `teacher`
- `student`

Filters supported:

- `section_id`
- `q`
- `is_active`
- `skip`
- `limit`

Behavior:

- if `section_id` provided, backend validates access to that section first
- text search runs against:
  - `name`
  - `code`
- if caller is a student:
  - backend resolves the active student by email
  - forces `query["section_id"] = student.class_id`

Important limitation:

- students see groups for their whole section
- the backend does not restrict list output to only the student’s own group

That is not necessarily wrong, but it is a real visibility choice.

### 4.3 Create group

Endpoint:

- `POST /groups/`

Roles:

- `admin`
- `teacher`

Behavior:

- validates write access to target section
- normalizes `code` to uppercase
- blocks duplicate active `code` within the same section
- stores group as active with `created_at`

### 4.4 Update group

Endpoint:

- `PUT /groups/{group_id}`

Roles:

- `admin`
- `teacher`

Behavior:

- group must exist
- write access checked against the group’s section
- trims `name`
- uppercases `code`
- rechecks uniqueness of `code` within the same section

### 4.5 Archive group

Endpoint:

- `DELETE /groups/{group_id}`

Roles:

- `admin`
- `teacher`

Behavior:

- group must exist and be active
- write access checked against the group’s section
- soft archives by setting:
  - `is_active = false`
  - `deleted_at`

Important gaps:

- no governance gate
- no destructive telemetry
- no dependency check for students or offerings already attached to the group

## 5. Schema Contract

Schema file:

- [group_item.py](/backend/app/schemas/group_item.py)

Create fields:

- `section_id`
- `name`
- `code`
- `description`

Update fields:

- `name`
- `code`
- `description`
- `is_active`

Output fields:

- `id`
- `section_id`
- `name`
- `code`
- `description`
- `is_active`
- `created_at`

Important contract limitation:

- output does not include section name
- clients must join section data separately for human-readable display

## 6. Frontend Implementation

Primary page:

- [GroupsPage.jsx](/frontend/src/pages/GroupsPage.jsx)

### 6.1 Frontend behavior

The page uses shared `EntityManager` CRUD scaffolding.

It loads:

- all sections through [sectionsApi.js](/frontend/src/services/sectionsApi.js)

### 6.2 Filters exposed

- section
- search
- active

### 6.3 Create support

Create form exposes:

- section
- group name
- group code
- description

### 6.4 List support

Columns shown:

- section
- group
- code
- description

### 6.5 Delete support

The shared CRUD UI enables delete.

Important mismatch:

- backend delete is not governance-gated
- UI does not warn about downstream dependencies on students or offerings

## 7. Downstream Dependencies

### 7.1 Students

Student master records can store:

- `group_id`

Observed in:

- [students.py](/backend/app/api/v1/endpoints/students.py)

Validation already exists there:

- `group_id` must belong to the provided `class_id`

This means group membership is part of student academic assignment state.

### 7.2 Course offerings

Offerings can optionally target one group:

- `course_offerings.group_id`

Validation:

- `group_id` must belong to `section_id`

Observed in:

- [course_offerings.py](/backend/app/api/v1/endpoints/course_offerings.py)

### 7.3 Class slots

Slots do not store group directly, but they inherit group restriction through their course offering.

### 7.4 Attendance

Attendance marking rejects students who do not belong to the offering group when a group is present.

Observed in:

- [attendance_records.py](/backend/app/api/v1/endpoints/attendance_records.py)

### 7.5 Student timetable and dashboard

Student schedule views include only offerings where:

- `group_id` is null
- or `group_id == student.group_id`

This makes groups a real schedule-visibility control.

## 8. Business Rules

### 8.1 Group belongs to one section

This is the core structural rule.

### 8.2 Group code uniqueness

Within one active section:

- group code must be unique

### 8.3 Teacher write rule

Teachers can manage groups only if they coordinate the parent section.

### 8.4 Student visibility rule

Students can list groups only within their own section context.

### 8.5 Group-scoped teaching rule

When an offering specifies a group:

- only students in that group should see the offering and its slots
- only students in that group should be eligible for attendance in those slots

## 9. Frontend vs Backend Gaps

### 9.1 No dependency awareness in delete flow

The UI allows delete/archive but does not surface whether the group is already referenced by:

- students
- course offerings

### 9.2 No row-level teacher hinting

The frontend does not explain that teachers can only manage groups for sections they coordinate.

The backend enforces it, but the UI does not make the rule obvious.

### 9.3 No enriched section context

The page shows section names, but not richer academic context such as:

- batch
- semester
- program

This can matter when identical section names exist across academic contexts.

## 10. Architectural Issues

### 10.1 Groups are deeply operational but lightly protected

Because groups affect offerings, schedules, and attendance, archiving them without dependency checks is risky.

### 10.2 Group lifecycle is isolated from student reassignment lifecycle

The group module can archive a group, but the reviewed code does not show automatic handling for:

- students currently assigned to that group
- offerings currently scoped to that group

That creates potential orphaned references or invalid academic state.

### 10.3 Section naming debt leaks into groups

Groups correctly use `section_id`, but the actual storage and lookup still go through legacy `classes`.

This is acceptable for now, but it keeps the class/section naming debt alive in downstream modules.

## 11. Risks and Bugs Identified

### 11.1 No archive dependency protection

Archiving a group can leave downstream references intact in:

- students
- course offerings

Risk:

- inconsistent visibility and attendance behavior

### 11.2 No governance or telemetry on destructive action

Compared with hardened academic setup entities, group delete is still lightweight.

### 11.3 Student visibility may be broader than intended

Students can list all groups in their section, not only their assigned group.

This may be acceptable, but if groups are meant to hide cohort structure, the current visibility is too broad.

## 12. Cleanup Strategy

### 12.1 Keep groups as section-scoped sub-cohorts

This is the correct conceptual role for the module.

### 12.2 Add dependency-aware archive protection

Before allowing group delete/archive, check for:

- active students using the group
- active course offerings using the group

Then either:

- block archive
- require governance review
- or require migration target reassignment

### 12.3 Improve UI context

Show richer parent context for sections so operators can distinguish similarly named sections.

### 12.4 Decide student visibility policy explicitly

Choose whether students should see:

- all groups in their section
- or only their own group

Then align backend and frontend behavior explicitly.

## 13. Testing Requirements

### 13.1 Unit tests

- section existence validation
- teacher write denied when not coordinator
- duplicate group code blocked within section
- code normalization to uppercase
- student list scoped to own section

### 13.2 Integration tests

- admin create/update/archive group
- teacher coordinator create/update/archive own section group
- teacher denied on unrelated section group
- group-scoped offering visibility for students
- attendance blocked when student group does not match offering group

### 13.3 Frontend tests

- create form payload correctness
- section filter behavior
- delete action availability
- section label rendering

## 14. Current Module Assessment

The group module is small but structurally meaningful. It is the section partitioning layer that enables subgroup teaching and subgroup attendance control.

Strengths:

- clear section ownership
- good uniqueness enforcement
- clean downstream integration into offerings and attendance
- straightforward CRUD UI

Weaknesses:

- no dependency-aware archive protection
- no governance or audit parity
- limited UI context for operators
- unresolved policy choice around student group visibility

As implemented today, the module is useful and coherent, but it is under-protected relative to the operational impact groups have on offerings, attendance, and student schedules.

