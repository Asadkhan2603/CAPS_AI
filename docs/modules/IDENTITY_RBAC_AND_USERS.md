# Identity, RBAC, And Users

## Purpose

This module owns authentication, profile management, user administration, role scope, permission checks, and access-related compatibility rules.

## Data Model

Core records:

- users
- user sessions
- role and admin type metadata
- extended teacher roles
- role scope for class coordinator and related governance rules

Key fields:

- `role`
- `admin_type`
- `extended_roles`
- `role_scope`
- `faculty_id`, `department_id`, `program_id`, `specialization_id`

## APIs

Primary endpoints:

- `/auth/register`
- `/auth/login`
- `/auth/refresh`
- `/auth/logout`
- `/auth/me`
- `/auth/change-password`
- `/auth/profile`
- `/auth/profile/avatar`
- `/users`
- `/users/lookups`
- `/users/{user_id}`
- `/users/{user_id}/extensions`
- `/admin/rbac/design`
- `/admin/rbac/permissions`
- `/admin/rbac/roles`
- `/admin/rbac/admins`

## Workflow

1. user authenticates through `/auth/login`
2. frontend stores the access token in session-backed auth state
3. route guards use `FEATURE_ACCESS` and backend permissions
4. admin manages users and extensions through `/users`
5. teacher coordinator scope is enforced in section, timetable, and mapping flows
6. super admin manages dynamic admin roles, permission overrides, and scope assignments through `/admin/rbac/*`

## Dependencies

- `backend/app/domains/auth/`
- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/api/v1/endpoints/users.py`
- `backend/app/core/security.py`
- `backend/app/core/permission_registry.py`
- `backend/app/services/rbac.py`
- `docs/rbac/access-control-design.md`
- `docs/rbac/deployment-hardening.md`
- `docs/rbac/role-permission-mapping.json`
- `frontend/src/context/AuthContext.jsx`
- `frontend/src/routes/ProtectedRoute.jsx`
