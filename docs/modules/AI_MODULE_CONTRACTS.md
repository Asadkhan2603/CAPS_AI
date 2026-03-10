# AI Module Contracts

## Purpose

This document defines the stable AI payload shapes currently used by CAPS AI across submissions, evaluations, chat, similarity, runtime config, and durable AI jobs.

Primary implementation files:

- [ai.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\ai.py)
- [submissions.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\submissions.py)
- [evaluations.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\evaluations.py)
- [similarity.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\similarity.py)
- [ai_runtime.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_runtime.py)
- [ai_jobs.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_jobs.py)

## Submission AI Result

Used in:

- `GET /submissions/`
- `GET /submissions/{submission_id}`
- `POST /submissions/{submission_id}/ai-evaluate`

Relevant AI fields:

- `ai_status`
- `ai_score`
- `ai_feedback`
- `ai_provider`
- `ai_prompt_version`
- `ai_runtime_snapshot`
- `ai_error`
- `similarity_score`

`ai_runtime_snapshot` shape:

- `provider_enabled`
- `effective_provider_enabled`
- `openai_model`
- `openai_timeout_seconds`
- `openai_max_output_tokens`
- `similarity_threshold`

## Evaluation AI Preview

Used in:

- `POST /evaluations/ai-preview`

Fields:

- `submission_id`
- `internal_total`
- `grand_total`
- `grade`
- `ai_score`
- `ai_feedback`
- `ai_insight`

`ai_insight` shape:

- `summary`
- `strengths`
- `gaps`
- `suggestions`
- `risk_flags`
- `confidence`
- `status`
- `provider`
- `prompt_version`
- `runtime_snapshot`

## Evaluation Record AI Fields

Used in:

- `GET /evaluations/`
- `GET /evaluations/{evaluation_id}`
- `POST /evaluations/`
- `PUT /evaluations/{evaluation_id}`
- `POST /evaluations/{evaluation_id}/ai-refresh`

Relevant AI fields:

- `ai_score`
- `ai_feedback`
- `ai_status`
- `ai_provider`
- `ai_prompt_version`
- `ai_runtime_snapshot`
- `ai_confidence`
- `ai_risk_flags`
- `ai_strengths`
- `ai_gaps`
- `ai_suggestions`

## Evaluation Trace Item

Used in:

- `GET /evaluations/{evaluation_id}/trace`

Fields:

- `id`
- `ai_score`
- `ai_status`
- `ai_provider`
- `ai_prompt_version`
- `ai_runtime_snapshot`
- `ai_confidence`
- `ai_risk_flags`
- `grade`
- `internal_total`
- `grand_total`
- `created_at`

## Teacher AI Chat Thread

Used in:

- `POST /ai/evaluate`
- `GET /ai/history/{student_id}/{exam_id}`

Thread fields:

- `id`
- `teacher_id`
- `student_id`
- `exam_id`
- `question_id`
- `messages`
- `created_at`
- `updated_at`

Message fields:

- `role`
- `content`
- `timestamp`
- `question_id`
- `provider_error`
- `provider`
- `prompt_version`
- `runtime_snapshot`

Notes:

- teacher messages typically use only `role`, `content`, `timestamp`, and `question_id`
- AI messages additionally persist provider/runtime metadata

## Similarity Log

Used in:

- `GET /similarity/checks`
- `POST /similarity/checks/run/{submission_id}`

Fields:

- `id`
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

## Runtime Config Contract

Used in:

- `GET /ai/admin/runtime-config`
- `PUT /ai/admin/runtime-config`

Response fields:

- `effective`
- `provider`

`effective` fields:

- `provider_enabled`
- `openai_model`
- `openai_timeout_seconds`
- `openai_max_output_tokens`
- `similarity_threshold`
- `openai_configured`
- `effective_provider_enabled`

`provider` fields:

- `openai_configured`
- `provider_enabled`
- `mode`
- `model`
- `timeout_seconds`
- `max_output_tokens`
- `similarity_threshold`

## Durable AI Job Contract

Used in:

- `POST /submissions/ai-evaluate/pending`
- `POST /similarity/checks/run-async/{submission_id}`
- `GET /ai/jobs`
- `GET /ai/jobs/{job_id}`
- `GET /ai/ops/overview`

Job fields:

- `id`
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

Supported `job_type` values:

- `bulk_submission_ai`
- `similarity_check`

Supported `status` values:

- `queued`
- `running`
- `completed`
- `failed`

`progress` fields:

- `total`
- `completed`
- `failed`
- `skipped`
- `fallback`

## AI Operations Overview

Used in:

- `GET /ai/ops/overview`

Top-level fields:

- `scope`
- `provider`
- `runtime_config`
- `summary`
- `recent_evaluation_runs`
- `recent_similarity_flags`
- `recent_chat_threads`
- `recent_jobs`

`summary` currently includes:

- `submissions_total`
- `submissions_pending`
- `submissions_running`
- `submissions_completed`
- `submissions_fallback`
- `submissions_failed`
- `evaluations_total`
- `evaluations_with_ai`
- `trace_runs_total`
- `similarity_flags_total`
- `chat_threads_total`
- `jobs_total`
- `jobs_queued`
- `jobs_running`
- `jobs_failed`
- `jobs_completed`

## Contract Guidance

- treat `ai_prompt_version`, `runtime_snapshot`, and `engine_version` as audit metadata, not user-editable fields
- treat `fallback` as a valid AI outcome, not a transport error
- prefer these stable contracts over inferring fields ad hoc from UI-specific usage
