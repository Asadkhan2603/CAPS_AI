# Classes To Sections Migration Plan

## Purpose

This plan documents how the repo should continue moving from legacy `class` terminology to canonical `section` terminology without breaking active logic.

## Data Model

Current mixed state:

- public API path: `/sections`
- storage collection: `classes`
- downstream references: often `class_id`

Affected records:

- sections
- students
- enrollments
- assignments
- timetables
- similarity logs
- user role scope

## APIs

Affected endpoints:

- `/sections`
- `/students`
- `/enrollments`
- `/assignments`
- `/timetables`
- `/analytics/teacher/sections`

## Workflow

### Current safe state

- keep `/sections` as the canonical route
- keep compatibility aliases in schemas and serializers
- keep `class_id` where downstream code still consumes it

### Target migration state

1. standardize docs on `section`
2. standardize frontend labels on `section`
3. convert internal helpers from `class_*` names where safe
4. introduce `section_id` in downstream persisted records if and when storage migration is planned
5. retire compatibility aliases only after tests and data migration are complete

## Dependencies

- `backend/app/api/v1/endpoints/sections.py`
- `backend/app/api/v1/endpoints/students.py`
- `backend/app/api/v1/endpoints/enrollments.py`
- `backend/app/api/v1/endpoints/timetables.py`
- `backend/app/services/section_mapping.py`
- `backend/tests/test_auth.py`
- `backend/tests/test_timetables.py`
