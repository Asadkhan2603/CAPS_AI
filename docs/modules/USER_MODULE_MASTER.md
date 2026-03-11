# User Module Master

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
User Module
|-- User Master Records
|-- Role And Subtype Assignment
|-- Extension Role Management
|-- Governance-Gated Role Changes
`-- Cross-Module Authority References
```

## Internal Entity And Flow Tree

```text
User
|-- Role and subtype identity
|-- Extension roles
|-- Governance-protected mutations
`-- Referenced by coordinator, club, and admin modules
```

Primary implementation sources:

- `backend/app/api/v1/endpoints/users.py`
- `backend/app/models/users.py`
- `backend/app/schemas/user.py`
- `backend/app/core/permission_registry.py`
- `backend/app/core/security.py`
- `backend/app/services/governance.py`
- `backend/app/services/audit.py`
- `frontend/src/pages/UsersPage.jsx`
- `frontend/src/config/featureAccess.js`
- `frontend/src/utils/permissions.js`

Related references:

- `docs/modules/AUTH_MODULE_MASTER.md`
- `docs/modules/RBAC_MODULE_MASTER.md`
- `docs/modules/GOVERNANCE_MODULE_MASTER.md`
- `docs/modules/TEACHER_MODULE_MASTER.md`
- `docs/modules/STUDENT_MODULE_MASTER.md`

## 1. Module Overview

The user module is the administrative identity management layer of CAPS AI. It is not the same as the auth module.

Current separation of concerns:

- auth module:
  - login
  - tokens
  - logout
  - self-profile
  - avatar upload
- user module:
  - list users
  - create users
  - assign extension roles
  - attach role scope
  - deactivate users

The user module therefore answers:

- who exists in the system
- what base role they have
- which extension roles they hold
- what scope those extension roles apply to

This module is one of the main control points for RBAC and governance because it directly changes authority distribution.

## 2. Identity Model

### Base Roles

The core role field is:

- `admin`
- `teacher`
- `student`

### Admin Types

Admin users may additionally carry:

- `super_admin`
- `admin`
- `academic_admin`
- `compliance_admin`

Important implementation detail:

- user creation through `/users/` defaults admin users to `admin`
- bootstrap auth registration may default first admin to `super_admin`

So admin subtype depends on creation path.

### Extension Roles

The current extension role model allows:

- for teachers:
  - `year_head`
  - `class_coordinator`
  - `club_coordinator`
- for students:
  - `club_president`

Unsupported role-extension combinations are rejected.

### Role Scope

The user schema models role scope separately from base role.

Implemented scope objects:

- `class_coordinator`
- `club_president`

Class coordinator scope supports:

- `faculty_id`
- `department_id`
- `program_id`
- `specialization_id`
- `department_code`
- `course_id`
- `year_id`
- `batch_id`
- `semester_id`
- `class_id`

Club president scope supports:

- `club_id`

This is the structural bridge between user administration and row-level access control in academic and club modules.

## 3. Collections And Public Shape

### `users`

Purpose:

- canonical application identity store

Key fields used by the user module:

- `full_name`
- `email`
- `hashed_password`
- `role`
- `admin_type`
- `extended_roles`
- `role_scope`
- `is_active`
- `must_change_password`
- `profile`
- `avatar_filename`
- `avatar_updated_at`

Relations:

- class coordinator mapping to `classes.class_coordinator_user_id`
- club coordinator / president linkage to `clubs`
- auth module depends on the same collection for login

Public projection from `user_public(...)`:

- `id`
- `full_name`
- `email`
- `role`
- `admin_type`
- `extended_roles`
- `role_scope`
- `is_active`
- `must_change_password`
- `profile`
- `avatar_url`
- `avatar_updated_at`
- `created_at`

Important note:

- `hashed_password` is never returned publicly

## 4. Backend Logic Implemented

### List Users

`GET /users/`

Permission:

- `users.read`

Current registry mapping:

- admin role only
- admin types allowed:
  - `super_admin`
  - `admin`

Behavior:

- returns up to 1000 user rows
- no paging
- no filter
- no search

This is sufficient for small scale but not a scalable user administration endpoint.

### Create User

`POST /users/`

Permission:

- `users.update`

Current registry mapping:

- admin role only
- admin type allowed:
  - `super_admin`

Validation implemented:

- email normalized to lowercase
- duplicate email rejected
- non-teacher cannot carry extension roles
- non-admin cannot carry `admin_type`
- admin creation defaults `admin_type` to `admin`

Creation behavior:

- password is hashed at creation time
- `role_scope` starts as empty object
- `must_change_password` defaults to false
- `is_active` defaults to true

### Update Extension Roles

`PATCH /users/{user_id}/extensions`

Permission:

- `users.update`

This is the most important endpoint in the module.

It:

- validates that the target role supports extension roles
- validates that requested extension roles are allowed for that role
- optionally enforces governance approval when `role_change_approval_enabled` is on
- updates linked academic or club ownership records
- writes audit logs with old/new role state

### Governance Review Hook

Role changes are governed through:

- `enforce_review_approval(...)`
- `review_type = "role_change"`

If governance policy enables role-change approval:

- missing `review_id` blocks execution
- non-approved review blocks execution
- approved review allows change

This is one of the stronger governance integrations in the current codebase.

### Scope Propagation For `class_coordinator`

When assigning `class_coordinator`:

1. user-supplied scope is read
2. if `class_id` is provided:
   - class must exist
   - any existing class coordinator assignment for that user is cleared
   - selected class is updated to point to this user
   - scope is hydrated from class document:
     - `faculty_id`
     - `department_id`
     - `program_id`
     - `specialization_id`
     - `course_id`
     - `year_id`
     - `batch_id`
     - `semester_id`

When removing `class_coordinator`:

- `role_scope.class_coordinator` is removed
- all classes pointing to that user are cleared

This endpoint therefore does more than update the user document. It propagates authority into academic records.

### Scope Propagation For `club_president`

When assigning `club_president`:

1. supplied `club_id` is validated
2. any existing club presidency for the user is cleared
3. target club receives `president_user_id = user_id`
4. role scope is stored on the user

When removing `club_president`:

- user scope is cleared
- club presidency links are cleared

### Deactivate User

`DELETE /users/{user_id}`

Permission:

- `users.update`

Behavior:

- cannot deactivate self
- sets `is_active = false`
- clears `class_coordinator_user_id` from classes
- clears `coordinator_user_id` from clubs
- clears `president_user_id` from clubs
- writes audit event with `action_type = role_change`

Important point:

- this is not a hard delete
- user row remains in the system

## 5. Permission Model

### Current User Permissions

Defined in `permission_registry.py`:

- `users.read`
- `users.update`

Current allowed admin types:

- `users.read`
  - `super_admin`
  - `admin`
- `users.update`
  - `super_admin`

Practical consequence:

- normal admin can list users
- only super admin can create users, change extension roles, or deactivate users

This is a clear privilege split and one of the few places where admin-type separation is enforced cleanly.

## 6. Frontend Implementation

### `UsersPage.jsx`

This is the main user administration UI.

Implemented features:

- list teachers
- list students
- search teachers
- search students
- open per-user modal
- view details tab
- manage permissions tab

The page currently focuses on:

- teacher extension role assignment
- student club president assignment

### Permission Editing UI

Teacher extension toggles supported in UI:

- `year_head`
- `class_coordinator`
- `club_coordinator`

Student extension toggles supported in UI:

- `club_president`

### Scope Editing UI

For teacher `class_coordinator`, the UI allows scoped selection of:

- faculty
- department
- program
- specialization
- batch
- semester
- section

For student `club_president`, the UI allows:

- club selection

### Save Behavior

The page sends:

- `extended_roles`
- `role_scope`

to:

- `PATCH /users/{id}/extensions`

### Current UI Gap

The users page does not currently expose:

- user creation
- user deactivation
- admin subtype editing
- governance review_id prompt for role changes

That means part of the backend contract exists without equivalent admin UI support.

## 7. Frontend Access Model

`FEATURE_ACCESS.users` currently allows:

- role: `admin`
- admin types:
  - `super_admin`
  - `admin`

This means:

- super admin can enter the page and fully use backend write actions
- admin can enter the page but will be backend-blocked on `users.update` operations

That is a frontend/backend mismatch at action level.

The route guard is broad enough for read access, but not aligned to write capability.

## 8. Current Strengths

### Strong Separation Of Read vs Update

The system distinguishes:

- who can see users
- who can change user authority

That is correct for a privileged admin module.

### Role Scope Is First-Class

The user model does not only store extension names. It also stores scope context. This is necessary for future row-level authorization hardening.

### Governance Integration Exists

Role change is already wired into governance review approval. That is a high-value control.

### Side-Effect Synchronization Exists

Changing extension roles also updates:

- class coordinator links
- club president links

That prevents obvious drift between user authority and linked ownership records.

## 9. Current Gaps And Risks

### No UI For Governance Review On Role Change

Backend can require:

- approved `review_id`

But `UsersPage.jsx` does not currently prompt for or pass `review_id` when saving extensions.

So if two-person approval is enabled, the UI will fail on save.

### No User Create UI

Backend supports `POST /users/`, but the main user admin page does not expose creation flow.

### No User Deactivate UI

Backend supports deactivation, but the frontend page does not expose it.

### Frontend Access Is Broader Than Write Access

`admin` can open the page because `users.read` allows it.

But update actions require:

- `users.update`
- effectively super admin only

This can produce confusing UX unless action buttons are hidden or downgraded.

### No Pagination Or Server Search

`GET /users/` returns a large in-memory list with no filtering. That does not scale well.

### Role Scope Is Not Fully Enforced Everywhere

The user module stores `role_scope`, but many downstream modules still enforce ownership through:

- direct record fields
- extension presence
- coordinator links

and only partially through stored scope.

That means user administration is ahead of some downstream authorization consumers.

### Deactivate Uses Role-Change Audit Type

User deactivation is logged with:

- `action_type = role_change`

That is workable but semantically imprecise. Deactivation is identity lifecycle, not a role change.

## 10. Architectural Issues

### User Module vs Auth Module Overlap

The same `users` collection is used by:

- auth
- user admin
- RBAC
- profile rendering

This is normal, but the boundary is split by endpoint ownership rather than collection ownership.

Practical split:

- `/auth/*` manages self-service user state
- `/users/*` manages admin-controlled user state

### Extension Roles Are Mixed With Ownership Propagation

Updating a user's extension role also mutates:

- classes
- clubs

That is useful, but it means the user module has side effects into domain modules. It is not a pure identity service.

### Teacher Scope Still Carries Legacy Academic Fields

`ClassCoordinatorScope` still includes:

- `course_id`
- `year_id`

even though canonical academic direction is section-centered. This preserves legacy compatibility but keeps the user module coupled to both academic models.

## 11. Cleanup Strategy

### Phase 1

- add UI support for `review_id` when governance requires role-change approval
- disable write controls in `UsersPage.jsx` for non-super-admin users

### Phase 2

- add user create flow to frontend
- add user deactivate flow to frontend
- add pagination and server-side search to `/users/`

### Phase 3

- normalize audit action types:
  - separate `role_change`
  - `user_deactivation`
- document exact side effects of extension-role assignments

### Phase 4

- reduce legacy academic fields inside `ClassCoordinatorScope`
- move more downstream authorization to explicit `role_scope` checks

## 12. Testing Requirements

### Backend Tests

Required tests:

- user list permission split between `users.read` and `users.update`
- duplicate email rejection
- non-admin cannot set `admin_type`
- non-teacher cannot receive teacher extensions
- invalid extension role for target role rejected
- class coordinator scope assignment updates `classes.class_coordinator_user_id`
- removing class coordinator clears class links
- club president assignment updates `clubs.president_user_id`
- role change blocked when governance requires `review_id`
- deactivate self rejected
- deactivate user clears linked class and club ownership

### Frontend Tests

Required tests:

- users page hides or disables write actions for non-super-admin
- extension toggle and scope draft behavior
- governance-required save failure is surfaced correctly
- class scope dropdown narrowing works correctly

### Integration Tests

Required tests:

- role assignment in users module changes downstream access in sections, enrollments, timetable, and attendance
- governance-approved role change succeeds end to end
- governance-blocked role change fails with clear UI message

## Final Summary

The user module is the system authority-assignment layer. It already supports:

- privileged user creation
- extension-role assignment
- scope storage
- downstream ownership propagation
- governed role-change approval
- safe deactivation instead of hard delete

Its strongest parts are:

- explicit separation of `users.read` and `users.update`
- role-scope modeling
- governance integration
- propagation into classes and clubs

Its main gaps are:

- missing frontend create/deactivate flows
- missing `review_id` UI for governed role changes
- broad read UI for admins who cannot actually write
- poor scalability of the list endpoint

The next useful hardening move is to bring the frontend up to the real backend contract, especially for governance-aware role changes and super-admin-only write actions.
