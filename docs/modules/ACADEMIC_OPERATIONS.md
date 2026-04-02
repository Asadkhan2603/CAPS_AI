# Academic Operations

## Purpose

This module owns the operational academic tree used after the master hierarchy is established.

## Data Model

Entities:

- batches
- semesters
- sections
- groups
- students
- enrollments

Important operational links:

- semester belongs to batch
- section belongs to batch and semester
- group belongs to section
- student and enrollment currently reference section through `class_id`

## APIs

Primary endpoints:

- `/batches`
- `/semesters`
- `/sections`
- `/sections/sync-groups`
- `/sections/{section_id}/lock`
- `/sections/{section_id}/unlock`
- `/groups`
- `/students`
- `/students/bulk-import/preview`
- `/students/bulk-import/commit`
- `/enrollments`

## Workflow

1. create batches and semesters under a program or specialization
2. create sections within semesters
3. auto-sync groups for sections
4. create or bulk-import students
5. map students into sections and optional groups
6. enforce section coordinator lock rules where needed

## Dependencies

- `backend/app/api/v1/endpoints/batches.py`
- `backend/app/api/v1/endpoints/semesters.py`
- `backend/app/api/v1/endpoints/sections.py`
- `backend/app/api/v1/endpoints/groups.py`
- `backend/app/api/v1/endpoints/students.py`
- `backend/app/api/v1/endpoints/enrollments.py`
- `backend/app/services/section_mapping.py`
- `backend/app/services/student_bulk_import.py`
- frontend academic setup and student bulk pages
