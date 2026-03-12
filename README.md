# CAPS AI

Academic governance and AI-assisted evaluation platform built with FastAPI, React, and MongoDB.

## Status

Roadmap status:
- Phase 0: completed
- Phase 1: mostly completed
- Phase 2: completed
- Phase 3: in progress

Primary planning and audit references:
- [audit/roadmap.md](./audit/roadmap.md)
- [docs/README.md](./docs/README.md)
- [audits/AI_MODULE_AUDIT.md](./audits/AI_MODULE_AUDIT.md)

## Repository Structure

- `backend/`: FastAPI app, API endpoints, services, models, schemas, tests
- `frontend/`: React + Vite dashboard
- `docs/`: tracked project documentation, module masters, guides, audit notes
- `audit/`: repository-wide audit reports and roadmap
- `audits/`: focused module audit reports
- `scripts/`: local setup, seeding, migration, and safety utilities
- `uploads/`: local runtime upload storage

## Prerequisites

- Python 3.11+
- Node.js 20+
- MongoDB on `mongodb://localhost:27017`
- Docker Desktop for containerized local runs

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:

```bash
cd frontend
npm install
copy .env.example .env
npm run dev -- --host 0.0.0.0 --port 5173
```

Local URLs:
- API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Frontend: `http://localhost:5173`

## Docker

```bash
docker compose up -d --build
docker compose ps
```

Stop:

```bash
docker compose down
```

## Quality Checks

Backend:

```bash
cd backend
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m flake8 app tests
python ..\scripts\check_backend_safety.py
```

Frontend:

```bash
cd frontend
npm run lint
npm run test:ci
npm run build
```

## Runtime API Domains

All primary APIs are mounted under `/api/v1`.

- auth and identity: `/auth`, `/users`
- academic setup: `/faculties`, `/departments`, `/programs`, `/specializations`, `/batches`, `/semesters`, `/sections`
- academics: `/students`, `/groups`, `/subjects`, `/course-offerings`, `/class-slots`, `/attendance-records`, `/enrollments`
- assessment and AI: `/assignments`, `/submissions`, `/evaluations`, `/similarity`, `/ai`
- scheduling: `/timetables`
- communication: `/notices`, `/notifications`
- clubs and events: `/clubs`, `/club-events`, `/event-registrations`
- governance and audit: `/review-tickets`, `/audit-logs`
- admin domains: `/admin/system`, `/admin/analytics`, `/admin/communication`, `/admin/governance`, `/admin/recovery`

Compatibility notes:
- `/sections` is the canonical public route for section management.
- The underlying legacy storage artifact is still the `classes` collection and `backend/app/models/classes.py`.
- Removed public endpoints such as `/courses`, `/years`, and `/branches` are documentation-only legacy references now.

## Documentation

Start here:
- [docs/README.md](./docs/README.md)
- [docs/guides/module-index.md](./docs/guides/module-index.md)
- [docs/DOCUMENTATION_AUDIT_REPORT.md](./docs/DOCUMENTATION_AUDIT_REPORT.md)

## Kubernetes

Base manifests are kept in the repository root:
- `k8s-namespace.yaml`
- `k8s-mongodb.yaml`
- `k8s-redis.yaml`
- `k8s-backend.yaml`
- `k8s-frontend.yaml`
- `k8s-ingress.yaml`
- `k8s-configmap.yaml`
- `k8s-secrets.yaml`
- `k8s-uploads-pvc.yaml`
