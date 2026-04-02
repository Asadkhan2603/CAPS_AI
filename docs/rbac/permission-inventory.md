# Permission Inventory

## Current Counts

- RBAC permissions: `110`
- Legacy permission keys: `24`
- Total named permission keys across the codebase: `134`

## RBAC Formula

The RBAC catalog currently defines:

- `11` permission groups
- `10` actions per group

So the RBAC total is:

`11 x 10 = 110`

## RBAC Permission Groups

- `student_management`
- `faculty_management`
- `complaints`
- `reports`
- `users`
- `communication`
- `clubs`
- `subjects`
- `analytics`
- `audit`
- `system`

## RBAC Actions

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

## Source Of Truth

- RBAC catalog: `backend/app/services/rbac.py`
- Legacy permission registry: `backend/app/core/permission_registry.py`
- Role-permission design snapshot: `docs/rbac/role-permission-mapping.json`
