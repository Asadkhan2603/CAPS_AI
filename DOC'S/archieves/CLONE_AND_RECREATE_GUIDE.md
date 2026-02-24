# CAPS AI - Full Clone and Recreate Guide

## 1. Purpose
This document is a complete technical handoff for anyone who wants to clone this repository and recreate the project from scratch.

It covers:
- How to run backend and frontend locally
- Exact environment variables
- Architecture and module boundaries
- Role-based access model (Admin/Teacher/Student + extensions)
- API surface used by the frontend
- MongoDB data model/collections
- Validation, testing, and troubleshooting
- How to rebuild this project if source structure changes

---

## 2. What This Project Is
`CAPS AI` is an academic operations platform with:
- User authentication and role-based access
- Academic structure management (course/department/branch/year/section)
- Assignment/submission/evaluation workflows
- Similarity/plagiarism analysis support
- AI-assisted submission evaluation workflows
- Institutional communication (notices/notifications)
- Clubs, events, and registrations
- Auditing and governance screens

Primary layers:
- Backend: FastAPI + MongoDB
- Frontend: React (Vite) + Tailwind

---

## 3. Repository Layout
Root folders:
- `backend/` - FastAPI application, schemas, endpoints, tests
- `frontend/` - React dashboard app
- `DOC'S/` - architecture and handoff docs
- `docs/` - supplementary docs

Important backend paths:
- `backend/app/main.py` - app bootstrap, middleware, exception handlers
- `backend/app/api/v1/router.py` - API route registration
- `backend/app/api/v1/endpoints/` - domain endpoints
- `backend/app/core/config.py` - settings and env parsing
- `backend/app/core/security.py` - JWT and password hashing
- `backend/app/core/database.py` - Mongo client
- `backend/app/schemas/` - pydantic request/response contracts
- `backend/app/models/` - document mappers/normalizers
- `backend/tests/` - pytest tests

Important frontend paths:
- `frontend/src/main.jsx` - app bootstrap/provider stack
- `frontend/src/routes/AppRoutes.jsx` - route map
- `frontend/src/routes/ProtectedRoute.jsx` - route guard
- `frontend/src/config/featureAccess.js` - frontend feature ACL
- `frontend/src/context/AuthContext.jsx` - login/session state
- `frontend/src/services/apiClient.js` - axios client/interceptors
- `frontend/src/services/sectionsApi.js` - sections service adapter
- `frontend/src/components/layout/` - shell (sidebar/topbar/layout)
- `frontend/src/pages/` - page modules

---

## 4. Runtime Stack
Backend:
- Python 3.11+
- FastAPI 0.128.x
- Uvicorn 0.35.x
- Motor (MongoDB async driver)
- Pydantic v2
- JOSE JWT
- OpenAI SDK (AI evaluation flows)

Frontend:
- Node.js 20+
- React 18.3.x
- React Router 6.27.x
- Vite 5.4.x
- Tailwind CSS 3.4.x
- Axios
- Recharts
- Framer Motion
- Lucide React

Database:
- MongoDB running locally (default `mongodb://localhost:27017`)

---

## 5. Clone and First-Time Setup
### 5.1 Clone
```bash
git clone <your-repo-url>
cd CAPS_AI
```

### 5.2 Backend Setup
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Then start backend:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5.3 Frontend Setup
Open a second terminal:
```bash
cd frontend
npm install
copy .env.example .env
npm run dev -- --host 0.0.0.0 --port 5173
```

App URLs:
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Backend docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

---

## 6. Environment Variables

## 6.1 Backend (`backend/.env`)
Reference (`backend/.env.example`):
```env
ENVIRONMENT=development
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=caps_ai
JWT_SECRET=replace_with_a_long_random_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=20
OPENAI_MAX_OUTPUT_TOKENS=400
SIMILARITY_THRESHOLD=0.8
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://192.168.2.70:5173
```

Notes:
- `JWT_SECRET` must be strong and private.
- `OPENAI_API_KEY` is required for AI evaluation features.
- In non-dev environment, default `JWT_SECRET=change_me` is blocked by config.

## 6.2 Frontend (`frontend/.env`)
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Fallback in code (`frontend/src/services/apiClient.js`) uses the same local URL.

---

## 7. Backend Architecture

## 7.1 App Bootstrap and Middleware
`backend/app/main.py`:
- Registers CORS middleware with configured origins
- Adds security/observability middleware:
  - `X-Request-Id`
  - `X-Trace-Id`
  - `X-Response-Time-Ms`
  - `X-Content-Type-Options`
  - `X-Frame-Options`
  - `Referrer-Policy`
  - `Permissions-Policy`
- Registers centralized handlers for:
  - `HTTPException`
  - `RequestValidationError`
  - unhandled `Exception`

All errors include `error_id` + `X-Error-Id` for traceability.

## 7.2 Auth and Security
`backend/app/core/security.py`:
- Password hashing: PBKDF2-SHA256
- Token: JWT with claims `sub`, `email`, `role`, `extended_roles`, `exp`
- Role enforcement helpers:
  - `require_roles([...])`
  - `require_teacher_extensions([...])`
  - `require_admin_or_teacher_extensions([...])`

Important auth behavior:
- First admin registration is allowed, additional admin self-registration is blocked.
- Access token is bearer type.

## 7.3 API Router Map
`backend/app/api/v1/router.py` exposes:
- `/auth`
- `/users`
- `/courses`
- `/departments`
- `/branches`
- `/years`
- `/sections`
- `/classes` (legacy compatibility alias; use `/sections` for new code)
- `/students`
- `/subjects`
- `/assignments`
- `/submissions`
- `/ai`
- `/evaluations`
- `/similarity`
- `/analytics`
- `/branding`
- `/notices`
- `/notifications`
- `/review-tickets`
- `/audit-logs`
- `/enrollments`
- `/clubs`
- `/club-events`
- `/event-registrations`

---

## 8. Frontend Architecture

## 8.1 Provider Stack
`frontend/src/main.jsx` provider order:
1. `BrowserRouter`
2. `ThemeProvider`
3. `AuthProvider`
4. `ToastProvider`

## 8.2 Routing and Guards
- Root routes: `frontend/src/routes/AppRoutes.jsx`
- Guard: `frontend/src/routes/ProtectedRoute.jsx`
- ACL config: `frontend/src/config/featureAccess.js`

Public routes:
- `/login`
- `/register`

Protected routes include:
- `/dashboard`, `/history`, `/profile`, `/analytics`, `/academic-structure`
- `/courses`, `/departments`, `/branches`, `/years`, `/sections`
- `/students`, `/subjects`, `/assignments`, `/submissions`
- `/submissions/:submissionId/evaluate`
- `/review-tickets`, `/notices`, `/notifications`
- `/clubs`, `/club-events`, `/event-registrations`
- `/evaluations`, `/enrollments`
- `/audit-logs`, `/developer-panel`, `/users`

Canonical UI route is `/sections` (legacy `/classes` URLs are not used by frontend).

## 8.3 API Client Behavior
`frontend/src/services/apiClient.js`:
- Base URL from `VITE_API_BASE_URL`
- Adds `Authorization: Bearer <token>`
- Adds `X-Trace-Id`, `X-Request-Id`
- Stores request timing metadata
- Stores recent trace entries in memory for diagnostics

## 8.4 Auth Session Behavior
`frontend/src/context/AuthContext.jsx`:
- Login: `POST /auth/login`
- Session validation: `GET /auth/me`
- Logout: clears local storage and state

Storage keys:
- `caps_ai_token`
- `caps_ai_user`

## 8.5 Theme and Toast
- Theme key: `caps_ai_theme`
- Toasts managed by `ToastContext` with auto-dismiss

---

## 9. Roles and Access Model
Primary roles:
- `admin`
- `teacher`
- `student`

Teacher extension roles (from backend schema):
- `year_head`
- `class_coordinator`
- `club_coordinator`
- `club_president`

Frontend ACL (`featureAccess.js`) examples:
- `users`: admin only
- `developerPanel`: admin only
- `students/subjects/assignments`: admin + teacher
- `enrollments`: admin + teacher with extension (`year_head` or `class_coordinator`)

Backend remains final authority for access checks.

---

## 10. MongoDB Collections (Operational)
Collections used across endpoints include:
- `users`
- `courses`
- `departments`
- `branches`
- `years`
- `classes` (stored collection name, exposed through sections API)
- `students`
- `subjects`
- `assignments`
- `submissions`
- `evaluations`
- `similarity_logs`
- `review_tickets`
- `notices`
- `notifications`
- `enrollments`
- `audit_logs`
- `clubs`
- `club_events`
- `event_registrations`
- `settings` (branding metadata)
- `ai_evaluation_chats`

There are no SQL migrations; Mongo collections are created/used dynamically.

---

## 11. Functional Modules (Feature Inventory)
Academic setup/core:
- Courses, Departments, Branches, Years, Sections/Classes
- Students, Subjects

Academic operations:
- Assignments CRUD
- Submission upload/workflow
- Evaluation records
- Review tickets
- Enrollments

Intelligence:
- Similarity scans/logs
- AI submission evaluation chat/history

Communication:
- Notices (scoped)
- Notifications

Institutional:
- Clubs, Club Events, Event Registrations

Governance:
- Users + extension role assignment
- Audit logs
- Branding/logo upload
- Developer panel

---

## 12. Recreating the Project from Scratch (Implementation Blueprint)
If someone needs to rebuild this project with the same behavior:

1. Recreate backend foundations:
- FastAPI app
- CORS and security headers middleware
- centralized error handlers with `error_id`
- config loader (`.env` -> settings)
- Mongo async connector

2. Recreate auth/security:
- PBKDF2 hashing
- JWT generation/validation
- current-user dependency
- role and extension-role dependency helpers

3. Recreate domain modules in this order:
- Users/Auth
- Academic structure (courses/departments/branches/years/sections)
- Students/Subjects
- Assignments/Submissions/Evaluations
- Similarity and AI endpoints
- Notices/Notifications
- Clubs/Events/Registrations
- Enrollments/Audit/Branding/Analytics

4. Recreate frontend shell:
- Router
- Protected route
- Auth context
- Theme + toast providers
- Sidebar/Topbar layout

5. Recreate frontend features in same backend order:
- Auth pages
- Dashboard + analytics
- Academic CRUD pages
- Assignments/submissions/evaluations/reviews
- Notices/notifications
- Clubs/events
- Admin tools (users/audit/developer panel)

6. Keep naming consistent:
- Use `/sections` in new API/frontend code.
- Keep `/classes` only as backend legacy alias until old clients/tests are removed.

---

## 13. Verification Checklist After Clone
Backend checks:
- `GET /health` returns `{ "status": "ok" }`
- `GET /docs` loads OpenAPI
- `POST /api/v1/auth/register` works for first user
- `POST /api/v1/auth/login` returns `access_token` and `user`

Frontend checks:
- Login page loads
- Authenticated navigation renders sidebar/topbar
- Role-based pages hide/show correctly
- Unauthorized route attempts redirect to `/dashboard`

Cross-service checks:
- `VITE_API_BASE_URL` points to backend `api/v1`
- Browser network requests include bearer token
- CORS allows `localhost:5173`

---

## 14. Test and Build Commands
Backend tests:
```bash
cd backend
.venv\Scripts\python.exe -m pytest -q
```

Frontend build:
```bash
cd frontend
npm run build
```

Frontend preview:
```bash
npm run preview
```

---

## 15. Troubleshooting Guide
Issue: frontend not loading
- Ensure Vite is running on 5173
- Open `http://localhost:5173`
- Hard refresh (`Ctrl+F5`)

Issue: login fails with 401
- Verify user exists
- Verify password hash field exists in `users`
- Check JWT secret consistency

Issue: 403 on enrollments for teacher
- Ensure teacher has extension role: `year_head` or `class_coordinator`
- Verify backend extension enforcement is satisfied

Issue: CORS blocked
- Add origin to `CORS_ORIGINS` in `backend/.env`
- Restart backend

Issue: AI endpoints failing
- Set valid `OPENAI_API_KEY`
- Check timeout/model vars
- Inspect backend logs for `error_id`

Issue: old route/client mismatch (`classes` vs `sections`)
- Use only `/sections` endpoints/routes and remove legacy client calls.

---

## 16. Security and Operational Notes
- Never commit real API keys or production secrets.
- Rotate leaked keys immediately.
- Replace default JWT secret in non-dev.
- Keep TLS termination and secure cookie/token handling in production.
- Add rate limiting and stronger audit policy for public deployments.

---

## 17. Suggested Production Hardening
- Add Docker Compose for backend/frontend/mongodb
- Add CI for pytest + frontend build + lint
- Add health probes and log aggregation
- Add backup/restore policy for MongoDB
- Add seed scripts for admin/bootstrap data
- Add integration tests for role-gated workflows

---

## 18. Quick Start (One Screen)
Terminal 1:
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2:
```bash
cd frontend
npm install
copy .env.example .env
npm run dev -- --host 0.0.0.0 --port 5173
```

Open:
- `http://localhost:5173`

---

This guide is intended to be sufficient for a new engineer to clone, run, understand, and recreate the full system behavior.
