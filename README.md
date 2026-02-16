# CAPS AI

AI-assisted academic evaluation and plagiarism monitoring system.

## Current Baseline

- Week 1: Project setup (FastAPI + React + MongoDB)
- Week 2: Authentication and role-based route protection
- Week 3: Academic structure management (Sections, Subjects, Section-Subjects)

## Project Structure

- `backend/` FastAPI app, services, schemas, tests, and Python dependencies.
- `frontend/` React app scaffold, routes, styles, and API client.
- `docs/` Documentation files.
- `scripts/` Helper scripts.

## Prerequisites

- Python 3.11+ (recommended)
- Node.js 20+ and npm
- MongoDB local instance on `mongodb://localhost:27017`

## Backend Setup

```bash
cd backend
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:

- API: `http://localhost:8000`
- Docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Frontend Setup

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Frontend URL:

- App: `http://localhost:5173`

## Run Tests

```bash
cd backend
pytest -q
```

## Auth Endpoints

- `POST /api/v1/auth/register` Register user (`admin`, `teacher`, or `student`).
- `POST /api/v1/auth/login` Authenticate and receive JWT bearer token.
- `GET /api/v1/auth/me` Get current authenticated user profile.
- `GET /api/v1/users/` Admin-only user listing.

## Academic Structure Endpoints (Week 3)

- Sections: `GET/POST /api/v1/sections`, `GET/PUT/DELETE /api/v1/sections/{section_id}`
- Section-Subjects: `GET/POST /api/v1/section-subjects`, `GET/PUT/DELETE /api/v1/section-subjects/{mapping_id}`
- Subjects: `GET/POST /api/v1/subjects`, `GET/PUT/DELETE /api/v1/subjects/{subject_id}`

## Protected CRUD List Query Params

- `GET /api/v1/sections/`: `q`, `academic_year`, `semester`, `is_active`, `skip`, `limit`
- `GET /api/v1/section-subjects/`: `section_id`, `subject_id`, `teacher_user_id`, `is_active`, `skip`, `limit`
- `GET /api/v1/students/`: `q`, `section_id`, `is_active`, `skip`, `limit`
- `GET /api/v1/subjects/`: `q`, `is_active`, `skip`, `limit`
- `GET /api/v1/assignments/`: `q`, `subject_id`, `section_id`, `created_by`, `skip`, `limit`

Roadmap reference: `DOC'S/CAPS_AI_Project_Roadmap.md`.
