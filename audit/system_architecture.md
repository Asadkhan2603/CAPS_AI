# System Architecture

## Overview

CAPS AI is a section-centered academic operations platform with a React frontend, a FastAPI backend, MongoDB-backed persistence, optional Redis-backed runtime features, and a workbook-driven master hierarchy import path.

The active architecture is:

`React UI -> apiClient -> FastAPI /api/v1 endpoints -> service layer -> Mongo collections / external runtime adapters`

## Clean Architecture Shape

## Frontend

Primary frontend layers:

- `frontend/src/routes/`
  Route registration, redirects, protected access, workspace routing.
- `frontend/src/components/layout/`
  App shell, sidebar, header, responsive navigation.
- `frontend/src/pages/`
  Feature-level screens.
- `frontend/src/components/`
  Reusable feature widgets and shared UI.
- `frontend/src/services/`
  HTTP client and API wrappers.
- `frontend/src/utils/`
  pure helpers, pagination, permissions, quick search, templates.
- `frontend/src/context/` and `frontend/src/hooks/`
  auth, theme, toast, and session state.

Frontend data flow:

1. Route resolves through [frontend/src/routes/AppRoutes.jsx](D:/VS%20CODE/MY%20PROJECT/CAPS_AI/frontend/src/routes/AppRoutes.jsx)
2. Access control is checked with `FEATURE_ACCESS`
3. Page component calls a service in `frontend/src/services`
4. [frontend/src/services/apiClient.js](D:/VS%20CODE/MY%20PROJECT/CAPS_AI/frontend/src/services/apiClient.js) attaches auth and trace headers
5. Backend responds with the response envelope middleware
6. UI renders normalized response payloads

## Backend

Primary backend layers:

- `backend/app/main.py`
  app bootstrap, middleware, exception handling, startup tasks.
- `backend/app/api/v1/`
  HTTP routing and endpoint orchestration.
- `backend/app/services/`
  business rules, validation, workflows, cross-collection operations.
- `backend/app/models/`
  serializer helpers that turn Mongo documents into API payloads.
- `backend/app/schemas/`
  request and response validation contracts.
- `backend/app/core/`
  configuration, database, indexes, security, rate limit, observability, response envelope.
- `backend/app/domains/auth/`
  the only active domain package currently used in runtime.

Backend request flow:

1. FastAPI receives request
2. middleware adds request IDs, trace IDs, rate limiting, security headers, and response envelope behavior
3. endpoint validates input using schema objects
4. endpoint delegates business logic to services
5. services read and write Mongo collections
6. model serializers shape response payloads
7. envelope middleware returns `data` to the frontend

## Data Stores And Runtime Services

- MongoDB is the primary system of record
- Redis is an optional runtime dependency controlled by config
- the scheduler starts during app lifespan unless startup tasks are skipped
- OpenAI and Cloudinary are external adapters used by AI and media workflows

## Canonical Module Boundaries

The repo should be documented around these stable module groups.

### 1. Identity, access, and governance

Scope:

- auth
- users
- permissions
- audit logs
- destructive action reviews
- recovery and admin governance

Primary backend areas:

- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/api/v1/endpoints/users.py`
- `backend/app/api/v1/endpoints/admin_governance.py`
- `backend/app/api/v1/endpoints/admin_recovery.py`
- `backend/app/services/governance.py`
- `backend/app/services/audit.py`

### 2. Academic master hierarchy

Scope:

- universities
- faculties
- departments
- programs
- specializations
- workbook import and master integrity checks

Primary backend areas:

- `backend/scripts/import_master_hierarchy.py`
- `backend/scripts/audit_academic_integrity.py`
- `backend/app/services/master_hierarchy.py`
- `backend/app/services/academic_hierarchy.py`

### 3. Academic operations

Scope:

- batches
- semesters
- sections
- groups
- students
- enrollments
- section mapping
- bulk student onboarding

Primary backend areas:

- `backend/app/api/v1/endpoints/batches.py`
- `backend/app/api/v1/endpoints/semesters.py`
- `backend/app/api/v1/endpoints/sections.py`
- `backend/app/api/v1/endpoints/groups.py`
- `backend/app/api/v1/endpoints/students.py`
- `backend/app/api/v1/endpoints/enrollments.py`
- `backend/app/services/section_mapping.py`
- `backend/app/services/student_bulk_import.py`

### 4. Course delivery

Scope:

- subjects
- course offerings
- class slots
- timetables
- attendance records

Primary backend areas:

- `backend/app/api/v1/endpoints/subjects.py`
- `backend/app/api/v1/endpoints/course_offerings.py`
- `backend/app/api/v1/endpoints/class_slots.py`
- `backend/app/api/v1/endpoints/timetables.py`
- `backend/app/api/v1/endpoints/attendance_records.py`

### 5. Assessment and AI

Scope:

- assignments
- submissions
- evaluations
- similarity
- AI chat and AI ops

Primary backend areas:

- `backend/app/api/v1/endpoints/assignments.py`
- `backend/app/api/v1/endpoints/submissions.py`
- `backend/app/api/v1/endpoints/evaluations.py`
- `backend/app/api/v1/endpoints/similarity.py`
- `backend/app/api/v1/endpoints/ai.py`
- `backend/app/services/evaluation_workflow.py`
- `backend/app/services/similarity_pipeline.py`
- `backend/app/services/ai_ops_workflow.py`

### 6. Communication and clubs

Scope:

- notices
- notifications
- communication previewing
- clubs
- club events
- event registrations

Primary backend areas:

- `backend/app/api/v1/endpoints/notices.py`
- `backend/app/api/v1/endpoints/notifications.py`
- `backend/app/api/v1/endpoints/admin_communication.py`
- `backend/app/api/v1/endpoints/clubs.py`
- `backend/app/api/v1/endpoints/club_events.py`
- `backend/app/api/v1/endpoints/event_registrations.py`

### 7. Analytics and system health

Scope:

- analytics dashboards
- feed generation
- student interventions
- system health snapshots
- admin analytics and admin system surfaces

Primary backend areas:

- `backend/app/api/v1/endpoints/analytics.py`
- `backend/app/api/v1/endpoints/admin_analytics.py`
- `backend/app/api/v1/endpoints/admin_system.py`
- `backend/app/services/system_health_snapshots.py`
- `backend/app/services/analytics_snapshot.py`

## Standardized Folder Direction

Final structure should follow these conventions:

- endpoints own HTTP only
- services own business logic
- schemas own validation contracts
- models own serializer output only
- domains are used only when they contain real repository/service abstractions
- docs describe canonical names, not legacy aliases

Preferred naming:

- `section`, not `class`
- `specialization`, not `branch`
- `program`, not `course`
- `batch`, not `year`

Compatibility note:

- storage still uses the `classes` collection
- many downstream records still use `class_id`
- docs should label that as a compatibility bridge, not the target design

## System Data Flow

### A. Master hierarchy flow

1. Workbook is parsed by `import_master_hierarchy.py`
2. canonical field contract is validated
3. business IDs are normalized
4. master collections are upserted
5. downstream safety checks protect dependent records

### B. Student onboarding flow

1. Admin or coordinator uses `StudentBulkWorkflow`
2. file is uploaded as CSV or XLSX
3. backend validates preview rows
4. commit creates or maps students
5. enrollments and section mappings are synchronized
6. optional section lock protects future mapping integrity

### C. Academic delivery flow

1. subjects and course offerings are created
2. sections own course delivery
3. timetables and class slots operate on section scope
4. attendance, assignments, submissions, and evaluations consume that scope

### D. Communication and analytics flow

1. notices and activity items are generated in operational modules
2. analytics aggregates cross-module data
3. feed and admin dashboards read those aggregates
4. governance and audit trails track sensitive changes

## Excel-Oriented Data Hierarchy

The export design should mirror the canonical hierarchy and keep referential joins simple.

### Mandatory sheet ordering

1. Institutions
2. Faculties
3. Departments
4. Programs
5. Specializations
6. Batches
7. Semesters
8. Sections
9. Groups
10. Users
11. Students
12. Enrollments
13. Subjects
14. Course Offerings

### Join strategy

- top-level sheets should expose stable business IDs where available
- downstream sheets should expose local record IDs and parent IDs
- student and enrollment sheets must preserve the current `class_id` compatibility link until the codebase fully migrates

## Architectural Constraints

These constraints are active in the repo today and should shape the next phases:

- the public API standard is section-based, but storage is still class-based
- root documentation is empty and currently breaks runtime-matrix validation
- the workbook-driven master hierarchy process is blocked until the canonical workbook source is restored or redefined
- placeholder domain packages exist and should not be treated as architectural pillars

## Final Target

The final documented structure should describe CAPS AI as:

- a workbook-seeded institutional hierarchy
- a section-based academic operations platform
- a modular frontend workspace shell
- a FastAPI service layer with explicit module boundaries
- an exportable relational academic graph suitable for normalized Excel sheets
