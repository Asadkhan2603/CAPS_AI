# AI Module Action Plan

## Purpose

This document converts the current [AI_MODULE_MASTER.md](/docs/modules/AI_MODULE_MASTER.md) analysis into an execution plan with priorities, delivery scope, and acceptance criteria.

## Current State Summary

The AI module is already embedded in real academic workflows:

- submission AI scoring
- evaluation AI insight and trace persistence
- teacher AI chat
- similarity detection and alerting
- dedicated AI operations visibility for teacher/admin users

The system's strongest property is fallback-first resilience. Its main weaknesses are fragmented AI operations visibility, request-path heavy processing, and limited operator controls.

Implemented so far:

- teacher evaluation console now shows persisted AI state, stored-AI refresh, and trace history
- dedicated AI operations page now exposes scoped AI throughput and recent activity
- runtime AI configuration now persists through `settings` and is visible/editable from the AI operations page for admins
- bulk submission AI and async similarity now run through durable persisted `ai_jobs`
- prompt/runtime metadata is now stored on submissions, evaluations, traces, chat messages, and similarity logs
- canonical contracts are now documented in [AI_MODULE_CONTRACTS.md](/docs/modules/AI_MODULE_CONTRACTS.md)

## Audit Roadmap Alignment (2026-03-11)

This action plan is now aligned with the repository-level audit roadmap in [audit/roadmap.md](/audit/roadmap.md).

Completed audit tasks reflected in codebase:
- `Phase 0` security hardening completed in commit `56fbe7d`.
  - dependency upgrades and lockfile refreshes
  - SHA256 idempotency for submission AI bulk evaluation
  - CI quality gates for `pip_audit`, `npm audit`, and coverage thresholds
- `Phase 1` performance fixes completed in commits `9f39c65`, `d3eac0a`, `13722be`, `455069a`, `76438a9`.
  - batched notice fanout and reduced high-limit query scans
  - teacher-scope query reductions across notices, submissions, enrollments, and class slots

Open from prior phases:
- endpoint/scheduler observability metrics and alerting remain open from Phase 1

## Phase 2 Refactor Plan (Completed)

Goal:
- reduce AI endpoint complexity and remove duplicated access-control logic without changing external API contracts

Workstream A: Access-control extraction
- add centralized access helper/service for teacher assignment and class scope checks
- replace duplicated `_teacher_can_access_assignment` implementations in:
  - [ai.py](/backend/app/api/v1/endpoints/ai.py)
  - [evaluations.py](/backend/app/api/v1/endpoints/evaluations.py)
  - [similarity.py](/backend/app/api/v1/endpoints/similarity.py)
  - [submissions.py](/backend/app/api/v1/endpoints/submissions.py)

Workstream B: AI endpoint decomposition
- split [ai.py](/backend/app/api/v1/endpoints/ai.py) into smaller route modules by concern:
  - runtime config/admin operations
  - AI ops/jobs endpoints
  - chat/evaluation endpoints
- keep route prefixes and RBAC behavior backward-compatible

Workstream C: Evaluation and AI service boundary
- move non-HTTP evaluation AI orchestration from endpoints into services
- keep endpoint handlers focused on request validation, authorization, and response mapping

Teacher and student focused fixes included in Phase 2:
- teacher: align AI Operations scope policy with intended year-head/class-coordinator visibility
- teacher: expose explicit fallback-mode indicator consistently in teacher AI screens
- student: enforce explicit policy for AI score/feedback visibility (full, summarized, or hidden)
- student: standard disclaimer text for AI-generated feedback in student-facing evaluation views

Phase 2 Definition of Done:
1. duplicated AI access helpers removed from endpoints
2. `ai.py` and `evaluations.py` reduced via internal module split
3. no route or RBAC regressions in backend tests
4. docs and contracts updated to match refactored internals

Status:

- backend implementation completed on 2026-03-11 in `7d3c52c`
- frontend policy UX completed on 2026-03-12
  - teacher fallback-mode indicators added to evaluation/submission review screens
  - student disclosure text added to submissions/evaluations surfaces
  - student-facing UI keeps detailed AI score/feedback hidden and only exposes process-level AI status
- validation baseline: backend flake8, backend safety checks, backend tests, and frontend build passing after refactor

## Gap Analysis

## Gap 1: Evaluation AI trace exists but is weakly exposed

Current state:

- backend trace persistence exists in `ai_evaluation_runs`
- `GET /evaluations/{evaluation_id}/trace` already exists
- teacher workflow UI did not clearly surface historical trace runs

Impact:

- low visibility into why AI changed over time
- weaker teacher trust and weaker auditability during re-evaluation

Priority:

- `P1`

Recommended action:

- surface persisted evaluation AI state and trace history directly inside the teacher evaluation console
- expose a refresh action that uses the existing `ai-refresh` endpoint and then reloads trace history

Acceptance criteria:

- teacher/admin can see stored AI status, provider, confidence, and risk flags for an evaluation
- teacher/admin can view recent trace runs without leaving the evaluation screen
- AI refresh updates the stored evaluation and trace list in the same workflow

Status:

- implemented on 2026-03-10 in [EvaluateSubmission.jsx](/frontend/src/pages/Teacher/EvaluateSubmission.jsx)

## Gap 2: AI response contracts are not centralized enough

Current state:

- AI payload fields are reused across submissions, evaluations, trace runs, and chat
- contract shape is understandable in code, but not documented in one canonical reference

Impact:

- frontend and backend drift risk
- harder onboarding for future AI feature work

Priority:

- `P1`

Recommended action:

- create a small AI contracts document covering:
  - submission AI result
  - evaluation AI preview
  - evaluation AI trace item
  - teacher AI chat message/thread
- align frontend rendering to those contracts explicitly

Acceptance criteria:

- one document defines the stable field sets
- frontend consumers do not infer fields ad hoc from unrelated endpoints

Status:

- implemented on 2026-03-10 in [AI_MODULE_CONTRACTS.md](/docs/modules/AI_MODULE_CONTRACTS.md)

## Gap 3: Heavy processing still runs close to request time

Current state:

- OpenAI calls, extraction reuse, and similarity vectorization still occur in user-triggered request flows
- some work is moved into `run_in_threadpool`, but that is not durable job orchestration

Impact:

- higher latency variance
- weaker retry/idempotency behavior
- harder scaling under bulk evaluation or large similarity candidate sets

Priority:

- `P1`

Recommended action:

- move bulk AI evaluation and similarity runs into durable background jobs
- add persisted job state and idempotency keys for teacher/admin initiated operations

Acceptance criteria:

- long-running AI and similarity workloads no longer depend on the request lifecycle
- bulk runs expose `queued`, `running`, `completed`, and `failed` state
- retries do not create duplicate trace or alert records

Status:

- implemented on 2026-03-10 through [ai_jobs.py](/backend/app/services/ai_jobs.py), [submissions.py](/backend/app/api/v1/endpoints/submissions.py), and [similarity.py](/backend/app/api/v1/endpoints/similarity.py)

## Gap 4: No administrative AI configuration surface

Current state:

- provider configuration and operational settings are backend/config driven
- there is no admin UI for runtime visibility of provider mode or thresholds

Impact:

- operators cannot easily verify fallback mode, provider health, or similarity thresholds

Priority:

- `P2`

Recommended action:

- add an admin diagnostics/config page showing:
  - provider enabled/disabled state
  - effective provider name
  - fallback mode status
  - key similarity thresholds and timeout settings

Acceptance criteria:

- admins can see effective AI runtime mode without reading environment/config directly
- misconfiguration is visible before teachers report workflow issues

Status:

- implemented on 2026-03-10 in [ai.py](/backend/app/api/v1/endpoints/ai.py) and [AIModulePage.jsx](/frontend/src/pages/AIModulePage.jsx)

## Gap 5: AI governance is mostly implicit

Current state:

- prompts, provider choices, and AI review policy are embedded in service code and behavior
- no explicit prompt versioning or model governance layer exists

Impact:

- harder to compare behavior over time
- weak operational traceability when prompts or providers change

Priority:

- `P2`

Recommended action:

- add prompt/version identifiers to AI trace records
- capture model/config metadata in evaluation traces and submission AI runs
- document teacher override expectations and review policy

Acceptance criteria:

- trace records can answer which prompt/config produced a result
- governance changes are measurable over time

Status:

- partially implemented on 2026-03-10 through prompt/runtime metadata in [ai_runtime.py](/backend/app/services/ai_runtime.py), [evaluation_ai_module.py](/backend/app/services/evaluation_ai_module.py), and the persisted submission/evaluation/chat contracts

## Delivery Roadmap

## Sprint 1

- close the teacher trace visibility gap
- document AI response contracts
- define job model for async AI and similarity work

Status:

- completed

## Sprint 2

- implement durable async execution for bulk evaluation and similarity runs
- add admin diagnostics for provider/runtime visibility

Status:

- completed

## Sprint 3

- add prompt/config version metadata
- add AI observability dashboards and operational metrics

Status:

- prompt/config version metadata completed
- broader observability dashboards and cost-oriented operational metrics remain open

## Sprint 4 (Phase 2 Structural Refactor)

- extract shared access control helpers used by AI-related endpoints
- split AI and evaluation endpoint modules into smaller routers
- push evaluation AI orchestration into service-layer units with thin endpoint handlers
- finalize teacher/student AI visibility policy implementation

Status:

- implementation completed for backend service and endpoint restructuring
- remaining follow-up is policy UX and observability depth, not structural backend gaps

## Implementation Notes

The first implemented improvement should stay inside the current architecture:

- do not split the AI domain into a new subsystem prematurely
- keep fallback-first behavior intact
- improve visibility and safety before introducing more platform complexity

This keeps the next step practical: better operator and teacher visibility now, queue-backed execution next.

## Remaining Work

The original priority gaps are now closed enough for active use. The remaining AI module work is operational depth rather than missing foundation:

- add richer trace/job filtering across time, provider, and actor
- add module-level metrics or dashboards for provider fallback rate, queue latency, and failure rate
- add policy/governance reporting around teacher override behavior and AI usage trends
- finalize teacher/student policy UX decisions in frontend surfaces (fallback indicators, disclosure text, visibility rules)



