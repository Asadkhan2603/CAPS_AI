# Evaluations And Grading

## Purpose

This module owns evaluation records, AI previews, lifecycle transitions, trace visibility, and grading finalization behavior.

## Data Model

Entities:

- evaluations
- AI evaluation runs
- evaluation traces

Important states:

- draft evaluation creation
- AI preview and AI refresh
- finalized and override-unfinalize transitions

## APIs

Primary endpoints:

- `/evaluations`
- `/evaluations/{evaluation_id}`
- `/evaluations/{evaluation_id}/trace`
- `/evaluations/ai-preview`
- `/evaluations/{evaluation_id}/ai-refresh`
- `/evaluations/{evaluation_id}`
- `/evaluations/{evaluation_id}/finalize`
- `/evaluations/{evaluation_id}/override-unfinalize`

## Workflow

1. create evaluation from assignment or submission context
2. request AI preview if needed
3. persist or refresh evaluation output
4. finalize the evaluation when grading is complete
5. review trace data for auditability

## Dependencies

- `backend/app/api/v1/endpoints/evaluations.py`
- `backend/app/api/v1/endpoints/evaluations_ai.py`
- `backend/app/api/v1/endpoints/evaluations_lifecycle.py`
- `backend/app/api/v1/endpoints/evaluations_read.py`
- `backend/app/services/evaluation_workflow.py`
- `backend/app/services/ai_evaluation.py`
