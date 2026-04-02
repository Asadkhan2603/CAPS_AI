# Access Control Design

## Overview

This RBAC design keeps the existing `users` collection as the authentication source of truth and adds dedicated RBAC collections for roles, permissions, role-to-permission links, user-level overrides, and scope assignments. The system is built for MongoDB but preserves the relational intent of the original requirement by modeling many-to-many relationships explicitly.

## Role Model

Admin accounts keep `role = "admin"` for compatibility with existing APIs and route guards.

Primary admin role assignment is stored as:

- `role_id`
- `rbac_role_code`
- `admin_type`

Supported system admin roles:

- `SUPER_ADMIN`
- `COMPLIANCE_ADMIN`
- `ACADEMIC_ADMIN`
- `YEAR_ADMIN`
- `HOD`
- `DEAN`

`SUPER_ADMIN` is the only role allowed to create or delete admin users and mutate role definitions.

## Permission Model

Permissions are normalized as `module + action`, with a generated key:

- `student_management.view`
- `users.assign_role`
- `complaints.approve`
- `analytics.generate`

Canonical actions:

- `view`
- `create`
- `edit`
- `delete`
- `approve`
- `assign_role`
- `activate`
- `deactivate`
- `export`
- `generate`

Canonical permission groups:

- `Student Management`
- `Faculty Management`
- `Complaints`
- `Reports`
- `Users`
- `Communication`
- `Clubs`
- `Subjects`
- `Analytics`
- `Audit`
- `System`

## Collections

Mongo collections used by the RBAC subsystem:

- `roles`
- `permissions`
- `role_permissions`
- `user_permissions`
- `scopes`

Relationship intent:

- one role -> many permissions through `role_permissions`
- one user -> one primary admin role through `users.role_id`
- one user -> optional permission overrides through `user_permissions`
- one user -> many scope rows through `scopes`

## Access Decision Flow

1. authenticate user and load `users` document
2. resolve admin role from `role_id` or `rbac_role_code`
3. load role permissions
4. merge user-level overrides
5. evaluate required role and permission
6. apply scope filter when the request targets department-scoped or year-scoped data
7. return `403 Forbidden` when any requirement fails

## Scope Rules

Scope rows may contain:

- `department_id`
- `year_id`

`year_id` is treated as the academic batch start year or cohort identifier, for example `2027`.

Scope behavior:

- `SUPER_ADMIN` bypasses scope filtering
- `HOD` is expected to carry `department_id`
- `YEAR_ADMIN` is expected to carry `year_id`
- `DEAN` may carry one or both, depending on faculty governance structure
- if a user has multiple scope rows, access is the union of those rows

Query filter strategy:

- one scope row becomes a direct filter
- multiple scope rows become an `$or` filter
- empty scope set means unrestricted only for `SUPER_ADMIN`; for other scoped roles it should be treated as misconfiguration

## JWT Claims

Access token payload includes:

- `sub`
- `email`
- `role`
- `admin_type`
- `rbac_role_code`
- `permissions`
- `scopes`

This keeps frontend route guards lightweight while the backend remains the enforcement source of truth.

## Audit Coverage

Audit events are written for:

- admin creation
- admin updates
- admin activation and deactivation
- admin soft delete
- role creation
- role permission updates
- role deletion
- login activity

## Compatibility Notes

Legacy non-admin access rules stay supported through the existing permission registry for:

- teachers
- students
- legacy admin accounts that do not yet have RBAC role links

This allows phased rollout without blocking the current platform.
