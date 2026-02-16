# CAPS AI

AI-assisted academic evaluation and plagiarism monitoring system.

## Current Baseline (Week 1 Setup)

- Backend: FastAPI project with modular API routers and health endpoints.
- Frontend: React + Vite app with routing and API connectivity check.
- Database target: MongoDB (via Motor driver in backend core).

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

## Immediate Next Development Targets

1. Implement authentication (JWT login/register and role guards).
2. Add MongoDB CRUD for sections, students, subjects, assignments.
3. Connect submission upload parsing and similarity engine.
4. Build analytics and evaluation workflows end-to-end.

Roadmap reference: `DOC'S/CAPS_AI_Project_Roadmap.md`.
