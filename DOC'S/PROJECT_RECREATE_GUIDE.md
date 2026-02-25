# CAPS AI - Complete Project Recreate Guide

## 1. Purpose
This guide is for engineers who want to:
- Clone the CAPS AI repository
- Run backend and frontend locally
- Understand architecture, modules, permissions, and data flow
- Recreate the project from scratch with the same behavior

This is based on the **current codebase state** (FastAPI backend + React/Vite frontend).

---

## 2. System Overview
CAPS AI is an academic operations platform with role-based access for:
- `admin`
- `teacher`
- `student`

Core capabilities:
- Auth and profile management
- Academic setup: courses, departments, branches, years, sections/classes
- Academic operations: students, subjects, assignments, submissions, evaluations, review tickets, enrollments
- Communication: feed, announcements/notices, notifications, message placeholder
- Clubs hub: clubs, club events, event registrations, membership/application lifecycle, analytics
- Admin control plane: system, governance, compliance, recovery, analytics, communication dashboards
- AI and similarity workflows
- Audit logging, security headers, request tracing, rate limiting

---

## 3. Tech Stack

### Backend
- Python 3.11+
- FastAPI
- Uvicorn
- Motor (MongoDB async driver)
- Pydantic v2
- `python-jose` JWT
- Cloudinary SDK

See `backend/requirements.txt` for exact versions.

### Frontend
- React 18
- Vite 5
- React Router 6
- Tailwind CSS
- Axios
- Recharts
- Framer Motion
- Lucide icons

See `frontend/package.json` for exact versions.

### Database
- MongoDB (default local URI: `mongodb://localhost:27017`)

---

## 4. Repository Layout
- `backend/` FastAPI API, schemas, models, services, tests
- `frontend/` React app
- `DOC'S/` active handoff docs
- `DOC'S/archieves/` archived docs
- `docs/` additional docs
- `uploads/` runtime uploaded files

Key backend files:
- `backend/app/main.py`
- `backend/app/api/v1/router.py`
- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/app/core/indexes.py`

Key frontend files:
- `frontend/src/main.jsx`
- `frontend/src/routes/AppRoutes.jsx`
- `frontend/src/routes/ProtectedRoute.jsx`
- `frontend/src/config/featureAccess.js`
- `frontend/src/services/apiClient.js`

---

## 5. Environment Variables

## 5.1 Backend (`backend/.env`)
Copy from `backend/.env.example`:

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
RATE_LIMIT_MAX_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://192.168.2.70:5173
```

Notes:
- Cloudinary keys are required for notice image/file upload.
- In non-development mode, `JWT_SECRET=change_me` is blocked by config.

## 5.2 Frontend (`frontend/.env`)

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## 6. Local Setup and Run

## 6.1 Clone
```bash
git clone <repo-url>
cd CAPS_AI
```

## 6.2 Backend setup
Windows PowerShell:
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 6.3 Frontend setup
Open second terminal:
```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev -- --host 0.0.0.0 --port 5173
```

## 6.4 URLs
- Frontend: `http://localhost:5173`
- Backend API root: `http://localhost:8000/api/v1`
- OpenAPI docs: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

---

## 7. Backend Architecture

## 7.1 API bootstrap
`backend/app/main.py`:
- Mounts API router at `settings.api_prefix` (default `/api/v1`)
- Adds CORS middleware
- Adds rate-limit middleware
- Adds request tracing and security headers middleware
- Adds centralized exception handlers with `error_id`
- Ensures DB indexes on startup (`ensure_indexes()`)

## 7.2 Auth/security
`backend/app/core/security.py`:
- Password hash: PBKDF2-SHA256
- JWT payload includes:
  - `sub`, `email`, `role`, `admin_type`, `extended_roles`, `exp`
- Guards:
  - `require_roles([...])`
  - `require_teacher_extensions([...])`
  - `require_admin_or_teacher_extensions([...])`
  - permission checks for admin types (`super_admin`, `admin`, `academic_admin`, `compliance_admin`)

## 7.3 API modules
Router file: `backend/app/api/v1/router.py`

Registered module prefixes:
- `/auth`
- `/users`
- `/courses`
- `/departments`
- `/branches`
- `/years`
- `/classes` and `/sections` (same router; `/sections` canonical)
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
- `/admin/system`
- `/admin/analytics`
- `/admin/communication`
- `/admin/recovery`

## 7.4 Index strategy
Defined in `backend/app/core/indexes.py`:
- unique `users.email`
- operational indexes for notices, assignments, submissions, evaluations, notifications
- audit indexes (`created_at`, `resource_type+severity+created_at`)
- club ecosystem indexes (`clubs`, `club_members`, `club_events`, `event_registrations`)
- soft-delete indexes (`is_deleted`) across major collections

---

## 8. Frontend Architecture

## 8.1 Provider tree
`frontend/src/main.jsx` order:
1. `BrowserRouter`
2. `ThemeProvider`
3. `AuthProvider`
4. `ToastProvider`

## 8.2 API client
`frontend/src/services/apiClient.js`:
- Base URL from `VITE_API_BASE_URL`
- Adds `Authorization` header from `caps_ai_token`
- Adds `X-Trace-Id` and `X-Request-Id`
- Stores recent API traces in-memory (`getRecentApiTraceEntries()`)

## 8.3 Routing
`frontend/src/routes/AppRoutes.jsx` includes:
- Public: `/login`, `/register`
- Main app routes: dashboard, academic, operations, communication, clubs, profile, analytics, audit, etc.
- Admin V2 routes:
  - `/admin/dashboard`
  - `/admin/governance`
  - `/admin/academic-structure`
  - `/admin/operations`
  - `/admin/clubs`
  - `/admin/communication`
  - `/admin/compliance`
  - `/admin/analytics`
  - `/admin/system`
  - `/admin/recovery`
  - `/admin/developer`

## 8.4 Feature ACL
Source: `frontend/src/config/featureAccess.js`
- Admin-only sections for admin modules, users, developer/system domains
- Teacher/Student access scoped by feature
- Enrollment for teacher requires extension role:
  - `year_head` or `class_coordinator`

---

## 9. Roles and Access Model

Primary roles:
- `admin`
- `teacher`
- `student`

Admin subtype (`admin_type`):
- `super_admin`
- `admin`
- `academic_admin`
- `compliance_admin`

Teacher/student extension roles:
- `year_head`
- `class_coordinator`
- `club_coordinator`
- `club_president`

Important principle:
- Frontend ACL is UX gating.
- Backend is the final authorization authority.

---

## 10. Communication Module (Current)

Main UI routes:
- `/communication/feed`
- `/communication/announcements`
- `/communication/messages`

Legacy route still available:
- `/notices`

Notice API (`/api/v1/notices`):
- `GET /` list notices with filters and pagination
- `POST /` create notice
- `DELETE /{notice_id}` soft-delete notice and cleanup cloud assets

Current notice payload (logical):
- `title`
- `message`
- `priority`
- `scope`
- `scope_ref_id`
- `expires_at`
- optional multipart files under `images`

Notice storage supports:
- `images` metadata (Cloudinary URL/public_id/mime)
- future-ready fields (`is_pinned`, `scheduled_at`, `read_count`, `seen_by`)

---

## 11. Clubs Module (Current)

Core endpoints:
- `/clubs`
- `/club-events`
- `/event-registrations`

Capabilities:
- Club lifecycle/status transitions with governance checks
- Membership open/approval flow
- Applications review
- Club analytics
- Events with registration windows, capacity, payment flags
- Student registration with optional payment receipt upload (`/event-registrations/submit`)

Status and governance controls are enforced server-side.

---

## 12. Data Collections (Operational)
Likely collections used by current endpoints:
- `users`
- `courses`
- `departments`
- `branches`
- `years`
- `classes` (also exposed as sections)
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
- `club_members`
- `club_applications`
- `club_events`
- `event_registrations`
- `settings` (branding)
- AI-related collections used by evaluation history/chat features

---

## 13. Recreate Blueprint (If Building From Scratch)

1. Build backend foundations:
- FastAPI app + router hierarchy
- config loader + environment parsing
- Mongo async connector
- global middleware (CORS, rate limit, security headers, tracing)
- centralized exception handling

2. Build auth/security:
- PBKDF2 hashing
- JWT issue/verify
- current-user dependency
- role and extension/admin-type checks

3. Build modules in this order:
- Auth + Users
- Academic structure (courses/departments/branches/years/classes/sections)
- Students + Subjects
- Assignments + Submissions + Evaluations + Review Tickets
- Notices + Notifications + Communication shell
- Clubs + Club Events + Event Registrations
- Admin domain endpoints
- Analytics + Audit + Branding + AI

4. Build frontend shell:
- providers
- route guards
- dashboard layout
- sidebar/topbar
- API client interceptors

5. Build frontend pages by dependency order:
- Auth
- Core dashboard/profile/history/analytics
- Academic setup and operations
- Communication module
- Clubs module
- Admin v2 panels

6. Add compatibility:
- Support both `/classes` and `/sections` paths

---

## 14. Verification Checklist

Backend:
- `GET /health` returns healthy response
- `GET /docs` loads OpenAPI
- first admin registration works
- login returns token + user
- protected endpoints reject unauthorized access correctly

Frontend:
- login/logout works
- role-based navigation renders correctly
- announcements load and create flow works
- clubs list/events/registration flows work for role
- admin pages gated by role + admin type

Build/test:
- backend tests pass:
```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```
- frontend build passes:
```powershell
cd frontend
npm run build
```

---

## 15. Troubleshooting

Frontend not loading:
- verify Vite running on `5173`
- check `frontend/.env` base URL
- hard refresh browser

401/403 errors:
- token expired or user role mismatch
- verify `admin_type` / extension roles
- inspect backend response `detail` and `X-Error-Id`

CORS blocked:
- add frontend origin to `CORS_ORIGINS` in `backend/.env`
- restart backend

Notice images not uploading:
- verify Cloudinary keys in backend env
- confirm multipart upload with `images`
- check backend logs and error ID

Club event registration blocked:
- verify event `status=open`
- verify registration window (`registration_start`/`registration_end`)
- verify capacity not reached
- verify payment reference when event requires payment

---

## 16. Security and Ops Notes
- Never commit real secrets to `.env.example`.
- Rotate any leaked credential immediately.
- Keep JWT secret strong in production.
- Use HTTPS and managed secret injection in deployment.
- Add CI checks (`pytest`, frontend build) before merge.

---

## 17. Quick Start (2-Terminal)
Terminal 1 (backend):
```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 (frontend):
```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev -- --host 0.0.0.0 --port 5173
```

Open:
- `http://localhost:5173`

---

This document is intended to be sufficient for an engineer to clone, run, understand, and recreate the full project behavior.

---

## 18. Phase 2 Security and Governance (Implemented)

### 18.1 Advanced Auth
- Refresh token rotation is enforced on `/api/v1/auth/refresh`.
- Device session tracking is stored in `user_sessions`:
  - `user_id`, `refresh_jti`, `fingerprint`, `ip_address`, `user_agent`, `created_at`, `rotated_at`, `revoked_at`
- Token fingerprinting uses `X-Device-Fingerprint` header when present; fallback fingerprint is derived from user-agent + IP hash.
- IP tracking uses `X-Forwarded-For` (first hop) or request client host.
- Login anomaly events are recorded as `action_type=login_anomaly` when a new device/network pattern is detected.

### 18.2 Compliance Engine
- Immutable audit mirror is written to `audit_logs_immutable` with hash chaining:
  - `integrity_hash`, `previous_hash`, `source_audit_log_id`
- Admin action review queue APIs:
  - `GET /api/v1/admin/governance/reviews`
  - `POST /api/v1/admin/governance/reviews`
  - `PATCH /api/v1/admin/governance/reviews/{review_id}`
- Governance policy APIs:
  - `GET /api/v1/admin/governance/policy`
  - `PATCH /api/v1/admin/governance/policy`
- Governance dashboard:
  - `GET /api/v1/admin/governance/dashboard`
- Soft-delete restore actions are also mirrored to `recovery_logs` (when collection available).

### 18.3 Data Governance Controls
- Role-change approval flow (policy-based):
  - If `role_change_approval_enabled=true`, `PATCH /api/v1/users/{user_id}/extensions` requires `review_id`.
- Two-person rule for destructive actions (policy-based):
  - If `two_person_rule_enabled=true`, delete actions for courses/departments/branches/years/classes require approved `review_id`.
- System health dashboard remains available:
  - `GET /api/v1/admin/system/health`

---

## 19. Phase 4 Reliability and Operability (Kickoff Started)

Phase 4 start in this codebase focuses on **automated operations** and **runtime visibility**.

### 19.1 Automated jobs (in-app scheduler)
- New scheduler service: `backend/app/services/scheduler.py`
- Startup/shutdown integration: `backend/app/main.py`
- Feature-flagged by env:
  - `SCHEDULER_ENABLED`
  - `SCHEDULED_NOTICE_POLL_SECONDS`
  - `ANALYTICS_SNAPSHOT_HOUR_UTC`
  - `ANALYTICS_SNAPSHOT_MINUTE_UTC`

Jobs now automated:
- Scheduled notice fanout dispatch polling
- Daily analytics snapshot precompute

### 19.2 Health visibility
- `/api/v1/admin/system/health` includes scheduler status for admin observability.

### 19.3 Container readiness
- `docker-compose.yml` now includes Redis service (`redis:7-alpine`) used by:
  - rate limiting
  - token blacklist
  - analytics cache
  - scheduler-backed workloads

### 19.4 Operational defaults
- Local/dev remains safe by default (`SCHEDULER_ENABLED=false` in `.env.example`).
- Production template enables scheduler + Redis in `backend/.env.production`.
