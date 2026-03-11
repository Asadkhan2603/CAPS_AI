# Student Module Master

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
Student Module
|-- Student Master Records
|-- Enrollment Linkage
|-- Submission Participation
|-- Evaluation Visibility
|-- Timetable And Attendance Views
`-- Internship Touchpoints
```

## Internal Entity And Flow Tree

```text
User
`-- Student master record
    |-- Enrollment
    |-- Submission participation
    |-- Evaluation results
    `-- Timetable and attendance visibility
```

Primary implementation sources:

- `backend/app/api/v1/endpoints/students.py`
- `backend/app/api/v1/endpoints/enrollments.py`
- `backend/app/api/v1/endpoints/submissions.py`
- `backend/app/api/v1/endpoints/evaluations.py`
- `backend/app/api/v1/endpoints/attendance_records.py`
- `backend/app/api/v1/endpoints/timetables.py`
- `backend/app/schemas/student.py`
- `backend/app/schemas/enrollment.py`
- `backend/app/models/students.py`
- `backend/app/models/enrollments.py`
- `backend/app/models/submissions.py`
- `backend/app/models/evaluations.py`
- `frontend/src/pages/StudentsPage.jsx`
- `frontend/src/pages/EnrollmentsPage.jsx`
- `frontend/src/pages/SubmissionsPage.jsx`
- `frontend/src/pages/EvaluationsPage.jsx`
- `frontend/src/pages/DashboardPage.jsx`

Related references:

- `docs/modules/ACADEMIC_MODULE_MASTER.md`
- `docs/modules/ATTENDANCE_MODULE_MASTER.md`
- `docs/modules/TIMETABLE_MODULE_MASTER.md`
- `docs/modules/AUTH_MODULE_MASTER.md`
- `docs/modules/RBAC_MODULE_MASTER.md`

## 1. Module Overview

The student module in the current CAPS AI codebase is not one isolated CRUD surface. It is a multi-part domain made up of:

1. student master records
2. enrollment of students into sections
3. student-facing academic execution surfaces
   - submissions
   - evaluations
   - attendance visibility
   - timetable visibility
   - internship clock-in status on dashboard

That means the student module is both:

- a master-data module for administrators and teachers
- an operational experience module for the student user role

The backend separates these concerns across multiple endpoint files. The frontend also separates them across multiple pages.

## 2. Student Domain Model

### Core Student Record

The base student document stores:

- `full_name`
- `roll_number`
- `email`
- `class_id`
- `group_id`
- `is_active`
- `created_at`

This is a lightweight student master record. It does not currently include rich profile, academic history, guardian data, program metadata, or admission metadata directly in the `students` collection.

### Enrollment Layer

The separate `enrollments` collection stores the association between a student and a section:

- `class_id`
- `student_id`
- `student_roll_number`
- `assigned_by_user_id`
- `created_at`

This means student-to-section linkage currently exists in two places:

- `students.class_id`
- `enrollments.class_id`

That is a deliberate practical split in code, but it introduces duplication risk.

### Operational Student Artifacts

Students also appear indirectly in:

- `submissions`
- `evaluations`
- `attendance_records`
- `internship_sessions`
- timetable lookups through `enrollments`

These are not student master records, but they are core parts of the student module’s operational footprint.

## 3. Relationship To Academic Structure

The effective current relationship chain is:

`Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section -> Student`

Operational extensions then continue to:

- `Group`
- `Assignment`
- `Submission`
- `Evaluation`
- `Class Slot`
- `Attendance Record`
- `Timetable`

Important note:

The student master record does not directly store faculty, department, program, specialization, batch, or semester. Instead, it stores:

- `class_id`
- optionally `group_id`

This keeps the student document thin, but it also means student identity is highly dependent on the correctness of section setup and section-based joins.

## 4. Data Collections

### `students`

Purpose:

- canonical student master record for current implementation

Key fields:

- `full_name`
- `roll_number`
- `email`
- `class_id`
- `group_id`
- `is_active`
- `created_at`

Relations:

- belongs to one `class` or section through `class_id`
- optionally belongs to one group through `group_id`
- may be resolved from auth context by matching `students.email == current_user.email`

Validation implemented:

- roll number uniqueness
- class must exist if provided
- group must exist if provided
- group must belong to the provided class if both are set

### `enrollments`

Purpose:

- section enrollment tracking

Key fields:

- `class_id`
- `student_id`
- `student_roll_number`
- `assigned_by_user_id`
- `created_at`

Relations:

- references one section
- references one student by canonical student object id
- caches `student_roll_number` for display and lookup stability

Validation implemented:

- class must exist
- student must exist
- duplicate enrollment for the same student and class is blocked

Important duplication:

- the existence of both `students.class_id` and `enrollments.class_id` means enrollment state is not fully normalized into one authoritative source

### `submissions`

Purpose:

- stores uploaded student assignment files and AI evaluation status

Key fields:

- `assignment_id`
- `student_user_id`
- `original_filename`
- `stored_filename`
- `file_mime_type`
- `file_size_bytes`
- `notes`
- `status`
- `ai_status`
- `ai_score`
- `ai_feedback`
- `ai_provider`
- `ai_prompt_version`
- `ai_runtime_snapshot`
- `ai_error`
- `similarity_score`
- `extracted_text`
- `created_at`

Relations:

- belongs to an assignment
- belongs to one authenticated student user
- later links to evaluations by `submission_id`

### `evaluations`

Purpose:

- stores teacher/admin marking outcomes for a student submission

Key fields:

- `submission_id`
- `student_user_id`
- `teacher_user_id`
- `attendance_percent`
- `skill`
- `behavior`
- `report`
- `viva`
- `final_exam`
- `internal_total`
- `grand_total`
- `grade`
- `ai_score`
- `ai_feedback`
- `ai_status`
- `ai_provider`
- `ai_prompt_version`
- `ai_runtime_snapshot`
- `remarks`
- `is_finalized`
- `finalized_at`
- `finalized_by_user_id`
- `created_at`
- `updated_at`

Relations:

- belongs to one submission
- references student user, not student master record
- references evaluating teacher

### `attendance_records`

Purpose:

- classroom attendance state for a student against a class slot

Student-related fields:

- `student_id`
- `class_slot_id`
- `status`
- `marked_by_user_id`
- `marked_at`

### `internship_sessions`

Purpose:

- student internship clock-in and clock-out tracking

Key fields:

- `student_user_id`
- `student_id`
- `status`
- `clock_in_at`
- `clock_out_at`
- `total_minutes`

## 5. Backend Logic Implemented

### Student Creation Logic

`POST /students/`:

- validates duplicate roll number
- validates `class_id` if provided
- validates `group_id` if provided
- validates group ownership under section if both are given
- lowercases email if provided
- sets `is_active = true`

### Student Update Logic

`PUT /students/{student_id}`:

- normalizes email, full name, and roll number
- re-checks duplicate roll number if roll changes
- re-validates class and group references
- allows `is_active` updates

### Student Delete Logic

`DELETE /students/{student_id}`:

- performs hard delete
- does not archive
- does not use governance review
- does not preserve delete telemetry in the student document itself

This is a notable difference from the hardened academic setup entities.

### Enrollment Creation Logic

`POST /enrollments/`:

- validates class existence
- validates whether current teacher/admin can manage that class
- resolves student by object id or roll number
- blocks duplicate enrollment for same student in same class
- stores canonical student object id
- stores `student_roll_number` as a denormalized helper
- writes audit event

### Teacher-Scoped Enrollment Access

Enrollment management is not open to all teachers.

A teacher can manage enrollments only if they have:

- `year_head`, or
- `class_coordinator`

`class_coordinator` access is restricted further to classes coordinated by that teacher.

`year_head` currently receives broad class management reach across active classes.

### Student Submission Upload Logic

Only students can upload submissions.

Validation includes:

- assignment must exist
- assignment must not be closed
- file extension must be one of:
  - `.pdf`
  - `.docx`
  - `.txt`
  - `.md`
- file must be non-empty
- file size must be <= 10 MB

On success:

- file is stored locally under `uploads/submissions`
- text extraction is performed on request path
- submission row is inserted with `ai_status = pending`

### Student Submission Visibility

Students can list only their own submissions because backend forces:

- `query['student_user_id'] = current_user._id`

Teachers can only view submissions tied to assignments they own or sections they coordinate.

### Evaluation Visibility

Students can list and retrieve only evaluations where:

- `evaluation.student_user_id == current_user._id`

Teachers can access only their own evaluations.

### Timetable Visibility

Student timetable in `timetables.py` resolves through:

1. student profile lookup by email
2. enrollment lookup by student object id or roll number
3. published timetable lookup by enrolled class

This is important because timetable visibility uses `enrollments`, not only `students.class_id`.

### Attendance Visibility

Student classroom attendance visibility is currently indirect:

- `GET /attendance-records/` for students scopes to the current student record by email match
- `GET /class-slots/my` scopes to student section and group

That means student daily academic execution context is built from:

- `students`
- `class_slots`
- `attendance_records`

### Internship Attendance Logic

Student dashboard includes internship attendance:

- `clock-in`
- `clock-out`
- `status`
- auto-close after configured hours

This is implemented in the attendance router but functionally belongs to the student experience layer.

## 6. Business Rules

### Student Master Rules

1. `roll_number` must be unique.
2. `class_id` must reference an existing section if provided.
3. `group_id` must reference an active group if provided.
4. `group_id` must belong to `class_id` when both are provided.

### Enrollment Rules

1. Enrollment requires an existing section.
2. Enrollment requires an existing student.
3. Duplicate enrollment of the same student in the same class is rejected.
4. Teachers can manage enrollments only if they are `year_head` or `class_coordinator`.
5. Class coordinators may manage only their own coordinated classes.

### Submission Rules

1. Only students can upload submissions.
2. Submission requires a valid assignment.
3. Closed assignments reject uploads.
4. Uploads are limited to allowed document types.
5. Uploads are limited to 10 MB.

### Evaluation Rules

1. Students can only see their own evaluations.
2. Teachers can only evaluate submissions they are authorized to access.
3. Finalized evaluations become locked unless overridden through admin flow.

### Student Session Rules

1. Dashboard student identity is derived from auth user plus student profile lookup.
2. Student timetable access depends on enrollment presence.
3. Internship attendance supports only one active session at a time.

## 7. API Endpoints

### Student Master Endpoints

Base route: `/students`

#### `GET /students/`

Purpose:

- list student master records

Filters:

- `q`
- `class_id`
- `is_active`
- `skip`
- `limit`

Access:

- `admin`
- `teacher`

#### `GET /students/{student_id}`

Purpose:

- fetch one student master record

Access:

- `admin`
- `teacher`

#### `POST /students/`

Purpose:

- create student master record

Access:

- guarded by legacy `academic:manage`

#### `PUT /students/{student_id}`

Purpose:

- update student master record

Access:

- guarded by legacy `academic:manage`

#### `DELETE /students/{student_id}`

Purpose:

- delete student master record

Access:

- guarded by legacy `academic:manage`

Behavior:

- hard delete

### Enrollment Endpoints

Base route: `/enrollments`

#### `GET /enrollments/`

Purpose:

- list enrollments

Access:

- `admin`
- teachers with `year_head` or `class_coordinator`

#### `POST /enrollments/`

Purpose:

- create enrollment

Access:

- `admin`
- teachers with `year_head` or `class_coordinator`

### Student Submission Endpoints

Base route: `/submissions`

#### `GET /submissions/`

Access:

- `admin`
- `teacher`
- `student`

Behavior:

- students see their own rows only
- teachers see only accessible assignments

#### `GET /submissions/{submission_id}`

Access:

- `admin`
- `teacher`
- `student`

Scoped by ownership and assignment access.

#### `POST /submissions/upload`

Access:

- `student` only

#### `POST /submissions/{submission_id}/ai-evaluate`

Access:

- `admin`
- `teacher`

#### `POST /submissions/ai-evaluate/pending`

Access:

- `admin`
- `teacher`

Behavior:

- queues durable bulk AI work and returns AI job metadata instead of finishing the batch inline

### Evaluation Endpoints

Base route: `/evaluations`

#### `GET /evaluations/`

Access:

- `admin`
- `teacher`
- `student`

Students see their own evaluations only.

#### `GET /evaluations/{evaluation_id}`

Access:

- `admin`
- `teacher`
- `student`

#### `POST /evaluations/`

Access:

- `admin`
- `teacher`

#### `PATCH /evaluations/{evaluation_id}/finalize`

Access:

- `admin`
- `teacher`

#### `PATCH /evaluations/{evaluation_id}/override-unfinalize`

Access:

- `admin`

### Student-Adjacent Attendance And Timetable Endpoints

These are not owned by the student module, but they are part of the effective student experience:

- `GET /class-slots/my`
- `GET /attendance-records/`
- `GET /timetables/my`
- `POST /attendance-records/internship/clock-in`
- `POST /attendance-records/internship/clock-out`
- `GET /attendance-records/internship/status`

## 8. Frontend Implementation

### `StudentsPage.jsx`

Implements:

- admin/teacher student master CRUD UI

Features:

- search by name, roll number, email
- filter by section
- filter by active state
- create student
- edit student through shared entity manager
- assign optional group when section is selected
- delete student enabled

The page now exposes both section and group assignment in line with the backend contract.

### `EnrollmentsPage.jsx`

Implements:

- enrollment list
- enrollment create form

Role behavior:

- create hidden unless user can manage enrollments
- management logic mirrors backend role intent:
  - admin
  - teacher with `year_head`
  - teacher with `class_coordinator`

Current limitation:

- no update flow
- no delete or unenroll flow

### `SubmissionsPage.jsx`

Student mode:

- upload assignment files
- filter/search own submissions
- view AI processing state

Admin/teacher mode:

- view all accessible submissions
- run AI evaluation
- queue bulk AI for pending submissions
- open evaluation console
- admin can see teacher marks merged from evaluations

### `EvaluationsPage.jsx`

Student mode:

- view own evaluations only
- filter by finalized status
- search by submission, grade, remarks

Admin/teacher mode:

- shared entity manager for evaluation CRUD
- trace viewer
- direct AI refresh
- finalize action
- admin override unfinalize action
- AI console handoff to submission evaluation page

### `DashboardPage.jsx`

Student dashboard integrates:

- student identity summary
- daily timetable from class slots
- deadlines
- urgent notices
- evaluations summary
- internship attendance status and actions

This makes dashboard a key student module surface even though it is not a dedicated student CRUD page.

## 9. Current Strengths

### Strong Student-Owned Visibility Rules

Submissions and evaluations are correctly scoped by current authenticated student user id.

### Practical Enrollment Access Rules

Enrollment is not open to all teachers. It is restricted to supervision-style extensions.

### Student UX Is Richer Than Student Master Data

Even though the `students` collection is simple, the student-facing product already exposes:

- submissions
- evaluations
- attendance-related views
- timetable
- internship status

### Section And Group Validation Exists

Student master updates validate:

- section existence
- active group existence
- group-section ownership

That prevents obviously inconsistent assignments.

## 10. Current Gaps And Risks

### Student Delete Is Hard Delete

`DELETE /students/{student_id}` physically removes the student record.

This is inconsistent with:

- academic setup soft-delete standard
- governance-gated destructive action hardening

### Student Permissions Still Use Legacy `academic:manage`

Student create, update, and delete still depend on:

- `academic:manage`

That is inconsistent with the newer entity-level permission strategy adopted for academic setup.

### Enrollment State Is Duplicated

Student-to-section relation currently exists in:

- `students.class_id`
- `enrollments.class_id`

These can drift if not managed carefully.

### Student Master And Enrollment State Are Still Split

The student page now exposes `group_id`, but the broader duplication between `students.class_id` and `enrollments.class_id` still exists.

### Student Lookup Depends On Email In Several Places

Some student-facing flows resolve student record by:

- `students.email == auth_user.email`

This is convenient, but it assumes tight alignment between auth user email and student master email. That can break if either record changes independently.

### Timetable Uses Enrollments, Not Only Student Master

Student timetable resolution depends on `enrollments`, which means a student with `students.class_id` set but no enrollment rows may still fail timetable lookup.

### No Student Profile Authority Model

There is no explicit documented rule defining whether the authoritative identity for a learner is:

- auth user
- student master record
- enrollment row

The code uses all three depending on the workflow.

## 11. Architectural Issues

### Dual Student Identity

The platform currently uses two student identifiers:

1. authenticated user id in auth-driven flows
2. student master record id and roll number in academic-driven flows

Examples:

- submissions use `student_user_id`
- attendance records use student master `student_id`
- enrollments store student master id and roll number

This works, but it is not a fully unified learner identity model.

### Legacy `class_id` Naming

The code still uses:

- `class_id`

even after the academic module chose canonical `section` terminology. This naming remains embedded across:

- students
- enrollments
- timetables
- assignments
- submissions

### Student Module Is Cross-Cutting, Not Encapsulated

Student functionality is spread across:

- student master CRUD
- enrollment
- attendance
- timetable
- submissions
- evaluations

That reflects real business flow, but it makes a single “student module” harder to evolve unless a clear authoritative model is documented.

## 12. Cleanup Strategy

### Phase 1

- convert student delete from hard delete to soft archive
- add governance pattern if destructive student operations are considered sensitive
- move student CRUD off legacy `academic:manage`

### Phase 2

- choose authoritative section membership source:
  - either `students.class_id`
  - or `enrollments`
- remove duplicate ownership semantics

### Phase 3

- normalize `class_id` naming toward canonical section terminology at API boundary

### Phase 4

- define a unified learner identity contract across:
  - auth user
  - student master
  - enrollment
  - submission
  - evaluation

## 13. Testing Requirements

### Student Master Tests

Required tests:

- create student with unique roll number
- reject duplicate roll number
- reject invalid class
- reject invalid group
- reject group not belonging to class
- update student email normalization
- update student roll number uniqueness

### Enrollment Tests

Required tests:

- create enrollment by roll number
- create enrollment by student object id
- reject duplicate enrollment
- reject unauthorized teacher
- allow class coordinator on owned class
- allow year head on active classes

### Student Submission Tests

Required tests:

- only student can upload
- reject closed assignment
- reject unsupported file type
- reject oversize file
- student sees only own submissions
- teacher sees only accessible submissions

### Evaluation Tests

Required tests:

- student sees only own evaluations
- teacher cannot access other teacher evaluations
- finalize flow
- admin override unfinalize flow

### End-To-End Student Experience Tests

Required tests:

- authenticated student dashboard resolves student profile correctly
- timetable lookup works from enrollment
- class slot visibility respects section and group
- attendance visibility stays limited to current student
- internship attendance widget matches backend session state

## Final Summary

The student module is currently a cross-cutting operational domain, not a single CRUD table. Its implemented shape is:

- student master record
- section enrollment
- student-owned submission and evaluation flows
- student timetable and attendance visibility
- internship session tracking

Its strongest current qualities are:

- good ownership scoping for student-facing submissions and evaluations
- workable teacher-scoped enrollment management
- meaningful student dashboard integration

Its main architectural issues are:

- hard delete on student master records
- duplicated section membership state
- mixed learner identity across auth user and student master
- lingering legacy `class_id` naming
- permission lag behind newer entity-level academic policy

The correct next hardening move is not adding more student UI first. It is normalizing the authority model for:

- who a student is
- where a student is enrolled
- which identifier is authoritative across academic and user-facing flows
