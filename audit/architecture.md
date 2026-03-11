# CAPS AI Architecture Audit

## Scope and Method
- Audited repository snapshot on 2026-03-11.
- Inspected tracked source/config files (`git ls-files` reported 313 tracked files), plus active documentation files present in workspace.
- Verified key runtime paths with tests/build/static analysis:
  - Backend tests: `85 passed` (`backend`, `pytest -q`)
  - Frontend lint/tests/build: pass (`frontend`, `npm run lint`, `npm run test:ci`, `npm run build`)

## 1. Project Overview
CAPS AI is a full-stack academic platform with:
- FastAPI backend (`backend/app/main.py:30`) exposing versioned REST APIs under `/api/v1` (`backend/app/main.py:148`, `backend/app/core/config.py:54`)
- React + Vite frontend (`frontend/src/main.jsx:10`) with role-based route guards (`frontend/src/routes/ProtectedRoute.jsx:6`)
- MongoDB primary datastore (`backend/app/core/database.py:3`)
- Redis-backed rate limiting/blacklist support (`backend/app/core/redis_store.py:30`, `backend/app/core/security.py:121`)
- Built-in scheduler for AI jobs, notices, and analytics snapshots (`backend/app/services/scheduler.py:31`)

## 2. Architecture Diagram (Text)
```text
[Browser SPA: React/Vite]
  |
  | axios + bearer token + trace headers
  | (frontend/src/services/apiClient.js:78-93)
  v
[FastAPI app]
  - RateLimitMiddleware (backend/app/main.py:32)
  - CORS + Security headers (backend/app/main.py:38,47)
  - Response envelope (backend/app/main.py:110)
  - API router /api/v1 (backend/app/main.py:148)
  |
  v
[Endpoint Layer: backend/app/api/v1/endpoints/*]
  - auth/users/academic/ai/admin domains
  |
  v
[Service Layer (partial)]
  - auth domain service/repository
  - governance, audit, ai runtime/jobs, scheduler
  |
  v
[MongoDB collections + indexes]
  - db.<collection> via Motor
  - startup index ensure (backend/app/core/indexes.py:20)
  |
  +--> [Redis]
       - token blacklist / rate limiting fallback chain
```

## 3. Tech Stack Detection
- Backend: Python, FastAPI, Motor (MongoDB), python-jose JWT, scikit-learn, OpenAI SDK, Redis async client.
  - References: `backend/requirements.txt:1-17`
- Frontend: React 18, Vite 5, React Router 6, Axios, Recharts, Framer Motion.
  - References: `frontend/package.json:15-24`
- Infra: Docker Compose, Kubernetes manifests, GitHub Actions CI.
  - References: `docker-compose.yml:1`, `k8s-backend.yaml:18`, `.github/workflows/ci.yml:1`

## 4. Folder Structure and Responsibilities
- `backend/app/api/v1/endpoints/`: HTTP API handlers and RBAC gates.
- `backend/app/services/`: domain services (governance, audit, AI jobs/runtime, scheduler).
- `backend/app/core/`: app wiring, config, security, middleware, indexes, DB clients.
- `backend/tests/`: backend unit/integration-style API tests.
- `frontend/src/pages/`: route-level screens.
- `frontend/src/services/`: API client + feature-specific API helpers.
- `frontend/src/routes/`: route map and protection.
- `.github/workflows/`: CI pipeline definitions.
- `scripts/`: seeding/migration/safety-check utilities.

## 5. Key Modules and Responsibilities
- Auth/session lifecycle:
  - `backend/app/api/v1/endpoints/auth.py`
  - `backend/app/domains/auth/service.py`
  - `backend/app/domains/auth/repository.py`
- Academic hierarchy and setup:
  - Router mounts: `backend/app/api/v1/router.py:46-53`
  - Canonical sections route uses classes handler: `backend/app/api/v1/router.py:52`
- AI flows:
  - Teacher chat/evaluation orchestration: `backend/app/api/v1/endpoints/ai.py`
  - Submission AI jobs: `backend/app/api/v1/endpoints/submissions.py:224`
  - Similarity pipeline: `backend/app/services/similarity_pipeline.py:69-70`
- Governance and destructive action controls:
  - `backend/app/services/governance.py`
  - Safety contract check script: `scripts/check_backend_safety.py`
- Frontend access policy:
  - Route gate: `frontend/src/routes/ProtectedRoute.jsx:22-30`
  - Feature matrix/nav grouping: `frontend/src/config/featureAccess.js`, `frontend/src/config/navigationGroups.js`

## 6. Execution Flow (Frontend -> Backend -> Database)
1. User action in page component triggers API call through Axios client (`frontend/src/services/apiClient.js:78`).
2. Request interceptor attaches bearer token and trace IDs (`frontend/src/services/apiClient.js:82-91`).
3. FastAPI middlewares execute: rate-limit, CORS/security headers, response envelope (`backend/app/main.py:32-146`).
4. Endpoint validates auth/permissions via `Depends(require_roles|require_permission)` (example: `backend/app/api/v1/endpoints/classes.py:85`, `:133`).
5. Endpoint/service executes Motor queries (`find`, `insert_one`, `update_one`) against MongoDB.
6. Optional background/scheduler processing updates async artifacts (`backend/app/services/scheduler.py:136-143`).
7. Response envelope returned; frontend response interceptor unwraps envelope (`frontend/src/services/apiClient.js:113-115`).

## 7. Entry Points
- Backend runtime entry:
  - `backend/app/main.py:30` (`FastAPI(...)`)
  - Uvicorn command in container: `backend/Dockerfile:15`
- API route root:
  - `backend/app/api/v1/router.py:42-91`
- Frontend runtime entry:
  - `frontend/src/main.jsx:10-20`
- Frontend route entry:
  - `frontend/src/routes/AppRoutes.jsx:152`
- CI entry:
  - `.github/workflows/ci.yml:1`

## 8. Architecture Review

### Strengths
- Clear API versioning (`/api/v1`) and centralized route graph.
- Consistent RBAC helper usage for many endpoints.
- Scheduler has distributed lock logic for multi-replica safety (`backend/app/services/scheduler.py:155-193`).
- Startup index bootstrapping exists (`backend/app/core/indexes.py:20`).

### Architectural Problems
1. Endpoint-heavy monolith: large handlers mix HTTP concerns, domain logic, and persistence.
   - Examples: `backend/app/api/v1/endpoints/analytics.py` (752 lines), `timetables.py` (578), `evaluations.py` (509).
2. Partial layering inconsistency:
   - Auth uses repository/service abstraction, but most modules query `db` directly in endpoints.
3. Legacy naming drift across canonical model:
   - Router canonical path uses `/sections` but handler/module still `classes` (`backend/app/api/v1/router.py:52`).
   - Legacy fields still present in schema (`course_id`, `year_id`, `branch_name` in `backend/app/schemas/class_item.py:39-46`).
4. Documentation/runtime divergence:
   - README and script docs still advertise removed `/courses`, `/years`, `/branches`.
   - `README.md:104`, `scripts/README.md:5-15`, `backend/app/models/README.md:4-6`.

### What Breaks First at 10x Scale
1. In-memory query fanout and high-limit `to_list` paths (memory + latency pressure).
   - `backend/app/services/background_jobs.py:47` (`to_list(length=50000)`)
2. Sequential notification fanout loop (N awaits per user).
   - `backend/app/services/background_jobs.py:67-75`
3. Similarity engine CPU and memory overhead for TF-IDF/cosine on large candidate sets.
   - `backend/app/services/similarity_engine.py:25-29`
4. Large endpoint modules become change bottlenecks (merge/conflict/regression risk).

### Modules That Need Refactoring First
1. `backend/app/api/v1/endpoints/analytics.py`
2. `backend/app/api/v1/endpoints/timetables.py`
3. `backend/app/api/v1/endpoints/evaluations.py`
4. `backend/app/services/background_jobs.py`
5. `backend/app/services/similarity_pipeline.py`
6. Frontend large pages:
   - `frontend/src/pages/ClubsPage.jsx` (946 lines)
   - `frontend/src/components/ui/EntityManager.jsx` (776 lines)
   - `frontend/src/pages/DashboardPage.jsx` (607 lines)

