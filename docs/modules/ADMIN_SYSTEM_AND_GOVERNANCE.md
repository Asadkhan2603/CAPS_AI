# Admin System And Governance

## Purpose

This module manages admin-only governance policies, destructive action reviews, recovery operations, audit visibility, and system health oversight.

## Data Model

Entities:

- governance policy state
- admin action reviews
- audit logs
- user sessions
- system health snapshots
- soft-deleted recoverable records

## APIs

Primary endpoints:

- `/audit-logs`
- `/review-tickets`
- `/admin/governance/policy`
- `/admin/governance/reviews`
- `/admin/governance/dashboard`
- `/admin/governance/sessions`
- `/admin/recovery`
- `/admin/recovery/{collection}/{item_id}/restore`
- `/admin/system/health`

## Workflow

1. admin policy defines destructive-action expectations
2. review tickets and governance reviews mediate risky operations
3. audit logs expose historical actions
4. recovery endpoints restore archived records when allowed
5. admin system health surfaces runtime and retention status

## Dependencies

- `backend/app/api/v1/endpoints/audit_logs.py`
- `backend/app/api/v1/endpoints/review_tickets.py`
- `backend/app/api/v1/endpoints/admin_governance.py`
- `backend/app/api/v1/endpoints/admin_recovery.py`
- `backend/app/api/v1/endpoints/admin_system.py`
- `backend/app/services/governance.py`
- `backend/app/services/system_health_snapshots.py`
