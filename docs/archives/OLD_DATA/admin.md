# CAPS AI - Admin Module Guide (v2 - Enterprise Rebuild)

---

## 1) Purpose
This document defines the complete architecture, governance model, contracts, workflows, and validation checklist for rebuilding the **Admin Module** in CAPS AI.

This guide ensures:
- Backend and frontend remain contract-safe
- Permissions are future-proof
- Governance is scalable
- Destructive operations are safe
- Observability and compliance are built-in

---

## 2) Admin Philosophy
Admin in CAPS AI is not just CRUD access.

Admin is the **Control Plane of the Platform**.

Admin governs:
- Identity and Access
- Academic Infrastructure
- Academic Operations
- Clubs and Engagement
- Communication
- Compliance and Audit
- Analytics
- System Health
- Recovery and Safety

---

## 3) Admin Architecture Overview

### 3.1 Domain-Based Structure
```text
/admin
/admin/dashboard
/admin/governance
/admin/academic-structure
/admin/operations
/admin/clubs
/admin/communication
/admin/compliance
/admin/analytics
/admin/system
/admin/recovery
/admin/developer
```

This replaces flat navigation with domain separation.

---

## 4) Admin Role Model (v2 Upgrade)

### 4.1 Admin Role Types
| Role | Capability |
|------|------------|
| super_admin | Full system access, create/delete admins |
| admin | Academic + club + communication governance |
| academic_admin | Only academic structure |
| compliance_admin | Read-only audit + analytics |

### 4.2 User Schema Update
```json
{
  "role": "admin",
  "admin_type": "super|standard|academic|compliance"
}
```

### 4.3 Permission-Based Middleware (Future Proof)
```python
ROLE_PERMISSIONS = {
    "super_admin": ["*"],
    "admin": [
        "users.read",
        "users.update",
        "clubs.manage",
        "courses.manage",
        "announcements.publish"
    ],
    "academic_admin": [
        "courses.manage",
        "departments.manage",
        "sections.manage"
    ],
    "compliance_admin": [
        "audit.read",
        "analytics.read"
    ]
}
```

Decorator example:
```python
@require_permission("users.update")
```

---

## 5) Runtime and Environment

### Backend
- Python 3.11+
- FastAPI
- Uvicorn
- MongoDB

Run:
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
- Node.js 20+
- React + Vite

Run:
```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

---

## 6) Admin Domains (Detailed)

### 6.1 Dashboard (`/admin/dashboard`)
Widgets:
- Total users
- Active students
- Active clubs
- Pending review tickets
- Assignments completion rate
- Events this week
- System errors (last 24h)

Backend:
- `GET /admin/analytics/overview`

### 6.2 Governance Domain
Users Management

Endpoints:
- `GET /users/`
- `PATCH /users/{id}/extensions`

Features:
- Assign extended roles
- Scope validation
- Role compatibility validation

Extension rules:
- Teacher -> `year_head`, `class_coordinator`, `club_coordinator`
- Student -> `club_president`

Invalid combinations return `400`.

### 6.3 Academic Structure Domain
Order of dependency:
1. courses
2. departments
3. branches
4. years
5. sections/classes

Endpoints:
- `/courses`
- `/departments`
- `/branches`
- `/years`
- `/sections`

Validation:
- Cannot create section without valid year + branch
- Cannot delete upstream entity with active dependencies

### 6.4 Academic Operations Domain
Collections:
- students
- subjects
- assignments
- submissions
- evaluations
- review_tickets
- enrollments

Endpoints:
- `/students`
- `/subjects`
- `/assignments`
- `/submissions`
- `/evaluations`
- `/review-tickets`
- `/enrollments`

### 6.5 Clubs Governance Domain
Club lifecycle states (replace legacy `is_active`):
- draft
- pending_activation
- active
- registration_closed
- suspended
- archived
- dormant

State rules:
- draft -> active (requires coordinator)
- active -> archived (no pending events)
- inactive clubs auto-mark dormant after inactivity

Endpoints:
- `/clubs`
- `/clubs/{id}`
- `/clubs/{id}/members`
- `/clubs/{id}/applications`
- `/club-events`
- `/event-registrations`

Admin capabilities:
- Activate / suspend / archive club
- Assign coordinator
- Open / close registration
- Approve / reject applications
- View analytics

### 6.6 Communication Domain
Endpoints:
- `/notices`
- `/notifications`

Add preview endpoint:
- `POST /admin/communication/preview-target`

Returns:
- Matched users count
- Estimated reach before publish

### 6.7 Compliance and Audit Domain
Audit Logs Upgrade fields:
```json
{
  "action_type": "",
  "resource_type": "",
  "resource_id": "",
  "old_value": {},
  "new_value": {},
  "ip_address": "",
  "user_agent": "",
  "severity": "low|medium|high",
  "timestamp": ""
}
```

Endpoint:
- `GET /audit-logs`

Filters:
- by user
- by date range
- by resource
- by severity

### 6.8 Analytics Domain
Platform metrics:
- Daily active users
- Login count
- Assignment completion %
- Club participation %
- Event attendance %
- Review ticket SLA

Collection:
- `platform_metrics`

Endpoint:
- `GET /admin/analytics/platform`

### 6.9 System Health Domain
Endpoint:
- `GET /admin/system/health`

Returns:
- DB status
- Collection counts
- Uptime
- Error count
- Active sessions
- Slow query logs

### 6.10 Recovery Domain (Soft Delete System)
All destructive operations use:
```json
{
  "is_deleted": true,
  "deleted_at": "",
  "deleted_by": ""
}
```

Recovery endpoints:
- `GET /admin/recovery`
- `PATCH /admin/recovery/{collection}/{id}/restore`

### 6.11 Developer Domain
Admin-only technical controls:
- Toggle maintenance mode
- Feature flags
- Background job status
- Index rebuild

---

## 7) Authentication and Session Model

Login:
- `POST /auth/login`

Session validation:
- `GET /auth/me`

Upgrade recommendation:
- Add `token_version`
- Increment on password change to invalidate old tokens

---

## 8) Mongo Collections Admin Controls
- users
- courses
- departments
- branches
- years
- classes
- students
- subjects
- assignments
- submissions
- evaluations
- review_tickets
- enrollments
- notices
- notifications
- clubs
- club_members
- club_applications
- club_events
- event_registrations
- audit_logs
- admin_actions
- platform_metrics
- settings

---

## 9) Error Handling Standard
Error envelope:
```json
{
  "success": false,
  "detail": "Message",
  "error_id": "UUID"
}
```

Header:
- `X-Error-Id`

---

## 10) Security Requirements
- Strong `JWT_SECRET`
- Token versioning
- Rate limiting on login
- Role-based middleware enforcement
- CORS origin whitelist
- Limit `super_admin` accounts
- No direct DB manipulation

---

## 11) Admin QA Checklist

### Access
- Admin can access all domains
- Other roles blocked appropriately

### Governance
- Extension updates validated
- Invalid combinations rejected

### Academic
- Dependencies enforced

### Clubs
- Activation requires coordinator
- Registration toggle works
- Application approval works

### Communication
- Preview reach works
- Announcements visible in feed

### Audit
- Logs recorded for every admin action

### Recovery
- Soft delete works
- Restore works

---

## 12) Deployment Readiness
Before production:
- Indexes auto-create successfully
- Admin login stable
- All admin routes render
- Dashboard aggregation performs < 300ms
- Audit logging verified
- Recovery tested
- Production build passes

---

## 13) Rebuild Order (Recommended)
### Phase 1
- Security middleware
- Permission framework
- Auth + users

### Phase 2
- Academic structure

### Phase 3
- Operations

### Phase 4
- Clubs governance

### Phase 5
- Audit + analytics

### Phase 6
- System health + recovery

---

## 14) Future Expansion Ready
Admin Module supports:
- AI analytics layer
- Multi-tenant mode
- Department-level admin
- SLA tracking engine
- Feature flag system
- Platform-wide policy engine