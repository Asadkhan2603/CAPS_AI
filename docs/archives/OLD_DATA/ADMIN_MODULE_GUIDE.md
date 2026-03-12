# CAPS AI Admin Module Guide (Recreate Blueprint)

## 1) Goal
This document is a complete `admin module` blueprint for CAPS AI.
A new developer should be able to recreate the admin experience, permissions, and workflows without breaking backend contracts.

Scope of this guide:
- Admin feature boundaries
- Frontend route/page behavior
- Backend endpoints admin depends on
- Data contracts and expected fields
- Rebuild sequence (backend + frontend)
- Validation checklist and troubleshooting

## 2) What "Admin Module" Means in CAPS AI
Admin is the governance role for the platform.
Admin controls:
- Account governance (`users`, extension roles)
- Academic structure setup (`courses`, `departments`, `branches`, `years`, `sections/classes`)
- Operational oversight (`students`, `subjects`, `assignments`, `submissions`, `evaluations`, `review tickets`, `enrollments`)
- Communication governance (`feed`, `announcements/notices`, `messages placeholder`)
- Clubs governance (clubs hub lifecycle, membership approvals, events oversight, analytics)
- Compliance and operations (`audit logs`, branding/logo, developer panel)

## 3) Runtime and Environment

### 3.1 Backend
- Python 3.11+
- FastAPI
- Uvicorn
- MongoDB

Run:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3.2 Frontend
- Node.js 20+
- React + Vite

Run:
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

### 3.3 Required env
Backend: `backend/.env`
- `MONGODB_URL`
- `MONGODB_DB`
- `JWT_SECRET`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `CORS_ORIGINS`

Frontend: `frontend/.env`
- `VITE_API_BASE_URL=http://localhost:8000/api/v1`

## 4) Key Files for Admin Module

### 4.1 Frontend
- Routes: `frontend/src/routes/AppRoutes.jsx`
- Access matrix: `frontend/src/config/featureAccess.js`
- Route guard: `frontend/src/routes/ProtectedRoute.jsx`
- Auth context/session: `frontend/src/context/AuthContext.jsx`
- Sidebar navigation: `frontend/src/components/layout/Sidebar.jsx`
- Admin pages:
  - `frontend/src/pages/UsersPage.jsx`
  - `frontend/src/pages/CoursesPage.jsx`
  - `frontend/src/pages/DepartmentsPage.jsx`
  - `frontend/src/pages/BranchesPage.jsx`
  - `frontend/src/pages/YearsPage.jsx`
  - `frontend/src/pages/ClassesPage.jsx`
  - `frontend/src/pages/AuditLogsPage.jsx`
  - `frontend/src/pages/DeveloperPanelPage.jsx`
  - `frontend/src/pages/Communication/AnnouncementsPage.jsx`
  - `frontend/src/pages/ClubsPage.jsx`

### 4.2 Backend
- API root router: `backend/app/api/v1/router.py`
- Security and role dependencies: `backend/app/core/security.py`
- Startup indexes: `backend/app/core/indexes.py`
- Auth endpoints: `backend/app/api/v1/endpoints/auth.py`
- User extension management: `backend/app/api/v1/endpoints/users.py`
- Clubs governance: `backend/app/api/v1/endpoints/clubs.py`
- Club events: `backend/app/api/v1/endpoints/club_events.py`
- Event registrations: `backend/app/api/v1/endpoints/event_registrations.py`
- Global exception handlers/middleware: `backend/app/main.py`

## 5) Admin ACL (Source of Truth)
Frontend ACL file: `frontend/src/config/featureAccess.js`

Admin has access to all functional modules.
Admin-only restrictions:
- `users`
- `developerPanel`
- `courses`
- `departments`
- `branches`
- `years`

Note:
- `sections` currently allows `admin` + `teacher`
- frontend ACL is UX gate only; backend role checks remain authoritative

## 6) Authentication and Session Model

### 6.1 Login flow
- `POST /api/v1/auth/login`
- returns token + user
- frontend stores:
  - `caps_ai_token`
  - `caps_ai_user`

### 6.2 Session validation
- `GET /api/v1/auth/me` on app load in `AuthContext`
- invalid token -> localStorage cleared and user logged out

### 6.3 Important limitation
One browser profile = one active session (single token key).
Use separate browser profiles/incognito for concurrent admin/teacher/student testing.

## 7) Backend Contracts Admin Uses

All paths below are under `/api/v1`.

### 7.1 Auth/Profile
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /auth/change-password`
- `PATCH /auth/profile`
- `POST /auth/profile/avatar`

### 7.2 User governance
- `GET /users/` (admin only)
- `PATCH /users/{user_id}/extensions` (admin only)

Payload shape for extension update:
```json
{
  "extended_roles": ["class_coordinator"],
  "role_scope": {
    "class_coordinator": {
      "class_id": "<class_object_id>"
    }
  }
}
```

Rules:
- Teacher allowed: `year_head`, `class_coordinator`, `club_coordinator`
- Student allowed: `club_president`
- Invalid combinations return `400`

### 7.3 Academic setup/core
- `/courses`
- `/departments`
- `/branches`
- `/years`
- `/sections` (alias over classes router)
- `/students`
- `/subjects`

### 7.4 Academic operations
- `/assignments`
- `/submissions`
- `/evaluations`
- `/review-tickets`
- `/enrollments`

### 7.5 Communication
- `/notices`
- `/notifications`
- `/communication/*` frontend pages use these backend resources

### 7.6 Clubs governance
- `GET /clubs/`
- `POST /clubs/`
- `PATCH /clubs/{club_id}`
- `POST /clubs/{club_id}/join`
- `GET /clubs/{club_id}/members`
- `PATCH /clubs/{club_id}/members/{member_id}`
- `GET /clubs/{club_id}/applications`
- `PATCH /clubs/{club_id}/applications/{application_id}`
- `GET /clubs/{club_id}/analytics`
- `/club-events`
- `/event-registrations`

## 8) Admin Data Contracts (Critical Fields)

### 8.1 User output fields relied by frontend
From `UserOut` schema:
- `id`
- `full_name`
- `email`
- `role`
- `extended_roles`
- `role_scope`
- `must_change_password`
- `profile`
- `created_at`

### 8.2 Club output fields relied by frontend Clubs Hub
- `id`, `name`, `description`
- `category`, `academic_year`
- `coordinator_user_id`, `coordinator_name`, `coordinator_email`
- `president_user_id`, `president_name`, `president_email`
- `status`, `registration_open`, `membership_type`, `max_members`, `member_count`
- `is_active` (legacy compatibility)

### 8.3 Event output fields
- `id`, `club_id`, `title`, `description`
- `event_type`, `visibility`
- `event_date`, `capacity`
- `status`

## 9) Admin UI: Page-by-Page Behavior

### 9.1 `/users`
- list all users
- assign extension roles + scope
- backend validates role-extension compatibility
- side effects:
  - class coordinator can bind to class
  - club president can bind to club

### 9.2 `/courses` `/departments` `/branches` `/years` `/sections`
- foundational setup pages
- should be completed before heavy operations

### 9.3 `/audit-logs`
- governance visibility
- verify role/extension updates and sensitive actions

### 9.4 `/developer-panel`
- admin-only technical control panel

### 9.5 `/communication/announcements`
- admin publishes notices/announcements
- audience mapping handled in frontend + validated by backend

### 9.6 `/clubs` (Clubs Hub)
Tabs:
- `Overview` (directory + lifecycle actions)
- `Members`
- `Events`
- `Announcements` (navigates to communication)
- `Analytics`

Admin can:
- create/activate/close/archive clubs
- assign coordinator and optionally president
- open/close registration
- review applications
- manage full club lifecycle

## 10) Recreation Plan (Admin Module)

### Step 1: backend foundations
Implement or verify:
- `get_current_user`, `require_roles`, extension-role helpers
- global exception handlers with `error_id`
- startup index creation

### Step 2: auth + users
Implement:
- `/auth/login`, `/auth/me`
- `/users/`
- `/users/{id}/extensions` with role-scope side effects

### Step 3: academic setup pages and endpoints
Implement in order:
1. courses
2. departments
3. branches
4. years
5. sections/classes

### Step 4: admin operations modules
Implement:
- students, subjects, assignments, submissions, evaluations, review tickets, enrollments

### Step 5: communication governance
Implement:
- notices + notifications integration
- announcements page and filters

### Step 6: clubs governance
Implement:
- club lifecycle endpoints and Clubs Hub UI
- applications/members/events/analytics

### Step 7: operations polish
Implement:
- audit logs
- branding/logo upload
- developer panel

## 11) Mongo Collections Admin Touches
- `users`
- `courses`
- `departments`
- `branches`
- `years`
- `classes` (also served as sections)
- `students`
- `subjects`
- `assignments`
- `submissions`
- `evaluations`
- `review_tickets`
- `enrollments`
- `notices`
- `notifications`
- `clubs`
- `club_members`
- `club_applications`
- `club_events`
- `event_registrations`
- `audit_logs`
- `settings`

## 12) Validation and QA Checklist (Admin Recreate Acceptance)

### 12.1 Access control
- admin can access all pages
- teacher/student blocked from admin-only pages

### 12.2 User governance
- extension update succeeds for valid payload
- invalid extension-role combinations return clear `400`

### 12.3 Academic setup dependencies
- sections creation works only with valid upstream entities

### 12.4 Communication
- admin can create announcements and view in feed

### 12.5 Clubs Hub
- clubs list loads
- admin creates club
- activation enforces coordinator requirement
- registration toggle works
- application approve/reject works
- analytics endpoint responds

### 12.6 Audit/branding
- audit page loads
- logo upload updates sidebar branding

## 13) Error Handling and Troubleshooting

### 13.1 Standard backend error envelope
Errors generally include:
- `success: false`
- `detail`
- `error_id`
- `X-Error-Id`

### 13.2 Fast debug flow
1. `GET /health`
2. Inspect browser network (status + response `detail`)
3. Confirm `VITE_API_BASE_URL`
4. Check token validity with `/auth/me`
5. Trace backend log by `error_id`

### 13.3 Frequent admin-side failure patterns
- `401` token expired/invalid
- `403` role mismatch
- `404` backend not restarted after route changes
- `422` payload schema mismatch
- `500` runtime bug (check logs)

Known current runtime risk to watch:
- notice date comparisons can fail if naive/aware datetime formats mix

## 14) Security Requirements
- keep `JWT_SECRET` private and strong
- do not commit real API keys in repo
- limit number of admin accounts
- prefer role/extension APIs over direct DB writes
- verify CORS origin list before deployment

## 15) Deployment Readiness (Admin Module)
Before release:
1. backend starts and creates indexes successfully
2. admin login and `/auth/me` stable
3. all admin routes render without redirects/errors
4. clubs hub tabs load without 404
5. audit and branding flows pass
6. frontend production build passes (`npm run build`)

## 16) Quick Recreate Commands

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

---
This guide is intended to be sufficient to recreate the full admin module behavior with minimal assumptions.

