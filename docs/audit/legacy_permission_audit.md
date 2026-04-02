# Legacy Permission System Audit

## Summary
- Final Decision: `NEEDS_MIGRATION`
- Reason: The legacy system is still on the critical path for backend authorization, frontend feature gating, and several permissions that do not exist as first-class RBAC permissions. Removing it now would break active APIs and would also leave existing authorization drift unresolved.

## Current State
- Total RBAC permissions: `28`
- Total Legacy permissions: `24`
- Overlap count: `15` semantic overlaps through `LEGACY_PERMISSION_ALIASES` (`0` exact key matches)
- Unique legacy permissions: `9` legacy-only permissions with no RBAC alias coverage

## Key Findings

### 1. Duplications
- There are no exact duplicate permission keys between legacy and RBAC. The systems use different naming models:
  - Legacy: dotted and colon-based keys such as `users.read`, `academic:manage`, `club:create`
  - RBAC: normalized `module.action` keys such as `student_management.edit`
- The real duplication is semantic, not exact. `backend/app/services/rbac.py` bridges `15` legacy keys into RBAC through `LEGACY_PERMISSION_ALIASES`.
- Duplicate semantic mappings:

| Legacy Permission | RBAC Alias Target(s) |
| --- | --- |
| `analytics.read` | `reports.view`, `reports.manage_reports` |
| `audit.read` | `reports.view`, `reports.manage_reports` |
| `system.read` | `reports.manage_reports` |
| `universities.manage` | `faculty_management.create`, `faculty_management.edit`, `faculty_management.delete` |
| `faculties.manage` | `faculty_management.create`, `faculty_management.edit`, `faculty_management.delete` |
| `departments.manage` | `faculty_management.create`, `faculty_management.edit`, `faculty_management.delete` |
| `programs.manage` | `student_management.create`, `student_management.edit`, `student_management.delete` |
| `specializations.manage` | `student_management.create`, `student_management.edit`, `student_management.delete` |
| `batches.manage` | `student_management.create`, `student_management.edit`, `student_management.delete` |
| `semesters.manage` | `student_management.create`, `student_management.edit`, `student_management.delete` |
| `sections.manage` | `student_management.create`, `student_management.edit`, `student_management.delete` |
| `students.manage` | `student_management.create`, `student_management.edit`, `student_management.delete` |
| `students.bulk_import` | `student_management.create`, `student_management.manage_users` |
| `students.bulk_map` | `student_management.edit` |
| `sections.lock_mapping` | `student_management.approve` |

### 2. Legacy-Only Dependencies
- Active backend APIs still depend only on legacy permissions with no RBAC alias:
  - `backend/app/api/v1/endpoints/users.py`
    - `users.read`
    - `users.update`
  - `backend/app/api/v1/endpoints/subjects.py`
    - `academic:manage`
  - `backend/app/api/v1/endpoints/admin_communication.py`
    - `announcements.publish`
  - `backend/app/api/v1/endpoints/clubs.py`
    - `club:create`
    - `club:update`
- Direct business-logic checks still use legacy keys:
  - `backend/app/api/v1/endpoints/students.py`
    - `students.bulk_import`
    - `students.bulk_map`
  - `backend/app/api/v1/endpoints/enrollments.py`
    - `students.manage`
    - `students.bulk_map`
- Unused legacy permissions still exist in the registry and increase confusion:
  - `admin:analytics`
  - `clubs.manage`
  - `communication:publish`
- Frontend access control still depends on legacy-style admin typing rather than RBAC role codes or RBAC permissions:
  - `frontend/src/config/featureAccess.js`
  - `frontend/src/config/navigationGroups.js`
  - `frontend/src/routes/AppRoutes.jsx`
  - `frontend/src/utils/permissions.js`
- The frontend still expects legacy admin types such as `admin` and `department_admin`, while the RBAC system roles are `SUPER_ADMIN`, `COMPLIANCE_ADMIN`, `ACADEMIC_ADMIN`, `YEAR_ADMIN`, `HOD`, and `DEAN`.

### 3. RBAC Gaps
- RBAC does not currently model several active legacy domains as first-class permissions:
  - user administration: `users.read`, `users.update`
  - communication publishing: `announcements.publish`
  - club administration: `club:create`, `club:update`, `clubs.manage`
  - subjects or generalized academic management: `academic:manage`
  - system, analytics, and audit administration as separate RBAC domains
- The backend uses direct RBAC role middleware only once:
  - `backend/app/api/v1/endpoints/admin_rbac.py` uses `check_role("SUPER_ADMIN")`
- Most backend permission checks still flow through the legacy wrapper:
  - `63` `require_permission(...)` uses
  - only `1` direct `check_role(...)` use
- Many endpoints bypass both RBAC and the legacy registry entirely by using broad role gates such as `require_roles(["admin"])` or `require_roles(["admin", "teacher"])`. This means RBAC is not yet the system-wide source of truth.

### 4. Naming & Design Issues
- Permission naming is inconsistent across the codebase:
  - dotted: `users.read`
  - colon-based: `academic:manage`, `club:create`
  - normalized RBAC: `student_management.manage_reports`
- Scope and resource specificity are lost in some alias mappings:
  - `universities.manage`, `faculties.manage`, and `departments.manage` all collapse into the same `faculty_management.*` RBAC bucket
  - `programs.manage`, `specializations.manage`, `batches.manage`, `semesters.manage`, `sections.manage`, and `students.manage` all collapse into `student_management.*`
- Ambiguous permission patterns remain:
  - `manage_users`
  - `manage_reports`
  - `academic:manage`
  - `clubs.manage`
- Authorization identity is split between:
  - `admin_type`
  - `rbac_role_code`
  - `permissions`
  - `requiredAdminTypes` in the frontend

### 5. Security Risks
- Over-permissive alias bridging currently widens access beyond the legacy intent:
  - `analytics.read` aliases to `reports.view` and `reports.manage_reports`
  - `audit.read` aliases to `reports.view` and `reports.manage_reports`
  - `system.read` aliases to `reports.manage_reports`
- Because of those aliases, the following RBAC roles can satisfy backend admin analytics, audit, or system checks even though the frontend hides those pages from them:
  - `YEAR_ADMIN`
  - `HOD`
  - `DEAN`
- This creates a direct API-level access mismatch between frontend navigation rules and backend enforcement.
- `sections.lock_mapping` is mapped to `student_management.approve`, which is not semantically equivalent and may grant lock authority too broadly.
- Broad `require_roles(["admin"])` checks remain on sensitive modules, which bypass permission granularity entirely:
  - `backend/app/api/v1/endpoints/ai_admin.py`
  - `backend/app/api/v1/endpoints/branding.py`
  - `backend/app/api/v1/endpoints/review_tickets.py`
  - `backend/app/api/v1/endpoints/club_events.py`
  - `backend/app/api/v1/endpoints/timetables.py`
  - `backend/app/api/v1/endpoints/evaluations_lifecycle.py`
- Dual authorization paths make it easier for backend and frontend policy to drift apart:
  - frontend allows or hides by `admin_type`
  - backend resolves by legacy registry plus optional RBAC alias bridge

### 6. Maintainability Issues
- The codebase currently maintains:
  - `24` legacy permissions
  - `28` RBAC permissions
  - a legacy admin-type matrix
  - an RBAC role-permission matrix
  - alias glue between the two
- Debugging authorization now requires checking multiple layers:
  - `PERMISSION_REGISTRY`
  - `LEGACY_PERMISSION_ALIASES`
  - JWT token `permissions`
  - `admin_type`
  - `rbac_role_code`
  - route-level `require_roles(...)`
- The frontend and backend do not share one source of truth for authorization.
- The coexistence of legacy-only, aliased, and bypassed paths makes future permission changes risky and slow.

## Risk Assessment

| Risk | Impact | Affected Area |
|------|--------|---------------|
| Delete legacy permissions now | Critical | `users`, `subjects`, `admin_communication`, `clubs` APIs would lose authorization checks or fail closed |
| Keep current alias bridge unchanged | High | `admin_analytics`, `audit_logs`, `admin_governance`, `admin_system`, `admin_recovery` can be reached through overly broad report permissions |
| Keep frontend on legacy `admin_type` values | High | UI access will stay inconsistent for `YEAR_ADMIN`, `HOD`, `DEAN`, and any future custom RBAC roles |
| Continue using broad `require_roles(["admin"])` checks | High | Sensitive admin routes bypass permission-level authorization entirely |
| Leave legacy-only permissions unmigrated | Medium | Permission model remains fragmented and hard to reason about |
| Maintain both systems long term | Medium | Debugging, onboarding, and policy changes remain costly and error-prone |

## Recommendation

- Clear action:
  - Migrate first
  - Keep legacy temporarily
  - Do not delete legacy yet

## Migration Plan (if needed)

Step-by-step:
1. Map every active legacy permission to an explicit RBAC permission or RBAC module. Add missing first-class RBAC domains for `users`, `communication`, `clubs`, `subjects`, `analytics`, `audit`, and `system`.
2. Replace semantic aliasing with exact RBAC permissions. Remove coarse mappings such as `system.read -> reports.manage_reports`.
3. Migrate backend routes from `require_permission(...)` legacy keys to explicit RBAC permission keys. Migrate direct `has_permission(...)` checks in `students.py` and `enrollments.py`.
4. Replace broad `require_roles(["admin"])` checks on sensitive endpoints with RBAC `check_role(...)` or RBAC permission checks.
5. Migrate frontend access control from `admin_type` and `requiredAdminTypes` to `rbac_role_code` or explicit permission claims.
6. Remove support for legacy-only admin types such as `department_admin` once equivalent RBAC roles or custom roles exist.
7. Add regression tests proving that each migrated API behaves the same or more strictly under RBAC.
8. Remove `PERMISSION_REGISTRY`, `LEGACY_PERMISSION_ALIASES`, and legacy admin-type dependencies only after all route, business-logic, and frontend checks are migrated.

## Final Verdict
- The legacy permission system is not safe to delete; it must be migrated out deliberately because it still authorizes active APIs, the frontend still depends on legacy admin typing, and the current RBAC alias bridge is already introducing security and consistency problems.
