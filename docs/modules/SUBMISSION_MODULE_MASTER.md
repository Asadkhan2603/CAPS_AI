# SUBMISSION MODULE MASTER

## Module Tree

```text
Submission Module
|-- Submission Records
|-- File Upload Storage
|-- Extracted Text Processing
|-- Teacher Review Access
|-- AI Evaluation Entry Point
`-- Evaluation Dependency
```

## Internal Entity And Flow Tree

```text
Assignment
`-- Submission
    |-- File and extracted text
    |-- Teacher access and review
    `-- Evaluation and AI workflows
```

## 1. Module Overview

The submission module is the learner-delivery record for assignment work. It stores the uploaded artifact, extracted text, AI review state, and teacher-accessible submission metadata for each student assignment upload.

This module sits between:

- assignments
- evaluations
- AI-assisted scoring
- similarity analysis

It is therefore one of the most important workflow modules in CAPS AI. It is not just file storage. It is the system-of-record for what the student submitted, what text was extracted, and whether AI processing has been attempted.

Primary backend files:

- [submissions.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\api\v1\endpoints\submissions.py)
- [submission.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\schemas\submission.py)
- [submissions.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\models\submissions.py)

Primary frontend files:

- [SubmissionsPage.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\SubmissionsPage.jsx)
- [EvaluateSubmission.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\Teacher\EvaluateSubmission.jsx)

## 2. Core Domain Model

### 2.1 Primary entity

The module centers on:

- `submissions`

Each submission belongs to:

- one assignment
- one student user

Each submission may additionally accumulate:

- extracted text
- AI evaluation state
- AI score and feedback
- similarity score

### 2.2 Purpose of the record

A submission record answers these questions:

- which assignment did the student submit for?
- what file was uploaded?
- what text was extracted from it?
- what is the current AI review state?
- what downstream evaluation can be attached to it?

## 3. Data Model

Schema/model files:

- [submission.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\schemas\submission.py)
- [submissions.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\models\submissions.py)

### 3.1 Collection

Primary collection:

- `submissions`

### 3.2 Stored fields

Observed fields exposed by the model/schema:

- `id`
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

### 3.3 File storage model

Uploads are stored on local disk under:

- `uploads/submissions`

Constraints:

- max size: `10 MB`
- allowed extensions:
  - `.pdf`
  - `.docx`
  - `.txt`
  - `.md`

Important operational implication:

- submission file storage is local-disk based, not durable object storage

### 3.4 AI state model

AI state is stored directly on the submission row:

- `ai_status`
- `ai_score`
- `ai_feedback`
- `ai_provider`
- `ai_error`

Observed `ai_status` values in code:

- `pending`
- `running`
- `completed`
- `failed`

This is a practical denormalized design, but it couples AI execution state tightly to the main submission record.

## 4. Backend Logic Implemented

### 4.1 Teacher access model

Teacher access is not global.

Teacher can access a submission if:

- they created the underlying assignment
- or they coordinate the assignment’s class/section

Helper functions:

- `_teacher_can_access_assignment(...)`
- `_teacher_accessible_assignment_ids(...)`
- `_teacher_can_access_submission(...)`

This means the teacher read model is assignment-owner or class-coordinator scoped.

### 4.2 List submissions

Endpoint:

- `GET /submissions/`

Roles:

- `admin`
- `teacher`
- `student`

Supported filters:

- `assignment_id`
- `student_user_id`
- `status`
- `skip`
- `limit`

Scope behavior:

- student:
  - forced to own `student_user_id`
- teacher:
  - restricted to accessible assignment ids
- admin:
  - unrestricted

### 4.3 Get one submission

Endpoint:

- `GET /submissions/{submission_id}`

Scope behavior:

- student can only read own submission
- teacher can only read if teacher-accessible
- admin can read all

### 4.4 Upload submission

Endpoint:

- `POST /submissions/upload`

Role:

- student only

Validation:

- assignment must exist
- assignment must not be closed
- file extension must be allowed
- file must not be empty
- file must not exceed 10 MB

Upload behavior:

- reads file bytes into memory
- extracts text using:
  - `parse_file_content(...)`
- stores file under generated uuid filename
- inserts submission document with:
  - `status = submitted`
  - `ai_status = pending`
  - null AI fields initially

Important note:

- the upload path currently does not prevent multiple submissions per assignment by the same student
- no duplicate submission guard was observed in the reviewed code

### 4.5 AI evaluate one submission

Endpoint:

- `POST /submissions/{submission_id}/ai-evaluate`

Roles:

- `admin`
- `teacher`

Behavior:

- verifies submission access
- if already completed and `force = false`, returns cached result
- otherwise sets `ai_status = running`
- runs AI feedback generation through:
  - `generate_ai_feedback(...)`
- stores AI result fields back onto submission
- writes audit event

Important architectural fact:

- AI evaluation still runs inline with the request path

### 4.6 Bulk AI evaluate pending submissions

Endpoint:

- `POST /submissions/ai-evaluate/pending`

Roles:

- `admin`
- `teacher`

Behavior:

- queries submissions whose AI state is:
  - `pending`
  - `failed`
  - `null`
- optional filter by assignment
- teachers can only evaluate accessible submissions
- each row is processed synchronously in loop
- each result writes an audit event

Important implication:

- this is convenient operationally
- but it is still request-time bulk work rather than queued background processing

### 4.7 Update submission

Endpoint:

- `PUT /submissions/{submission_id}`

Roles:

- `admin`
- `teacher`
- `student`

Behavior:

- student can only update:
  - `notes`
- teacher/admin can update any schema field exposed by `SubmissionUpdate`

Editable fields include:

- `notes`
- `status`
- `ai_status`
- `ai_score`
- `ai_feedback`
- `ai_provider`
- `ai_error`
- `similarity_score`

Important implication:

- teacher/admin can directly mutate AI fields and submission state
- this is flexible but weakens process integrity if not carefully governed

### 4.8 Delete submission

Endpoint:

- `DELETE /submissions/{submission_id}`

Roles:

- `admin`
- `teacher`
- `student`

Scope:

- student only own submission
- teacher only teacher-accessible submission
- admin unrestricted

Behavior:

- hard deletes Mongo document
- deletes stored file from local disk if present

Important architectural issue:

- this is a hard delete, not a soft archive
- the collection still appears in recovery allowlist, which creates a contract mismatch

## 5. Frontend Implementation

### 5.1 `SubmissionsPage.jsx`

This page is the main submission UI for both students and teaching/admin users.

Student behavior:

- upload assignment file
- add notes
- view own submissions
- see AI status
- search/filter own submissions

Teacher/admin behavior:

- view submission table
- filter by assignment
- run AI for one submission
- bulk-run AI for pending submissions
- open evaluation console

Important implementation note:

- the page does not expose delete actions even though backend delete exists

### 5.2 Student upload UI

Student upload form exposes:

- assignment
- notes
- file

The page also displays:

- allowed file types
- 10 MB max size
- upload progress state through `FileUpload`

### 5.3 Teacher/admin table actions

Available actions:

- `Evaluate`
  - navigates to evaluation console
- `Run/Rerun AI`
  - triggers AI evaluation endpoint

### 5.4 `EvaluateSubmission.jsx`

This page is not the submission module itself, but it uses submission data heavily.

It loads:

- submission
- assignment
- student
- existing evaluation

It also uses:

- `submission.extracted_text`
- `submission.notes`

as input to the AI-assisted evaluation conversation and preview flows.

This means submission records are foundational to the teacher evaluation workspace.

## 6. Business Rules

### Rule 1: Only students upload submissions

The upload endpoint is student-only.

### Rule 2: Closed assignments reject submissions

Students cannot upload to assignments whose status is `closed`.

### Rule 3: File validation is strict

Allowed types:

- PDF
- DOCX
- TXT
- MD

Max size:

- 10 MB

### Rule 4: AI status starts pending

New uploads always start with:

- `ai_status = pending`

### Rule 5: Teacher scope follows assignment ownership or class coordination

Teachers are not universal submission viewers.

### Rule 6: Students can only self-edit notes

Students cannot directly change:

- submission status
- AI status
- AI score
- similarity score

## 7. Frontend vs Backend Gaps

### 7.1 Backend delete exists, frontend does not expose it

This is likely safer for students, but it means UI and API lifecycle support differ.

### 7.2 No duplicate submission policy in UI or backend

The reviewed upload flow does not show clear prevention of multiple submissions per assignment by the same student.

If multiple submissions are allowed, that policy is not surfaced clearly.

### 7.3 No explicit download/view file action in main UI

The page shows filenames, but not a dedicated download or file preview workflow in the reviewed code.

### 7.4 Submission list is assignment-id centric

The teacher/admin UI is functional, but still fairly technical. It lacks richer assignment, student, and course context.

## 8. Architectural Issues

### 8.1 Hard delete conflicts with recovery assumptions

The submission endpoint hard deletes rows, but submissions are included in generic recovery allowlists.

This is an architectural inconsistency.

### 8.2 AI execution is still request-path heavy

Single and bulk AI evaluation both execute synchronously from request handlers.

This creates:

- throughput risk
- timeout risk
- user-facing latency

### 8.3 Local disk storage is not durable

Submission files are stored on local disk.

This is not safe for:

- ephemeral containers
- multi-instance scale-out
- cross-node access

### 8.4 Submission row stores too many concerns

The record holds:

- file metadata
- extracted text
- AI execution state
- similarity score

This is pragmatic, but it mixes storage, processing, and review state in one aggregate.

## 9. Risks and Bugs Identified

### 9.1 No duplicate submission guard observed

A student may be able to upload multiple submissions for the same assignment.

This may be intended, but if not, it is a policy hole.

### 9.2 Hard delete destroys evidence

Deleting a submission removes:

- database row
- uploaded file

This is risky for academic auditability.

### 9.3 Extracted text stored inline

Full extracted answer text is stored directly in the submission record.

This is useful for AI and evaluation, but it increases:

- document size
- sensitivity of the record

### 9.4 Bulk AI is operationally heavy

The bulk AI endpoint loops synchronously and runs AI work inline.

## 10. Downstream Dependencies

Submissions feed directly into:

- evaluations
- AI evaluation preview
- AI chat
- similarity scoring
- history pages

Observed frontend/backend dependencies:

- [EvaluateSubmission.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\Teacher\EvaluateSubmission.jsx)
- [evaluations.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\api\v1\endpoints\evaluations.py)
- [similarity.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\api\v1\endpoints\similarity.py)
- [HistoryPage.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\HistoryPage.jsx)

## 11. Cleanup Strategy

### Short-term

- decide whether multiple submissions per assignment are allowed
- if not, enforce duplicate prevention
- add explicit file download/view action in UI
- stop hard delete for academic evidence if retention matters

### Medium-term

- move uploaded files to durable object storage
- move AI evaluation to queued durable worker flow
- add stronger audit/retention semantics for submission lifecycle changes

### Long-term

Separate concerns more clearly:

- artifact storage
- extracted content
- AI processing state
- academic review state

without losing the current pragmatic usability.

## 12. Testing Requirements

### Unit tests

- file extension validation
- max file size validation
- assignment closed rejection
- student-only upload restriction
- teacher access scope
- AI evaluate cached-return behavior
- student update limited to notes only

### API tests

- student upload success
- student cannot read another student submission
- teacher can read accessible submission
- teacher cannot read unrelated submission
- AI evaluate updates ai fields
- bulk AI skips teacher-inaccessible rows
- delete removes file and row

### Integration tests

- submission upload -> evaluation console load
- submission upload -> extracted text available for evaluation AI
- similarity workflow updates submission-linked signals

## 13. Current Module Assessment

The submission module is a real workflow core, not a simple upload endpoint.

Strengths:

- clear student upload path
- strong teacher scope logic
- practical AI state model
- direct integration into evaluation tooling

Weaknesses:

- hard delete instead of recoverable archive
- local file storage
- request-time heavy AI processing
- unclear duplicate submission policy

As implemented today, the module is functional and central to assessment workflows. Its biggest weaknesses are operational durability and lifecycle integrity, not missing core functionality.