# Evaluation Module Master

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
Evaluation Module
|-- Evaluation Records
|-- Grade Calculation
|-- AI Preview And Refresh
|-- Finalization Controls
|-- Review-Ticket Adjacency
`-- Audit And Trace Storage
```

## Internal Entity And Flow Tree

```text
Submission
`-- Evaluation
    |-- Score components
    |-- Computed totals and grade
    |-- AI insight and trace
    `-- Finalize or reopen paths
```

## 1. Module Overview

The evaluation module is the grading authority for submitted academic work. It sits after the submission workflow and before review-ticket, audit, analytics, and student result visibility. In the current codebase, an evaluation is not a generic marksheet row. It is a compound assessment record that combines:

- human-entered component scores
- computed totals and grade
- teacher remarks
- AI-assisted interpretation and risk signals
- finalization state
- admin override history

Operationally, this module is the point where a submission becomes an assessed academic artifact.

Primary implementation surfaces:

- [evaluations.py](/backend/app/api/v1/endpoints/evaluations.py)
- [evaluation.py](/backend/app/schemas/evaluation.py)
- [evaluations.py model](/backend/app/models/evaluations.py)
- [EvaluationsPage.jsx](/frontend/src/pages/EvaluationsPage.jsx)
- [EvaluateSubmission.jsx](/frontend/src/pages/Teacher/EvaluateSubmission.jsx)


## 2. Functional Position In The System

The evaluation module depends on the following upstream modules:

- assignment module
- submission module
- auth and user module
- teacher authority model
- AI module

The evaluation module feeds the following downstream modules:

- review ticket workflow
- student academic visibility
- analytics
- audit and compliance

Current workflow:

1. assignment exists
2. student submits work
3. teacher or admin evaluates submission
4. system computes totals and grade
5. AI insight may be previewed, refreshed, and persisted
6. evaluation may be finalized
7. finalized evaluations may later be reopened through ticket flow or direct admin override


## 3. Core Data Model

### 3.1 Main Collection: `evaluations`

Purpose:

- stores the official assessment record for one submission

Key fields currently implemented:

- `_id`
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
- `remarks`
- `ai_score`
- `ai_feedback`
- `ai_status`
- `ai_provider`
- `ai_confidence`
- `ai_risk_flags`
- `ai_strengths`
- `ai_gaps`
- `ai_suggestions`
- `is_finalized`
- `finalized_at`
- `finalized_by_user_id`
- `created_at`
- `updated_at`

Relations:

- `submission_id` -> `submissions._id`
- `student_user_id` -> `users._id`
- `teacher_user_id` -> `users._id`
- `finalized_by_user_id` -> `users._id`

Important semantic rule:

- one evaluation record exists per submission

This is enforced in create flow by checking for an existing evaluation before insert.

### 3.2 Supporting Collection: `ai_evaluation_runs`

Purpose:

- stores AI trace snapshots for evaluation-generation and evaluation-refresh operations

What is persisted:

- evaluation id
- submission id
- teacher id
- totals
- grade
- AI provider/status/confidence
- AI strengths, gaps, suggestions, risk flags
- timestamps

Role:

- gives operational traceability for AI-assisted grading output
- supports later investigation of why a result looked a certain way

Current gap:

- backend and the dedicated teacher console now surface trace history for a single evaluation
- remaining gap is broader cross-evaluation trace discovery and module-level AI operations visibility


## 4. Scoring Logic Implemented

The module does not treat the raw score fields as final truth. Totals and grade are derived values.

### 4.1 Score Components

The current schema accepts:

- `attendance_percent` in range `0..100`
- `skill` in range `0..2.5`
- `behavior` in range `0..2.5`
- `report` in range `0..10`
- `viva` in range `0..20`
- `final_exam` in range `0..60`

These fields represent the teacher-entered scoring inputs.

### 4.2 Computed Values

[evaluations.py](/backend/app/api/v1/endpoints/evaluations.py) delegates derived calculations to [grading.py](/backend/app/services/grading.py):

- `internal_total(...)`
- `grand_total(...)`
- `grade_from_total(...)`

Current computed outputs:

- `internal_total`
- `grand_total`
- `grade`

This means the API is the source of truth for grading math. The frontend does not own these calculations.

### 4.3 Grade Recalculation Behavior

On create:

- all totals and grade are computed before insert

On update:

- if score-bearing fields change, totals and grade are recomputed
- AI insight is also regenerated for changed scoring state

This is correct architecture. It prevents UI-side drift in grade computation.


## 5. AI Logic Implemented

The evaluation module is tightly integrated with AI assistance. It is not a separate AI screen bolted on afterward.

### 5.1 AI Preview

Endpoint:

- `POST /evaluations/ai-preview`

Purpose:

- produce AI insight for a submission and score payload before persisting an evaluation

Behavior:

- computes totals and grade from proposed payload
- if submission already contains `ai_score` and `ai_feedback`, preview reuses that submission-level AI output
- otherwise builds fresh AI insight asynchronously via threadpool helper

Response includes:

- `internal_total`
- `grand_total`
- `grade`
- `ai_score`
- `ai_feedback`
- `ai_insight`

### 5.2 AI Persistence On Create / Update

When an evaluation is created or when grading inputs materially change:

- AI insight is computed
- relevant AI fields are stored on the evaluation record
- a trace record is written to `ai_evaluation_runs`

### 5.3 AI Refresh

Endpoint:

- `POST /evaluations/{evaluation_id}/ai-refresh`

Purpose:

- re-run AI interpretation against current evaluation marks and submission content

Behavior:

- teacher/admin only
- teacher must own evaluation
- rebuilds AI insight from:
  - evaluation totals
  - submission extracted text
  - submission metadata
- updates evaluation AI fields
- writes AI trace

### 5.4 Current AI Architectural Reality

Strengths:

- deterministic fallback behavior exists
- AI output is persisted and traceable
- preview and persisted AI are separated

Weaknesses:

- expensive AI work still runs inside request-time flows
- generic evaluation list pages still do not expose a module-wide AI timeline or cross-evaluation trace discovery
- evaluation AI depends heavily on submission extracted text being present and well-formed


## 6. Access Control And Ownership

### 6.1 Read Access

Current role-level read behavior:

- `admin` can read evaluations
- `teacher` can read evaluations
- `student` can read evaluations

Actual row scoping:

- student reads are restricted to own `student_user_id`
- teacher reads are restricted to own `teacher_user_id`
- admin reads are broader

### 6.2 Create / Update Authority

Create and update are allowed for:

- teacher
- admin

Teacher authority is not global. A teacher can evaluate only if they are allowed to access the submission’s assignment.

Teacher authority check currently combines:

- assignment creator ownership
- class coordinator access to the assignment’s class

This is implemented through `_ensure_teacher_can_evaluate_submission(...)` and assignment access helpers in [evaluations.py](/backend/app/api/v1/endpoints/evaluations.py).

### 6.3 Finalization Authority

Finalize:

- teacher or admin can finalize
- teacher must own evaluation

Unfinalize:

- admin only
- requires a reason payload through `ReviewTicketDecision`

Important governance gap:

- direct admin unfinalize exists as a bypass path even though the system also has a review-ticket workflow for reopening finalized evaluations


## 7. Finalization Model

The evaluation module distinguishes draft grading from finalized grading.

### 7.1 Finalized State

Stored fields:

- `is_finalized`
- `finalized_at`
- `finalized_by_user_id`

Meaning:

- finalized evaluations are intended to be locked for ordinary teacher editing

### 7.2 Enforcement

Current behavior:

- if evaluation is finalized and caller is not admin, update is blocked
- admin may still update finalized evaluation
- admin may also explicitly unfinalize through override endpoint

### 7.3 Practical Consequence

This is not a hard immutability model. It is a teacher-lock model with admin escape hatch.

That may be operationally acceptable, but it needs to be documented clearly because “finalized” does not mean “permanently frozen.”


## 8. Review Ticket Relationship

The evaluation module is tightly related to review tickets, but the relationship is incomplete.

Implemented relationship:

- finalized evaluations can be reopened through review-ticket flow elsewhere in the system

Current inconsistency:

- admin can bypass ticket workflow entirely with `PATCH /evaluations/{id}/override-unfinalize`

Architectural impact:

- the module currently supports both governed reopen and direct privileged reopen
- this weakens the audit semantics of “all reopen actions are ticket-backed”


## 9. API Endpoints

Primary endpoints in [evaluations.py](/backend/app/api/v1/endpoints/evaluations.py):

### 9.1 List Evaluations

- `GET /evaluations/`

Supports filters:

- `student_user_id`
- `teacher_user_id`
- `submission_id`
- `is_finalized`

### 9.2 Get Evaluation By Id

- `GET /evaluations/{evaluation_id}`

### 9.3 Get Evaluation Trace

- `GET /evaluations/{evaluation_id}/trace`

Purpose:

- fetch AI trace history for an evaluation

### 9.4 AI Preview

- `POST /evaluations/ai-preview`

Purpose:

- preview totals, grade, and AI insight before saving

### 9.5 Create Evaluation

- `POST /evaluations/`

Purpose:

- create official evaluation record for a submission

### 9.6 Refresh AI

- `POST /evaluations/{evaluation_id}/ai-refresh`

Purpose:

- recompute AI insight for existing evaluation

### 9.7 Update Evaluation

- `PUT /evaluations/{evaluation_id}`

Purpose:

- modify marks, remarks, or finalization-related state

### 9.8 Finalize Evaluation

- `PATCH /evaluations/{evaluation_id}/finalize`

### 9.9 Admin Override Unfinalize

- `PATCH /evaluations/{evaluation_id}/override-unfinalize`

Purpose:

- reopen a finalized evaluation through privileged admin path


## 10. Frontend Implementation

### 10.1 Main Listing Page

Frontend page:

- [EvaluationsPage.jsx](/frontend/src/pages/EvaluationsPage.jsx)

Current behavior differs by role.

#### Student Experience

Student mode:

- fetches own submissions and evaluations
- shows summary cards:
  - total evaluations
  - finalized evaluations
  - average score
- supports search and finalized filter
- shows evaluation cards/table content with:
  - submission
  - score
  - grade
  - finalized state
  - remarks
  - date

This is read-oriented and acceptable for current scope.

#### Teacher/Admin Experience

Teacher/admin mode uses shared CRUD component:

- overlay-based create and edit form
- list view
- overlay-based filtering
- row actions

Create form supports:

- submission selection
- all scoring fields
- remarks
- `is_finalized`

Columns include:

- submission
- student
- teacher
- AI status
- AI score
- AI confidence
- AI risk flags
- AI feedback
- internal total
- grand total
- grade
- finalized state
- created date

Row actions:

- `Open AI Console`
- `View Trace`
- `Refresh AI`
- `Finalize`
- `Unfinalize` for admin through structured modal reason capture

### 10.2 Dedicated Teacher Evaluation Console

Frontend page:

- [EvaluateSubmission.jsx](/frontend/src/pages/Teacher/EvaluateSubmission.jsx)

This is the richer evaluation workspace.

Capabilities:

- load submission and assignment context
- load existing evaluation
- edit marks
- create evaluation if absent
- update evaluation if present
- preview AI insight before save
- show persisted evaluation AI state after save
- refresh stored evaluation AI for the current evaluation
- view recent evaluation AI trace history inline
- access evaluation chat history
- send evaluation chat messages
- persist and reuse prompt/runtime-backed AI metadata

This page is a better fit for complex grading than the generic CRUD page.


## 11. Frontend Capability Matrix

### Supported In UI

- list evaluations
- create evaluation
- update evaluation
- preview AI
- finalize evaluation
- admin override unfinalize
- view student results
- open AI grading console
- use chat-assisted evaluation workflow

### Missing Or Weak In UI

- generic evaluations list page still does not show a broader evaluation event timeline
- generic evaluations list page still does not intentionally visualize AI strengths, gaps, and suggestions
- no immutable history/timeline view for evaluation state changes


## 12. Business Rules Implemented

The following rules are implemented or strongly implied in code:

### 12.1 One Evaluation Per Submission

- create flow rejects duplicate evaluation for the same submission

### 12.2 Totals Are Derived

- `internal_total`, `grand_total`, and `grade` are computed by backend service logic

### 12.3 Teacher Scope Is Not Open-Ended

- teacher must own or legitimately access the submission’s assignment context

### 12.4 Students Can Only See Their Own Evaluations

- enforced by row filter on `student_user_id`

### 12.5 Finalized Evaluations Are Teacher-Locked

- teacher cannot edit finalized evaluation
- admin can still intervene

### 12.6 AI Trace Is Persisted On Create And Refresh

- create/update/refresh flows persist trace data into `ai_evaluation_runs`
- trace rows now also store `ai_prompt_version` and `ai_runtime_snapshot`


## 13. Frontend Vs Backend Gaps

### 13.1 Trace Visibility Gap

Backend:

- supports `GET /evaluations/{id}/trace`

Frontend:

- teacher evaluation console exposes trace history for one evaluation
- generic evaluations page now exposes a dedicated trace viewer modal

### 13.2 AI Refresh Gap

Backend:

- supports explicit AI refresh endpoint

Frontend:

- teacher evaluation console exposes a first-class stored-AI refresh action
- generic evaluations page now also surfaces refresh directly

### 13.3 Governance UX Gap

Backend:

- admin unfinalize requires a reason payload

Frontend:

- uses a structured modal
- no review-id style governance flow
- still has no review-id style governance flow

### 13.4 Rich AI Data Gap

Backend stores:

- confidence
- risk flags
- strengths
- gaps
- suggestions

Frontend mostly surfaces:

- `ai_score`
- `ai_feedback`

This is now only partly true.

The dedicated evaluation console also surfaces:

- stored AI status/provider
- confidence
- risk flags
- recent trace history

The generic evaluations page now also surfaces:

- AI status
- confidence
- risk flags
- trace viewer
- direct AI refresh

The remaining gap is that list UI still underuses strengths, gaps, and suggestions outside the dedicated console.


## 14. Architectural Issues

### 14.1 Evaluation Is Doing Too Much

The aggregate currently mixes:

- grade recording
- grade calculation
- AI interpretation
- finalization workflow
- reopen workflow adjacency
- audit generation

This is workable, but it makes the module heavy and operationally central.

### 14.2 Finalization Is Not Truly Immutable

The presence of admin override means “finalized” is not equivalent to “locked forever.” It means “teacher locked, admin reopenable.”

That is fine if intentional, but it must be treated as a policy choice, not as true record immutability.

### 14.3 Review-Ticket Bypass

If review tickets are intended to be the canonical reopen path, direct override-unfinalize is an architectural bypass.

### 14.4 AI Work In Request Path

Create/update/refresh operations still do meaningful AI work during user-facing requests.

Under scale, this can:

- increase latency
- create timeout pressure
- make evaluation save performance depend on AI provider responsiveness

### 14.5 Evaluation Ownership Model Is Narrow

Teacher row access is tied to `teacher_user_id` on the evaluation record. If assignment ownership or coordinator mapping changes later, historical and current authority semantics may diverge.


## 15. Risks

### 15.1 Operational Risk

- AI latency can slow grading operations

### 15.2 Governance Risk

- direct admin reopen weakens ticket-based governance discipline

### 15.3 UX Risk

- generic CRUD UI hides important evaluation semantics

### 15.4 Auditability Risk

- trace exists, but lack of mainline UI means operators may not use it

### 15.5 Policy Drift Risk

- finalization expectations may be misunderstood by users if they assume it is irreversible


## 16. Cleanup Strategy

Recommended cleanup path:

### Phase 1: Surface Existing Backend Features Better

- extend beyond per-row trace viewer into broader evaluation timeline/history
- display AI strengths, gaps, and suggestions intentionally outside the dedicated console
- link broader AI activity review into the dedicated AI operations page where appropriate

### Phase 2: Tighten Governance Semantics

- decide whether admin override-unfinalize should remain
- if it remains, treat it as exceptional and audit-heavy
- if review tickets are canonical, require ticket reference for reopen

### Phase 3: Reduce Request-Time AI Cost

- move AI refresh or regeneration to worker-backed asynchronous flow
- keep synchronous preview only where necessary

### Phase 4: Clarify Finalization Contract

- document finalization policy in UI
- distinguish:
  - draft
  - finalized
  - reopened

### Phase 5: Improve Historical Explainability

- add evaluation event timeline:
  - created
  - AI refreshed
  - updated
  - finalized
  - reopened


## 17. Testing Requirements

The evaluation module should have strong unit, integration, and UI coverage because it affects academic integrity.

### 17.1 Unit Tests

- grading math
- score validation boundaries
- one-evaluation-per-submission enforcement
- teacher ownership checks
- finalized-update blocking for teachers
- admin override reason validation
- AI preview fallback behavior

### 17.2 Integration Tests

- create evaluation from valid submission
- reject duplicate evaluation
- update evaluation and verify recomputed totals
- finalize evaluation then reject teacher update
- allow admin override unfinalize
- verify student cannot fetch another student’s evaluation
- verify teacher cannot update another teacher’s evaluation
- verify trace endpoint returns expected AI history

### 17.3 Frontend Tests

- student view renders finalized and score filters correctly
- teacher evaluation console can preview AI and save evaluation
- finalize and unfinalize actions call correct endpoints
- role-based rendering of admin-only unfinalize
- display of AI score and grade after save

### 17.4 Governance / Audit Tests

- audit record emitted on create
- audit record emitted on update
- audit record emitted on finalize
- audit record emitted on override-unfinalize
- AI trace row created on create/refresh/update when applicable


## 18. Current Status Summary

The evaluation module is already a meaningful production subsystem. It is not missing core grading capability. The current implementation supports:

- controlled grading
- computed totals and grades
- student and teacher scoped access
- AI-assisted preview and refresh
- finalization
- admin reopen
- audit logging

The main gaps are not absence of functionality. The main gaps are:

- governance consistency
- uneven frontend exposure of backend features between the generic list and the dedicated teacher console
- request-time AI cost
- clarity of finalization semantics

That means the correct next step is refinement and hardening, not a ground-up rewrite.


