# Testing Guide

## Overview

This guide defines how CAPS AI is verified today.

The current test strategy has four layers:
1. backend automated tests with `pytest`
2. frontend unit and policy tests with `vitest`
3. static analysis and safety checks for critical backend paths
4. manual end-to-end validation for flows not yet covered by browser automation

Primary CI file:
- [ci.yml](.github/workflows/ci.yml)

This guide is based on the current repo state, not an ideal future pipeline.

## Testing Stack

### Backend

Runtime and tests use:
- Python
- `pytest`
- `httpx` for API/client-style testing where needed

Dependencies:
- [requirements.txt](/backend/requirements.txt)
- [requirements-dev.txt](/backend/requirements-dev.txt)

### Frontend

Runtime and tests use:
- React
- Vite
- `vitest`
- ESLint

Frontend package definition:
- [package.json](/frontend/package.json)

### Static Analysis

Current static analysis tools:
- `flake8`
- `mypy`
- `bandit`
- custom backend safety checker

Safety checker:
- [check_backend_safety.py](scripts/check_backend_safety.py)

## Testing Architecture

```text
Verification Pyramid
|-- Manual Full-Stack Validation
|   `-- login, routing, critical workflows, deployment health
|-- Frontend Automated Validation
|   |-- lint
|   |-- vitest unit/policy tests
|   `-- production build
|-- Backend Automated Validation
|   |-- pytest unit and integration-style tests
|   `-- targeted behavior tests by module
`-- Static Analysis And Safety Gates
    |-- flake8
    |-- mypy
    |-- bandit
    `-- custom AST safety checks
```

## Backend Test Layout

Current test directory:
- `backend/tests`

Current files visible in the repo:
- [conftest.py](/backend/tests/conftest.py)
- [test_auth.py](/backend/tests/test_auth.py)
- [test_health.py](/backend/tests/test_health.py)
- [test_timetables.py](/backend/tests/test_timetables.py)
- [test_academic_permissions.py](/backend/tests/test_academic_permissions.py)
- [test_academic_setup_rules.py](/backend/tests/test_academic_setup_rules.py)
- [test_departments.py](/backend/tests/test_departments.py)
- [test_destructive_action_telemetry.py](/backend/tests/test_destructive_action_telemetry.py)
- [test_soft_delete.py](/backend/tests/test_soft_delete.py)
- [test_main_missing_blocks.py](/backend/tests/test_main_missing_blocks.py)

### Conftest Role

Current `conftest.py` is minimal and mainly ensures backend path insertion for imports.

Implication:
- the suite is relatively lightweight
- there is no large shared fixture orchestration layer yet

## Frontend Test Layout

Current explicit frontend test visibility from recent hardening work includes:
- [permissions.test.js](/frontend/src/utils/permissions.test.js)

This test currently verifies:
- admin subtype access behavior
- teacher extension-role gating
- frontend policy alignment with backend academic setup permissions

Current frontend testing model is still sparse compared with backend behavior coverage.

## CI Architecture

Defined in [ci.yml](.github/workflows/ci.yml).

### Job 1: `backend-static-analysis`

Runs on:
- `ubuntu-latest`
- Python `3.11`

Installs:
- backend runtime requirements
- backend dev/static-analysis requirements

Runs:
- `python -m pip_audit -r backend/requirements.txt --ignore-vuln CVE-2024-23342`
- `flake8`
- `mypy`
- `bandit`
- `python scripts/check_backend_safety.py`

Current CI static-analysis scope:
- `backend/app/services/governance.py`
- `backend/app/api/v1/endpoints/faculties.py`
- `backend/app/api/v1/endpoints/departments.py`
- `backend/app/api/v1/endpoints/programs.py`
- `backend/app/api/v1/endpoints/specializations.py`
- `backend/app/api/v1/endpoints/batches.py`
- `backend/app/api/v1/endpoints/semesters.py`
- `backend/app/api/v1/endpoints/classes.py` (sections)
- `scripts/check_backend_safety.py`

### Job 2: `backend`

Runs:
- `pytest -q --cov=app --cov-report=term-missing --cov-fail-under=55` in `backend`

### Job 3: `frontend`

Runs on Node `20` with npm cache.

Executes:
- `npm ci`
- `npm audit --omit=dev --audit-level=high`
- `npm run lint`
- `npm run test:ci`
- `npm run test:coverage`
- `npm run build`

### Job 4: `backend-perf-smoke`

Runs:
- `python scripts/perf_smoke.py`

Current scope:
- `/health`
- `/api/v1/admin/system/health`
- `/api/v1/auth/login`
- authenticated teacher submission-list smoke path

## Static Analysis And Safety Gates

### Flake8

Purpose:
- style and low-level correctness linting in targeted critical backend files

### Mypy

Purpose:
- catch typed contract drift and some unreachable or incompatible code paths in targeted modules

### Bandit

Purpose:
- security-oriented static scanning on targeted Python files

### Custom Safety Checker

Implementation:
- [check_backend_safety.py](scripts/check_backend_safety.py)

Current checks include:
- obvious unreachable statements after terminal control flow
- required governance delete handlers exist where expected
- protected delete handlers include `review_id`
- protected delete handlers call `enforce_review_approval(...)`

Architectural value:
- this is not generic linting
- it encodes project-specific safety policy for destructive academic actions

## Recommended Local Test Commands

### Full Backend Test Run

```powershell
cd backend
pip install -r requirements.txt
pytest -q
```

### Full Frontend Validation Run

```powershell
cd frontend
npm ci
npm run lint
npm run test:ci
npm run build
```

### Static Analysis Run

From repo root (current CI commands):

```powershell
python -m pip install -r backend/requirements.txt
python -m pip install -r backend/requirements-dev.txt
python -m pip_audit -r backend/requirements.txt --ignore-vuln CVE-2024-23342
python -m flake8 backend/app/services/governance.py backend/app/api/v1/endpoints/faculties.py backend/app/api/v1/endpoints/departments.py backend/app/api/v1/endpoints/programs.py backend/app/api/v1/endpoints/specializations.py backend/app/api/v1/endpoints/batches.py backend/app/api/v1/endpoints/semesters.py backend/app/api/v1/endpoints/classes.py scripts/check_backend_safety.py
python -m mypy --config-file mypy.ini backend/app/services/governance.py backend/app/api/v1/endpoints/faculties.py backend/app/api/v1/endpoints/departments.py backend/app/api/v1/endpoints/programs.py backend/app/api/v1/endpoints/specializations.py backend/app/api/v1/endpoints/batches.py backend/app/api/v1/endpoints/semesters.py backend/app/api/v1/endpoints/classes.py scripts/check_backend_safety.py
python -m bandit -c bandit.yaml backend/app/services/governance.py backend/app/api/v1/endpoints/faculties.py backend/app/api/v1/endpoints/departments.py backend/app/api/v1/endpoints/programs.py backend/app/api/v1/endpoints/specializations.py backend/app/api/v1/endpoints/batches.py backend/app/api/v1/endpoints/semesters.py backend/app/api/v1/endpoints/classes.py scripts/check_backend_safety.py
python scripts/check_backend_safety.py
```

### Full Local Stack Validation

```powershell
docker compose up -d --build
Invoke-WebRequest http://localhost:8000/health
```

Then manually verify:
- login
- one admin route
- one teacher route
- one student route
- one governance-sensitive delete flow if touched

## Targeted Test Selection By Change Type

### If You Change Auth

Run at minimum:
- backend auth tests
- frontend login/session validation manually
- full backend pytest if token or security code changed

Manual checks:
- login
- refresh behavior
- logout
- session expiry behavior
- `/auth/me` validation

### If You Change Academic Setup

Run at minimum:
- [test_academic_permissions.py](/backend/tests/test_academic_permissions.py)
- [test_academic_setup_rules.py](/backend/tests/test_academic_setup_rules.py)
- [test_departments.py](/backend/tests/test_departments.py)
- [test_soft_delete.py](/backend/tests/test_soft_delete.py)
- frontend permission test if UI access changed
- static analysis and safety checker if delete/governance paths changed

Manual checks:
- canonical hierarchy pages load
- edit/create/delete behavior works
- legacy compatibility pages do not regress unexpectedly if still in use

### If You Change Governance Or Destructive Actions

Run at minimum:
- [test_destructive_action_telemetry.py](/backend/tests/test_destructive_action_telemetry.py)
- [test_departments.py](/backend/tests/test_departments.py)
- static analysis suite
- frontend governance prompt flows manually if `EntityManager` or feature access changed

Manual checks:
- missing `review_id` is blocked
- approved review executes correctly
- telemetry and audit write correctly
- UI surfaces governance failure and retry correctly

### If You Change Timetables Or Attendance

Run at minimum:
- [test_timetables.py](/backend/tests/test_timetables.py)
- relevant manual attendance/timetable routes

Manual checks:
- timetable generation
- publish/lock behavior
- teacher or student timetable view
- attendance mark flow if class-slot behavior changed

### If You Change Frontend Route Access Or Policy Logic

Run at minimum:
- [permissions.test.js](/frontend/src/utils/permissions.test.js)
- `npm run lint`
- `npm run build`

Manual checks:
- route redirect behavior
- admin subtype access
- teacher extension-role access
- protected fallback redirect to `/dashboard`

## Current High-Value Test Coverage

### Backend Strengths

The strongest recent backend coverage is in:
- academic setup policy enforcement
- program duration, batch seeding, and semester generation rules
- governance-protected delete behavior
- destructive action telemetry
- soft-delete semantics

### Frontend Strengths

The strongest explicit frontend automated coverage currently visible is:
- policy/access gating logic through `permissions.test.js`

### Operational Strengths

CI already enforces:
- backend test suite
- frontend lint/test/build
- safety-critical static analysis for governance-sensitive files

## Current Gaps In Coverage

### 1. Sparse Frontend Behavioral Tests

There is not yet broad component or page-level frontend test coverage across major workflows.

Examples of missing broad coverage classes:
- login form interactions
- `EntityManager` governance modal flows
- admin workflow pages
- rich pages like `EvaluateSubmission`

### 2. Limited API-Level Integration Breadth

Some backend rule tests are strong, but not every module has API-level integration tests through a full client/request path.

### 3. No Standard Browser E2E Automation

There is currently no standard Playwright or Cypress suite in CI.

Consequence:
- many route wiring and SPA integration regressions still rely on manual verification

### 4. Limited Load And Scale Test Layer

Current pipeline now includes a lightweight backend performance smoke gate, but it still does not cover:
- concurrency tests
- sustained load tests
- scheduler behavior under scale
- high-volume analytics behavior

### 5. Narrow Static Analysis Scope

The strongest static analysis only covers selected safety-critical files, not the entire backend tree.

This is pragmatic, but it means many modules remain outside strict CI static guarantees.

## Recommended Manual Validation Matrix

For release-grade confidence, run these after automated tests:

### Core User Journeys

- admin login and dashboard
- teacher login and at least one workflow page
- student login and at least one read-only academic page

### Academic Flows

- create or update one canonical academic entity
- load academic structure page
- validate at least one lower-hierarchy page such as programs or sections

### Assessment Flows

- create assignment
- upload submission or verify existing submission rendering
- open evaluation console

### Governance Flows

- attempt protected delete without `review_id`
- retry with approved review if applicable

### Operational Checks

- `/health`
- one admin analytics or system page
- one notification or communication path if affected by change

## Testing Philosophy For This Repo

The repo is currently best served by a pragmatic verification model:
- strong targeted backend tests on safety-critical rules
- lightweight frontend automated policy checks
- production-build validation for frontend
- CI safety gates for destructive paths
- manual workflow testing for complex browser and cross-module flows

This is not yet a full pyramid with heavy E2E coverage. It is a controlled hybrid that prioritizes correctness in governance and academic integrity paths first.

## Recommended Next Improvements

1. add browser E2E coverage for login, academic setup, and governance delete retry flows
2. add component or page tests for `EntityManager`
3. widen static analysis coverage to more backend modules once current lint debt is reduced
4. add API-level integration coverage for modules still validated mostly by direct function tests
5. expand perf smoke toward concurrent and queue-aware checks, then tie release decisions to `release-governance.md`


