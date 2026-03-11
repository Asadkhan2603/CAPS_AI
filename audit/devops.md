# CAPS AI DevOps / Infrastructure Audit

## 1. Environment Configuration Review

### Observed
- Backend settings are environment-driven (`backend/app/core/config.py:50-137`).
- Production guard exists for JWT secret default:
  - `backend/app/core/config.py:142-143`
- K8s config sets `AUTH_REGISTRATION_POLICY=bootstrap_strict` (`k8s-configmap.yaml:19`), which is safer than code default.

### Risks
- Defaults in code are permissive for development (`JWT_SECRET=change_me`, open registration mode).
- Placeholder secret values in manifests:
  - `k8s-secrets.yaml:8`

### Recommendation
- Add startup fatal checks for production to reject placeholder secrets and unsafe policy combinations.

## 2. Docker / Deployment Config Review

### Observed
- Compose stack includes MongoDB + Redis + backend + frontend (`docker-compose.yml:1-47`).
- Backend container uses Python 3.13 (`backend/Dockerfile:1`), CI uses Python 3.11 (`.github/workflows/ci.yml:20,89`).
- K8s manifests use local `:latest` image tags:
  - `k8s-backend.yaml:40`
  - `k8s-frontend.yaml:40`

### Risks
- Runtime skew between CI and container can hide version-specific defects.
- `latest` tags reduce deployment reproducibility and rollback safety.

### Recommendation
- Align CI/runtime Python version.
- Use immutable image tags (git SHA/semver) and promote through environments.

## 3. CI/CD Pipeline Review

### Observed
- CI jobs: static analysis, backend tests, frontend checks (`.github/workflows/ci.yml`).
- Safety script is integrated (`.github/workflows/ci.yml:71`).

### Gaps
- Full backend flake8 is not enforced in CI; safety-critical subset only.
- Dependency vulnerability scanning not included in CI gate.
- No coverage threshold enforcement.

### Recommendation
1. Add `pip_audit` and `npm audit --omit=dev` (or equivalent SCA) as policy gate.
2. Add coverage generation + minimum threshold gate.
3. Expand lint/static checks across full backend package.

## 4. Logging / Monitoring Review

### Observed
- Structured JSON logs with request/trace IDs:
  - `backend/app/core/observability.py:21-49`
- Request lifecycle logging in middleware:
  - `backend/app/main.py:54-101`
- Scheduler logs leadership and job loops:
  - `backend/app/services/scheduler.py:54-66,116-132`

### Gaps
- No explicit external observability integration (metrics/traces export) in repo.
- No centralized alerting rules for scheduler failures, queue lag, or AI job error rates.

## 5. Production Readiness Verdict
**Not fully production-ready yet.**

Reasons:
1. Vulnerable dependency versions currently present (backend and frontend).
2. Deployment reproducibility/hardening gaps (`latest` image tags, runtime version skew).
3. Missing CI gates for dependency risk and coverage quality.
4. Performance hotspots likely to degrade at higher scale.

## 6. Missing for Deployment Maturity
1. Immutable image tagging and release promotion strategy.
2. Dependency vulnerability gate + remediation SLA policy.
3. Coverage-based quality gates.
4. Runtime dashboards/alerts for API latency, Mongo pressure, scheduler/AI queue health.
5. Formal secrets management workflow (rotation and non-placeholder enforcement).

## 7. Documentation Audit

### Findings
- Root docs are stale relative to runtime route graph:
  - `README.md:104` still lists `/courses`, `/years`.
  - `scripts/README.md:5-15` still uses legacy course/year/branch terms.
  - `backend/app/models/README.md:4-6` lists legacy collections.
- Frontend README is outdated for auth storage behavior:
  - says local storage at `frontend/README.md:21`, but code uses session storage (`frontend/src/services/apiClient.js:9-13`).
- Entire `docs/` tree is ignored by git:
  - `.gitignore:65`

### Recommendation
- Update docs to canonical hierarchy and current auth/runtime behavior.
- Stop ignoring `docs/` if documentation is intended to be versioned.

## 8. Database Review

### Schema Design
- MongoDB document model with many string foreign-key references (manual referential integrity).
  - Example relations in schemas:
    - `backend/app/schemas/class_item.py:7-13`
    - `backend/app/schemas/submission.py:8-9`
    - `backend/app/schemas/evaluation.py:20,65-67`

### Indexing
- Extensive index bootstrap exists (`backend/app/core/indexes.py:20-112`), including TTL for token blacklist (`:48-49`) and composite operational indexes.

### Issues
1. No migration/versioning framework; schema evolution is script/manual-driven.
2. Legacy collections still indexed (`db.courses`, `db.branches`, `db.years` at `backend/app/core/indexes.py:78-80`) despite canonical move.
3. Heavy join-like query patterns in app layer suggest denormalization/read-model opportunities.

### Recommendation
- Introduce migration/version metadata for collection shape changes.
- Retire legacy indexes/collections where decommissioned.
- Add query profiling and index utilization checks in release checklist.

