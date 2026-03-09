# Backend Architecture Guide

## Overview

The backend is a FastAPI application backed by MongoDB and optional Redis, with business logic split across route modules, core runtime utilities, service helpers, and a limited but growing domain layer.

Primary backend entry points:
- [main.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\main.py)
- [router.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\router.py)
- [config.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\config.py)
- [database.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\database.py)

Core architectural characteristics:
- async HTTP service via FastAPI
- MongoDB as primary operational datastore
- Redis-backed or Mongo/local fallback rate limiting
- route-first modular organization
- cross-cutting governance, audit, AI, scheduler, and analytics services
- canonical and legacy academic models coexisting in the same runtime

## Top-Level Backend Tree

```text
backend/
|-- Dockerfile
|-- requirements.txt
|-- requirements-dev.txt
`-- app/
    |-- main.py
    |-- api/
    |   `-- v1/
    |       |-- router.py
    |       `-- endpoints/
    |-- core/
    |-- domains/
    |-- models/
    |-- schemas/
    |-- services/
    `-- utils/
```

## Runtime Bootstrap Flow

Application bootstrap happens in [main.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\main.py).

Startup sequence:
1. load settings and configure logging
2. create FastAPI app
3. install middleware stack
4. include API router under `settings.api_prefix`
5. on startup:
   - ensure Mongo indexes
   - start scheduler
6. on shutdown:
   - stop scheduler

Public runtime routes:
- `GET /health`
- `GET /`

Purpose:
- health and smoke validation outside versioned API namespace

## Main Package Responsibilities

### `app/api`

Role:
- HTTP interface
- route registration
- request parsing
- route-level dependencies and permissions
- response model binding

Key files:
- [router.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\router.py)
- `backend/app/api/v1/endpoints/*.py`

The endpoint layer is currently the dominant orchestration layer for business actions.

### `app/core`

Role:
- foundational runtime infrastructure
- shared security and observability behavior
- low-level helpers used by endpoint and service layers

Important files:
- [config.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\config.py)
- [database.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\database.py)
- [security.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\security.py)
- [permission_registry.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\permission_registry.py)
- [rate_limit.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\rate_limit.py)
- [observability.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\observability.py)
- [indexes.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\indexes.py)
- [response.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\response.py)
- [soft_delete.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\soft_delete.py)

### `app/services`

Role:
- cross-module business workflows
- reusable operational logic
- AI, analytics, scheduler, grading, notifications, and governance helpers

Important files:
- [ai_chat_service.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_chat_service.py)
- [ai_evaluation.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_evaluation.py)
- [analytics_snapshot.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\analytics_snapshot.py)
- [audit.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\audit.py)
- [background_jobs.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\background_jobs.py)
- [cloudinary_uploads.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\cloudinary_uploads.py)
- [evaluation_ai_module.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\evaluation_ai_module.py)
- [file_parser.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\file_parser.py)
- [governance.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\governance.py)
- [grading.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\grading.py)
- [notifications.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\notifications.py)
- [pdf_report.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\pdf_report.py)
- [scheduler.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\scheduler.py)
- [similarity_engine.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\similarity_engine.py)

### `app/domains`

Role:
- partial domain-layer abstraction where the codebase has started moving logic out of route modules

Current active domain subpackages:
- `academic`
- `auth`

Current state:
- domain abstraction exists, but the majority of modules still orchestrate directly inside endpoint files

### `app/models`

Role:
- public field shaping and model exposure helpers for selected collections

### `app/schemas`

Role:
- request validation
- response typing
- contract boundaries for HTTP payloads

## API Route Architecture

The full route graph is centralized in [router.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\router.py).

### Route Families

Identity and governance:
- auth
- users
- audit logs
- review tickets
- admin governance
- admin recovery
- admin system

Academic core:
- faculties
- departments
- programs
- specializations
- batches
- semesters
- sections
- students
- groups
- subjects
- course offerings
- class slots
- attendance records
- enrollments

Legacy academic compatibility:
- courses
- branches
- years
- classes

Assessment and AI:
- assignments
- submissions
- evaluations
- similarity
- ai

Communication and engagement:
- notices
- notifications
- clubs
- club events
- event registrations

Analytics:
- analytics
- admin analytics
- admin communication preview

### Canonical Academic Model At Route Level

The backend now explicitly documents the canonical academic hierarchy in [router.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\router.py):

```text
Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section
```

Legacy compatibility routes remain mounted and some are marked deprecated in OpenAPI:
- `/courses`
- `/branches`
- `/years`
- `/classes`

Canonical replacement:
- `/sections`

## Middleware Architecture

Installed middleware in [main.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\main.py):

### 1. RateLimitMiddleware

Implementation:
- [rate_limit.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\rate_limit.py)

Behavior:
- rate limits mutating routes and auth endpoints
- keying uses user id when token is available, otherwise IP + user-agent
- prefers Redis
- falls back to Mongo counters
- in development may fall back to in-memory
- in production or staging, fails closed with `503` if distributed limiter backends are unavailable

Architectural implication:
- this is a safety-first rate limiter for production
- local fallback exists only to avoid blocking development when Redis is down

### 2. CORS Middleware

Behavior:
- allow configured origins
- always preserve common local frontend origins
- allows credentials and all methods/headers

### 3. SecurityHeadersMiddleware

Adds:
- request id and trace id headers
- response time header
- `X-Content-Type-Options`
- `X-Frame-Options`
- `Strict-Transport-Security`
- `Referrer-Policy`
- `Cross-Origin-Opener-Policy`
- `Permissions-Policy`

Also logs request start and request end events.

### 4. ResponseEnvelopeMiddleware

Purpose:
- optionally wraps JSON responses in a standardized envelope

Behavior:
- skips non-API routes and error responses
- skips root and health routes
- preserves already-enveloped payloads

## Error Handling Architecture

Global exception handlers in [main.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\main.py):
- `HTTPException`
- `RequestValidationError`
- catch-all `Exception`

All handlers:
- generate an `error_id`
- log structured context with request and trace ids
- return normalized error envelopes

This gives the backend a centralized operational error model even though business logic is distributed across many endpoint modules.

## Configuration Architecture

Configuration is centralized in [config.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\config.py) using a dataclass-backed settings object.

### Major Configuration Areas

Application:
- environment
- app name and version
- API prefix

Database and cache:
- Mongo URL and DB name
- Redis enabled and URL

Auth and security:
- JWT secret and algorithm
- access and refresh expiry
- account lockout settings
- auth registration policy

AI and analysis:
- OpenAI key and model
- AI timeout and output token settings
- similarity threshold

Operational controls:
- rate limit window and max requests
- response envelope enabled
- scheduler enabled
- scheduler lock timings
- analytics cache TTL
- scheduled notice poll interval
- snapshot schedule

Media and upload integrations:
- Cloudinary config
- CORS origin set

### Configuration Strengths

- one central source of environment-backed config
- explicit coercion helpers for bool, int, and float
- non-development startup guard for default JWT secret
- local CORS defaults avoid common dev lockouts

## Security Architecture

Primary security implementation:
- [security.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\security.py)

### Authentication Model

Uses:
- OAuth2 bearer token dependency for FastAPI
- PBKDF2 SHA-256 password hashing
- JWT access and refresh tokens
- blacklist checking for revoked tokens

Token payload includes:
- subject user id
- email
- role
- admin subtype
- extended roles
- token type
- expiry
- JTI

### Authorization Model

Backend authorization uses several levels:

1. base-role checks
2. teacher extension-role checks
3. permission-registry checks
4. row-level ownership or scope logic inside endpoint modules

Key helpers:
- `get_current_user`
- `require_roles`
- `require_teacher_extensions`
- `require_admin_or_teacher_extensions`
- `has_permission`
- `require_permission`

Architectural implication:
- permission registry gives a central policy layer
- row-level scope still lives mostly in endpoint code, not a unified policy engine

## Data Access Architecture

### MongoDB Binding

Database binding is intentionally thin:
- [database.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\database.py)

Current model:
- singleton Motor client
- direct collection access through `db.<collection>`

### Mongo Helpers

Additional helper:
- [mongo.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\mongo.py)

Used for:
- object id parsing and query safety helpers

### Index Management

Startup index bootstrap:
- [indexes.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\indexes.py)

Purpose:
- enforce required indexes at startup
- support performance-sensitive query paths
- protect newer soft-delete and governance-related lookup patterns

## Domain And Business Logic Placement

The codebase currently uses three business logic placement styles.

### Style 1: Route-Heavy Modules

Many modules still implement:
- validation
- collection reads and writes
- workflow branching
- audit calls

all inside endpoint files.

Examples:
- departments
- classes/sections
- evaluations
- timetables
- clubs

### Style 2: Shared Cross-Cutting Services

Used when logic spans multiple modules or is operationally central.

Examples:
- audit
- governance
- grading
- scheduler
- analytics snapshot
- AI helpers

### Style 3: Domain-Layer Extraction

Used in limited areas where the codebase has started to separate repository and service concerns.

Examples:
- auth domain
- academic domain

Current conclusion:
- the backend is not fully layered in a strict DDD sense
- it is a pragmatic hybrid, with service extraction where needed and direct endpoint orchestration elsewhere

## Observability Architecture

Primary file:
- [observability.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\observability.py)

Current design:
- JSON log formatter
- request and trace ids via `contextvars`
- structured logs with event payloads
- error ids for exception flows

Operational benefit:
- logs are machine-readable
- request correlation works across middleware and exception handling

Current limitation:
- this is logging and header correlation, not full distributed tracing infrastructure

## Governance And Audit Architecture

Primary files:
- [governance.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\governance.py)
- [audit.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\audit.py)

### Governance

Current behavior:
- stores governance policy in `settings`
- stores admin action reviews in `admin_action_reviews`
- enforces review approval for protected actions
- marks approved reviews as executed
- emits destructive action telemetry on block and completion

### Audit

Current behavior:
- stores mutable audit logs in `audit_logs`
- stores immutable chained logs in `audit_logs_immutable`
- writes destructive action telemetry through the audit layer

Architectural significance:
- governance and audit are not side features; they are integrated backend control planes

## Scheduler And Background Processing Architecture

Primary file:
- [scheduler.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\scheduler.py)

### Current Design

- optional runtime component enabled by config
- leader election through Mongo lock document
- only leader starts job loops
- scheduled notice dispatch loop
- daily analytics snapshot loop

Benefits:
- avoids duplicate background execution in multi-instance environments when leadership lock behaves correctly

Operational caution:
- leader election correctness depends on datastore availability and deployment behavior
- scheduler still lives inside app process, not a dedicated worker deployment

## File And Upload Architecture

Current upload/storage behavior is mixed.

Local disk paths still exist for:
- profile avatars
- branding logo
- submission and registration related file flows in parts of the codebase

Cloudinary integration helpers also exist:
- [cloudinary_uploads.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\cloudinary_uploads.py)

Architectural implication:
- file handling is not yet fully normalized around one durable storage strategy

## AI And Analysis Architecture

AI-related service files:
- [ai_evaluation.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_evaluation.py)
- [evaluation_ai_module.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\evaluation_ai_module.py)
- [ai_chat_service.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\ai_chat_service.py)
- [similarity_engine.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\similarity_engine.py)

Current reality:
- AI is not isolated behind one internal gateway
- some AI and similarity flows still run close to request time
- traces and logs exist, but execution cost still affects API behavior

## Deployment Shape

Current repo deployment targets:
- Docker Compose for local stack
- Kubernetes manifests for cluster deployment

Backend container source:
- [Dockerfile](d:\VS CODE\MY PROJECT\CAPS_AI\backend\Dockerfile)

Relevant runtime manifests:
- [docker-compose.yml](d:\VS CODE\MY PROJECT\CAPS_AI\docker-compose.yml)
- [k8s-backend.yaml](d:\VS CODE\MY PROJECT\CAPS_AI\k8s-backend.yaml)
- [k8s-configmap.yaml](d:\VS CODE\MY PROJECT\CAPS_AI\k8s-configmap.yaml)
- [k8s-secrets.yaml](d:\VS CODE\MY PROJECT\CAPS_AI\k8s-secrets.yaml)

## Testing And Static Analysis Architecture

Backend runtime verification in CI currently includes:
- `pytest`
- `flake8`
- `mypy`
- `bandit`
- custom backend safety checks

Key files:
- [ci.yml](d:\VS CODE\MY PROJECT\CAPS_AI\.github\workflows\ci.yml)
- [requirements-dev.txt](d:\VS CODE\MY PROJECT\CAPS_AI\backend\requirements-dev.txt)
- [check_backend_safety.py](d:\VS CODE\MY PROJECT\CAPS_AI\scripts\check_backend_safety.py)

Current CI emphasis:
- strongest static analysis coverage is on governance-sensitive and academic-setup-sensitive modules
- not every backend module is under strict typed/static analysis coverage yet

## Strengths Of The Current Backend Architecture

1. Clear FastAPI runtime entry point.
2. Centralized middleware, tracing, and error handling.
3. Strong recent progress on governance, soft delete, and audit semantics.
4. Canonical academic hierarchy is now explicitly documented at router level.
5. Scheduler leadership model is more production-aware than naive per-instance startup jobs.
6. Config is centralized and reasonably defensive.

## Main Structural Weaknesses

1. Hybrid layering is uneven.
   - some modules are service-backed
   - many still keep orchestration directly inside endpoint files

2. Legacy and canonical academic models still coexist.

3. File storage strategy is mixed and not fully durable.

4. Some expensive AI and similarity workloads still run too close to request path.

5. Authorization semantics are improved but not fully normalized across all modules.

6. Delete semantics differ across modules.
   - some are hard delete
   - some are soft delete/archive
   - some are governance-gated

## Recommended Reading Order For Engineers

1. [main.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\main.py)
2. [config.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\config.py)
3. [router.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\router.py)
4. [security.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\security.py)
5. [permission_registry.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\permission_registry.py)
6. [governance.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\governance.py)
7. [audit.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\audit.py)
8. [scheduler.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\scheduler.py)
9. domain modules and route modules for the business area you are touching

## Architecture Summary

The backend is best understood as a pragmatic modular FastAPI monolith.

It is not a pure layered architecture and not a microservice system. It is a single deployable backend with:
- centralized runtime controls
- modular route families
- shared cross-cutting services
- growing domain abstraction in selected areas
- a substantial amount of workflow logic still living in endpoint files

That architecture is workable for the current system size. The next engineering gains come from targeted normalization, not from splitting the backend by default.
