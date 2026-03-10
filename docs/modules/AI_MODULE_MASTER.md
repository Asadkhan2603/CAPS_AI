# AI Module Master

## Module Tree

```text
AI Module
|-- Submission AI Evaluation
|-- Evaluation AI Preview And Refresh
|-- Teacher AI Chat
|-- Similarity Detection
`-- AI Trace Storage
```

## Internal Entity And Flow Tree

```text
Submission
`-- AI scoring and feedback
    `-- Evaluation preview
        `-- Evaluation persistence
            `-- AI trace

Teacher chat
`-- AI guidance on evaluation context

Similarity
`-- Pairwise checks
    `-- Alerts and logs
```

## 1. Module Overview

The AI module in CAPS AI is not a single model endpoint. It is a collection of AI-assisted academic workflows built around student submissions, teacher evaluation support, and similarity detection.

The implemented AI surface currently spans four main capabilities:

1. AI evaluation of submission text
2. AI-assisted evaluation preview and traceable insights
3. Teacher-to-AI chat for exam or assignment evaluation discussion
4. Similarity detection across submissions with alerting

Primary backend files:

- [ai.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\ai.py)
- [submissions.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\submissions.py)
- [evaluations.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\evaluations.py)
- [similarity.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\similarity.py)
- [ai_runtime.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_runtime.py)
- [ai_jobs.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_jobs.py)
- [ai_chat_service.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_chat_service.py)
- [ai_evaluation.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_evaluation.py)
- [evaluation_ai_module.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\evaluation_ai_module.py)
- [submission_ai.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\submission_ai.py)
- [similarity_pipeline.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\similarity_pipeline.py)
- [similarity_engine.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\similarity_engine.py)

Primary frontend consumers:

- [SubmissionsPage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\SubmissionsPage.jsx)
- [AIModulePage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\AIModulePage.jsx)
- [EvaluateSubmission.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Teacher\EvaluateSubmission.jsx)
- [aiService.js](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\services\aiService.js)

Companion planning document:

- [AI_MODULE_ACTION_PLAN.md](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\AI_MODULE_ACTION_PLAN.md)
- [AI_MODULE_CONTRACTS.md](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\AI_MODULE_CONTRACTS.md)

Important implementation reality:

- OpenAI is optional
- deterministic fallback logic exists throughout
- AI state is stored inside domain records rather than in a single isolated AI domain table

That means AI in CAPS AI is an augmentation layer over academic workflows, not a standalone product surface.

## 2. AI Capabilities Implemented

## 2.1 Submission AI scoring

Submission text is extracted and then passed through AI scoring logic to produce:

- `ai_status`
- `ai_score`
- `ai_feedback`
- `ai_provider`
- `ai_error`

These fields are stored on `submissions`.

Submission AI records now also persist:

- `ai_prompt_version`
- `ai_runtime_snapshot`

## 2.2 Evaluation AI insight

Evaluation workflows use AI-generated insight to enrich teacher grading with:

- AI score
- AI feedback
- confidence
- strengths
- gaps
- suggestions
- risk flags

These fields are stored on `evaluations`.

Evaluation AI records now also persist:

- `ai_prompt_version`
- `ai_runtime_snapshot`

## 2.3 Teacher AI evaluation chat

Teachers and admins can ask AI for evaluation guidance in a chat-style thread scoped by:

- student
- exam or assignment
- question

Threads are stored in `ai_evaluation_chats`.

## 2.4 Similarity detection

The system computes TF-IDF cosine similarity across submissions tied to the same assignment and stores:

- similarity scores
- matched submission ids
- flagged status
- visibility metadata

These records are stored in `similarity_logs`.

## 3. Collections and Stored AI State

The AI module uses multiple collections rather than one monolithic AI data store.

## 3.1 `submissions`

AI-related fields:

- `ai_status`
- `ai_score`
- `ai_feedback`
- `ai_provider`
- `ai_error`
- `similarity_score`
- `extracted_text`

Purpose:

- store submission-level AI evaluation result
- store extracted text used by AI and similarity flows

## 3.2 `evaluations`

AI-related fields:

- `ai_score`
- `ai_feedback`
- `ai_status`
- `ai_provider`
- `ai_confidence`
- `ai_risk_flags`
- `ai_strengths`
- `ai_gaps`
- `ai_suggestions`

Purpose:

- persist teacher-facing AI insight alongside academic grading data

## 3.3 `ai_evaluation_runs`

Used by evaluation trace persistence.

Purpose:

- keep historical AI trace records for evaluation generation and refresh operations

Stored fields include:

- evaluation id
- submission id
- actor user id
- AI provider/status/score
- prompt version
- runtime snapshot
- confidence
- strengths
- gaps
- suggestions
- created_at

This collection is important because it preserves traceability of AI assistance over time.

## 3.4 `ai_evaluation_chats`

Schema/model files:

- [ai_chat.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\schemas\ai_chat.py)
- [ai_chat.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\models\ai_chat.py)

Stored fields:

- `teacher_id`
- `student_id`
- `exam_id`
- `question_id`
- `messages`
- `created_at`
- `updated_at`

AI messages inside `messages` now also capture:

- `provider`
- `provider_error`
- `prompt_version`
- `runtime_snapshot`

Purpose:

- persist teacher-AI conversation history by student and exam

Indexes:

- unique `(student_id, exam_id)`
- `teacher_id`
- `exam_id`

## 3.5 `similarity_logs`

Schema/model files:

- [similarity_log.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\schemas\similarity_log.py)
- [similarity_logs.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\models\similarity_logs.py)

Stored fields:

- `source_submission_id`
- `matched_submission_id`
- `source_assignment_id`
- `matched_assignment_id`
- `source_class_id`
- `matched_class_id`
- `visible_to_extensions`
- `score`
- `threshold`
- `is_flagged`
- `engine_version`
- `created_at`

Purpose:

- persist pairwise similarity checks and flagging decisions

## 3.6 `ai_jobs`

Stored fields:

- `job_type`
- `status`
- `requested_by_user_id`
- `requested_by_role`
- `idempotency_key`
- `params`
- `progress`
- `summary`
- `error`
- `requested_at`
- `started_at`
- `completed_at`
- `worker_id`

Purpose:

- persist durable AI and similarity job state outside the request lifecycle
- support queued, running, completed, and failed operator-visible execution

## 4. Backend Logic Implemented

## 4.1 OpenAI-backed evaluation service with fallback

File:

- [ai_evaluation.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_evaluation.py)

Behavior:

- computes heuristic metrics from submission text
- attempts OpenAI response generation and JSON parsing
- falls back to deterministic local evaluation if:
  - OpenAI key is not configured
  - provider returns invalid output
  - provider fails

Return contract includes:

- score
- summary
- status
- provider
- error
- prompt version
- runtime snapshot

This fallback design is important because it keeps academic flows working even without external AI availability.

## 4.5 Runtime configuration and durable AI jobs

Files:

- [ai_runtime.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_runtime.py)
- [ai_jobs.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_jobs.py)
- [scheduler.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\scheduler.py)

Behavior:

- stores effective runtime overrides in `settings`
- exposes prompt version and runtime snapshots across AI-producing workflows
- queues bulk submission AI and async similarity work into persisted `ai_jobs`
- processes queued jobs through opportunistic kickoff plus scheduler polling
- tracks `queued`, `running`, `completed`, and `failed` lifecycle state

## 4.2 AI insight builder for evaluations

File:

- [evaluation_ai_module.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\evaluation_ai_module.py)

Behavior:

- calls `generate_ai_feedback(...)`
- derives strengths, gaps, and suggestions from the summary text
- computes confidence level
- computes risk flags from:
  - attendance percent
  - grand total
  - AI score
  - grade

Risk flags currently include examples such as:

- `low_attendance`
- `critical_academic_risk`
- `below_passing_trend`
- `weak_submission_quality`
- `manual_review_recommended`

## 4.3 AI chat generation

File:

- [ai_chat_service.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_chat_service.py)

Behavior:

- accepts teacher instruction, question text, rubric, and student answer
- calls OpenAI if configured
- otherwise returns structured fallback text with:
  - suggested marks
  - explanation
  - constructive feedback
  - improvement suggestions

The service also strips accidental markdown fenced blocks to keep UI output cleaner.

## 4.4 Similarity engine

File:

- [similarity_engine.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\similarity_engine.py)

Behavior:

- normalizes source and candidate text
- vectorizes using TF-IDF
- computes cosine similarity
- returns normalized scores between `0.0` and `1.0`

This is not LLM-based similarity. It is a classical vector-space similarity engine.

## 5. AI API Endpoints

## 5.1 Dedicated AI operations and chat endpoints

File:

- [ai.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\ai.py)

### `GET /ai/admin/runtime-config`

Purpose:

- return effective runtime configuration and provider mode

Access:

- `admin`

### `PUT /ai/admin/runtime-config`

Purpose:

- persist runtime overrides for provider enablement, model, timeout, token limit, and similarity threshold

Access:

- `admin`

### `GET /ai/ops/overview`

Purpose:

- return scoped AI operational summary including provider mode, runtime config, recent evaluation runs, recent jobs, similarity flags, and chat threads

Access:

- `teacher`
- `admin`

### `GET /ai/jobs`

Purpose:

- list durable AI jobs for the current operator scope

### `GET /ai/jobs/{job_id}`

Purpose:

- inspect one durable AI job

### `POST /ai/evaluate`

Purpose:

- send a teacher/admin AI evaluation chat message
- receive AI response
- persist or extend the chat thread

Access:

- `teacher`
- `admin`

Behavior:

- validates teacher access to the assignment
- optionally resolves submission context
- persists both teacher and AI messages into `ai_evaluation_chats`
- writes audit event `ai_chat_evaluate`

### `GET /ai/history/{student_id}/{exam_id}`

Purpose:

- fetch AI chat history for a teacher/admin on a student and exam pair

Access:

- `teacher`
- `admin`

## 5.2 Submission AI endpoints

File:

- [submissions.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\submissions.py)

### `POST /submissions/{submission_id}/ai-evaluate`

Purpose:

- run AI evaluation for one submission

Access:

- `teacher`
- `admin`

Behavior:

- checks teacher access to the submission
- respects `force` for rerun
- writes AI result back to the submission record
- stores prompt/runtime metadata on the submission
- audits the action

### `POST /submissions/ai-evaluate/pending`

Purpose:

- bulk-evaluate pending or failed submissions

Access:

- `teacher`
- `admin`

Behavior:

- filters by `ai_status in ['pending', 'failed', None]`
- optional assignment filter
- queues a durable `ai_jobs` record instead of doing the full bulk run inside the request
- returns queued job metadata for operator tracking

## 5.3 Evaluation AI endpoints

File:

- [evaluations.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\evaluations.py)

### `POST /evaluations/ai-preview`

Purpose:

- generate AI insight preview before saving marks

Behavior:

- reuses submission-level AI output if already available
- otherwise builds fresh AI insight asynchronously via threadpool

### `GET /evaluations/{evaluation_id}/trace`

Purpose:

- fetch historical AI trace records for one evaluation

### `POST /evaluations/{evaluation_id}/ai-refresh`

Purpose:

- rerun AI insight for an existing evaluation

Behavior:

- updates AI fields on the evaluation
- persists a new trace record
- audits the refresh action

## 5.4 Similarity endpoints

File:

- [similarity.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\similarity.py)

### `GET /similarity/checks`

Purpose:

- list similarity log records

Access:

- `admin`
- `teacher`

Teacher visibility is scoped through:

- assignment ownership
- class coordinator ownership
- `year_head` extension role

### `POST /similarity/checks/run/{submission_id}`

Purpose:

- run synchronous similarity analysis for one submission

### `POST /similarity/checks/run-async/{submission_id}`

Purpose:

- queue asynchronous similarity analysis as a durable AI job

Behavior:

- requires plagiarism to be enabled for the assignment
- persists a `similarity_check` job in `ai_jobs`
- similarity writes are idempotent by source/match/threshold/engine version
- notifies relevant actors only when a flag transitions into the flagged state

## 6. Frontend Implementation

## 6.1 Submission AI UI

Frontend file:

- [SubmissionsPage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\SubmissionsPage.jsx)

Teacher/admin capabilities:

- run AI for one submission
- bulk-run AI for pending submissions
- inspect AI status, score, provider, and feedback in the table

Student capabilities:

- view AI status on their own submissions

## 6.2 Teacher AI-assisted evaluation console

Frontend file:

- [EvaluateSubmission.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Teacher\EvaluateSubmission.jsx)

Capabilities:

- load submission and assignment context
- preview AI insight before saving marks
- show persisted evaluation AI state after save
- refresh stored evaluation AI through `/evaluations/{evaluation_id}/ai-refresh`
- load historical AI trace via `/evaluations/{evaluation_id}/trace`
- open teacher-AI chat panel
- send evaluation guidance prompts through `/ai/evaluate`
- load historical chat via `/ai/history/...`

This is the main frontend surface where the AI module becomes an interactive teacher workflow.

## 6.3 Dedicated AI service wrapper

Frontend file:

- [aiService.js](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\services\aiService.js)

Current wrappers:

- `sendEvaluationChatMessage(...)`
- `getEvaluationChatHistory(...)`
- `getAiOperationsOverview(...)`
- `getEvaluationTrace(...)`
- `refreshEvaluationAi(...)`
- `getAiRuntimeConfig(...)`
- `updateAiRuntimeConfig(...)`
- `listAiJobs(...)`
- `getAiJob(...)`

This is a narrow wrapper layer, not a broader typed AI SDK.

## 6.4 Dedicated AI operations page

Frontend file:

- [AIModulePage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\AIModulePage.jsx)

Capabilities:

- show provider/runtime mode and key AI settings
- let admins update effective runtime AI settings
- show submission AI pipeline counts
- show durable AI job queue state
- show recent evaluation AI runs with direct evaluation-console handoff
- show recent similarity flags
- show recent AI chat thread activity

This page gives the module a first-class standalone operational UI for teacher/admin roles.

## 6.5 Analytics and dashboard consumption

AI signals also appear indirectly in:

- teacher section analytics
- dashboard similarity alert counts
- submission tables
- evaluation preview cards

This means AI output already influences operational prioritization, not only grading convenience.

## 7. Business Rules

### Rule 1: AI is assistive, not authoritative

Teachers can still save marks manually. AI is used for insight, scoring guidance, and flagging.

### Rule 2: Teacher access is scoped

Teachers cannot run AI against arbitrary assignments or submissions. Access is constrained by:

- assignment creator ownership
- class coordinator scope

### Rule 3: Submission AI and evaluation AI are connected

Evaluation preview prefers existing submission-level AI output when available. This keeps traces more deterministic and avoids unnecessary recomputation.

### Rule 4: Similarity analysis respects plagiarism toggle

If assignment plagiarism is disabled, similarity checks are rejected.

### Rule 5: AI fallback is part of normal operation

Missing OpenAI configuration does not fully disable the AI module. The system falls back to deterministic local logic.

### Rule 6: AI traces are persisted for evaluation workflows

Evaluation AI decisions are not purely transient. They can be inspected later through trace endpoints.

## 8. Strengths of Current Implementation

### Strength 1: Fallback-first resilience

The module is designed to keep functioning even when the external AI provider is unavailable.

### Strength 2: AI state is persisted

AI output is stored in submissions, evaluations, trace runs, chat threads, and similarity logs.

### Strength 3: Teacher workflow integration is real

The AI module is not isolated. It is integrated into:

- submission review
- evaluation console
- risk detection
- similarity alerting

### Strength 4: Similarity flow includes notifications

Flagged similarity results can notify assignment creators, class coordinators, and year heads.

## 9. Remaining Gaps

The original AI module gaps are now largely closed. The remaining work is mostly depth, not missing foundation.

### Gap 1: Cross-module AI exploration is still shallow

The module now has:

- a dedicated AI operations page
- admin runtime controls
- a durable AI job queue surface
- per-evaluation trace history

The remaining gap is deeper historical exploration:

- no global AI trace search across time/provider/actor
- no dedicated submission-plus-evaluation unified run explorer
- no richer filtering beyond the overview slices

### Gap 2: Governance is visible, but still not policy-driven

The system now persists:

- prompt versions
- runtime snapshots
- similarity engine version
- durable job state

What is still missing:

- explicit AI usage policy reporting
- provider cost visibility
- teacher override analytics
- stronger model change governance workflows

## 10. Risks and Architectural Issues

### Risk 1: Single-item AI flows still execute in request time

Bulk submission AI and async similarity are now durable jobs, but some work still happens directly in request flows:

- single submission AI evaluation
- synchronous similarity check endpoint
- teacher AI chat generation
- submission upload text extraction

### Risk 2: AI state is intentionally distributed

This keeps AI close to the academic records it augments, but it still means retention, reporting, and governance have to aggregate across:

- `submissions`
- `evaluations`
- `ai_evaluation_runs`
- `ai_evaluation_chats`
- `similarity_logs`
- `ai_jobs`

### Risk 3: Similarity engine remains in-process and memory-bound

The job queue makes similarity execution more durable, but the underlying TF-IDF computation still runs inside the application process.

### Risk 4: Governance metadata exists, but operator analytics remain limited

Prompt versions and runtime snapshots are now stored, but the module still lacks:

- fallback-rate dashboards
- queue latency tracking
- cost or token monitoring
- model change reporting

## 11. Recommended Cleanup Strategy

### Short-term

- build richer AI trace and job filtering on top of the new operations surface
- add module-level metrics for queue latency, failure rate, and fallback rate
- add tests around job idempotency and runtime-config persistence

### Medium-term

- decide whether synchronous similarity should remain exposed or become queue-first
- add operational dashboards or admin analytics tiles for AI job health
- expand governance reporting around teacher overrides and AI usage trends

### Long-term

Adopt a more deliberate AI platform layer:

- stronger observability and cost monitoring
- more explicit governance and review policy tooling
- broader AI analytics for trust, usage, and quality drift

## 12. Testing Requirements

Minimum automated coverage should include:

### Unit tests

- fallback response generation when OpenAI is unavailable
- heuristic score bounds in `generate_ai_feedback(...)`
- risk flag generation in `build_ai_insight(...)`
- similarity score normalization bounds
- runtime override normalization in `ai_runtime.py`

### API tests

- teacher can run AI only on owned/accessible assignments
- admin can update runtime config and view provider mode
- bulk submission AI returns durable job metadata
- async similarity returns durable job metadata
- evaluation trace endpoint returns prompt/runtime metadata

### Integration tests

- submission upload -> AI evaluation -> evaluation preview reuse path
- teacher evaluation chat history persistence across multiple messages
- bulk AI job queue -> submission update completion path
- similarity job retry does not create duplicate flag records

### Performance tests to add

- bulk AI queue throughput under multiple pending jobs
- similarity queue latency with increasing submission volume
- fallback behavior under provider outage

## 13. Final Summary

The AI module in CAPS AI is now a materially stronger subsystem than the earlier audit described. It provides:

- submission scoring assistance
- evaluation insight generation with trace persistence
- teacher AI chat with prompt/runtime metadata
- similarity detection with idempotent logging
- durable AI job orchestration
- admin runtime controls and operational visibility

Its strongest quality is still resilience through deterministic fallback, but it now also has the beginnings of real operational governance.

The correct direction remains:

- keep AI embedded in academic workflows
- preserve the fallback-first design
- use durable jobs for heavier workloads
- deepen observability and governance on top of the new runtime and job foundations
