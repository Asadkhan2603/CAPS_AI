# User And Section Mapping

## Purpose

This guide explains how users, students, coordinator scope, section placement, and bulk mapping work in the current CAPS AI implementation.

## Data Model

Relevant records:

- users
- students
- enrollments
- sections
- groups

Important fields:

- user `role`
- user `admin_type`
- user `extended_roles`
- user `role_scope.class_coordinator.class_id`
- student `class_id`
- enrollment `class_id`
- group `section_id`

Compatibility note:

- the platform uses `section` as the canonical term
- the current persisted mapping field is often still `class_id`

## APIs

Primary mapping endpoints:

- `/users`
- `/users/{user_id}/extensions`
- `/sections`
- `/sections/{section_id}/lock`
- `/sections/{section_id}/unlock`
- `/students`
- `/students/bulk-import/preview`
- `/students/bulk-import/commit`
- `/enrollments`
- `/analytics/teacher/sections`

## Workflow

### Admin-created mapping

1. admin creates or updates users
2. admin assigns extensions such as `class_coordinator`
3. admin creates sections
4. admin assigns `class_coordinator_user_id` to a section
5. students are created or imported
6. enrollments are created against the destination section

### Coordinator mapping flow

1. teacher must have `class_coordinator` in `extended_roles`
2. coordinator scope resolves through `role_scope.class_coordinator.class_id`
3. UI limits available sections and mappings
4. coordinator previews bulk mapping rows
5. coordinator commits mapping
6. section can be locked after a valid mapping cycle

### Bulk onboarding modes

Supported modes in the frontend workflow:

- `create_students`
- `map_existing`

Behavior:

- `create_students` creates global student records first
- `map_existing` maps existing student records into a target section and optional group

## Dependencies

- `backend/app/api/v1/endpoints/users.py`
- `backend/app/api/v1/endpoints/sections.py`
- `backend/app/api/v1/endpoints/students.py`
- `backend/app/api/v1/endpoints/enrollments.py`
- `backend/app/services/section_mapping.py`
- `backend/app/services/student_bulk_import.py`
- `frontend/src/components/students/StudentBulkWorkflow.jsx`
- `frontend/src/pages/CoordinatorStudentMappingPage.jsx`
