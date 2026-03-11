# RBAC Module Master

## Module Overview
This section provides a standardized summary for the module. Refer to the detailed sections below for full context.

## Responsibilities
- Core responsibilities are described in the detailed sections below.

## Components
- Primary backend endpoints, schemas, and UI surfaces are listed below.

## API Endpoints
- Refer to the API endpoint inventory in this document.

## Data Models
- Refer to the data model details in this document.

## Workflows
- Refer to the workflow and lifecycle sections below.

## Dependencies
- Refer to dependency notes in this document.

## Known Limitations
- Refer to current limitations described below.

## Improvements
- Refer to improvement opportunities listed below.


## Module Tree

```text
RBAC Module
|-- Base Roles
|-- Admin Types
|-- Extension Roles
|-- Permission Registry
|-- Frontend Access Helpers
`-- Route And Action Enforcement
```

## Internal Entity And Flow Tree

```text
User role model
|-- Base role
|-- Admin subtype
|-- Extension role
`-- Permission checks across API and UI
```

Primary implementation sources:

- `backend/app/core/permission_registry.py`
- `backend/app/core/security.py`
- `backend/app/api/v1/endpoints/users.py`
- `backend/app/schemas/user.py`
- `frontend/src/config/featureAccess.js`
- `frontend/src/utils/permissions.js`
- `frontend/src/routes/ProtectedRoute.jsx`
- `frontend/src/pages/UsersPage.jsx`

Related references:

- `docs/ACADEMIC_SETUP_LOGIC_AUDIT.md`
- `docs/modules/GOVERNANCE_MODULE_MASTER.md`
- `backend/tests/test_academic_permissions.py`
- `frontend/src/utils/permissions.test.js`

This document describes the RBAC system as implemented today, including backend authorization, user classification, extension roles, scoped permissions, and frontend route gating.

## 1. Module Overview

The RBAC module controls who can access which parts of CAPS AI and under what conditions.

The current system is not a flat `role -> page` model. It has multiple layers:

1. primary role
2. admin subtype
3. extension roles
4. optional role scope
5. backend permission checks
6. frontend feature gating

That makes the authorization model more expressive than simple role checks, but it also means policy can drift if the layers are not documented and tested together.

## 2. Authorization Architecture

The RBAC implementation is split into two separate but related layers.

### Backend Source Of Truth

The backend is authoritative.

Authorization is enforced through:

- JWT identity claims
- `get_current_user(...)`
- `require_roles(...)`
- `require_permission(...)`
- role-specific extension helpers

Important rule:

- frontend checks are only UX-level gating
- backend checks decide actual permission to execute the action

### Frontend Access Layer

The frontend uses:

- `FEATURE_ACCESS` in `frontend/src/config/featureAccess.js`
- `canAccessFeature(...)` in `frontend/src/utils/permissions.js`
- `ProtectedRoute.jsx`

This determines:

- whether a route is shown
- whether a sidebar item appears
- whether the user is redirected away from a page

It does not replace backend enforcement.

## 3. Identity Model

### Primary User Roles

Observed core roles in the current codebase:

- `admin`
- `teacher`
- `student`

These are stored on the user and embedded in JWT tokens.

### Admin Types

Admin accounts may carry an `admin_type`.

Observed admin types in current policy, routes, and tests:

- `super_admin`
- `admin`
- `academic_admin`
- `compliance_admin`
- `department_admin`

Behavior:

- `admin_type` is only valid when `role = admin`
- legacy admin users without `admin_type` are treated as `admin` by `_resolved_admin_type(...)`

Important implementation drift:

- [user.py](/backend/app/schemas/user.py) currently types `AdminType` as:
  - `super_admin`
  - `admin`
  - `academic_admin`
  - `compliance_admin`
- but the live backend permission policy, frontend feature matrix, and tests also rely on:
  - `department_admin`

This means the runtime RBAC model recognizes `department_admin`, but the typed schema contract still lags behind it.

### Extended Roles

Extended roles are secondary capabilities layered onto teacher or student users.

Current supported teacher extensions:

- `year_head`
- `class_coordinator`
- `club_coordinator`

Current supported student extension:

- `club_president`

Extended roles are stored in:

- `users.extended_roles`

Important constraint:

- [users.py](/backend/app/api/v1/endpoints/users.py) rejects `extended_roles` during user creation for non-teacher accounts
- but later extension-role updates explicitly support:
  - teacher extensions
  - student `club_president`

So user creation and user extension editing are not fully aligned.

### Role Scope

`role_scope` stores contextual boundaries for an extended role.

Examples already implemented:

- `class_coordinator.class_id`
- derived class coordinator academic scope:
  - `faculty_id`
  - `department_id`
  - `program_id`
  - `specialization_id`
  - `department_code`
  - `course_id`
  - `year_id`
  - `batch_id`
  - `semester_id`
- `club_president.club_id`

This means the RBAC module is not only role-aware. It is also partially context-aware.

## 4. Token And Session Claims

The security layer creates:

- access tokens
- refresh tokens

JWT payload fields currently include:

- `jti`
- `token_type`
- `sub`
- `email`
- `role`
- `admin_type`
- `extended_roles`
- `exp`

Important note:

- `role_scope` is not embedded in the token payload
- role scope is read from the current user document after token validation

This is the correct direction because it reduces stale-scope risk compared to long-lived embedded scope claims.

## 5. Backend Security Primitives

### `get_current_user(...)`

Purpose:

- decode token
- check blacklist
- load user document from database

Behavior:

- rejects invalid token
- rejects revoked token
- rejects missing user

### `require_roles(allowed_roles)`

Purpose:

- role-only authorization gate

Behavior:

- allows access if `current_user.role` is in allowed list
- otherwise raises 403

Use case:

- broad read access or simpler write routes

### `require_permission(permission)`

Purpose:

- permission registry backed authorization

Behavior:

- evaluates `has_permission(...)`
- raises 403 with:
  - `Missing required permission: <permission>`

This is the main RBAC abstraction for fine-grained backend authorization.

Important runtime value:

- explicit permission names make failures easier to test and reason about than generic role-only 403 responses

### `require_teacher_extensions(...)`

Purpose:

- require teacher role and one of specified teacher extensions

### `require_admin_or_teacher_extensions(...)`

Purpose:

- allow admin directly
- otherwise require teacher with specified supervisory extension

## 6. Permission Registry

The permission registry lives in:

- `backend/app/core/permission_registry.py`

It supports policy matching across:

- `roles`
- `admin_types`
- `teacher_extensions`
- `student_extensions`

### Current Permission Keys

#### User Administration

- `users.read`
- `users.update`

#### Analytics / Audit / System

- `analytics.read`
- `audit.read`
- `system.read`

#### Communication / Announcement Publishing

- `announcements.publish`
- `communication:publish`

#### Academic Setup

- `faculties.manage`
- `departments.manage`
- `programs.manage`
- `specializations.manage`
- `batches.manage`
- `semesters.manage`
- `sections.manage`

#### Clubs

- `clubs.manage`
- `club:create`
- `club:update`

#### Legacy / Transitional

- `academic:manage`
- `admin:analytics`

### Important Registry Behavior

For admins:

- permission match can depend on `admin_type`

For teachers:

- permission match can depend on teacher extension roles

For students:

- permission match can depend on student extension roles

## 7. Effective Permission Model

### Admin Policy

#### `users.read`

Allowed:

- `super_admin`
- `admin`

#### `users.update`

Allowed:

- `super_admin`

#### `analytics.read`

Allowed:

- `super_admin`
- `admin`
- `academic_admin`
- `compliance_admin`

#### `audit.read`

Allowed:

- `super_admin`
- `admin`
- `compliance_admin`

#### `system.read`

Allowed:

- `super_admin`
- `admin`
- `compliance_admin`

This permission is currently reused by:

- admin system diagnostics
- admin recovery
- governance admin APIs

That works, but it is semantically broader than the name suggests.

### Academic Setup Policy

Core academic setup entities:

- `faculties.manage`
- `departments.manage`

Allowed:

- `super_admin`
- `admin`
- `academic_admin`

Lower canonical hierarchy:

- `programs.manage`
- `specializations.manage`
- `batches.manage`
- `semesters.manage`
- `sections.manage`

Allowed:

- `super_admin`
- `admin`
- `academic_admin`
- `department_admin`
- `department_admin`

### Teacher Extension Based Policy

`announcements.publish` and `communication:publish` allow teacher access only when the teacher has one of:

- `year_head`
- `class_coordinator`
- `club_coordinator`

`clubs.manage` allows teacher access only when the teacher has:

- `club_coordinator`

### Student Extension Based Policy

The registry supports student extension checks, but the current visible usage is limited compared to admin and teacher paths.

## 8. Route-Level Enforcement Patterns

### Role-Based Endpoints

Many endpoints still use `require_roles(...)`.

Examples:

- timetable routes
- notifications
- review tickets
- evaluations
- groups

This is appropriate where access rules are broad and mostly role-level.

### Permission-Based Endpoints

Sensitive or administrative endpoints use `require_permission(...)`.

Examples:

- users
- governance admin routes
- academic setup write routes
- communication publish routes

However, some sensitive routes still remain outside this normalized model.

### Mixed Reality

The system currently uses both:

- explicit permission keys
- simple role gates

This is not inherently wrong, but it means the RBAC model is partly normalized and partly pragmatic.

Important current examples of drift:

- academic setup writes now use entity-level permissions
- `students.py` and `subjects.py` still rely on legacy `academic:manage`
- `/audit-logs` still uses `require_roles(...)` even though `audit.read` exists in the registry

## 9. User Management And Permission Editing

The main RBAC management UI is currently in:

- `frontend/src/pages/UsersPage.jsx`

### What It Supports

For teachers:

- toggle extension roles
- assign class coordinator scope using academic hierarchy selectors

For students:

- toggle `club_president`
- assign club scope

### Backend Endpoint

User extension editing is handled through:

- `PATCH /users/{user_id}/extensions`

Protected by:

- `require_permission("users.update")`

And additionally governed by:

- `enforce_review_approval(..., review_type="role_change")`

This is important:

- role and extension changes are already tied into governance review infrastructure

### Scope Propagation Logic

When assigning `class_coordinator` with a class id:

- backend loads the class
- clears previous coordinator assignments for that user
- assigns `class_coordinator_user_id` on the selected class
- derives scope fields from the class document

When removing `class_coordinator`:

- class scope is removed
- class coordinator assignments are cleared from classes

When assigning `club_president`:

- backend validates club existence
- clears previous club president assignments for that user
- assigns `president_user_id` on the selected club

This means role-scope assignment is not only stored on the user. It also updates dependent domain records.

Important limitation:

- `PATCH /users/{user_id}/extensions` is the real extension-management surface
- `POST /users/` does not support the full effective subtype and extension matrix that later exists in the system

## 10. Frontend Route Gating

### `FEATURE_ACCESS`

Frontend feature access is declared in:

- `frontend/src/config/featureAccess.js`

Each feature may specify:

- `allowedRoles`
- `requiredTeacherExtensions`
- `requiredAdminTypes`
- `deleteGovernance`

This drives:

- route protection
- sidebar visibility
- feature availability in dashboard navigation

### `canAccessFeature(...)`

Behavior:

- checks user role
- checks required teacher extensions
- checks required admin types for admin users

Helper behavior worth noting:

- `hasRole(...)` treats an empty `allowedRoles` list as permissive
- `hasAnyTeacherExtension(...)` treats non-teacher users as passing teacher-extension checks

That is acceptable because callers are expected to provide a role gate first, but it means frontend access helpers are intentionally convenience-oriented rather than strict policy engines.

### `ProtectedRoute.jsx`

Behavior:

- redirects unauthenticated users to `/login`
- redirects unauthorized users to `/dashboard`

This is a UX control, not a security boundary.

## 11. Current Frontend Permission Matrix

### Admin Surfaces

Admin pages such as:

- governance
- admin dashboard
- admin analytics
- admin system
- admin recovery
- admin academic structure

use:

- `allowedRoles: ['admin']`
- route-level `requiredAdminTypes` where needed

### Academic Setup Surfaces

Academic setup pages further refine admin access with `requiredAdminTypes`.

Examples:

- `faculties` excludes `department_admin`
- `programs` allows `department_admin`
- `sections` allows both admin and teacher at the UI layer

This now mirrors the backend academic permission split validated in:

- [test_academic_permissions.py](/backend/tests/test_academic_permissions.py)
- [permissions.test.js](/frontend/src/utils/permissions.test.js)

### General Multi-Role Pages

Examples:

- dashboard
- analytics
- timetable
- profile

allow some or all of:

- admin
- teacher
- student

## 12. Current Strengths

The RBAC system already has several strong foundations.

### Strong Areas

- backend remains source of truth
- permission registry supports multiple actor dimensions
- legacy admin fallback is handled explicitly
- teacher extension roles are real and operational
- role scope is partially implemented for contextual access
- user extension changes are governance-protected
- frontend permission tests exist
- academic permission alignment has improved significantly

## 13. Current Gaps And Risks

### Row-Level Scope Is Incomplete

This is the biggest RBAC gap.

The system supports:

- extension roles
- scope storage

But many permission checks still grant global access once the permission gate passes.

Example:

- `department_admin` can pass lower-hierarchy academic permission gates globally unless a route adds ownership validation

This remains the largest structural RBAC gap in the platform.

### Permission Semantics Are Not Fully Normalized

Some endpoints still use:

- `require_roles(...)`

where permission keys could be clearer or more auditable.

Some modules still rely on older keys such as:

- `academic:manage`

This remains in use in at least:

- `students.py`
- `subjects.py`

This means the permission registry has advanced faster than the full route inventory.

### Frontend And Backend Are Aligned Only Partially

The academic setup permission split now has tests, but full platform-wide alignment is not guaranteed.

Frontend still remains:

- UX gating
- not a security boundary

The strongest area of current alignment is academic setup. Full module-wide alignment still does not exist.

### Governance Admin Routes Use `system.read`

This is a naming mismatch more than a breakage.

Mutation operations in governance still use a permission called:

- `system.read`

That works technically, but it is semantically coarse.

### Audit Log Read Scope Is Broad

Audit log access allows:

- admin
- teacher

This may be intended, but it broadens sensitive operational visibility.

It also conflicts with the narrower backend registry key:

- `audit.read`

which currently allows only:

- `super_admin`
- `admin`
- `compliance_admin`

### Schema Drift For `department_admin`

This is now the clearest typed RBAC defect.

Current state:

- frontend routes and feature access use `department_admin`
- backend permission registry grants real capabilities to `department_admin`
- backend tests assert those capabilities
- user schema type does not include `department_admin`

This should be resolved explicitly. The current mixed state is not coherent.

## 14. Testing Requirements

### Backend Tests

- `has_permission(...)` behavior for admin types
- `has_permission(...)` behavior for teacher extensions
- missing permission registry key returns false
- legacy admin fallback resolves to `admin`
- `require_permission(...)` blocks correctly
- `require_roles(...)` blocks correctly
- role change governance enforcement on `/users/{id}/extensions`
- schema acceptance for every supported admin subtype once the runtime subtype list is finalized

### Frontend Tests

- `canAccessFeature(...)` for admin types
- `canAccessFeature(...)` for teacher extension roles
- route gating in `ProtectedRoute`
- academic feature matrix alignment tests
- sidebar and route visibility for `academic_admin`, `compliance_admin`, and `department_admin`

### Integration Tests

- user extension update changes `role_scope`
- class coordinator assignment updates `classes.class_coordinator_user_id`
- club president assignment updates `clubs.president_user_id`
- disallowed extension for role is rejected
- governance review required for role change when policy enabled

## 15. Recommended Cleanup Strategy

### Phase 1

Finish permission normalization.

- replace remaining `academic:manage` usage with entity-level keys where appropriate
- introduce clearer governance-specific permissions instead of reusing `system.read`
- align schema-level admin subtype definitions with the effective runtime policy, especially `department_admin`

### Phase 2

Strengthen scoped authorization.

- enforce row-level scope for `department_admin`
- use stored `role_scope` more consistently in write paths
- make scope-aware checks reusable instead of re-implementing them route by route

### Phase 3

Separate concerns more clearly.

- distinguish read permissions from mutation permissions
- distinguish operational admin from governance admin more explicitly

### Phase 4

Expand policy tests.

- add broader backend + frontend permission alignment coverage
- add module-by-module route-to-permission documentation

## Final Summary

The RBAC system in CAPS AI is already richer than a simple role gate. It supports:

- primary roles
- admin subtypes
- teacher and student extension roles
- partial contextual scope
- backend permission registry
- frontend feature gating
- governance-protected role changes

Its main weakness is not lack of expressive power. The main weakness is incomplete scope enforcement and some remaining policy inconsistency across modules.

The right next step is not inventing a new RBAC model. It is finishing normalization and enforcing scope consistently across the codebase.

