# CAPS AI Frontend Handoff Guide (Complete)

## 1) Goal
This document is a complete frontend handoff for a new developer.
Use it to rebuild or redesign the UI without breaking current behavior, role access, or backend contracts.

## 2) Stack and Runtime
- React 18 + Vite
- React Router v6
- Tailwind CSS
- Axios
- Recharts
- Framer Motion
- Lucide React

Requirements:
- Node.js 20+
- npm (lockfile is present)

## 3) Run and Build
From `frontend/`:
- `npm install`
- `npm run dev -- --host 0.0.0.0 --port 5173`
- `npm run build`
- `npm run preview`

## 4) Environment
File: `frontend/.env`

Required:
- `VITE_API_BASE_URL=http://localhost:8000/api/v1`

Fallback in code (`frontend/src/services/apiClient.js`) is the same URL if env var is missing.

## 5) App Bootstrap and Providers
Entry: `frontend/src/main.jsx`

Provider order:
1. `BrowserRouter`
2. `ThemeProvider`
3. `AuthProvider`
4. `ToastProvider`

Root component: `frontend/src/App.jsx`
Routes root: `frontend/src/routes/AppRoutes.jsx`

## 6) Core Architecture
- Route guard: `frontend/src/routes/ProtectedRoute.jsx`
- Feature ACL config: `frontend/src/config/featureAccess.js`
- Permission helpers: `frontend/src/utils/permissions.js`
- API client + interceptors: `frontend/src/services/apiClient.js`
- Layout shell: `frontend/src/components/layout/DashboardLayout.jsx`
- Sidebar nav and branding: `frontend/src/components/layout/Sidebar.jsx`
- Topbar/profile/theme: `frontend/src/components/layout/Topbar.jsx`

## 7) Auth and Session Behavior
Implementation: `frontend/src/context/AuthContext.jsx`

Flow:
- Login: `POST /auth/login`
- Validate token on app load: `GET /auth/me`
- Logout: clears local state + storage

Storage keys:
- `caps_ai_token`
- `caps_ai_user`

## 8) API Client Conventions
File: `frontend/src/services/apiClient.js`

Request behavior:
- Adds `Authorization: Bearer <token>` if token exists
- Adds `X-Trace-Id`, `X-Request-Id`
- Stores request metadata for latency tracing

Response behavior:
- Captures `x-trace-id`, `x-request-id`, `x-error-id`
- Pushes trace entries to an in-memory ring buffer (`getRecentApiTraceEntries`)

## 9) Services Layer
- `frontend/src/services/sectionsApi.js`
  - Reads/writes `/sections` (canonical frontend path)
- `frontend/src/services/aiService.js`
  - `POST /ai/evaluate`
  - `GET /ai/history/:studentId/:examId`

## 10) Routing (Actual)
Public:
- `/login`
- `/register`

Protected:
- `/dashboard`
- `/history`
- `/profile`
- `/analytics`
- `/academic-structure`
- `/courses`
- `/departments`
- `/branches`
- `/years`
- `/sections`
- `/students`
- `/subjects`
- `/assignments`
- `/submissions`
- `/submissions/:submissionId/evaluate`
- `/review-tickets`
- `/notices`
- `/clubs`
- `/club-events`
- `/notifications`
- `/evaluations`
- `/event-registrations`
- `/enrollments`
- `/audit-logs`
- `/developer-panel`
- `/users`

## 11) Role Access Matrix (Frontend Guard Level)
Source of truth: `frontend/src/config/featureAccess.js`

| Feature/Page | Admin | Teacher | Student |
|---|---|---|---|
| Dashboard, Analytics, History, Profile, Academic Structure | Yes | Yes | Yes |
| Students, Subjects, Assignments | Yes | Yes | No |
| Submissions | Yes | Yes | Yes |
| Review Tickets | Yes | Yes | No |
| Evaluations | Yes | Yes | Yes |
| Enrollments | Yes | Yes* | No |
| Notices, Notifications, Clubs, Club Events, Event Registrations | Yes | Yes | Yes |
| Audit Logs | Yes | Yes | No |
| Developer Panel | Yes | No | No |
| Users | Yes | No | No |
| Courses, Departments, Branches, Years | Yes | No |
| Sections | Yes | Yes | No |

`*` Teacher enrollments additionally require extension role `year_head` or `class_coordinator` in the frontend guard and backend.

## 12) Extension Roles (Teacher) Complete Notes
Extension roles returned from backend: `year_head`, `class_coordinator`, `club_coordinator`.

### 12.1 year_head
- Frontend impact:
  - Grants enrollments feature access via `requiredTeacherExtensions`.
- Backend expected behavior:
  - Can manage/view enrollments with supervisory scope.
  - Can publish year-scoped notices.

### 12.2 class_coordinator
- Frontend impact:
  - Grants enrollments feature access.
  - Section views for teachers are naturally scoped from backend.
- Backend expected behavior:
  - Coordinator class ownership checks on class details and notices.
  - Can publish class/section notices for owned class only.

### 12.3 club_coordinator
- Frontend impact:
  - No separate front-end route switch today; routes are already available to teacher.
- Backend expected behavior:
  - Club/event management and event registration visibility are coordinator-scoped.

Important: extension-role enforcement is mostly backend authoritative. Frontend should mirror for UX but not replace backend checks.

## 13) Backend Contract Used by Frontend (Detailed)
### Auth / Profile
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `PATCH /auth/profile`
- `POST /auth/profile/avatar`

### Academic Setup/Core
- `/courses`
- `/departments`
- `/branches`
- `/years`
- `/sections` (canonical; backend still keeps `/classes` as legacy alias)
- `/students`
- `/subjects`

### Operations
- `/assignments`
- `/submissions`
- `/evaluations`
- `/review-tickets`
- `/enrollments`

### Analytics
- `GET /analytics/summary`
- `GET /analytics/academic-structure`
- `GET /analytics/teacher/sections` (canonical; backend still keeps `/analytics/teacher/classes` as legacy alias)

### Communication
- `/notices`
- `/notifications`

### Clubs
- `/clubs`
- `/club-events`
- `/event-registrations`
- `/event-registrations/submit`

### Governance/Admin
- `/users`
- `PATCH /users/:id/extensions`
- `/audit-logs`
- `GET /branding/logo/meta`
- `POST /branding/logo`

### AI (Teacher evaluation workspace)
- `POST /ai/evaluate`
- `GET /ai/history/:studentId/:examId`

## 14) Role-by-Role Functional Behavior

### 14.1 Admin
Primary responsibilities in current frontend:
- Full academic structure CRUD: courses/departments/branches/years/sections
- User and extension-role management
- Audit visibility
- Branding upload in sidebar
- Can access almost all pages

Notes:
- Some backend endpoints still enforce ownership for certain teacher-created entities.

### 14.2 Teacher
Primary responsibilities:
- Students/subjects/assignments/submissions/evaluations/review tickets
- Notices/notifications
- Clubs/events (subject to backend scope rules)
- Enrollment management only with required extension role
- AI-assisted evaluation console (`/submissions/:submissionId/evaluate`)

### 14.3 Student
Primary responsibilities:
- View dashboard/history/profile
- Upload/view own submissions
- View own evaluations
- Notices/notifications/clubs/events/event registration

Student visibility depends on backend scoping (for notices and records).

## 15) Page Inventory
`frontend/src/pages/`:
- `AcademicStructurePage.jsx`
- `AnalyticsPage.jsx`
- `AssignmentsPage.jsx`
- `AuditLogsPage.jsx`
- `BranchesPage.jsx`
- `ClassesPage.jsx` (Sections UI)
- `ClubEventsPage.jsx`
- `ClubsPage.jsx`
- `CoursesPage.jsx`
- `DashboardPage.jsx`
- `DepartmentsPage.jsx`
- `DeveloperPanelPage.jsx`
- `EnrollmentsPage.jsx`
- `EvaluationsPage.jsx`
- `EventRegistrationsPage.jsx`
- `HistoryPage.jsx`
- `LoginPage.jsx`
- `NoticesPage.jsx`
- `NotificationsPage.jsx`
- `ProfilePage.jsx`
- `RegisterPage.jsx`
- `ReviewTicketsPage.jsx`
- `StudentsPage.jsx`
- `SubjectsPage.jsx`
- `SubmissionsPage.jsx`
- `UsersPage.jsx`
- `Teacher/EvaluateSubmission.jsx`

## 16) Components
### Layout
- `frontend/src/components/layout/Sidebar.jsx`
- `frontend/src/components/layout/Topbar.jsx`
- `frontend/src/components/layout/DashboardLayout.jsx`
- `frontend/src/components/layout/Breadcrumb.jsx`

### UI primitives
- `Alert.jsx`
- `Badge.jsx`
- `Card.jsx`
- `EntityManager.jsx`
- `FileUpload.jsx`
- `FormInput.jsx`
- `Modal.jsx`
- `PageLoader.jsx`
- `StatCard.jsx`
- `Table.jsx`
- `TeacherClassTiles.jsx`
- `Toast.jsx`

### Teacher-specific
- `frontend/src/components/Teacher/AIChatPanel.jsx`

## 17) Styling and Theme
- Tailwind config: `frontend/tailwind.config.cjs`
  - `darkMode: 'class'`
  - Brand color scale `brand.50` to `brand.900`
  - Shadow token: `soft`
- Global classes: `frontend/src/styles/global.css`
  - `.panel`, `.btn`, `.btn-primary`, `.btn-secondary`, `.input`, `.page-fade`

Theme behavior:
- `ThemeContext` toggles `dark` class on `<html>`.
- Theme persisted in localStorage key `caps_ai_theme`.

## 18) Vite and Build Optimization
File: `frontend/vite.config.js`
- Dev server host: `0.0.0.0`, port `5173`
- Manual chunks:
  - `react-vendor`
  - `charts-vendor`
  - `motion-vendor`
  - `icons-vendor`
  - `http-vendor`

## 19) Known Risks / Coupling
1. Some teacher flows call `/users/` (typically admin endpoint). If backend strictness increases, these screens may fail for teachers.
2. Frontend relies on specific response fields (`id`, `extended_roles`, avatar fields, etc.).
3. Frontend is standardized to `/sections`; backend keeps `/classes` as legacy compatibility alias.
4. Frontend permission checks are UX-level only; backend remains source of truth.

## 20) Rebuild Plan for New Developer
1. Recreate app shell first:
   - providers, route guards, sidebar/topbar, theme, toast
2. Implement `apiClient` interceptors and auth/session behavior
3. Rebuild modules in this order:
   - Auth + Dashboard
   - Academic setup/core CRUD
   - Assignments/Submissions/Evaluations/Review Tickets
   - Notices/Notifications
   - Clubs/Events/Registrations
   - Admin tools (users/audit/developer panel)
4. Keep ACL in one place (`featureAccess.js`)
5. Add integration tests for role navigation and protected workflows

## 21) Quick File Map
- Bootstrap: `frontend/src/main.jsx`, `frontend/src/App.jsx`
- Routing/access: `frontend/src/routes/*`, `frontend/src/config/featureAccess.js`, `frontend/src/utils/permissions.js`
- Context: `frontend/src/context/*`
- Hooks: `frontend/src/hooks/*`
- Services: `frontend/src/services/*`
- Layout: `frontend/src/components/layout/*`
- UI components: `frontend/src/components/ui/*`
- Teacher module: `frontend/src/components/Teacher/*`, `frontend/src/pages/Teacher/*`
- Feature pages: `frontend/src/pages/*`

---
This file is intentionally complete for admin/teacher/student and extension-role handoff.
