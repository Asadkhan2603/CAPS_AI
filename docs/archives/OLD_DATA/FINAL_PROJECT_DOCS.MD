# CAPS AI - Final Project Documentation

## 1. Project Snapshot
- Project: CAPS AI (Academic Governance + AI-assisted Evaluation Platform)
- Backend: FastAPI + MongoDB
- Frontend: React (Vite) + Tailwind
- Auth: JWT (role + extension role checks)
- Current validation status:
  - Backend tests: `50 passed` (latest run)
  - Frontend build: `vite build` success (latest run)
- Documentation generated on: `2026-02-18 00:18:21 +05:30`

## 2. Roles and Access Model
### Base Roles
- `admin`
- `teacher`
- `student`

### Teacher Extension Roles
- `year_head`
- `class_coordinator`
- `club_coordinator`

### Frontend feature gates (`frontend/src/config/featureAccess.js`)
- Common (`admin/teacher/student`): dashboard, analytics, history, profile, academic structure, submissions, evaluations, notices, notifications, clubs, club events, event registrations
- Admin + Teacher only: students, subjects, assignments, review tickets
- Admin + teacher(extension) only: enrollments (`year_head` or `class_coordinator`)
- Admin only: users, courses, years, classes, sections, section-subjects, audit logs

## 3. High-Level Architecture
- Backend API prefix: `/api/v1`
- Frontend calls backend via `VITE_API_BASE_URL`
- Core domains:
  - Academic core: courses, years, classes, sections, section-subjects, students, subjects, enrollments
  - Assessment core: assignments, submissions, evaluations, similarity checks
  - Institutional: notices, notifications, clubs, club events, event registrations
  - Governance: audit logs, review tickets, analytics
  - UX extensions: branding logo, profile management, history logs, academic hierarchy explorer

## 4. Working API Inventory
All APIs below are registered in `backend/app/api/v1/router.py`.

### Auth (`/auth`)
- `POST /register`
- `POST /login`
- `GET /me`
- `PATCH /profile`
- `POST /profile/avatar`
- `GET /profile/avatar/{user_id}`

### Users (`/users`)
- `GET /`
- `PATCH /{user_id}/extensions`

### Courses (`/courses`)
- `GET /`
- `GET /{course_id}`
- `POST /`
- `PUT /{course_id}`
- `DELETE /{course_id}`

### Years (`/years`)
- `GET /`
- `GET /{year_id}`
- `POST /`
- `PUT /{year_id}`
- `DELETE /{year_id}`

### Classes (`/classes`)
- `GET /`
- `GET /{class_id}`
- `POST /`
- `PUT /{class_id}`
- `DELETE /{class_id}`
- Supports structure fields: `faculty_name`, `branch_name`

### Sections (`/sections`)
- `GET /`
- `GET /{section_id}`
- `POST /`
- `PUT /{section_id}`
- `DELETE /{section_id}`

### Section Subjects (`/section-subjects`)
- `GET /`
- `GET /{mapping_id}`
- `POST /`
- `PUT /{mapping_id}`
- `DELETE /{mapping_id}`

### Students (`/students`)
- `GET /`
- `GET /{student_id}`
- `POST /`
- `PUT /{student_id}`
- `DELETE /{student_id}`

### Subjects (`/subjects`)
- `GET /`
- `GET /{subject_id}`
- `POST /`
- `PUT /{subject_id}`
- `DELETE /{subject_id}`

### Enrollments (`/enrollments`)
- `GET /`
- `POST /`

### Assignments (`/assignments`)
- `GET /`
- `GET /{assignment_id}`
- `POST /`
- `PUT /{assignment_id}`
- `PATCH /{assignment_id}/plagiarism`
- `DELETE /{assignment_id}`

### Submissions (`/submissions`)
- `GET /`
- `GET /{submission_id}`
- `POST /upload` (file upload)
- `POST /{submission_id}/ai-evaluate`
- `PUT /{submission_id}`
- `DELETE /{submission_id}`

### Evaluations (`/evaluations`)
- `GET /`
- `GET /{evaluation_id}`
- `POST /`
- `PUT /{evaluation_id}`
- `PATCH /{evaluation_id}/finalize`
- `PATCH /{evaluation_id}/override-unfinalize`

### Similarity (`/similarity`)
- `GET /checks`
- `POST /checks/run/{submission_id}`

### Analytics (`/analytics`)
- `GET /summary`
- `GET /teacher/classes`
- `GET /academic-structure`

### Notices (`/notices`)
- `GET /`
- `POST /`

### Notifications (`/notifications`)
- `GET /`
- `POST /`
- `PATCH /{notification_id}/read`

### Clubs (`/clubs`)
- `GET /`
- `POST /`

### Club Events (`/club-events`)
- `GET /`
- `POST /`
- `PUT /{event_id}`
- `DELETE /{event_id}`
- Role behavior:
  - Admin: delete allowed
  - Coordinator teacher: archive/restore/open/close for owned club events only

### Event Registrations (`/event-registrations`)
- `GET /`
- `POST /`
- `POST /submit` (full form + optional payment receipt upload)

### Review Tickets (`/review-tickets`)
- `GET /`
- `POST /`
- `PATCH /{ticket_id}/approve`
- `PATCH /{ticket_id}/reject`

### Audit Logs (`/audit-logs`)
- `GET /`

### Branding (`/branding`)
- `GET /logo/meta`
- `GET /logo`
- `POST /logo` (admin logo upload)

## 5. Implemented Feature Set
### Authentication and Security
- JWT login/register/me flow
- Password hashing (PBKDF2-SHA256)
- Role + extension-role authorization guards
- Security response headers middleware

### Academic Administration
- Full CRUD for courses/years/classes/sections/subjects/students
- Section-subject-teacher mapping
- Class enrollment model with extension-role checks

### Assessment Engine
- Assignment lifecycle with plagiarism toggle
- Student submission upload with file validation
- AI evaluation suggestion pipeline
- Teacher/admin evaluation with lock/unlock governance
- Similarity checks + threshold-driven flagged logs

### Governance and Institutional
- Notices + notifications
- Review ticket workflow
- Audit logs
- Analytics summary by role

### Club and Event Ecosystem
- Clubs + club events management
- Coordinator-scoped event management
- Student event registration (basic + full profile form)
- Optional receipt upload in event registration
- Admin event deletion + coordinator archive flow

### UX and UI Enhancements
- Feature-gated sidebar routing by role
- Top-right history shortcut
- Profile management page (personal + professional details)
- Profile photo upload
- Institute branding logo upload (admin) and global display
- Academic hierarchy explorer page:
  - Faculty -> Course -> Year -> Branch -> Section
  - Section tile view
  - Students list + log counters

## 6. Current Data/Hierarchy Behavior
- Hierarchy endpoint builds structure from current collections and class metadata.
- `faculty_name` and `branch_name` are now first-class class fields and should be filled during class creation for best structure quality.
- Student logs in hierarchy currently aggregate:
  - assignment submission count
  - event registration count

## 7. Role-Specific Behavior (Important)
- Student:
  - Can view own submissions/evaluations/registrations/profile/history
  - Cannot access admin modules
- Teacher:
  - Scoped access for sensitive resources (submissions, event registrations, hierarchy)
  - Club event management limited to assigned coordinator clubs
- Admin:
  - Full governance access
  - User extension assignment
  - Branding upload
  - Club event deletion

## 8. Known Issues / Technical Debt
- No frontend automated test suite yet (build-only validation on frontend).
- PyJWT/Jose deprecation warning appears in tests (`datetime.utcnow()` warning from dependency).
- Some hierarchy defaults are inferred when faculty/branch are missing in old class records.

## 9. Validation Summary (Latest)
### Backend
- Command: `python -m pytest`
- Result: `50 passed`

### Frontend
- Command: `npm run build`
- Result: success (production build generated)

## 10. Suggested Next Hardening Steps
1. Add frontend integration/e2e tests for role-based navigation and critical workflows.
2. Add API-level role matrix tests for all sensitive endpoints.
3. Add migration/backfill script for `faculty_name` and `branch_name` in legacy classes.
4. Add explicit OpenAPI role notes in endpoint docstrings for faster onboarding.
5. Add centralized observability (structured logs + request tracing + error IDs surfaced in UI).

## 11. Quick Start Commands
### Backend
```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd frontend
npm install
copy .env.example .env
npm run dev -- --host 0.0.0.0 --port 5173
```

### Health and Docs
- API root: `http://localhost:8000/`
- Health: `http://localhost:8000/health`
- Swagger: `http://localhost:8000/docs`
