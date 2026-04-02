# AI And Similarity

## Purpose

This module covers AI runtime configuration, AI ops visibility, evaluation chat support, and submission similarity checking.

## Data Model

Entities:

- AI runtime config
- AI jobs
- AI chat history
- similarity logs
- AI evaluation runs

Key runtime concerns:

- provider and model selection
- async job tracking
- trace visibility
- source and matched class compatibility fields in similarity logs

## APIs

Primary endpoints:

- `/ai/admin/runtime-config`
- `/ai/ops/overview`
- `/ai/jobs`
- `/ai/jobs/{job_id}`
- `/ai/evaluate`
- `/ai/history/{student_id}/{exam_id}`
- `/similarity/checks`
- `/similarity/checks/run/{submission_id}`
- `/similarity/checks/run-async/{submission_id}`

## Workflow

1. admin reviews runtime configuration
2. evaluation chat or AI operations invoke model-backed workflows
3. jobs and traces are persisted
4. similarity checks run against submission context
5. downstream analytics and review modules consume the results

## Dependencies

- `backend/app/api/v1/endpoints/ai.py`
- `backend/app/api/v1/endpoints/ai_admin.py`
- `backend/app/api/v1/endpoints/ai_ops.py`
- `backend/app/api/v1/endpoints/ai_chat.py`
- `backend/app/api/v1/endpoints/similarity.py`
- `backend/app/services/ai_runtime.py`
- `backend/app/services/ai_ops_workflow.py`
- `backend/app/services/similarity_pipeline.py`
