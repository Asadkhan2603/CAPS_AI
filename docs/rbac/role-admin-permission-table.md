# Admin Roles And Permissions

## Admin Role Table

| Role Code | Role Name | Scope Required | Permission Coverage |
| --- | --- | --- | --- |
| `SUPER_ADMIN` | Super Admin | `No` | All `110` RBAC permissions across every module and action |
| `COMPLIANCE_ADMIN` | Compliance Admin | `No` | `complaints`: `view`, `edit`, `approve`, `export`, `generate` ; `reports`: `view`, `export`, `generate` ; `analytics`: `view`, `export`, `generate` ; `audit`: `view`, `export`, `generate` ; `system`: `view` |
| `ACADEMIC_ADMIN` | Academic Admin | `No` | `student_management`: `view`, `create`, `edit`, `delete`, `approve`, `activate`, `deactivate`, `export`, `generate` ; `faculty_management`: `view`, `create`, `edit`, `delete`, `approve`, `activate`, `deactivate`, `export`, `generate` ; `subjects`: `view`, `create`, `edit`, `delete`, `approve`, `activate`, `deactivate`, `export`, `generate` ; `communication`: `view`, `create`, `edit`, `delete`, `approve` ; `clubs`: `view`, `create`, `edit`, `delete`, `approve`, `export`, `generate` ; `complaints`: `view`, `approve`, `export`, `generate` ; `reports`: `view`, `export`, `generate` ; `analytics`: `view`, `export`, `generate` |
| `YEAR_ADMIN` | Year Admin | `Yes` | `student_management`: `view`, `edit`, `approve`, `activate`, `deactivate`, `export`, `generate` ; `subjects`: `view`, `export`, `generate` ; `communication`: `view`, `create`, `edit` ; `complaints`: `view`, `approve` ; `reports`: `view`, `export`, `generate` |
| `HOD` | Head of Department | `Yes` | `student_management`: `view`, `approve`, `export`, `generate` ; `faculty_management`: `view`, `edit`, `approve`, `activate`, `deactivate`, `export`, `generate` ; `subjects`: `view`, `edit`, `approve`, `export`, `generate` ; `communication`: `view`, `create`, `edit`, `approve` ; `complaints`: `view`, `approve` ; `reports`: `view`, `export`, `generate` |
| `DEAN` | Dean | `Yes` | `student_management`: `view`, `approve`, `export`, `generate` ; `faculty_management`: `view`, `approve`, `activate`, `deactivate`, `export`, `generate` ; `subjects`: `view`, `approve`, `export`, `generate` ; `communication`: `view`, `approve`, `export`, `generate` ; `complaints`: `view`, `approve`, `export`, `generate` ; `reports`: `view`, `approve`, `export`, `generate` ; `analytics`: `view`, `export`, `generate` ; `audit`: `view`, `export`, `generate` |

## Scope Notes

| Role Code | Typical Scope Fields |
| --- | --- |
| `SUPER_ADMIN` | none |
| `COMPLIANCE_ADMIN` | none |
| `ACADEMIC_ADMIN` | none |
| `YEAR_ADMIN` | `year_id` |
| `HOD` | `department_id` |
| `DEAN` | `department_id` |

## Permission Modules

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

## Permission Actions

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

## References

- RBAC source: `backend/app/services/rbac.py`
- Design snapshot: `docs/rbac/role-permission-mapping.json`
- Permission inventory: `docs/rbac/permission-inventory.md`
