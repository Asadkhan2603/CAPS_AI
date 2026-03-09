# API Contracts Guide

## Overview

This guide defines the actual HTTP contract used by CAPS AI today.

It is based on:
- [main.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\main.py)
- [router.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\router.py)
- [response.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\response.py)
- [apiClient.js](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\services\apiClient.js)
- the route modules under `backend/app/api/v1/endpoints`

This document is not a Swagger replacement. It explains the stable patterns, request semantics, error semantics, and route families that clients must follow.

## Contract Scope

The API surface has three layers:

1. public runtime infrastructure routes
2. versioned API routes under `/api/v1`
3. frontend client-side transport conventions

Public non-versioned runtime routes:
- `GET /health`
- `GET /`

Versioned API root:
- default prefix: `/api/v1`

The prefix is controlled by [config.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\config.py) through `API_PREFIX`.

## Base URL Contract

### Backend

Default API prefix:
- `/api/v1`

Local health endpoint:
- `http://localhost:8000/health`

### Frontend

Frontend client base URL:
- `import.meta.env.VITE_API_BASE_URL || '/api/v1'`

Implementation:
- [apiClient.js](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\services\apiClient.js)

### Practical Environment Implications

Local standalone development commonly uses:
- backend on `http://localhost:8000`
- frontend on `http://localhost:5173`

Local Docker Compose uses:
- frontend published on `http://localhost:5173`
- backend published on `http://localhost:8000`

If frontend is served from a different origin without reverse proxying `/api/v1`, `VITE_API_BASE_URL` must be set correctly.

## HTTP Transport Conventions

### Content Types

Most endpoints use:
- `application/json`

File upload endpoints use:
- `multipart/form-data`

Known upload-style endpoints include:
- `POST /auth/profile/avatar`
- `POST /submissions/upload`
- `POST /branding/logo`
- event registration flows with proof uploads depending on path usage

### Methods

The API uses the following method meanings:

- `GET`: read data
- `POST`: create records or invoke workflow actions
- `PUT`: update an existing record
- `PATCH`: state transition or partial update
- `DELETE`: destructive or archive-style action depending on module

Important point:
- this repo does not use `DELETE` uniformly as hard delete
- in several modules, delete-style endpoints archive or soft-delete instead of physically removing the record

## Authentication Contract

Primary auth routes:
- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`
- `POST /auth/logout`
- `GET /auth/me`
- `POST /auth/change-password`
- `PATCH /auth/profile`
- `POST /auth/profile/avatar`
- `GET /auth/profile/avatar/{user_id}`

Primary backend auth implementation:
- [auth.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\auth.py)

### Token Model

The frontend expects:
- access token
- refresh token
- serialized user payload

Stored keys:
- `caps_ai_token`
- `caps_ai_refresh_token`
- `caps_ai_user`

Storage model:
- `sessionStorage`

Current design implication:
- browser auth is intentionally session-scoped
- closing the browser/session clears the stored auth artifacts unless some external browser restore behavior rehydrates them

### Authorization Header

Authenticated requests send:

```http
Authorization: Bearer <access_token>
```

The frontend adds this automatically when the access token exists.

### Refresh Behavior

The frontend client retries one time on `401` for non-auth routes:

1. detect `401`
2. skip retry for login, refresh, logout routes
3. call `/auth/refresh`
4. store new tokens
5. replay original request

If refresh fails:
- auth storage is cleared

## Request Metadata Contract

The frontend always attempts to attach:
- `X-Trace-Id`
- `X-Request-Id`

The backend echoes or creates:
- `X-Request-Id`
- `X-Trace-Id`
- `X-Response-Time-Ms`

On errors the backend also adds:
- `X-Error-Id`

These values are generated and logged in [main.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\main.py).

## Response Envelope Contract

The backend supports optional response wrapping.

Implementation:
- [response.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\response.py)

Middleware:
- `ResponseEnvelopeMiddleware` in [main.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\main.py)

The envelope is applied only when:
- `RESPONSE_ENVELOPE_ENABLED=true`
- route is under API prefix
- route is not `/health` or `/`
- response is JSON
- response status is below `400`

### Success Envelope

```json
{
  "success": true,
  "data": {},
  "error": null,
  "trace_id": "..."
}
```

### Error Envelope

```json
{
  "success": false,
  "data": null,
  "error": {
    "message": "...",
    "error_id": "...",
    "detail": "..."
  },
  "trace_id": "...",
  "detail": "...",
  "error_id": "..."
}
```

### Frontend Handling

The frontend client:
- unwraps success envelopes automatically
- normalizes enveloped errors into `detail` and `error_id`

Client rule:
- do not assume raw JSON business payloads in all environments
- always tolerate enveloped success and error forms

## Error Handling Contract

Global handlers exist for:
- `HTTPException`
- `RequestValidationError`
- generic unhandled exceptions

Expected status classes:
- `400`: invalid request or business rule failure
- `401`: unauthenticated or invalid auth state
- `403`: authenticated but forbidden, including governance denials
- `404`: resource not found
- `422`: schema or validation failure
- `500`: unhandled backend error

### Error Payload Semantics

Important error values:
- `detail`
- `error.message`
- `error.error_id`
- `trace_id`

Client rule:
- log both `trace_id` and `error_id`
- surface `detail` to support workflows when appropriate

## CORS Contract

CORS is configured in [main.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\main.py) from [config.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\config.py).

Configured behavior:
- `allow_credentials=True`
- `allow_methods=["*"]`
- `allow_headers=["*"]`

Origins are merged with common development defaults:
- `http://localhost:5173`
- `http://127.0.0.1:5173`

## Route Family Catalog

The current route catalog from [router.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\router.py) is below.

### Identity And Access

- `/auth`
- `/users`

Key operations:

`/auth`
- register
- login
- refresh
- logout
- current-user fetch
- password change
- profile patch
- avatar upload and fetch

`/users`
- list users
- create user
- patch extension roles
- deactivate user

### Canonical Academic Core

- `/faculties`
- `/departments`
- `/programs`
- `/specializations`
- `/batches`
- `/semesters`
- `/sections`
- `/students`
- `/groups`
- `/subjects`
- `/course-offerings`
- `/class-slots`
- `/attendance-records`
- `/enrollments`

Common contract pattern:
- list
- get by id
- create
- update
- delete or archive-style delete

Notable workflow operations:

`/attendance-records`
- `POST /mark`
- `POST /mark-bulk`
- `POST /internship/clock-in`
- `POST /internship/clock-out`
- `GET /internship/status`

`/class-slots`
- `GET /my` for current user scoped schedule

### Legacy Academic Compatibility Routes

Deprecated in router metadata:
- `/courses`
- `/branches`
- `/years`
- `/classes`

Canonical replacement for sections:
- `/sections`

Client rule:
- do not build new integrations against the legacy set unless migrating old data or screens

### Assessment And AI

- `/assignments`
- `/submissions`
- `/evaluations`
- `/similarity`
- `/ai`

Notable workflow actions:

`/assignments`
- `PATCH /{assignment_id}/plagiarism`

`/submissions`
- `POST /upload`
- `POST /{submission_id}/ai-evaluate`
- `POST /ai-evaluate/pending`

`/evaluations`
- `GET /{evaluation_id}/trace`
- `POST /ai-preview`
- `POST /{evaluation_id}/ai-refresh`
- `PATCH /{evaluation_id}/finalize`
- `PATCH /{evaluation_id}/override-unfinalize`

`/similarity`
- `GET /checks`
- `POST /checks/run/{submission_id}`
- `POST /checks/run-async/{submission_id}`

`/ai`
- `POST /evaluate`
- `GET /history/{student_id}/{exam_id}`

### Timetable And Scheduling

- `/timetables`

Notable workflow actions:
- `GET /shifts`
- `POST /generate-grid`
- `GET /lookups`
- `GET /class/{class_id}`
- `GET /my`
- `POST /{timetable_id}/publish`
- `POST /{timetable_id}/lock`

### Communication And Notifications

- `/notices`
- `/notifications`

Notable actions:

`/notices`
- list
- create
- delete
- `POST /process-scheduled`

`/notifications`
- list
- create
- `PATCH /{notification_id}/read`

### Clubs And Events

- `/clubs`
- `/club-events`
- `/event-registrations`

Notable actions:

`/clubs`
- `POST /{club_id}/join`
- `GET /{club_id}/members`
- `PATCH /{club_id}/members/{member_id}`
- `GET /{club_id}/applications`
- `PATCH /{club_id}/applications/{application_id}`
- `GET /{club_id}/analytics`

`/event-registrations`
- list
- create
- `POST /submit`

### Analytics And Audit

- `/analytics`
- `/audit-logs`
- `/review-tickets`

Notable actions:

`/analytics`
- `GET /summary`
- `GET /teacher/classes`
- `GET /teacher/sections`
- `GET /academic-structure`

`/review-tickets`
- list
- create
- approve
- reject

### Admin Route Families

- `/admin/system`
- `/admin/analytics`
- `/admin/communication`
- `/admin/governance`
- `/admin/recovery`

Notable admin endpoints:

`/admin/system`
- `GET /health`

`/admin/analytics`
- `GET /overview`
- `GET /platform`
- `POST /snapshots/run-daily`
- `GET /snapshots/history`
- `GET /audit-summary`

`/admin/communication`
- `POST /preview-target`

`/admin/governance`
- `GET /policy`
- `PATCH /policy`
- `POST /reviews`
- `GET /reviews`
- `PATCH /reviews/{review_id}`
- `GET /dashboard`
- `GET /sessions`

`/admin/recovery`
- `GET /`
- `PATCH /{collection}/{item_id}/restore`

## CRUD Pattern Contract

Most collection-backed endpoints follow these conventions:

### List

Common shape:

```http
GET /resource/?skip=0&limit=10
```

Typical characteristics:
- returns an array, not a paginated envelope object
- additional filters may be accepted per module
- pagination is usually `skip` + `limit`

### Get By Id

Common shape:

```http
GET /resource/{id}
```

### Create

Common shape:

```http
POST /resource/
Content-Type: application/json
```

### Update

Common shape:

```http
PUT /resource/{id}
Content-Type: application/json
```

### Workflow Action

Common shape:

```http
PATCH /resource/{id}/action
POST /resource/{id}/action
```

Used for:
- finalize
- lock
- publish
- AI refresh
- mark read
- join
- approve or reject

### Delete

Common shape:

```http
DELETE /resource/{id}
```

Important semantic rule:
- some delete routes hard delete
- some delete routes archive or soft-delete
- clients must not assume physical deletion

## Query Parameter Contract

The repo uses query params heavily for:
- list filters
- pagination
- governance inputs in selected destructive flows

Common query parameters:
- `skip`
- `limit`
- entity-specific filters such as `student_user_id`, `teacher_user_id`, `submission_id`, `is_finalized`
- `review_id` for governance-gated actions in selected endpoints

Client rule:
- send query params explicitly instead of encoding workflow state into path guesses

## File Upload Contract

Known file-oriented endpoints:
- avatar upload
- submission upload
- branding logo upload
- event-related proof upload flows

Upload client rule:
- use `multipart/form-data`
- do not send large files blindly without verifying endpoint-specific limits

Known current explicit avatar constraints from [auth.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\auth.py):
- max size `3MB`
- allowed types:
  - `.png`
  - `.jpg`
  - `.jpeg`
  - `.webp`

## Authorization Contract

Backend enforcement is the source of truth.

Current enforcement styles in the backend include:
- authenticated user required through `get_current_user`
- permission-based guards through `require_permission(...)`
- role-level checks inside route logic
- row-level ownership and scope checks inside route logic

Current frontend enforcement is advisory and UX-oriented:
- [featureAccess.js](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\config\featureAccess.js)
- [AppRoutes.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\routes\AppRoutes.jsx)

Client rule:
- never rely on frontend route access alone as proof of backend authorization

## Governance Delete Contract

Some destructive actions are governance-gated.

Backend behavior:
- may require approved `review_id`
- may reject with `403`
- may emit governance-specific error detail

Frontend behavior in shared CRUD flows:
- detects review requirement
- opens governance prompt
- sends `review_id`
- may send optional metadata fields

Relevant files:
- [governance.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\governance.py)
- [EntityManager.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\components\ui\EntityManager.jsx)
- [featureAccess.js](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\config\featureAccess.js)

Client rule:
- for admin destructive actions, be prepared to handle governance-required retry flows

## Trace And Observability Contract

Every request should be considered traceable through:
- request id
- trace id
- response timing
- structured backend logs
- audit events for important state changes
- destructive action telemetry for protected deletes
- recent client-side trace buffer

Support rule:
- ask users for `trace_id` and `error_id` before digging into backend logs

## Backward Compatibility Rules

The API is not fully uniform across old and new domains.

Current compatibility tensions:
- canonical academic model coexists with deprecated legacy endpoints
- section data is still stored in class-shaped records
- some modules expose richer workflow endpoints than the generic CRUD model implies
- some destructive paths are hard delete while others are soft delete/archive

Client rule:
- prefer canonical route families
- treat legacy academic endpoints as compatibility-only
- do not infer delete semantics without checking module behavior

## Practical Client Rules

1. Use `/api/v1` unless deployment config overrides it.
2. Always tolerate enveloped and unwrapped JSON responses.
3. Preserve `trace_id` and `error_id`.
4. Treat `/sections` as canonical and `/classes` as legacy.
5. Expect `skip` and `limit` rather than a standardized paginated object.
6. Treat workflow actions such as finalize, publish, AI refresh, and restore as first-class API operations, not CRUD variants.
7. For admin destructive actions, support governance retry with `review_id`.
8. Do not assume every `DELETE` is a hard delete.

## Known Contract Gaps

1. No single generated contract file exists that summarizes all schemas and response examples per route.
2. Pagination is not standardized as a typed envelope object.
3. Some modules still mix canonical and compatibility-era semantics.
4. Governance-required delete flows are strongest in shared CRUD UIs, not in every custom page.
5. Third-party clients must actively handle config-driven envelope behavior.
