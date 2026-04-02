# Assignments And Submissions

## Purpose

This module manages assignment publication, submission uploads, and the bridge into AI-assisted evaluation flows.

## Data Model

Entities:

- assignments
- submissions

Important fields:

- assignment `class_id`
- assignment `subject_id`
- submission `assignment_id`
- AI evaluation status metadata on submissions

## APIs

Primary endpoints:

- `/assignments`
- `/assignments/{assignment_id}/plagiarism`
- `/submissions`
- `/submissions/upload`
- `/submissions/{submission_id}/ai-evaluate`
- `/submissions/ai-evaluate/pending`

## Workflow

1. teacher creates an assignment for a section and subject
2. student uploads a submission
3. submission metadata and artifacts are persisted
4. AI evaluation may be triggered synchronously or from pending runs
5. later evaluation and similarity modules consume the resulting records

## Dependencies

- `backend/app/api/v1/endpoints/assignments.py`
- `backend/app/api/v1/endpoints/submissions.py`
- `backend/app/services/submission_ai.py`
- `backend/app/services/file_parser.py`
- `backend/app/services/cloudinary_uploads.py`
- course delivery and evaluations modules
