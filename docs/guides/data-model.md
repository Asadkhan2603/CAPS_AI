# Data Model Guide

## Overview

CAPS AI uses MongoDB as its primary operational datastore. The application is not built around an ORM or relational foreign keys. Most entities are persisted directly as Mongo documents and are accessed through the shared Motor database binding in [database.py](/backend/app/core/database.py).

Primary data model files and runtime anchors:
- [database.py](/backend/app/core/database.py)
- [indexes.py](/backend/app/core/indexes.py)
- [soft_delete.py](/backend/app/core/soft_delete.py)
- route modules under `backend/app/api/v1/endpoints`

Current persistence characteristics:
- document-store model, not relational normalization
- application-enforced integrity
- mixed canonical and compatibility-era academic structures
- strong use of direct collection access from endpoint modules
- index-driven performance safeguards for core query paths

## Data Model Tree

```text
MongoDB Database
|-- Identity And Access
|   |-- users
|   |-- user_sessions
|   |-- token_blacklist
|   |-- admin_action_reviews
|   |-- audit_logs
|   |-- audit_logs_immutable
|   |-- recovery_logs
|   |-- settings
|   `-- scheduler_locks
|
|-- Academic Core
|   |-- faculties
|   |-- departments
|   |-- programs
|   |-- specializations
|   |-- batches
|   |-- semesters
|   |-- classes  (section storage)
|   |-- students
|   |-- groups
|   |-- subjects
|   |-- course_offerings
|   |-- class_slots
|   |-- attendance_records
|   |-- internship_sessions
|   `-- enrollments
|
|-- Legacy Academic Compatibility
|   |-- branches
|   |-- courses
|   `-- years
|
|-- Assessment And AI
|   |-- assignments
|   |-- submissions
|   |-- evaluations
|   |-- ai_evaluation_runs
|   |-- ai_evaluation_chats
|   |-- review_tickets
|   `-- similarity_logs
|
|-- Communication And Engagement
|   |-- notices
|   |-- notifications
|   |-- clubs
|   |-- club_members
|   |-- club_applications
|   |-- club_events
|   `-- event_registrations
|
`-- Reporting And Operations
    |-- analytics_snapshots
    |-- timetable_subject_teacher_maps
    `-- rate_limit_counters (runtime fallback utility collection)
```

## Canonical Academic Hierarchy

The adopted canonical academic hierarchy is:

```text
Faculty
`-- Department
    `-- Program
        `-- Specialization
            `-- Batch
                `-- Semester
                    `-- Section
```

Important implementation detail:
- section records are still physically stored in `classes`
- `/sections` is the canonical API route
- there is no `/classes` backend route

## Legacy Academic Compatibility Hierarchy

The older compatibility-era model still exists in storage, but the backend routes are no longer mounted:

```text
Department
`-- Branch
    `-- Course
        `-- Year
            `-- Section/Class
```

Collections involved:
- `branches`
- `courses`
- `years`
- `classes`

This structure is still referenced by some analytics, communication fanout, and older flows. It should not be extended as the primary future model.

## Collection Catalog

### Identity And Access Collections

#### `users`

Purpose:
- principal identity store for admins, teachers, and students

Typical fields:
- full name
- email
- hashed password
- role
- admin subtype
- extension roles
- role scope
- active state
- lockout and profile-related fields
- avatar metadata

Key relationships:
- referenced broadly across academic, governance, communication, and assessment modules
- teacher and student workflow records often store user ids directly

Important constraints:
- unique email index enforced

#### `user_sessions`

Purpose:
- refresh/session tracking and revocation support

Indexed fields:
- `user_id`
- `refresh_jti` unique
- `created_at`
- `revoked_at`

#### `token_blacklist`

Purpose:
- revoked token tracking

Important constraints:
- unique `jti`
- TTL index on `expires_at`

#### `admin_action_reviews`

Purpose:
- governance approval records for protected admin actions

Typical fields:
- review type
- action
- entity type
- entity id
- requester
- reviewer
- status
- timestamps
- metadata

Indexed fields:
- `status`, `created_at`
- `entity_type`, `entity_id`

#### `audit_logs`

Purpose:
- mutable operational audit store

Typical fields:
- actor
- action
- entity type
- entity id
- detail
- old value
- new value
- severity
- timestamps

#### `audit_logs_immutable`

Purpose:
- immutable chained audit record store

Important fields:
- `integrity_hash`
- `previous_hash`
- `source_audit_log_id`

Important constraints:
- unique `integrity_hash`

#### `recovery_logs`

Purpose:
- recovery/restore action log

Indexed field:
- `created_at`

#### `settings`

Purpose:
- operational and system-wide configuration records

Known uses:
- governance policy
- branding logo metadata
- scheduler-related settings and global system flags

#### `scheduler_locks`

Purpose:
- leader election storage for in-process scheduler

Characteristics:
- runtime operational collection rather than business-domain entity

### Canonical Academic Collections

#### `faculties`

Purpose:
- top-level academic grouping under the university

Typical fields:
- name
- code
- university name/code where present in current UI/API contract
- active/delete state

Key relationships:
- parent of departments

Soft delete semantics:
- `is_active`
- `deleted_at`
- `deleted_by`

#### `departments`

Purpose:
- faculty-contained academic departments

Typical fields:
- name
- code
- `faculty_id`
- university metadata
- active/delete state

Key relationships:
- child of faculty
- parent of programs
- legacy parent by code for branches in compatibility mode

#### `programs`

Purpose:
- department-contained academic programs

Typical fields:
- name
- code
- `department_id`
- `duration_years`
- `total_semesters`
- active/delete state

Key relationships:
- child of department
- parent of specializations and batches

Important business semantics:
- duration and semester generation logic lives here conceptually

#### `specializations`

Purpose:
- optional specialization track within a program

Typical fields:
- name
- code
- `program_id`
- active/delete state

Key relationships:
- child of program
- may scope batches

#### `batches`

Purpose:
- intake/cohort records within a program or specialization track

Typical fields:
- name
- code
- `program_id`
- optional `specialization_id`
- start year
- end year
- active/delete state

Key relationships:
- child of program
- optionally child of specialization
- parent of semesters

#### `semesters`

Purpose:
- semester records for a batch

Typical fields:
- batch id
- semester number or term identifier
- active/delete state

Key relationships:
- child of batch
- parent context for sections and offerings

#### `classes`

Purpose:
- actual storage for section records

Canonical meaning:
- section entity

Legacy meaning:
- class entity

Typical fields currently seen in the codebase:
- canonical academic linkage ids
- some legacy compatibility linkage ids
- class coordinator user id
- active/delete state

Key relationships:
- section anchor for students, enrollments, offerings, timetables, and attendance visibility

Architectural note:
- this collection is one of the main normalization tensions in the system

#### `students`

Purpose:
- student master records

Typical fields:
- roll number
- email
- name/profile fields
- `class_id`
- optional `group_id`
- active state

Key relationships:
- linked to section through `class_id`
- duplicated membership relationship also exists in `enrollments`

#### `groups`

Purpose:
- section-scoped sub-cohorts

Typical fields:
- `section_id`
- code
- name
- active state

Constraints:
- indexed on section + code + active state

#### `subjects`

Purpose:
- academic catalog/reference subject records

Typical fields:
- name
- code
- description and status-oriented fields depending on module usage

Key relationships:
- referenced by assignments, offerings, timetables, and communication logic

#### `course_offerings`

Purpose:
- teaching-delivery contract for a section in a semester and academic year

Typical fields:
- `section_id`
- `semester_id`
- academic year
- teacher user id
- optional group scoping
- active state

Indexed fields:
- `section_id`, `semester_id`, `academic_year`, `is_active`
- `teacher_user_id`, `is_active`

#### `class_slots`

Purpose:
- runtime executable teaching schedule records

Typical fields:
- `course_offering_id`
- day
- start time
- room code
- active state

Indexed fields:
- `course_offering_id`, `day`, `start_time`, `is_active`
- `day`, `room_code`, `is_active`

#### `attendance_records`

Purpose:
- per-student attendance state for a class slot

Typical fields:
- `class_slot_id`
- `student_id`
- attendance status
- marked timestamp

Constraints:
- unique on `class_slot_id + student_id`

#### `internship_sessions`

Purpose:
- internship attendance clock-in / clock-out state

Indexed fields:
- `student_user_id`, `clock_in_at`
- `status`, `clock_in_at`

#### `enrollments`

Purpose:
- section membership records

Typical fields:
- student id
- class/section id
- enrollment metadata

Architectural note:
- duplicates section membership semantics already partially present in `students.class_id`

### Legacy Academic Compatibility Collections

#### `branches`

Purpose:
- compatibility-era sub-department grouping

Current relation style:
- often linked by `department_code` rather than canonical foreign-id chain

Architectural note:
- this is one of the clearest denormalized compatibility structures still active in the system

#### `courses`

Purpose:
- compatibility-era academic course layer below branch

Current status:
- deprecated as canonical academic path
- still used by some downstream analytics and legacy flows

#### `years`

Purpose:
- compatibility-era year layer under course

Current status:
- deprecated but still referenced in legacy academic and communication logic

### Assessment And AI Collections

#### `assignments`

Purpose:
- teacher-created assessment tasks

Indexed fields:
- `created_by`, `created_at`
- `is_deleted`, `created_at`

#### `submissions`

Purpose:
- student submission records for assignments

Indexed fields:
- `assignment_id`, `created_at`

#### `evaluations`

Purpose:
- grading and AI-assisted evaluation records for submissions

Indexed fields:
- `student_user_id`, `created_at`
- `teacher_user_id`, `created_at`

#### `ai_evaluation_runs`

Purpose:
- persisted AI trace records for evaluations

Indexed fields:
- `evaluation_id`, `created_at`
- `submission_id`, `created_at`

#### `ai_evaluation_chats`

Purpose:
- teacher AI evaluation chat threads

Observed relation anchors:
- student id
- exam/assignment context
- teacher id

#### `review_tickets`

Purpose:
- evaluation reopen workflow records

#### `similarity_logs`

Purpose:
- similarity/plagiarism risk outputs

### Communication And Engagement Collections

#### `notices`

Purpose:
- core persisted communication artifact

Indexed fields:
- `is_active`, `created_at`
- `scope`, `scope_ref_id`
- legacy delete index on `is_deleted`, `deleted_at`

#### `notifications`

Purpose:
- user-targeted notification artifacts

Indexed fields:
- `target_user_id`, `created_at`

#### `clubs`

Purpose:
- club master records

Important constraints and indexes:
- unique `slug + academic_year`
- indexes on status and coordinator

#### `club_members`

Purpose:
- club membership records

Important constraints:
- unique `club_id + student_user_id`

#### `club_applications`

Purpose:
- pending and processed club join applications

Indexed fields:
- `club_id`, `student_user_id`, `status`

#### `club_events`

Purpose:
- club-scoped event records

Indexes:
- `club_id`, `status`, `event_date`
- legacy delete index on `is_deleted`, `created_at`

#### `event_registrations`

Purpose:
- registrations for events

Indexed fields:
- `event_id`, `student_user_id`

### Reporting And Operational Collections

#### `analytics_snapshots`

Purpose:
- daily or periodic snapshot analytics store

Used by:
- admin analytics history and reporting

#### `timetable_subject_teacher_maps`

Purpose:
- timetable subject-to-teacher mapping helper store

Constraint:
- unique on `class_id + subject_id`

#### `rate_limit_counters`

Purpose:
- Mongo fallback backing store for rate limiting

Operational nature:
- runtime utility collection, not business-domain data

## Index Strategy

Index bootstrap happens centrally in [indexes.py](/backend/app/core/indexes.py).

### Index Categories In Use

1. uniqueness protection
2. time-ordered access
3. active-state filtered access
4. workflow-specific composite indexes
5. TTL expiry for revocation or counter cleanup

### Important Unique Indexes

- `users.email`
- `clubs.slug + academic_year`
- `club_members.club_id + student_user_id`
- `token_blacklist.jti`
- `user_sessions.refresh_jti`
- `audit_logs_immutable.integrity_hash`
- `timetable_subject_teacher_maps.class_id + subject_id`
- `attendance_records.class_slot_id + student_id`

### Important Active-State Indexes

Canonical academic setup collections now share active/delete lookup indexes:
- faculties
- departments
- programs
- specializations
- batches
- semesters
- courses
- branches
- years
- classes

Pattern:
- `is_active + deleted_at`

This supports the newer soft-delete semantics and recovery visibility.

## Relationship Model

Mongo does not enforce foreign keys here. Relationship integrity is application-enforced.

### Canonical Academic Relationships

- `departments.faculty_id` -> faculty
- `programs.department_id` -> department
- `specializations.program_id` -> program
- `batches.program_id` -> program
- `batches.specialization_id` -> specialization, optional
- `semesters.batch_id` -> batch
- section/class record -> canonical academic lineage fields

### Teaching Delivery Relationships

- `students.class_id` -> section/class record
- `students.group_id` -> group, optional
- `groups.section_id` -> section/class record
- `course_offerings.section_id` -> section/class record
- `course_offerings.semester_id` -> semester
- `course_offerings.teacher_user_id` -> user
- `class_slots.course_offering_id` -> course offering
- `attendance_records.class_slot_id` -> class slot
- `attendance_records.student_id` -> student
- `enrollments.class_id` -> section/class record

### Assessment Relationships

- `assignments.subject_id` -> subject
- `assignments.class_id` -> section/class record in legacy/current mixed usage
- `submissions.assignment_id` -> assignment
- `submissions.student_user_id` -> user
- `evaluations.submission_id` -> submission
- `evaluations.student_user_id` -> user
- `evaluations.teacher_user_id` -> user
- `ai_evaluation_runs.evaluation_id` -> evaluation
- `review_tickets.evaluation_id` -> evaluation workflow context

### Communication And Engagement Relationships

- `notifications.target_user_id` -> user
- `club_members.club_id` -> club
- `club_members.student_user_id` -> user or student identity context depending on module flow
- `club_applications.club_id` -> club
- `club_events.club_id` -> club
- `event_registrations.event_id` -> club event
- `event_registrations.student_user_id` -> user/student actor

## Soft Delete And Archive Semantics

### Canonical Academic Contract

Recent hardening work standardized academic setup soft delete around:
- `is_active`
- `deleted_at`
- `deleted_by`

Compatibility note:
- some collections still retain `is_deleted` for backward compatibility
- not all non-academic modules use the canonical contract yet

Migration helper:
- [migrate_academic_soft_delete.py](scripts/migrate_academic_soft_delete.py)

### Current Mixed Delete Model

Across the broader repo, delete semantics still vary:
- canonical academic setup: mostly archive/soft delete
- some engagement or assessment modules: may still hard delete
- governance-gated delete is applied selectively, not universally

Architectural implication:
- restore capability and delete safety remain collection-dependent

## Denormalization Patterns

The current data model intentionally stores some duplicated or derived references for operational simplicity.

Examples:
- `students.class_id` plus `enrollments.class_id`
- teacher user ids directly on offerings, evaluations, and workflow records
- coordinator user ids on section/class and club records
- AI output stored directly on evaluation records
- settings documents used as configuration registry
- compatibility structures using department code or older academic identifiers

### Benefits

- faster reads for common workflows
- simpler frontend payloads for many screens
- less join-like reconstruction for operational pages

### Costs

- relationship drift when upstream ownership changes
- ambiguous authority semantics over time
- more cleanup work during architecture consolidation
- coexistence of canonical and compatibility models in the same records

## Integrity Controls

Since Mongo is used without relational foreign keys, integrity is enforced through application code and indexes.

Current control types:
- id parsing and existence checks
- duplicate checks before create or update
- index-enforced uniqueness in selected collections
- soft delete state checks
- governance approval for sensitive destructive actions
- audit logging for important mutations

This means correctness depends heavily on route and service logic quality.

## Current Model Tensions

### 1. Dual Academic Model Conflict

Canonical hierarchy and compatibility hierarchy still coexist.

Effect:
- same business concept can be represented through two lineage models
- analytics and communication code still touch compatibility collections

### 2. Section Stored As `classes`

Canonical route:
- `/sections`

Physical collection:
- `classes`

Route note:
- `/classes` is not mounted; it is a storage-only legacy name

Effect:
- naming mismatch leaks into code, docs, and mental model

### 3. Duplicated Section Membership

Both of these carry section membership semantics:
- `students.class_id`
- `enrollments.class_id`

Effect:
- risk of inconsistent student placement state

### 4. Mixed Soft Delete Semantics

Canonical academic setup is improving, but not every module uses the same delete contract.

Effect:
- recovery quality varies by module
- delete assumptions cannot be generalized safely

### 5. Mixed Durable Versus Local File References

Some entities depend on file paths or uploads tied to local disk behavior.

Effect:
- model portability across deployments is weaker than a full object-storage approach

## Recommended Data Reading Order

1. `users`, auth, sessions, blacklist, governance, and audit collections
2. canonical academic collections
3. section/class, students, groups, enrollments
4. offerings, slots, attendance, and timetables
5. assignments, submissions, evaluations, AI traces, review tickets
6. notices, notifications, clubs, events, registrations
7. analytics snapshots and operational runtime collections

## Data Model Summary

The current data model is a pragmatic Mongo operational model with strong application-level behavior and selective indexing.

Its strongest areas are:
- directness of operational reads and writes
- recent hardening around canonical academic soft delete and governance-sensitive actions
- workable support for diverse workflows in one datastore

Its weakest areas are:
- coexistence of canonical and legacy academic structures
- section/class naming mismatch
- duplicated membership semantics
- uneven delete and recovery behavior across modules

The correct next step is disciplined normalization around canonical academic entities and consistent lifecycle semantics, not a wholesale redesign of persistence technology.


