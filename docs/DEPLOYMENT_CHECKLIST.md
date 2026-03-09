# CAPS AI Deployment Checklist

## 1. Environment

- Set backend `.env` values:
  - `MONGODB_URL`
  - `MONGODB_DB`
  - `JWT_SECRET` (non-default)
  - `ACCESS_TOKEN_EXPIRE_MINUTES`
  - `OPENAI_API_KEY` (if AI provider enabled)
  - `CORS_ORIGINS` (production frontend origins)

## 2. Backend Validation

- Install dependencies in virtualenv.
- Run tests:
  - `.venv\Scripts\python.exe -m pytest -q`
- Verify startup:
  - `GET /health` returns `{"status":"ok"}`
- Verify docs:
  - `/docs` loads.

## 3. Frontend Validation

- Set `VITE_API_BASE_URL` to deployed backend URL.
- Run production build:
  - `npm run build`
- Smoke test login and dashboard routes.

## 4. Security Checks

- Confirm strong JWT secret is configured.
- Confirm CORS allows only intended origins.
- Confirm security response headers exist on API responses.
- Confirm role-based access checks with admin/teacher/student test users.

## 5. Operational Smoke Tests

- Auth bootstrap flow:
  - Register first admin (bootstrap only) -> login -> me
- Auth provisioning flow (required after bootstrap):
  - Login as admin -> create teacher/student via `/api/v1/users` -> login as created user -> me
- Auth closure validation:
  - Attempt `/api/v1/auth/register` for any role after first admin exists -> expect `403`
- Assignment lifecycle: create/open/close
- Submission upload and AI evaluate
- Similarity run and flagged notification path
- Evaluation finalize and admin override path
- Notice publishing and expiry behavior
- Club event registration duplicate/capacity rules

## 6. Release Notes

- Record commit hash for deployed version.
- Record DB backup/snapshot reference.
- Record known warnings and mitigations.

## 7. Docker Release Checklist

- Confirm Docker Desktop is running.
- Rebuild and start stack:
  - `docker compose up -d --build`
- Verify containers:
  - `docker compose ps`
- Verify backend health:
  - `GET http://localhost:8000/health`
- Verify frontend:
  - `http://localhost:5173`
