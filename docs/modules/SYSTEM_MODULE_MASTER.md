# System Module Master

## Module Overview
This section provides a standardized summary for the module. Refer to the detailed sections below for full context.

## Responsibilities
- Core responsibilities are described in the detailed sections below.

## Components
- Primary backend endpoints, schemas, and UI surfaces are listed below.

## API Endpoints
- Refer to the API endpoint inventory in this document.

## Data Models
- Refer to the data model details in this document.

## Workflows
- Refer to the workflow and lifecycle sections below.

## Dependencies
- Refer to dependency notes in this document.

## Known Limitations
- Refer to current limitations described below.

## Improvements
- Refer to improvement opportunities listed below.


## Module Tree

```text
System Module
|-- Application Bootstrap
|-- Config And Environment
|-- Database And Redis Infrastructure
|-- Scheduler And Background Jobs
|-- Diagnostics And Recovery APIs
`-- Rate Limiting And Operational Controls
```

## Internal Entity And Flow Tree

```text
Runtime startup
|-- Config load
|-- Database and index initialization
|-- Scheduler leadership
`-- Operational endpoints and recovery controls
```

Primary implementation sources:

- [main.py](/backend/app/main.py)
- [config.py](/backend/app/core/config.py)
- [database.py](/backend/app/core/database.py)
- [indexes.py](/backend/app/core/indexes.py)
- [rate_limit.py](/backend/app/core/rate_limit.py)
- [redis_store.py](/backend/app/core/redis_store.py)
- [response.py](/backend/app/core/response.py)
- [observability.py](/backend/app/core/observability.py)
- [scheduler.py](/backend/app/services/scheduler.py)
- [admin_system.py](/backend/app/api/v1/endpoints/admin_system.py)
- [admin_recovery.py](/backend/app/api/v1/endpoints/admin_recovery.py)

Primary frontend surfaces:

- [AdminSystemPage.jsx](/frontend/src/pages/Admin/AdminSystemPage.jsx)
- [AdminRecoveryPage.jsx](/frontend/src/pages/Admin/AdminRecoveryPage.jsx)
- [AdminDashboardPage.jsx](/frontend/src/pages/Admin/AdminDashboardPage.jsx)
- [AdminDeveloperPage.jsx](/frontend/src/pages/Admin/AdminDeveloperPage.jsx)
- [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx)
- [featureAccess.js](/frontend/src/config/featureAccess.js)

This document describes the System Module as implemented today.

In CAPS AI, the system module is not a business module like academics or assignments. It is the runtime and platform control plane responsible for:

- application startup and shutdown
- database connectivity and index bootstrapping
- scheduler leadership and background job orchestration
- health and diagnostic reporting
- rate limiting
- response and error envelope behavior
- logging and request tracing
- soft-delete recovery workflows

## 1. Module Overview

The System Module is the operational backbone of CAPS AI.

It exists to keep the backend service bootable, observable, and governable in live environments.

Its current responsibilities are spread across four layers:

1. runtime bootstrap
2. infrastructure adapters and platform controls
3. operational APIs
4. admin-facing monitoring and recovery UI

The module is intentionally cross-cutting. It does not model one user workflow. Instead, it governs how the whole application behaves in production and development.

Key implementation reality:

- the public health route is `/health`
- the protected admin health route is `/api/v1/admin/system/health`
- the scheduler starts from application startup, but leadership is elected through a Mongo-backed lock
- rate limiting prefers Redis, then Mongo, then local memory fallback
- recovery is built around soft-delete metadata, not point-in-time database restore

## 2. Runtime Bootstrap Architecture

## 2.1 FastAPI application setup

File:

- [main.py](/backend/app/main.py)

Core startup path:

1. load settings
2. configure structured logging
3. instantiate FastAPI
4. add rate-limit middleware
5. add CORS middleware
6. add security-header and request-trace middleware
7. add response-envelope middleware
8. mount API router under configured prefix
9. run startup tasks:
   - `ensure_indexes()`
   - `app_scheduler.start()`
10. run shutdown task:
   - `app_scheduler.stop()`

This is the effective operational lifecycle of the backend.

## 2.2 Public health and root routes

Public runtime routes in `main.py`:

- `GET /health`
- `GET /`

Behavior:

- `/health` returns a minimal readiness signal: `{"status": "ok"}`
- `/` returns a basic service banner message

Important detail:

- `/health` intentionally bypasses response envelope wrapping
- this makes it simpler for external probes and infrastructure checks

## 2.3 Exception and response normalization

`main.py` installs global exception handlers for:

- `HTTPException`
- `RequestValidationError`
- unhandled `Exception`

These handlers:

- generate structured error envelopes
- stamp `X-Error-Id`
- log request and trace ids

This gives CAPS AI a consistent error contract at the platform layer.

## 3. Configuration Model

## 3.1 Environment-backed settings

File:

- [config.py](/backend/app/core/config.py)

`Settings` is a dataclass populated from environment variables.

Major configuration groups:

### Runtime identity

- `environment`
- `app_name`
- `app_version`
- `api_prefix`

### Data and auth

- `mongodb_url`
- `mongodb_db`
- `jwt_secret`
- `jwt_algorithm`
- `access_token_expire_minutes`
- `refresh_token_expire_days`

### Security and abuse controls

- `account_lockout_max_attempts`
- `account_lockout_window_minutes`
- `account_lockout_duration_minutes`
- `rate_limit_max_requests`
- `rate_limit_window_seconds`
- `cors_origins`

### AI and analytics operations

- `openai_api_key`
- `openai_model`
- `openai_timeout_seconds`
- `openai_max_output_tokens`
- `similarity_threshold`
- `ai_job_poll_seconds`
- `analytics_cache_ttl_seconds`

### Scheduler controls

- `scheduler_enabled`
- `scheduler_lock_id`
- `scheduler_lock_ttl_seconds`
- `scheduler_lock_renew_seconds`
- `scheduled_notice_poll_seconds`
- `analytics_snapshot_hour_utc`
- `analytics_snapshot_minute_utc`

### Storage and media

- `cloudinary_cloud_name`
- `cloudinary_api_key`
- `cloudinary_api_secret`

### Miscellaneous runtime behavior

- `response_envelope_enabled`
- `redis_enabled`
- `redis_url`
- `internship_auto_logout_hours`

## 3.2 Configuration safeguards

Important built-in validation:

- non-development environments cannot run with default `JWT_SECRET = change_me`
- invalid `AUTH_REGISTRATION_POLICY` values are normalized back to `single_admin_open`
- local frontend origins are always merged into CORS to prevent accidental local lockout

This is useful operationally, but it also means configuration is permissive in development and stricter in non-development environments.

## 4. Core Infrastructure Adapters

## 4.1 Database adapter

File:

- [database.py](/backend/app/core/database.py)

Behavior:

- creates a global Motor client using `settings.mongodb_url`
- binds the application database using `settings.mongodb_db`

This is a simple adapter with no connection pooling customization in code. It relies on Motor defaults.

## 4.2 Redis adapter

File:

- [redis_store.py](/backend/app/core/redis_store.py)

Capabilities:

- JSON get and set
- increment with TTL
- token blacklist tracking
- availability probing

Runtime behavior:

- only active when `REDIS_ENABLED` is true and Redis library is available
- connection attempts are retried with a short backoff
- failures degrade gracefully by returning `None` or `False`

This adapter is central to:

- analytics caching
- rate limiting
- token blacklist acceleration

## 4.3 Response envelope helper

File:

- [response.py](/backend/app/core/response.py)

Purpose:

- provide a standard success or error envelope shape
- detect already-wrapped payloads

This is infrastructure behavior rather than business behavior.

## 4.4 Observability primitives

File:

- [observability.py](/backend/app/core/observability.py)

Capabilities:

- request-scoped `request_id`
- request-scoped `trace_id`
- structured JSON log formatting
- error id generation

This module underpins most system-level logging behavior.

## 5. Startup Index Bootstrapping

## 5.1 Index creation flow

File:

- [indexes.py](/backend/app/core/indexes.py)

`ensure_indexes()` is executed during app startup.

It creates indexes for:

- users
- notices
- assignments
- submissions
- evaluations
- notifications
- audit logs
- governance review storage
- recovery logs
- academic collections
- timetable collections
- groups and offerings
- attendance collections
- internship sessions
- AI evaluation run storage
- AI job storage
- idempotent similarity log storage

## 5.2 Index creation behavior

`_safe_create_index(...)` intentionally tolerates several existing-index conflicts:

- code `85`
- code `86`
- code `11000`

This makes startup more resilient to index drift and repeated deploys.

Tradeoff:

- startup is less brittle
- but silent acceptance can mask index-option drift if the database already holds a non-ideal index shape

## 6. Rate Limiting Architecture

## 6.1 Middleware placement

File:

- [rate_limit.py](/backend/app/core/rate_limit.py)

The rate limiter is mounted as application middleware near startup.

It applies only to:

- mutating methods: `POST`, `PUT`, `PATCH`, `DELETE`
- auth routes containing `/auth/`

This avoids placing rate limit cost on most reads while still protecting the high-risk write and login surfaces.

## 6.2 Actor identity model

Rate limit keys are derived from:

- bearer token subject when a valid JWT is present
- otherwise client IP + user-agent

This creates a practical abuse-control identity even before authentication succeeds.

## 6.3 Backend selection order

The rate limiter attempts storage in this order:

1. Redis
2. Mongo `rate_limit_counters`
3. local in-memory deque map

Production and staging behavior:

- if Redis and Mongo are unavailable, the system fails closed with `503`

Development behavior:

- falls back to local in-memory counters

Important implication:

- development is tolerant
- production is intentionally stricter

## 6.4 Known limitation

The local-memory fallback remains per-process and can grow key cardinality.

The middleware prunes stale keys aggressively, but that does not make it distributed-safe.

## 7. Scheduler and Background Operations

## 7.1 Scheduler purpose

File:

- [scheduler.py](/backend/app/services/scheduler.py)

The scheduler is the operational orchestrator for recurring background jobs.

Current scheduled jobs:

1. scheduled notice dispatch polling
2. durable AI job polling and execution
3. daily analytics snapshot generation

## 7.2 Leadership model

The scheduler is not blindly run by every app instance.

Current design:

- app startup calls `app_scheduler.start()`
- scheduler attempts to become leader using `scheduler_locks`
- only leader instance runs background loops
- leadership is renewed with TTL-based heartbeats

Stored lock fields:

- `_id`
- `owner_id`
- `expires_at`
- `heartbeat_at`
- `created_at`

This is a substantial improvement over naive multi-replica scheduling.

## 7.3 Scheduler state exposed to operators

`app_scheduler.status()` returns:

- `enabled`
- `running`
- `is_leader`
- `instance_id`
- `lock_id`
- `lock_ttl_seconds`
- `lock_renew_seconds`
- `scheduled_notice_poll_seconds`
- `ai_job_poll_seconds`
- `snapshot_time_utc`
- `last_notice_dispatch_at`
- `last_notice_dispatch_count`
- `last_snapshot_at`

This state is surfaced in admin health APIs rather than remaining internal-only.

## 7.4 Scheduler risks

The leader-election model is pragmatic, but remaining risks include:

- dependence on Mongo availability and lock correctness
- no separate worker deployment boundary
- background work still lives in the web process

This is acceptable for moderate load, but it is still a web-process-hosted queue/worker model rather than a separately deployed worker tier.

## 8. Operational APIs

## 8.1 Public health endpoint

Route:

- `GET /health`

Purpose:

- external runtime probe
- lightweight readiness indicator

Access:

- public

## 8.2 Admin system health endpoint

File:

- [admin_system.py](/backend/app/api/v1/endpoints/admin_system.py)

Route:

- `GET /api/v1/admin/system/health`

Access:

- `require_permission("system.read")`

Current returned metrics:

- timestamp
- DB ping status
- scheduler status object
- application uptime
- `error_count_24h`
- `active_sessions_24h`
- `slow_query_count_24h`
- latest slow-query logs
- collection counts for key collections

This is the main system diagnostics API currently exposed to operators.

## 8.3 Recovery API

File:

- [admin_recovery.py](/backend/app/api/v1/endpoints/admin_recovery.py)

Routes:

- `GET /api/v1/admin/recovery`
- `PATCH /api/v1/admin/recovery/{collection}/{item_id}/restore`

Access:

- `require_permission("system.read")`

Recoverable collection set:

- `courses`
- `departments`
- `branches`
- `years`
- `classes`
- `notices`
- `notifications`
- `clubs`
- `club_events`
- `assignments`
- `submissions`
- `evaluations`
- `review_tickets`

Important behavior:

- recovery queries use soft-delete semantics
- restore writes audit log event
- restore also appends a row into `recovery_logs` when available

Note:
- legacy collections such as `courses`, `branches`, and `years` remain in the recovery set even though their API routes are retired

Important limitation:

- some collections in this list do not follow identical deletion semantics, so the recovery contract is only as strong as each collection's delete implementation

## 9. Frontend Implementation

## 9.1 `AdminSystemPage.jsx`

Purpose:

- show runtime health and key system counters

Current UI includes:

- DB status
- uptime
- error count in last 24h
- active sessions in last 24h
- slow query count
- timestamp
- collection count dump
- latest slow query log entries

This is a direct UI projection of `/admin/system/health`.

## 9.2 `AdminRecoveryPage.jsx`

Purpose:

- provide soft-delete recovery operations for selected collections

Current capabilities:

- choose a collection
- list recoverable rows
- inspect delete metadata
- restore one row

The page is operational, but intentionally basic.

## 9.3 `AdminDashboardPage.jsx`

Purpose:

- aggregate system, analytics, and governance summary into one control-plane landing page

System-related usage:

- fetches `/admin/system/health`
- surfaces DB status
- combines system health with governance and analytics cards

This page acts as the operational summary dashboard rather than the full diagnostics screen.

## 9.4 `AdminDeveloperPage.jsx`

Purpose:

- link into lower-level developer tooling

Current implementation:

- mainly a shell page pointing to `/developer-panel`

This is adjacent to the system module, but not yet a rich operational surface by itself.

## 9.5 Route and UI access contract

Frontend routes:

- `/admin/system`
- `/admin/recovery`
- `/admin/developer`

Effective access rules from route guards and feature config:

- `admin/system`:
  - role `admin`
  - admin types `super_admin`, `admin`, `compliance_admin`
- `admin/recovery`:
  - role `admin`
  - admin types `super_admin`, `admin`
- `admin/developer`:
  - role `admin`
  - admin type `super_admin`

This is narrower than generic admin access and is consistent with the system-sensitive nature of these pages.

## 10. Business Rules

### Rule 1: System health is split into public and protected views

- `/health` is public and minimal
- `/admin/system/health` is protected and detailed

### Rule 2: Startup is responsible for index and scheduler initialization

The system assumes the web process performs operational bootstrapping.

### Rule 3: Rate limiting should fail closed in non-development

If distributed rate-limit backends are unavailable in staging or production, request processing is blocked with `503`.

### Rule 4: Recovery is soft-delete based

The module does not implement backup restore or document version rewind. It restores items by clearing delete markers.

### Rule 5: Scheduler job execution must be singleton-safe

The background scheduler is designed so only the elected leader executes recurring jobs.

### Rule 6: Response envelopes are optional and configuration-driven

Platform response shaping can be toggled with `RESPONSE_ENVELOPE_ENABLED`.

## 11. Collections Used By The System Module

The system module depends on several operational collections.

### `scheduler_locks`

Purpose:

- maintain singleton leadership for recurring jobs

Key fields:

- `_id`
- `owner_id`
- `expires_at`
- `heartbeat_at`
- `created_at`

### `rate_limit_counters`

Purpose:

- Mongo-backed rate-limit counter fallback

Key fields:

- `_id`
- `count`
- `created_at`
- `expires_at`

### `recovery_logs`

Purpose:

- track restore operations

Key fields:

- `collection`
- `entity_id`
- `action`
- `performed_by`
- `created_at`

### `settings`

Purpose:

- store global system-adjacent configuration records such as governance policy and branding metadata

### `audit_logs`

Purpose:

- store operational visibility events including login, error, slow-query, and restore audit records

## 12. Strengths Of Current Implementation

### Strong Area 1: Clear startup orchestration

The system has a coherent application entrypoint with middleware, error handling, and startup hooks in one place.

### Strong Area 2: Leader-elected scheduler

The scheduler now uses a lock-based leadership model instead of naive replica-wide execution.

### Strong Area 3: Structured request logging

Request and trace IDs plus JSON logs make platform diagnostics materially easier.

### Strong Area 4: Recovery is operationally usable

Recovery is not only conceptual. It has both backend and frontend restore flows.

### Strong Area 5: Production-safe rate-limit posture

The rate limiter does not silently degrade to unsafe local-only behavior in production.

## 13. Gaps And Risks

### Gap 1: System permission semantics are too coarse

The admin system and recovery endpoints use:

- `require_permission("system.read")`

That is semantically weak for routes that perform restore operations or expose operational internals.

More precise permission names would be better, such as:

- `system.health.read`
- `system.recovery.read`
- `system.recovery.restore`

### Gap 2: Recovery list includes entities with mixed delete semantics

The recovery module assumes soft-delete compatibility, but not all module delete paths are equally standardized.

This creates a fragile contract.

### Gap 3: Scheduler still runs inside API pods

The leader-election improvement avoids duplicate execution, but it does not isolate background work from web serving capacity.

### Gap 4: Public health endpoint is shallow

`/health` is suitable for probes, but it does not validate DB, Redis, or scheduler readiness.

That is fine for liveness, but insufficient for deeper readiness guarantees.

### Gap 5: System UI is diagnostics-heavy but action-light

Current admin system UI can observe the platform, but it cannot:

- restart scheduler
- force snapshot generation
- inspect lock state in detail
- clear rate-limit counters
- view Redis availability directly

### Gap 6: No dedicated deployment-state model

The system module has runtime diagnostics, but no explicit deployment metadata entity for:

- release version
- build hash
- environment fingerprints
- migration version state

## 14. Architectural Issues

### Issue 1: Web process owns too many responsibilities

The backend process currently handles:

- HTTP serving
- startup bootstrapping
- scheduler leadership
- recurring background jobs
- operational metrics exposure

This is pragmatic, but it compresses system concerns into one runtime.

### Issue 2: Recovery is operational, not transactional

The recovery model is record-level marker restoration. It is not:

- transactional rollback
- dependency-aware restore orchestration
- versioned snapshot restore

For simple archives this is fine. For complex cascades it can be incomplete.

### Issue 3: Index management is application-managed

This keeps deployment simple, but it also means:

- index drift is handled at app boot
- operational migrations and schema evolution remain partly implicit

### Issue 4: System metrics are partially derived from audit logs

Examples:

- error count
- active sessions
- slow query count

This is practical, but only as reliable as audit emission quality.

## 15. Testing Requirements

### Backend tests

- `GET /health` returns stable public payload
- `GET /admin/system/health` rejects unauthorized callers
- admin system health returns scheduler object
- DB ping failure is surfaced as `db_status = error`
- recovery list rejects unsupported collections
- restore clears delete metadata correctly
- restore writes audit and recovery log events
- scheduler leader acquisition and renewal logic behaves correctly
- rate limiter:
  - uses Redis when available
  - falls back to Mongo
  - fails closed in production if backends unavailable

### Integration tests

- startup executes index ensure flow safely
- startup plus scheduler stop path is idempotent
- admin dashboard successfully composes system and governance state
- system recovery page can restore a soft-deleted row end-to-end

### Operational tests to add

- multi-instance scheduler lock contention
- Redis outage behavior under production settings
- Mongo outage behavior for system health endpoint
- large audit log volumes and slow-query visibility accuracy

## 16. Recommended Cleanup Strategy

### Phase 1: Clarify permissions

Split `system.read` into narrower system permissions for:

- diagnostics read
- recovery read
- recovery restore
- developer operations

### Phase 2: Separate background execution

Move scheduled jobs into a dedicated worker or scheduler deployment instead of relying on API process leadership alone.

### Phase 3: Strengthen readiness signaling

Keep `/health` minimal, but add a true readiness contract that can verify:

- database
- Redis
- scheduler leadership visibility

### Phase 4: Standardize recovery contracts

Only collections with canonical soft-delete semantics should appear in generic recovery tooling, or each should provide an explicit restore contract.

### Phase 5: Expand operational visibility

Expose more system diagnostics such as:

- Redis availability
- build version
- environment fingerprint
- scheduler lock owner details
- index boot status

## Final Summary

The CAPS AI system module is the operational control plane of the platform.

It currently provides:

- runtime startup and shutdown orchestration
- structured logging and request tracing
- configurable response and security middleware
- multi-backend rate limiting
- startup index bootstrapping
- leader-elected recurring scheduler jobs
- admin health diagnostics
- soft-delete recovery workflows

Its strongest qualities are:

- pragmatic resilience
- observable request handling
- singleton-safe scheduler design
- usable recovery tooling

Its main weaknesses are:

- coarse permission semantics
- mixed recovery guarantees
- background work still sharing the web process
- limited operator controls beyond observation and restore

The right next step is not to replace this module. The right next step is to split responsibilities more cleanly and tighten the operational contracts that already exist.


