# RBAC Deployment Hardening

## Purpose

This runbook covers the production rollout steps for the RBAC-backed admin system, including runtime safeguards, environment requirements, and post-deploy verification.

## Required Runtime Settings

Set these in non-development environments:

- `JWT_SECRET` to a long random secret
- `BULK_STUDENT_TEMP_PASSWORD` to a non-default temporary password
- `AUTH_COOKIE_SECURE=true`
- `AUTH_COOKIE_SAME_SITE=strict` or `lax` based on frontend deployment topology
- `RATE_LIMIT_ENABLED=true`
- `RATE_LIMIT_MAX_REQUESTS` to an environment-appropriate threshold
- `RATE_LIMIT_WINDOW_SECONDS` to the matching window
- `REDIS_ENABLED=true` with a reachable `REDIS_URL`

## Migration And Seeding

Before exposing the RBAC UI or APIs:

1. run `python scripts/migrate_rbac_schema_version.py`
2. verify the `roles`, `permissions`, `role_permissions`, `user_permissions`, and `scopes` collections exist
3. log in once as the bootstrap admin to ensure default RBAC state is seeded
4. confirm system roles include `scope_required` metadata for `YEAR_ADMIN`, `HOD`, and `DEAN`

## Deployment Checklist

1. deploy backend with the RBAC schema migration applied
2. confirm rate limiting is enabled on auth and mutating routes
3. confirm refresh cookie settings are secure for the target environment
4. confirm `/api/v1/auth/me` returns `rbac_role_code`, `permissions`, and `scopes` for admin users
5. confirm `/api/v1/admin/rbac/design` loads for `SUPER_ADMIN`
6. confirm a scoped admin can only access assigned sections, students, enrollments, and programs
7. confirm scoped admins are blocked from global analytics and organization-wide hierarchy writes
8. confirm RBAC admin mutations write audit records

## Post-Deploy Smoke Tests

- `SUPER_ADMIN` can create a scoped `HOD`
- scoped `HOD` can list only in-scope programs, sections, students, and enrollments
- scoped `HOD` receives `403` on out-of-scope records
- deny overrides remove access immediately after the next login
- audit log entries exist for RBAC role/admin changes

## Rollback Notes

If the rollout must be paused:

- disable access to the Super Admin RBAC UI route
- keep the RBAC collections intact
- revert only the new endpoint enforcement if needed
- do not delete seeded roles or permission records, because existing admin tokens and records now reference them
