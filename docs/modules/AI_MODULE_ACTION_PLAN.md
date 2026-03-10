# AI Module Action Plan

## Purpose

This document converts the current [AI_MODULE_MASTER.md](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\AI_MODULE_MASTER.md) analysis into an execution plan with priorities, delivery scope, and acceptance criteria.

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
- canonical contracts are now documented in [AI_MODULE_CONTRACTS.md](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\AI_MODULE_CONTRACTS.md)

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

- implemented on 2026-03-10 in [EvaluateSubmission.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Teacher\EvaluateSubmission.jsx)

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

- implemented on 2026-03-10 in [AI_MODULE_CONTRACTS.md](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\AI_MODULE_CONTRACTS.md)

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

- implemented on 2026-03-10 through [ai_jobs.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_jobs.py), [submissions.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\submissions.py), and [similarity.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\similarity.py)

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

- implemented on 2026-03-10 in [ai.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\ai.py) and [AIModulePage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\AIModulePage.jsx)

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

- partially implemented on 2026-03-10 through prompt/runtime metadata in [ai_runtime.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_runtime.py), [evaluation_ai_module.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\evaluation_ai_module.py), and the persisted submission/evaluation/chat contracts

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
