# CAPS AI

Enterprise academic governance and AI-assisted evaluation platform.

Master plan reference:
- `DOC'S/CAPS_AI_ULTRA_PRO_MASTER_ROADMAP.md`

## Current Implementation Status

Completed backend phases (roadmap-aligned):
- Phase 1: Foundation setup, auth, RBAC, health APIs
- Phase 2: Academic core CRUD, role extensions, enrollment mapping
- Phase 3: Assignments, submissions, evaluation lock workflow
- Phase 4: AI suggestion pipeline and similarity engine
- Phase 5: Analytics, notices, clubs/events, registration constraints
- Phase 6 (in progress): hardening and release readiness

## Project Structure

- `backend/` FastAPI services, endpoints, schemas, models, tests
- `frontend/` React (Vite) SaaS dashboard frontend
- `DOC'S/` authoritative roadmap and planning documents
- `docs/` supplementary notes

## Prerequisites

- Python 3.11+
- Node.js 20+
- MongoDB on `mongodb://localhost:27017`

## Backend Run

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:
- API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Frontend Run

```bash
cd frontend
npm install
copy .env.example .env
npm run dev -- --host 0.0.0.0 --port 5173
```

Frontend URL:
- App: `http://localhost:5173`

## Test Commands

Use project virtualenv Python to avoid global-package conflicts:

```bash
cd backend
.venv\Scripts\python.exe -m pytest -q
```

## Core API Domains

- Auth and users: `/api/v1/auth`, `/api/v1/users`
- Academic structure: `/courses`, `/years`, `/classes`, `/students`, `/subjects`
- Academic operations: `/assignments`, `/submissions`, `/evaluations`
- Intelligence: `/similarity`, AI submission evaluation via `/submissions/{id}/ai-evaluate`
- Institutional modules: `/analytics`, `/notices`, `/notifications`, `/clubs`, `/club-events`, `/event-registrations`
- Governance: `/audit-logs`, `/enrollments`

## Security Baseline

- JWT auth with role and extension-role checks
- PBKDF2-SHA256 password hashing
- File type and upload size validation
- CORS-configured local origins
- Security response headers (`X-Content-Type-Options`, `X-Frame-Options`, etc.)
