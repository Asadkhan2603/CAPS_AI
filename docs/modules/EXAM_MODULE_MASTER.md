# Exam Module Master

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
Exam Module
|-- Assignment-Based Assessment
|-- Submission Intake
|-- Evaluation And Grading
|-- Review And Reopen Paths
`-- AI-Assisted Assessment Support
```

## Internal Entity And Flow Tree

```text
Assignment
`-- Submission
    `-- Evaluation
        `-- Review ticket or admin reopen
```

## 1. Module Overview

The CAPS AI codebase does not implement a standalone `exam` entity with its own timetable, attempt session, invigilation model, or published result workflow.

What exists today is an assessment pipeline assembled from three primary collections and their APIs:

1. `assignments`
2. `submissions`
3. `evaluations`

Those three collections together form the practical exam and assessment module used by the product.

Primary backend files:

- [assignments.py](/backend/app/api/v1/endpoints/assignments.py)
- [submissions.py](/backend/app/api/v1/endpoints/submissions.py)
- [evaluations.py](/backend/app/api/v1/endpoints/evaluations.py)
- [ai.py](/backend/app/api/v1/endpoints/ai.py)
- [grading.py](/backend/app/services/grading.py)
- [ai_evaluation.py](/backend/app/services/ai_evaluation.py)
- [evaluation_ai_module.py](/backend/app/services/evaluation_ai_module.py)

Primary frontend files:

- [AssignmentsPage.jsx](/frontend/src/pages/AssignmentsPage.jsx)
- [SubmissionsPage.jsx](/frontend/src/pages/SubmissionsPage.jsx)
- [EvaluateSubmission.jsx](/frontend/src/pages/Teacher/EvaluateSubmission.jsx)

Operational role of this module:

- define an assessment artifact
- allow students to submit work
- allow teachers or admins to mark work
- optionally enrich marking through AI-generated insight
- expose marks and status back to administrative and student views

Implementation reality:

- the system uses the words `assignment` and `exam` interchangeably in some flows
- the persisted object is usually an assignment
- teacher AI chat uses `exam_id`, but in practice this points to the assignment context

That naming inconsistency is important because it is the main reason the exam module boundary is currently blurred.

## 2. Implemented Exam Boundary

The current exam module is best understood as a staged workflow.

### 2.1 Stage 1: Assessment definition

An assessment begins when a teacher or admin creates an assignment in `assignments`.

The assignment defines:

- title
- description
- subject
- section
- deadline
- total marks
- open or closed state
- plagiarism-enabled flag

This is the closest current equivalent to an exam paper or assessment announcement.

### 2.2 Stage 2: Student attempt submission

Students upload files into `submissions`.

A submission stores:

- which assignment it belongs to
- which student submitted it
- uploaded file metadata
- notes
- AI evaluation state
- extracted text
- similarity score

This is the current equivalent of an exam attempt or practical submission.

### 2.3 Stage 3: Teacher evaluation

Teachers and admins create an `evaluation` record for a submission.

The evaluation stores:

- marking components
- totals
- grade
- remarks
- finalization state
- AI insight fields

This is the marking and result-generation layer of the module.

### 2.4 Stage 4: AI-assisted review

AI services augment the module by:

- scoring extracted submission text
- generating feedback
- producing grading preview insight
- supporting teacher-to-AI evaluation chat

These flows do not replace human grading. They act as a secondary analytical layer over the exam workflow.

## 3. Collections and Persistence Model

## 3.1 `assignments`

Purpose:

- store the assessment or exam definition visible to students and staff

Primary schema file:

- [assignment.py](/backend/app/schemas/assignment.py)

Public model mapping:

- [assignments.py](/backend/app/models/assignments.py)

Important stored fields:

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
- `is_active`
- `is_deleted`
- `deleted_at`
- `deleted_by`

Relations:

- `subject_id` references `subjects`
- `class_id` references the legacy `classes` collection rather than canonical `sections`
- `created_by` references `users`

Indexes currently defined:

- `(created_by, created_at)`
- `(is_deleted, created_at)`

Important note:

- delete behavior for assignments is soft archive, not hard delete

## 3.2 `submissions`

Purpose:

- store student attempt files and their AI-processing state

Primary schema file:

- [submission.py](/backend/app/schemas/submission.py)

Public model mapping:

- [submissions.py](/backend/app/models/submissions.py)

Important stored fields:

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
- `ai_error`
- `similarity_score`
- `extracted_text`
- `created_at`

Relations:

- `assignment_id` references `assignments`
- `student_user_id` references `users`

Indexes currently defined:

- `(assignment_id, created_at)`

Important note:

- delete behavior for submissions is hard delete plus file removal from local disk
- this is inconsistent with assignment soft delete

## 3.3 `evaluations`

Purpose:

- persist teacher grading and the final assessment result for a submission

Primary schema file:

- [evaluation.py](/backend/app/schemas/evaluation.py)

Public model mapping:

- [evaluations.py](/backend/app/models/evaluations.py)

Important stored fields:

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
- `ai_confidence`
- `ai_risk_flags`
- `ai_strengths`
- `ai_gaps`
- `ai_suggestions`
- `remarks`
- `is_finalized`
- `finalized_at`
- `finalized_by_user_id`
- `created_at`
- `updated_at`

Relations:

- `submission_id` references `submissions`
- `student_user_id` references `users`
- `teacher_user_id` references `users`
- `finalized_by_user_id` references `users`

Indexes currently defined:

- `(student_user_id, created_at)`
- `(teacher_user_id, created_at)`

Practical uniqueness rule:

- one evaluation per submission is enforced in endpoint logic by checking `submission_id`
- there is no documented unique database index shown in current index setup for `submission_id`

## 3.4 Related collections used by exam flows

The exam workflow also depends on adjacent collections:

- `subjects`
- `classes`
- `users`
- `ai_evaluation_runs`
- `ai_evaluation_chats`
- `similarity_logs`
- `audit_logs`

These are not the core exam entities, but the module cannot operate without them.

## 4. Backend Logic Implemented

## 4.1 Assignment lifecycle

File:

- [assignments.py](/backend/app/api/v1/endpoints/assignments.py)

Implemented behavior:

- teachers and admins can create assignments
- list is role-scoped
- teachers primarily see or mutate assignments they created or are allowed to manage
- update exists in backend
- plagiarism can be toggled independently through a dedicated patch route
- delete archives the assignment instead of removing it physically

Current lifecycle state is minimal:

- `open`
- `closed`

Missing lifecycle states:

- draft
- published
- archived
- result published
- locked after evaluation window

## 4.2 Submission upload and validation

File:

- [submissions.py](/backend/app/api/v1/endpoints/submissions.py)

Implemented behavior:

- only students can upload submissions
- assignment must exist
- assignment must not be closed
- uploaded file is stored under local `uploads/submissions`
- extracted text is derived on the request path
- submission record is persisted with metadata and AI fields initialized

Important access behavior:

- students can see only their own submissions
- teachers and admins can see broader submission lists
- teacher scope is filtered through assignment or class ownership logic

## 4.3 AI evaluation on submissions

Files:

- [submissions.py](/backend/app/api/v1/endpoints/submissions.py)
- [ai_evaluation.py](/backend/app/services/ai_evaluation.py)

Implemented behavior:

- teachers and admins can trigger AI scoring for one submission
- they can also bulk-run AI for pending submissions
- the service stores:
  - `ai_status`
  - `ai_score`
  - `ai_feedback`
  - `ai_provider`
  - `ai_error`
- the module supports deterministic fallback if the provider is unavailable

## 4.4 Grade computation logic

File:

- [grading.py](/backend/app/services/grading.py)

Implemented rules:

### Attendance points mapping

- `95-100` -> `5`
- `90-94` -> `4`
- `85-89` -> `3`
- `80-84` -> `2`
- `70-79` -> `1`
- below `70` -> `0`

### Internal total

`internal_total = attendance_points + skill + behavior + report + viva`

### Grand total

`grand_total = internal_total + final_exam`

### Grade mapping

- `90-100` -> `A+`
- `80-89.99` -> `A`
- `70-79.99` -> `B`
- `60-69.99` -> `C`
- below `60` -> `Needs Improvement`

This grading logic is centralized and reused by evaluation creation and update flows.

## 4.5 Evaluation creation

File:

- [evaluations.py](/backend/app/api/v1/endpoints/evaluations.py)

Implemented behavior:

- validates that submission exists
- validates caller has access to evaluate that submission
- rejects duplicate evaluation creation for the same submission
- computes:
  - `internal_total`
  - `grand_total`
  - `grade`
- stores optional remarks
- can create draft or immediately finalized evaluation depending on payload

## 4.6 Evaluation AI preview

File:

- [evaluations.py](/backend/app/api/v1/endpoints/evaluations.py)

Implemented behavior:

- preview endpoint accepts mark components before save
- computes totals and grade
- invokes AI insight generation
- returns a preview object containing:
  - totals
  - grade
  - AI score and feedback
  - structured AI insight summary, strengths, gaps, suggestions, risk flags, confidence

This gives teachers a pre-save advisory layer without committing the evaluation yet.

## 4.7 Evaluation update and finalization

File:

- [evaluations.py](/backend/app/api/v1/endpoints/evaluations.py)

Implemented behavior:

- update recomputes totals and grade every time mark inputs change
- finalized evaluations are protected from ordinary teacher mutation
- explicit finalize route sets:
  - `is_finalized`
  - `finalized_at`
  - `finalized_by_user_id`
- admin override route can unfinalize when needed

This is the strongest actual control in the exam module today.

## 4.8 Teacher-scoped access

Teacher access is not global. It is derived from academic ownership.

Observed patterns across assignment, submission, and evaluation endpoints:

- assignment creator ownership
- class coordinator ownership
- related class or section authority through academic roles
- admin can bypass most teacher scope restrictions

This gives the module usable authorization, but it is fragmented because it relies on different authority anchors across endpoints.

## 5. Business Rules

The following business rules are actively implemented or clearly implied by the code.

### Rule 1: An assessment is represented by an assignment

There is no standalone `exam` collection. Assignment is the persisted assessment definition.

### Rule 2: A submission requires an active, open assignment

Students cannot upload if:

- the assignment does not exist
- the assignment is closed

### Rule 3: Only students upload submissions

Upload is explicitly student-only.

### Rule 4: Only one evaluation should exist per submission

This is enforced in endpoint logic before insert.

### Rule 5: Marks must follow component bounds

Evaluation create and update enforce:

- `attendance_percent` between `0` and `100`
- `skill` between `0` and `2.5`
- `behavior` between `0` and `2.5`
- `report` between `0` and `10`
- `viva` between `0` and `20`
- `final_exam` between `0` and `60`

### Rule 6: Totals and grade are derived, not user-entered

The system calculates:

- `internal_total`
- `grand_total`
- `grade`

These values should not be treated as free-form frontend inputs.

### Rule 7: Finalized evaluations are protected

After finalization:

- teachers should not continue editing freely
- admin override is required for reversal or exceptional correction

### Rule 8: AI is advisory, not authoritative

AI output informs evaluation but does not automatically replace teacher judgment.

### Rule 9: Assignment plagiarism setting controls downstream similarity checks

Similarity analysis is tied to whether the assignment allows plagiarism checking.

## 6. API Surface

## 6.1 Assignment endpoints

File:

- [assignments.py](/backend/app/api/v1/endpoints/assignments.py)

### `GET /assignments/`

Purpose:

- list assignments with role-scoped filtering

### `GET /assignments/{assignment_id}`

Purpose:

- fetch one assignment

### `POST /assignments/`

Purpose:

- create a new assessment definition

### `PUT /assignments/{assignment_id}`

Purpose:

- update assignment metadata

### `PATCH /assignments/{assignment_id}/plagiarism`

Purpose:

- toggle plagiarism checks for the assignment

### `DELETE /assignments/{assignment_id}`

Purpose:

- archive assignment through soft delete semantics

## 6.2 Submission endpoints

File:

- [submissions.py](/backend/app/api/v1/endpoints/submissions.py)

### `GET /submissions/`

Purpose:

- list submissions

### `GET /submissions/{submission_id}`

Purpose:

- fetch one submission

### `POST /submissions/upload`

Purpose:

- upload a student submission file

### `POST /submissions/{submission_id}/ai-evaluate`

Purpose:

- run or rerun AI evaluation for a submission

### `POST /submissions/ai-evaluate/pending`

Purpose:

- bulk-run AI on pending or failed submissions

### `PUT /submissions/{submission_id}`

Purpose:

- update submission metadata such as notes or status

### `DELETE /submissions/{submission_id}`

Purpose:

- hard-delete submission and remove stored file

## 6.3 Evaluation endpoints

File:

- [evaluations.py](/backend/app/api/v1/endpoints/evaluations.py)

### `GET /evaluations/`

Purpose:

- list evaluations

### `GET /evaluations/{evaluation_id}`

Purpose:

- fetch one evaluation

### `GET /evaluations/{evaluation_id}/trace`

Purpose:

- inspect persisted AI trace history for one evaluation

### `POST /evaluations/ai-preview`

Purpose:

- generate totals, grade, and AI insight preview before save

### `POST /evaluations/`

Purpose:

- create a new evaluation for a submission

### `POST /evaluations/{evaluation_id}/ai-refresh`

Purpose:

- rerun AI insight for an existing evaluation

### `PUT /evaluations/{evaluation_id}`

Purpose:

- update a draft or mutable evaluation

### `PATCH /evaluations/{evaluation_id}/finalize`

Purpose:

- lock and finalize evaluation

### `PATCH /evaluations/{evaluation_id}/override-unfinalize`

Purpose:

- allow privileged admin reversal of finalization

## 6.4 AI chat endpoints used by exam evaluation

File:

- [ai.py](/backend/app/api/v1/endpoints/ai.py)

### `POST /ai/evaluate`

Purpose:

- send teacher/admin evaluation chat prompt and persist AI conversation

### `GET /ai/history/{student_id}/{exam_id}`

Purpose:

- load prior evaluation chat history

Important note:

- `exam_id` is effectively assignment-scoped in the current implementation

## 7. Frontend Implementation

## 7.1 `AssignmentsPage.jsx`

File:

- [AssignmentsPage.jsx](/frontend/src/pages/AssignmentsPage.jsx)

Implemented UI capabilities:

- list assignments
- create assignments
- delete assignments
- filter by subject, section, and status
- toggle plagiarism flag inline

Important gap:

- backend supports update, but this page does not expose full edit

## 7.2 `SubmissionsPage.jsx`

File:

- [SubmissionsPage.jsx](/frontend/src/pages/SubmissionsPage.jsx)

Student capabilities:

- upload submission file
- see assignment-linked submissions
- inspect AI status and upload history

Teacher or admin capabilities:

- browse submission records
- run AI for one submission
- bulk-run AI for pending submissions
- open evaluation console

Important implementation detail:

- teacher/admin view merges submission rows with evaluation rows to show marks and grading status

## 7.3 `Teacher/EvaluateSubmission.jsx`

File:

- [EvaluateSubmission.jsx](/frontend/src/pages/Teacher/EvaluateSubmission.jsx)

Implemented UI capabilities:

- load submission, assignment, and student context
- display extracted answer text
- derive question candidates from assignment description
- preview AI insight before save
- create or update evaluation
- open AI chat side panel for teacher guidance

This is the most complete real exam evaluation surface in the frontend.

## 8. Frontend vs Backend Gaps

### Gap 1: No explicit exam page or exam entity

The frontend exposes assignments and evaluations, not a distinct exam module.

### Gap 2: Assignment update is backend-only

The backend has `PUT /assignments/{assignment_id}`, but `AssignmentsPage.jsx` does not provide full edit UX.

### Gap 3: Submission update and delete are not clearly exposed as managed workflows

The backend supports submission update and delete. The frontend primarily focuses on upload, AI operations, and evaluation entry.

### Gap 4: Evaluation trace is backend-first

The backend exposes `GET /evaluations/{evaluation_id}/trace`, but there is no clear first-class UI for AI trace inspection.

### Gap 5: Finalization control is not fully modeled in UI

The backend has explicit finalize and override-unfinalize routes. The current evaluation console centers on save and AI preview, not a full review-board style finalize lifecycle.

### Gap 6: Result publication layer is missing

The module computes grades, but there is no explicit result publication workflow for students, exam cells, or controllers.

## 9. Risks and Architectural Issues

### Risk 1: Exam and assignment are conflated

This is the biggest architectural issue.

Current state:

- assignments are used as exams
- AI chat uses `exam_id`
- evaluation console labels the context as `Exam/Assignment`

This ambiguity makes future features harder:

- scheduled exams
- retakes
- practical vs theory assessment differentiation
- exam cell workflows

### Risk 2: Legacy class linkage remains in assessment definition

Assignments reference `class_id`, which points to legacy `classes` rather than canonical `sections`.

This keeps the exam workflow partially attached to the older academic model.

### Risk 3: Submission storage is not durable

Submissions use local filesystem storage under `uploads/submissions`.

Implications:

- poor resilience under multi-instance deployment
- complicated cleanup
- file loss risk in ephemeral environments

### Risk 4: Submission delete is destructive while assignment delete is archival

This inconsistency creates governance and recovery problems.

### Risk 5: Expensive work remains too close to request time

The module still performs heavy synchronous or near-synchronous work in live request flows:

- file parsing
- AI evaluation calls
- similarity processing

This can throttle throughput under load.

### Risk 6: No durable exam attempt model

There is no explicit record for:

- exam session start
- attempt state
- submit lock time
- invigilation
- autosave
- multiple attempts

This is acceptable for coursework-style assessments, but not for a full exam system.

## 10. Recommended Cleanup Strategy

### Short-term

- document clearly that current exam module equals assignment-submission-evaluation workflow
- stop using ambiguous labels where possible
- expose assignment edit and evaluation finalization deliberately in the frontend
- align delete semantics between assignments and submissions

### Medium-term

- decide whether to keep coursework and exam as one concept or split them
- migrate assignment `class_id` references toward canonical `section_id`
- move heavy AI and extraction work to a durable worker queue
- add stronger dependency checks before destructive submission operations

### Long-term

If CAPS AI needs a formal university exam office workflow, create a real exam domain with:

- exam definition
- exam schedule
- attempt model
- hall or shift allocation
- invigilation
- result publication
- moderation and approval flow

At that point:

- `assignments` can remain coursework or continuous assessment
- `exams` can become a distinct academic assessment subsystem

## 11. Testing Requirements

Minimum automated test coverage should include the following.

### Unit tests

- attendance point mapping in [grading.py](/backend/app/services/grading.py)
- internal total computation
- grand total computation
- grade bucket mapping
- AI fallback scoring behavior

### API tests

- teacher can create assignment only within allowed scope
- student cannot upload to closed assignment
- duplicate evaluation for same submission is rejected
- evaluation update recomputes totals and grade
- finalized evaluation blocks ordinary teacher edits
- admin override-unfinalize works as intended
- AI preview returns deterministic structure

### Integration tests

- assignment create -> student upload -> teacher evaluate -> finalize flow
- submission AI evaluate -> evaluation AI preview reuse path
- student can view own submission but not other students' submissions
- teacher can access only owned or scoped assessments

### Safety and governance tests to add

- submission delete should be reviewed for governance protection if retention requirements apply
- assignment archive should remain recoverable
- AI and file-processing jobs should be tested under queue-backed execution once migrated

## 12. Final Summary

The current CAPS AI exam module is a real assessment workflow, but it is not yet a full exam management subsystem.

What is implemented well:

- assignment definition
- student submission upload
- teacher evaluation and grading
- AI-assisted review
- finalization controls on evaluations

What is structurally weak:

- no standalone exam entity
- mixed use of assignment and exam terminology
- legacy `class_id` coupling
- local file storage
- inconsistent delete semantics
- limited frontend exposure of backend lifecycle features

The correct description of the current state is:

`Exam Module = Assignment + Submission + Evaluation + AI Assistance`

That is coherent enough for coursework and internal assessment workflows.

It is not yet sufficient for a fully normalized, institution-grade exam office system with scheduling, attempt orchestration, moderation, and published results.

