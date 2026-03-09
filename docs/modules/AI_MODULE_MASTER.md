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
- [ai_chat_service.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_chat_service.py)
- [ai_evaluation.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_evaluation.py)
- [evaluation_ai_module.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\evaluation_ai_module.py)
- [similarity_engine.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\similarity_engine.py)

Primary frontend consumers:

- [SubmissionsPage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\SubmissionsPage.jsx)
- [EvaluateSubmission.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Teacher\EvaluateSubmission.jsx)
- [aiService.js](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\services\aiService.js)

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
- `created_at`

Purpose:

- persist pairwise similarity checks and flagging decisions

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

This fallback design is important because it keeps academic flows working even without external AI availability.

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

## 5.1 Dedicated AI chat endpoints

File:

- [ai.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\ai.py)

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
- evaluates rows one by one
- audits each result

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

- queue asynchronous similarity analysis in background tasks

Behavior:

- requires plagiarism to be enabled for the assignment
- updates submission `similarity_score`
- persists similarity logs
- notifies relevant actors when a flag crosses threshold

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

This is a narrow wrapper layer, not a broader typed AI SDK.

## 6.4 Analytics and dashboard consumption

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

## 9. Frontend vs Backend Gaps

### Gap 1: No dedicated AI module page

The AI module is powerful, but it has no first-class standalone UI. It is distributed across submissions and evaluation screens.

### Gap 2: AI traces are backend-visible but not fully surfaced

The evaluation trace endpoint exists, but current frontend exposure is limited.

### Gap 3: No administrative AI configuration UI

There is no frontend control for:

- OpenAI provider state
- model name
- timeout
- output token limits
- similarity threshold

### Gap 4: No job orchestration UI for async similarity

The async endpoint exists, but there is no dedicated operator workflow or progress UI for queued similarity jobs.

## 10. Risks and Architectural Issues

### Risk 1: Blocking CPU and network work still occurs in request paths

The current AI implementation still does synchronous heavy work in request-time flows, including:

- OpenAI calls
- file parsing prior to AI scoring
- similarity vectorization and cosine similarity

Some operations are moved into `run_in_threadpool`, but that does not make them a durable queue-based background system.

### Risk 2: AI state is spread across multiple domain records

This is practical, but it makes centralized governance and retention harder.

### Risk 3: Similarity engine is memory-bound

The current similarity implementation builds TF-IDF vectors in process. This can become expensive for larger candidate sets.

### Risk 4: AI quality is partly heuristic and partly provider-based

That is acceptable, but it means consistency varies by configuration and failure mode.

### Risk 5: No full model governance layer

There is no current UI or policy layer for:

- model selection governance
- prompt versioning
- provider cost visibility
- AI output review policy

## 11. Recommended Cleanup Strategy

### Short-term

- document the AI response contracts centrally
- expose evaluation AI trace more clearly in UI
- surface configuration state such as provider and fallback mode in admin diagnostics

### Medium-term

- move heavy AI and similarity processing to a durable worker queue
- add idempotency and job-state tracking for bulk AI runs
- centralize AI run metadata for easier auditing

### Long-term

Adopt a more deliberate AI platform layer:

- queue-backed asynchronous evaluation and similarity jobs
- stronger model governance
- prompt/version tracking
- clearer AI observability and cost monitoring
- explicit teacher override and review analytics

## 12. Testing Requirements

Minimum automated coverage should include:

### Unit tests

- fallback response generation when OpenAI is unavailable
- heuristic score bounds in `generate_ai_feedback(...)`
- risk flag generation in `build_ai_insight(...)`
- similarity score normalization bounds

### API tests

- teacher can run AI only on owned/accessible assignments
- admin can audit AI chat and evaluation preview flows
- plagiarism-disabled assignments reject similarity runs
- evaluation trace endpoint returns persisted AI runs
- AI rerun behavior respects `force`

### Integration tests

- submission upload -> AI evaluation -> evaluation preview reuse path
- teacher evaluation chat history persistence across multiple messages
- similarity flag -> notification creation path

### Performance tests to add

- bulk pending AI evaluation throughput
- similarity run latency with increasing submission volume
- fallback behavior under provider outage

## 13. Final Summary

The AI module in CAPS AI is already a meaningful subsystem. It is not a toy chatbot integration. It provides:

- submission scoring assistance
- evaluation insight generation
- teacher AI chat
- plagiarism and similarity detection
- alert fanout for risky cases

Its strongest quality is resilience through deterministic fallback.

Its main architectural weakness is that expensive AI and similarity work still runs too close to request-time workflows and is spread across multiple domain records without a stronger centralized AI operations layer.

The correct direction is:

- keep AI embedded in academic workflows
- preserve the fallback-first design
- move expensive jobs to durable asynchronous execution
- improve observability, governance, and frontend visibility of AI traces and system state