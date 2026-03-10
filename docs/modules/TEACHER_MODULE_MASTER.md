# Teacher Module Master

## Module Tree

```text
Teacher Module
|-- Teacher Authority Model
|-- Assignment Ownership
|-- Evaluation Authority
|-- Timetable And Attendance Responsibility
|-- Coordinator And Year-Head Scope
`-- AI-Assisted Teaching Workflows
```

## Internal Entity And Flow Tree

```text
Teacher user
|-- Assignment creation and review
|-- Submission access
|-- Evaluation authority
|-- Attendance marking
`-- Timetable and section responsibilities
```

Primary implementation sources:

- `backend/app/api/v1/endpoints/assignments.py`
- `backend/app/api/v1/endpoints/submissions.py`
- `backend/app/api/v1/endpoints/evaluations.py`
- `backend/app/api/v1/endpoints/enrollments.py`
- `backend/app/api/v1/endpoints/class_slots.py`
- `backend/app/api/v1/endpoints/timetables.py`
- `backend/app/api/v1/endpoints/groups.py`
- `backend/app/api/v1/endpoints/attendance_records.py`
- `backend/app/api/v1/endpoints/subjects.py`
- `frontend/src/pages/AssignmentsPage.jsx`
- `frontend/src/pages/SubmissionsPage.jsx`
- `frontend/src/pages/EvaluationsPage.jsx`
- `frontend/src/pages/AIModulePage.jsx`
- `frontend/src/pages/Teacher/EvaluateSubmission.jsx`
- `frontend/src/components/ui/TeacherClassTiles.jsx`
- `frontend/src/components/Teacher/AIChatPanel.jsx`
- `frontend/src/services/aiService.js`
- `frontend/src/services/sectionsApi.js`

Related references:

- `docs/modules/STUDENT_MODULE_MASTER.md`
- `docs/modules/ACADEMIC_MODULE_MASTER.md`
- `docs/modules/TIMETABLE_MODULE_MASTER.md`
- `docs/modules/ATTENDANCE_MODULE_MASTER.md`
- `docs/modules/RBAC_MODULE_MASTER.md`

## 1. Module Overview

The teacher module is a supervision and delivery domain, not just a teacher user table. In the current codebase, teacher capability is distributed across:

- assignment creation and management
- submission review
- evaluation and finalization
- AI-assisted grading workflow
- section-scoped enrollment management for supervisory teachers
- class slot management for class coordinators
- timetable access and timetable write scope
- group management inside owned sections
- attendance marking

The teacher module therefore represents operational teaching authority.

It is shaped by two separate concepts:

1. base role:
   - `teacher`
2. extension roles:
   - `year_head`
   - `class_coordinator`
   - `club_coordinator`

Teacher authority is not global. It is constrained either by:

- record ownership
- section coordination
- extension-role scope

## 2. Teacher Authority Model

### Base Teacher Role

The base `teacher` role allows access to teacher-facing pages, but it does not automatically grant broad write authority across all academic data.

Examples:

- teacher can access assignments page
- teacher can access submissions page
- teacher can access evaluations page
- teacher can access timetable page

But write scope is often narrower inside each endpoint.

### Extension Roles

Teacher-specific extension roles in the current system are:

- `year_head`
- `class_coordinator`
- `club_coordinator`

Only the first two materially affect teacher academic control in the current code path discussed here.

### Practical Authority Types

The current teacher module effectively has four authority modes:

1. regular teacher as assignment owner
2. class coordinator
3. year head
4. admin acting through teacher-facing modules

## 3. Relationship To Academic Structure

Teacher authority converges mainly at the section level.

The most important field across the codebase is:

- `class_coordinator_user_id`

This makes section the effective center of teacher-scoped control.

The practical hierarchy is:

`Section -> Subject -> Assignment -> Submission -> Evaluation`

Teacher scheduling and attendance add:

`Section -> Course Offering -> Class Slot -> Attendance`

That means teacher workflows are built on top of academic structure rather than replacing it.

## 4. Core Backend Logic

### Assignment Ownership

Assignments are one of the clearest teacher-owned entities.

`assignments.py` implements:

- teacher can list only assignments where `created_by == current_user._id`
- teacher can retrieve only owned assignments
- teacher can update only owned assignments
- teacher can delete only owned assignments

Students can view assignments only if their visible classes match assignment class.

Admins bypass the ownership restriction.

### Student Visibility For Assignments

Student visibility is resolved by:

1. looking up student profiles by email or user id
2. collecting class ids from:
   - `students.class_id`
   - `enrollments.class_id`
3. filtering assignments by those class ids

This is important because teacher-created assignments are only visible to students in the relevant class scope.

### Plagiarism Toggle

Teachers can patch:

- `PATCH /assignments/{assignment_id}/plagiarism`

Rules:

- only teachers, not admins, can toggle this endpoint
- teacher must own the assignment

This is a notable business rule. Admin has broader system authority in many areas, but here the code intentionally preserves teacher control over assignment-level plagiarism settings.

### Submission Access

Teacher access to submissions is not arbitrary.

A teacher can access a submission if:

1. the related assignment exists, and
2. either:
   - assignment `created_by == teacher_user_id`, or
   - the assignment's class is coordinated by that teacher

This logic is implemented in:

- `_teacher_can_access_assignment(...)`
- `_teacher_accessible_assignment_ids(...)`
- `_teacher_can_access_submission(...)`

This is stronger than generic role-based access because it is tied to assignment ownership and section coordination.

### Evaluation Access

Teacher evaluation access is constrained in two layers.

1. to create an evaluation for a submission:
   - teacher must be allowed to evaluate that submission
2. to access an existing evaluation:
   - teacher must be the `teacher_user_id` stored on that evaluation

This prevents teachers from reading or editing evaluations owned by other teachers.

### Enrollment Management By Teachers

Teachers do not automatically manage student enrollments.

Enrollment endpoints require:

- admin, or
- teacher with `year_head` or `class_coordinator`

Then additional scope is applied:

- `year_head`
  - broad access to active classes
- `class_coordinator`
  - only classes where `class_coordinator_user_id == current_user._id`

This is one of the clearest examples of extension-role enforcement in the repo.

### Group Management

Groups are section-scoped and teacher writes are limited.

Teacher write access to groups requires:

- teacher role
- ownership of the related section via `class_coordinator_user_id`

Student read access is limited to the student's own section groups.

### Class Slot Management

Teachers can create, update, and delete class slots only if:

- they are class coordinator of the offering's section

Conflict validation includes:

- teacher overlap on same day/time
- room overlap on same day/time

This means teacher timetable execution control is section-coordinator based, not merely teacher-role based.

### Timetable Management

Teacher timetable write access is similarly scope-limited in `timetables.py`.

Teacher write mode requires:

- teacher role
- class coordinator scope
- ownership of the target class through `class_coordinator_user_id`

Teacher read access is broader than write access for some timetable views, but still scoped by assigned classes.

### Attendance Marking

Teachers can mark attendance only when:

- they are the mapped teacher of the offering, or
- they are the section class coordinator

This is a highly specific operational authority rule and one of the better implemented pieces of row-aware access in the repo.

## 5. Teacher-Facing Academic Workflow

The current teacher flow is:

1. create assignment
2. students upload submission
3. teacher reviews submissions
4. teacher may trigger AI evaluation on submission
5. teacher opens AI-assisted evaluation console
6. teacher previews AI insight and saves marks
7. teacher finalizes evaluation

That flow is spread across:

- `AssignmentsPage.jsx`
- `SubmissionsPage.jsx`
- `AIModulePage.jsx`
- `Teacher/EvaluateSubmission.jsx`
- `EvaluationsPage.jsx`

## 6. AI-Assisted Teacher Workflow

### Submission-Level AI

Teachers can run:

- `POST /submissions/{submission_id}/ai-evaluate`
- `POST /submissions/ai-evaluate/pending`

This updates submission fields:

- `ai_status`
- `ai_score`
- `ai_feedback`
- `ai_provider`
- `ai_error`

### Evaluation-Level AI Preview

Teachers can also request:

- `POST /evaluations/ai-preview`

This combines:

- manual marks input
- submission text
- grading functions
- AI insight generation

The AI preview does not itself finalize marks. It provides recommendation context.

### AI Evaluation Console

`Teacher/EvaluateSubmission.jsx` provides:

- submission detail
- question selection
- rubric input
- marks input
- AI preview
- persisted evaluation AI state
- stored-AI refresh
- evaluation trace history
- AI chat assistance

This is currently the richest teacher experience page in the system.

### AI Operations Overview

`AIModulePage.jsx` now gives teachers a dedicated AI operations surface for their accessible scope.

It currently provides:

- AI provider/runtime mode visibility
- admin-only runtime override controls
- submission AI pipeline counts
- durable AI job queue state
- recent evaluation AI runs
- recent similarity flags
- recent AI chat thread activity

This does not replace submission review or the evaluation console, but it gives teachers a first-class AI workflow overview.

### AI Chat

`AIChatPanel.jsx` and related service calls let a teacher:

- ask rubric-aligned evaluation questions
- review prior thread context
- use AI as evaluation support, not as final authority

The code structure aligns with a teacher-assist model rather than an automatic grading replacement model.

## 7. Data Collections Relevant To Teachers

### `assignments`

Purpose:

- teacher-authored academic work items for students

Key fields:

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
- `is_deleted`
- `deleted_at`
- `deleted_by`

Teacher relation:

- ownership is through `created_by`

### `submissions`

Purpose:

- student file submissions reviewed by teachers

Teacher relation:

- teacher can view/evaluate only if assignment access rule passes

### `evaluations`

Purpose:

- teacher marks and AI-assisted grading output

Teacher relation:

- `teacher_user_id`
- teacher read/write locked to own evaluations

### `classes`

Teacher relation:

- `class_coordinator_user_id`

This field controls:

- section-scoped visibility
- group management
- attendance marking fallback authority
- timetable write access
- class slot write access

### `course_offerings`

Teacher relation:

- `teacher_user_id`

This is the runtime link between teacher and scheduled teaching unit.

### `class_slots`

Teacher relation:

- indirectly through `course_offering_id`
- directly constrained by coordinator ownership when modifying

## 8. API Endpoints

### Assignment Endpoints

Base route: `/assignments`

#### `GET /assignments/`

Access:

- `admin`
- `teacher`
- `student`

Teacher behavior:

- list own assignments only

#### `GET /assignments/{assignment_id}`

Teacher behavior:

- can only retrieve owned assignment

#### `POST /assignments/`

Access:

- `admin`
- `teacher`

#### `PUT /assignments/{assignment_id}`

Teacher behavior:

- can update only owned assignment

#### `PATCH /assignments/{assignment_id}/plagiarism`

Access:

- `teacher` only in practical terms

Admin behavior:

- explicitly blocked

#### `DELETE /assignments/{assignment_id}`

Teacher behavior:

- can archive only owned assignment

### Submission Endpoints Relevant To Teachers

Base route: `/submissions`

#### `GET /submissions/`

Teacher behavior:

- visible only for accessible assignments

#### `GET /submissions/{submission_id}`

Teacher behavior:

- denied if submission is outside assignment/coordinator scope

#### `POST /submissions/{submission_id}/ai-evaluate`

Teacher behavior:

- allowed only for accessible submissions

#### `POST /submissions/ai-evaluate/pending`

Teacher behavior:

- bulk AI evaluation on accessible pending submissions

### Evaluation Endpoints Relevant To Teachers

Base route: `/evaluations`

#### `GET /evaluations/`

Teacher behavior:

- list own evaluations only

#### `GET /evaluations/{evaluation_id}`

Teacher behavior:

- must own the evaluation

#### `GET /evaluations/{evaluation_id}/trace`

Teacher behavior:

- must own the evaluation

#### `POST /evaluations/ai-preview`

Access:

- `admin`
- `teacher`

Teacher behavior:

- must be allowed to evaluate the related submission

#### `POST /evaluations/`

Access:

- `admin`
- `teacher`

#### `PUT /evaluations/{evaluation_id}`

Teacher behavior:

- scoped to own evaluation

#### `PATCH /evaluations/{evaluation_id}/finalize`

Access:

- `admin`
- `teacher`

#### `PATCH /evaluations/{evaluation_id}/override-unfinalize`

Access:

- `admin` only

### Enrollment Endpoints Relevant To Teachers

Base route: `/enrollments`

Teacher access requires:

- `year_head`, or
- `class_coordinator`

### Class Slot Endpoints Relevant To Teachers

Base route: `/class-slots`

Teacher write requires:

- coordinator ownership of offering section

### Group Endpoints Relevant To Teachers

Base route: `/groups`

Teacher write requires:

- coordinator ownership of section

## 9. Frontend Implementation

### `AssignmentsPage.jsx`

Implements:

- assignment CRUD page
- subject and section lookups
- plagiarism toggle UI for teachers

Teacher-specific behavior:

- toggle switch exposed only for teachers
- admin sees static plagiarism value

### `SubmissionsPage.jsx`

Teacher mode supports:

- viewing accessible submissions
- AI evaluation triggers
- bulk AI evaluation
- opening evaluation console

This page is one of the central teacher operational surfaces.

### `EvaluationsPage.jsx`

Teacher mode supports:

- evaluation CRUD
- trace viewer
- direct AI refresh
- finalize action
- structured admin override-unfinalize modal
- AI console navigation

Teacher can only operate within owned evaluation scope enforced by backend.

### `Teacher/EvaluateSubmission.jsx`

Implements the advanced teacher evaluation workspace:

- submission detail
- extracted text review
- question list
- rubric drafting
- marks input
- AI preview
- persisted evaluation AI state
- stored-AI refresh
- trace timeline for recent AI runs
- AI chat assistance

This is effectively the teacher grading cockpit.

### `AIModulePage.jsx`

Implements the dedicated teacher/admin AI operations view:

- provider mode and runtime settings visibility
- admin runtime config form for persisted overrides
- scoped AI throughput summary
- recent durable AI jobs
- recent evaluation AI activity with direct console handoff
- recent similarity flags
- recent AI chat thread activity

### `TeacherClassTiles.jsx`

Used on teacher dashboard to show:

- my sections
- student counts
- active assignments
- late submissions
- similarity alerts
- risk students

This is a read model, not a write screen, but it reflects the teacher’s supervised academic scope.

### `sectionsApi.js`

Provides teacher-facing helper access to:

- section lists
- teacher section analytics

## 10. Frontend Access Model

Relevant `FEATURE_ACCESS` entries currently expose:

- `students` to `admin`, `teacher`
- `groups` to `admin`, `teacher`
- `subjects` to `admin`, `teacher`
- `courseOfferings` to `admin`, `teacher`
- `classSlots` to `admin`, `teacher`, `student`
- `attendanceRecords` to `admin`, `teacher`, `student`
- `assignments` to `admin`, `teacher`
- `submissions` to `admin`, `teacher`, `student`
- `aiModule` to `admin`, `teacher`
- `evaluations` to `admin`, `teacher`, `student`
- `enrollments` to:
  - `admin`
  - `teacher` with `year_head` or `class_coordinator`

This matches backend intent reasonably well for enrollment gating and general teacher surfaces.

## 11. Current Strengths

### Row-Aware Teacher Scope Exists

Teacher authority is often tied to:

- assignment ownership
- evaluation ownership
- class coordinator ownership
- offering teacher mapping

This is materially better than role-only authorization.

### Teacher Workflow Is Operationally Complete

Teachers can:

- publish assignments
- review submissions
- evaluate with AI support
- finalize marks
- manage groups in owned sections
- manage enrollments with extension roles
- manage class slots in owned sections
- mark attendance

### AI Is Assistive, Not Final Authority

The current implementation still puts the teacher in control of marks save and evaluation finalization.

## 12. Current Gaps And Risks

### Teacher Authority Is Spread Across Multiple Patterns

Different modules enforce teacher scope differently:

- `created_by`
- `class_coordinator_user_id`
- `teacher_user_id`
- extension roles

This works, but it is not one normalized authority model.

### Some Teacher-Accessible Master Data Still Uses Legacy Permissioning

`subjects.py` still uses:

- `academic:manage`

That means teacher-facing academic tooling is not fully aligned with newer entity-level permissions.

### Assignment Creation Is Not Section-Scoped

Teachers can create assignments without an explicit backend check that they own or coordinate the target section. Ownership becomes relevant later for update/delete and student visibility, but section-authority validation at create time is weak.

### Subject Visibility Is Broad For Teachers

Teachers can read all subjects because subject reads are not scoped to actual teaching allocations.

### Year Head Scope Is Broad

`year_head` enrollment management currently resolves to all active classes, not a narrower year-specific subset. That is operationally convenient but broader than the extension name suggests.

### Group And Timetable Scope Depend On Legacy `classes`

Teacher operational ownership still centers on:

- `db.classes`
- `class_id`

This remains coupled to legacy naming despite the canonical `section` model.

## 13. Architectural Issues

### No Unified Teacher Assignment Model

The platform effectively uses several parallel ways to say a teacher is responsible:

1. assignment creator
2. evaluation owner
3. class coordinator
4. offering teacher
5. year head

These are all valid, but there is no single documented teacher authority matrix in code.

### Coordination And Teaching Are Not Fully Separated

A class coordinator can manage:

- groups
- enrollments
- class slots
- attendance
- timetable write paths

That is a broad operational role. If the product grows, this should be explicitly modeled rather than inferred from one field across many modules.

### Teacher Workflow Is Still Split Across Multiple Operational Surfaces

TeacherClassTiles and the new AI operations page improve visibility, but there is still no single teacher command center linking:

- assignments
- submissions
- AI operations
- evaluations
- attendance
- timetable

The workflow is operationally present but spread across multiple pages.

## 14. Cleanup Strategy

### Phase 1

- formalize a teacher authority matrix:
  - assignment owner
  - offering teacher
  - class coordinator
  - year head

### Phase 2

- enforce section ownership during assignment creation, not only on later mutation
- narrow `year_head` access to intended academic scope

### Phase 3

- move teacher-relevant academic master data off legacy `academic:manage`
- normalize section naming at API boundary

### Phase 4

- add a dedicated teacher command center page that aggregates:
  - my sections
  - pending submissions
  - AI operations health and recent runs
  - attendance actions
  - timetable conflicts
  - evaluations awaiting finalize

## 15. Testing Requirements

### Assignment Tests

Required tests:

- teacher sees only owned assignments
- student sees only visible-class assignments
- teacher cannot update another teacher assignment
- admin cannot toggle plagiarism
- teacher can toggle plagiarism only on owned assignment

### Submission Tests

Required tests:

- teacher sees only accessible submissions
- teacher cannot access out-of-scope submission
- bulk AI evaluation respects scope

### Evaluation Tests

Required tests:

- teacher cannot access another teacher evaluation
- teacher can preview AI only for accessible submission
- teacher finalize works within scope

### Enrollment / Coordination Tests

Required tests:

- class coordinator can manage own class enrollments
- class coordinator cannot manage other class enrollments
- year head scope behavior is explicitly tested

### Timetable / Attendance Tests

Required tests:

- class coordinator can create class slots for owned section
- teacher conflict detection rejects overlap
- teacher attendance marking allowed for offering teacher
- teacher attendance marking allowed for class coordinator
- unauthorized teacher attendance marking is rejected

## Final Summary

The teacher module is the operational teaching authority layer of CAPS AI. It is already richer than a simple “teacher role” implementation because real scope decisions depend on:

- assignment ownership
- evaluation ownership
- class coordinator ownership
- offering teacher mapping
- extension roles such as `year_head`

Its strongest parts are:

- scoped submission/evaluation access
- AI-assisted grading workflow
- dedicated AI operations visibility for teacher/admin scope
- coordinator-based operational controls
- attendance and timetable execution rules tied to actual ownership

Its main weaknesses are:

- fragmented authority semantics
- inconsistent permission normalization
- weak assignment-create scope validation
- broad `year_head` interpretation

The correct next hardening step is not adding more teacher UI first. It is to define and enforce one explicit teacher authority matrix across all teaching workflows.
