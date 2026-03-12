# Backend Model Serializers

This directory contains serializer helpers that convert MongoDB documents into API-facing payloads.

## Current Coverage

Platform and governance:
- `users.py`
- `audit_logs.py`
- `review_tickets.py`
- `notifications.py`

Academic setup and academics:
- `faculties.py`
- `departments.py`
- `programs.py`
- `specializations.py`
- `batches.py`
- `semesters.py`
- `classes.py`
- `students.py`
- `groups.py`
- `subjects.py`
- `course_offerings.py`
- `class_slots.py`
- `attendance_records.py`
- `enrollments.py`

Assessment and AI:
- `assignments.py`
- `submissions.py`
- `evaluations.py`
- `ai_chat.py`
- `similarity_logs.py`

Campus operations:
- `clubs.py`
- `club_events.py`
- `event_registrations.py`
- `notices.py`

## Compatibility Notes

- `classes.py` backs the canonical `/sections` API. The file and collection name are legacy compatibility artifacts.
- Legacy `branch_name` may still appear in serialized section documents for historical-row compatibility.
- AI-related serializers expose persisted runtime metadata such as `ai_status`, `ai_provider`, `ai_prompt_version`, and `ai_runtime_snapshot`.

## Scope Boundary

These files are not ODM models or schema definitions.
- Request and response validation lives under `backend/app/schemas/`
- Endpoint orchestration lives under `backend/app/api/v1/endpoints/`
- Domain logic lives under `backend/app/services/`
