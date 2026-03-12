# AI Module Audit
Date: 2026-03-11

## Scope
Backend API, AI services, data models, scheduler/job pipeline, and frontend AI surfaces (operations, evaluation console, submissions, evaluations). This audit focuses on runtime behavior and role-based access for admin, teacher, and student.

## Architecture Summary
The AI module is a set of backend services exposed through API endpoints and surfaced in three primary UI areas:
- AI Operations (admin/teacher) for runtime status, job queue, and recent AI activity.
- AI Assisted Evaluation Console (teacher/admin) for chat-based grading support and evaluation AI trace.
- Submissions and Evaluations (student/admin/teacher) to show AI status and feedback.

AI functionality is composed of three pipelines:
1. Submission evaluation AI (single and bulk).
2. Evaluation AI insights and trace history.
3. Similarity detection (plagiarism-style checks) with optional async jobs.

## Module Map
### Backend APIs
- /ai
  - GET /ai/admin/runtime-config (admin only)
  - PUT /ai/admin/runtime-config (admin only)
  - GET /ai/ops/overview (teacher/admin; scoped for teachers)
  - GET /ai/jobs (teacher/admin; teachers see only their jobs)
  - GET /ai/jobs/{job_id} (teacher/admin)
  - POST /ai/evaluate (teacher/admin) - AI chat evaluation
  - GET /ai/history/{student_id}/{exam_id} (teacher/admin) - AI chat history
- /submissions
  - POST /submissions/{submission_id}/ai-evaluate (teacher/admin)
  - POST /submissions/ai-evaluate/pending (teacher/admin; bulk queue)
- /evaluations
  - POST /evaluations/ai-preview (teacher/admin)
  - POST /evaluations/{evaluation_id}/ai-refresh (teacher/admin)
  - GET /evaluations/{evaluation_id}/trace (teacher/admin)
- /similarity
  - GET /similarity/checks (teacher/admin; scoped)
  - POST /similarity/checks/run/{submission_id} (teacher/admin; sync)
  - POST /similarity/checks/run-async/{submission_id} (teacher/admin; async job)

### Core Services
- ai_runtime: runtime configuration (OpenAI model, timeouts, thresholds) persisted to db.settings.
- ai_evaluation: OpenAI evaluation + deterministic fallback.
- ai_chat_service: OpenAI chat-based grading + fallback.
- submission_ai: runs AI evaluation and persists results on submissions.
- evaluation_ai_module: builds AI insight, risk flags, and summary for evaluations.
- ai_jobs: durable job queue for bulk submission evaluation and similarity jobs.
- similarity_pipeline: computes similarity scores and creates similarity logs.
- scheduler: optional background job runner for AI jobs.

### Data Stores
- submissions: ai_status, ai_score, ai_feedback, ai_provider, ai_error, ai_prompt_version, ai_runtime_snapshot.
- evaluations: ai_* fields persisted on create/update; students can view their own evaluations.
- ai_evaluation_runs: trace history of evaluation AI runs.
- ai_evaluation_chats: teacher-admin chat threads for a student+assignment.
- ai_jobs: durable job queue for bulk submission AI and similarity checks.
- similarity_logs: similarity scores, flags, and access scope extensions.
- settings: key "ai_runtime_config" stores runtime overrides.

### Frontend Surfaces
- /ai-operations: AI Operations dashboard (admin/teacher)
- /submissions/:id/evaluate: AI Assisted Evaluation Console (admin/teacher)
- /submissions: AI status per submission; bulk AI actions (admin/teacher)
- /evaluations: AI status and feedback per evaluation (student/admin/teacher)

## Runtime Configuration
- provider_enabled: toggle for OpenAI usage when configured.
- openai_model, openai_timeout_seconds, openai_max_output_tokens.
- similarity_threshold (0 to 1).
- openai_configured is derived from OPENAI_API_KEY.
- effective_provider_enabled = provider_enabled and openai_configured.

Runtime overrides are stored under db.settings key "ai_runtime_config". Admins can modify via /ai/admin/runtime-config and the AI Operations page.

## AI Workflows
1. Submission AI evaluation
   - Single: POST /submissions/{id}/ai-evaluate
   - Bulk: POST /submissions/ai-evaluate/pending -> ai_jobs queue
   - Persisted fields: ai_status, ai_score, ai_feedback, ai_provider, ai_prompt_version, ai_runtime_snapshot.
2. Evaluation AI
   - Preview: POST /evaluations/ai-preview (non-persistent)
   - Persisted: POST /evaluations/ (on creation) and PUT /evaluations/{id} (on update)
   - Trace: GET /evaluations/{id}/trace
3. AI chat evaluation
   - POST /ai/evaluate to generate AI grading suggestions
   - Stored in ai_evaluation_chats with thread history
4. Similarity detection
   - Sync: POST /similarity/checks/run/{submission_id}
   - Async: POST /similarity/checks/run-async/{submission_id} -> ai_jobs queue
   - Notifications for flagged matches

## Access Control Review
- AI operations and AI chat endpoints require teacher/admin.
- Runtime configuration is admin only.
- Teachers are scoped by assignment ownership or class coordination.
- Similarity logs are additionally visible to year_head and class_coordinator extensions.
- Students can view their own submissions and evaluations (AI status and feedback), but cannot invoke AI operations or chat endpoints.

## Observations and Gaps
1. Scheduler dependency
   - Async AI jobs run only when scheduler is enabled or when jobs are processed in-request.
   - Risk: queued jobs can stall if scheduler is disabled in production.
2. Status taxonomy
   - AI evaluation uses "completed" or "fallback". "failed" is rarely set.
   - UI shows "failed" state; backend mostly returns "fallback" on errors.
3. AI chat index creation
   - ai_evaluation_chats indexes are created lazily on first AI chat call.
   - Consider moving to core index initialization to avoid first-call overhead.
4. Scope mismatch
   - Similarity log visibility allows year_head/class_coordinator, but AI Operations overview is strictly assignment ownership/coordinator.
   - If year_head should view AI operations across cohorts, expand scope logic.
5. Student visibility
   - Students can view AI feedback in evaluations. Confirm if this is desired or should be redacted.

## Recommended Fixes
1. Ensure ai_jobs processing in production
   - Enable scheduler or run a dedicated worker that calls process_ai_jobs_once on interval.
2. Normalize AI status values
   - Choose a consistent set: pending, running, completed, fallback, failed.
   - Decide whether fallback is a failure (failed) or a separate state.
3. Move AI chat indexes into core index bootstrap
   - Add ai_evaluation_chats indexes to ensure_indexes().
4. Align year_head visibility
   - If year_head is expected to view AI operations, extend AI scope queries to include their classes/assignments.
5. Student-facing AI policy
   - If AI feedback should be hidden or summarized, filter fields in evaluations API for student role.

## Audit Task Status Update (2026-03-11)

Completed from repository audit roadmap:
- Phase 0 security tasks completed (`56fbe7d`):
  - dependency hardening
  - SHA256 migration for submission AI idempotency
  - CI gates for SCA and coverage
- Phase 1 performance tasks completed (`9f39c65`, `d3eac0a`, `13722be`, `455069a`, `76438a9`):
  - fanout batching
  - high-volume query scan reductions on teacher/admin scope paths

Open:
- observability metrics and alerting for AI endpoints/jobs remain open from Phase 1

## Phase 2 Refactor Planning Snapshot

Primary execution scope:
1. Extract shared AI access-control helper(s) and replace duplicate endpoint logic.
2. Split monolithic AI and evaluation endpoint files into smaller concern-based modules.
3. Move AI orchestration logic to service-layer boundaries and keep endpoints thin.

Target modules:
- `backend/app/api/v1/endpoints/ai.py`
- `backend/app/api/v1/endpoints/evaluations.py`
- `backend/app/api/v1/endpoints/submissions.py`
- `backend/app/api/v1/endpoints/similarity.py`

Non-functional guardrails:
- no API path changes
- no RBAC regression
- CI must stay green (tests, lint/static checks, safety checks)

## Phase 2 Completion Update (2026-03-11)

Completed in backend:
1. Shared access/policy services extracted and applied across AI, evaluations, submissions, and similarity endpoints.
2. `ai.py` split into `ai_admin`, `ai_ops`, `ai_chat`, and shared `ai_common` composition pattern.
3. `evaluations.py` split into read/ai/lifecycle modules with a composition wrapper and compatibility-safe DB indirection for tests.
4. Service-layer workflows introduced for:
   - AI runtime config response shaping
   - AI operations overview and job payload shaping
   - AI chat result normalization and thread upsert
   - evaluation totals/AI payload/trace orchestration

Validation status:
- backend flake8 checks passed on touched files
- backend safety script passed
- backend tests passed (`85 passed`)

Remaining:
- explicit observability dashboards and alerting for AI endpoints/jobs

## Teacher and Student Fix Suggestions
Teacher:
- Expand AI Operations scope for year_head/class_coordinator if those roles need broader visibility.
- Explicit fallback indicators are now present in teacher AI review screens.

Student:
- AI-generated disclosure text is now present in submissions/evaluations UI.
- Student-facing UI keeps detailed ai_feedback and ai_score hidden while preserving teacher-reviewed marks visibility.

## Files Reviewed
Backend:
- backend/app/api/v1/router.py
- backend/app/api/v1/endpoints/ai.py
- backend/app/api/v1/endpoints/similarity.py
- backend/app/api/v1/endpoints/submissions.py
- backend/app/api/v1/endpoints/evaluations.py
- backend/app/services/ai_runtime.py
- backend/app/services/ai_evaluation.py
- backend/app/services/ai_chat_service.py
- backend/app/services/ai_jobs.py
- backend/app/services/submission_ai.py
- backend/app/services/evaluation_ai_module.py
- backend/app/services/similarity_pipeline.py
- backend/app/services/scheduler.py
- backend/app/models/submissions.py
- backend/app/models/evaluations.py
- backend/app/models/ai_chat.py
- backend/app/schemas/ai_chat.py
- backend/app/schemas/evaluation.py
- backend/app/schemas/similarity_log.py
- backend/app/core/config.py
- backend/app/core/indexes.py

Frontend:
- frontend/src/config/featureAccess.js
- frontend/src/config/navigationGroups.js
- frontend/src/routes/AppRoutes.jsx
- frontend/src/services/aiService.js
- frontend/src/pages/AIModulePage.jsx
- frontend/src/pages/SubmissionsPage.jsx
- frontend/src/pages/Teacher/EvaluateSubmission.jsx
- frontend/src/components/Teacher/AIChatPanel.jsx
