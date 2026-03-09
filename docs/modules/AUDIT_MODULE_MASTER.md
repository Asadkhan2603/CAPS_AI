# Audit Module Master

## Module Tree

```text
Audit Module
|-- Mutable Audit Logs
|-- Immutable Audit Chain
|-- Destructive Action Telemetry
|-- Compliance Consumers
`-- Admin Audit Views
```

## Internal Entity And Flow Tree

```text
User action
`-- Audit write
    |-- audit_logs
    |-- audit_logs_immutable
    `-- compliance and system summaries
```

Primary implementation sources:

- [audit.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\audit.py)
- [audit_logs.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\audit_logs.py)
- [audit_logs.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\models\audit_logs.py)
- [audit_log.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\schemas\audit_log.py)
- [indexes.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\indexes.py)
- [admin_analytics.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\admin_analytics.py)
- [admin_system.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\admin_system.py)
- [governance.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\governance.py)

Primary frontend surfaces:

- [AuditLogsPage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\AuditLogsPage.jsx)
- [AdminCompliancePage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Admin\AdminCompliancePage.jsx)
- [AppRoutes.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\routes\AppRoutes.jsx)
- [featureAccess.js](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\config\featureAccess.js)

Relevant adjacent module references:

- [GOVERNANCE_MODULE_MASTER.md](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\GOVERNANCE_MODULE_MASTER.md)
- [SYSTEM_MODULE_MASTER.md](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\SYSTEM_MODULE_MASTER.md)

This document describes the audit module as implemented today, including operational audit logs, immutable audit chaining, telemetry events, list APIs, and compliance summary views.

## 1. Module Overview

The Audit Module is the event history and traceability layer of CAPS AI.

Its purpose is to record who did what, to which entity, when it happened, and at what severity level.

The module currently supports three related but distinct functions:

1. operational audit logging
2. immutable chained audit persistence
3. higher-level telemetry capture for destructive and governance-sensitive actions

This is not a general event bus. It is an audit-centric persistence layer used by many endpoint modules.

Important implementation reality:

- audit writes are decentralized across endpoints and services
- audit reads are centralized through `/audit-logs`
- immutable audit storage exists, but there is no separate UI for it
- compliance and system dashboards derive metrics from `audit_logs`

That means the audit module is already operationally important, not just a passive archive.

## 2. Core Audit Concepts

### Audit Event

An audit event is a persisted record of a meaningful application action such as:

- login
- logout
- restore
- review decision
- AI execution
- similarity check
- update
- delete or archive
- role change

### Mutable Audit Log

The main query surface is `audit_logs`.

This collection is optimized for:

- filtering
- dashboard summaries
- list display
- administrative investigation

### Immutable Audit Log

The system optionally writes a chained copy of every audit event into `audit_logs_immutable`.

This collection is meant to provide:

- append-only style persistence
- tamper-evident hash chaining

### Destructive Action Telemetry

Certain destructive operations emit structured telemetry through `log_destructive_action_event(...)`.

These events are also persisted via the general audit logging path.

This is how audit and governance intersect operationally.

## 3. Data Model And Collections

## 3.1 `audit_logs`

Purpose:

- primary mutable audit event store

Public mapping:

- [audit_logs.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\models\audit_logs.py)

API schema:

- [audit_log.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\schemas\audit_log.py)

Current fields exposed publicly:

- `id`
- `actor_user_id`
- `action`
- `action_type`
- `entity_type`
- `resource_type`
- `entity_id`
- `detail`
- `old_value`
- `new_value`
- `ip_address`
- `user_agent`
- `severity`
- `created_at`

Purpose of major fields:

- `actor_user_id`:
  - who performed the action
- `action`:
  - human-level action label
- `action_type`:
  - normalized category used for grouping and analytics
- `entity_type`:
  - domain object family affected
- `resource_type`:
  - broader grouping key when needed
- `entity_id`:
  - target entity reference
- `detail`:
  - summary explanation
- `old_value` and `new_value`:
  - before and after snapshots when available
- `severity`:
  - low, medium, high style risk classification

Indexes currently defined:

- `(created_at)`
- `(resource_type, severity, created_at)`

Operational role:

- primary investigation source
- source for compliance summaries
- source for some system-health derived metrics

## 3.2 `audit_logs_immutable`

Purpose:

- append-only tamper-evident audit chain

Current fields written by the service:

- all base audit fields from `audit_logs`
- `integrity_hash`
- `previous_hash`
- `source_audit_log_id`

Indexes currently defined:

- `(created_at)`
- unique `(integrity_hash)`

Behavior:

- every mutable audit write attempts to create an immutable chained copy
- the chain is formed by hashing a canonical payload plus the previous record hash

Important limitation:

- immutable logs are written on a best-effort basis
- exceptions during immutable write are swallowed
- there is no operator-facing integrity verification UI

## 3.3 `recovery_logs`

Purpose:

- specialized audit-adjacent store for recovery operations

Current fields written by recovery flows:

- `collection`
- `entity_id`
- `action`
- `performed_by`
- `created_at`

This is not a replacement for `audit_logs`. It is a narrower operational supplement.

## 4. Audit Write Path

## 4.1 Central write helper

File:

- [audit.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\audit.py)

Primary function:

- `log_audit_event(...)`

This function:

1. builds the mutable audit document
2. inserts into `audit_logs`
3. reads the inserted record back
4. attempts immutable chained persistence into `audit_logs_immutable`
5. returns the created document or fallback document

This is the canonical audit write path in the application.

## 4.2 Standard event payload shape

The helper captures:

- actor
- action
- action type
- entity type
- entity id
- resource type
- human-readable detail
- optional before/after values
- IP and user-agent when provided
- severity
- timestamp

This is broad enough to support:

- security events
- business workflow events
- recovery operations
- governance review actions

## 4.3 Immutable chaining behavior

For each audit event, the helper:

- loads the previous immutable row
- derives `previous_hash`
- creates a canonical JSON payload
- computes SHA-256 hash
- stores the new immutable row

This gives the audit module a tamper-evident chain rather than a plain duplicate store.

Tradeoff:

- the chain is useful
- but the current implementation is non-blocking and silent on failure

That means the immutable path is supportive, not strictly enforced.

## 5. Destructive Action Telemetry

## 5.1 Specialized telemetry helper

File:

- [audit.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\audit.py)

Secondary function:

- `log_destructive_action_event(...)`

Purpose:

- capture structured lifecycle telemetry for dangerous operations

Logged fields include:

- `event = destructive_action.telemetry`
- `actor_user_id`
- `action`
- `entity_type`
- `entity_id`
- `stage`
- `detail`
- `review_id_supplied`
- `review_id`
- `governance_required`
- `governance_completed`
- `outcome`
- `metadata`
- `created_at`

## 5.2 Telemetry persistence model

Destructive telemetry is:

- emitted to application logs
- also persisted into `audit_logs` through `log_audit_event(...)`

This means destructive telemetry is part of the audit module, not a separate observability-only stream.

## 5.3 Governance-coupled stages

Observed stages include:

- request or requested
- governance blocked
- governance completed
- completed

This makes the audit layer useful for reconstructing sensitive delete flows end-to-end.

## 6. Read APIs And Query Surface

## 6.1 Audit log listing

File:

- [audit_logs.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\audit_logs.py)

Route:

- `GET /api/v1/audit-logs/`

Supported filters:

- `actor_user_id`
- `entity_type`
- `resource_type`
- `action`
- `severity`
- `created_from`
- `created_to`
- `skip`
- `limit`

Current behavior:

- sorts newest first by `created_at`
- supports pagination
- returns public audit schema only

## 6.2 Access model for audit logs

Current read dependency:

- `require_roles(['admin', 'teacher'])`

This is a notable policy decision.

Frontend feature access:

- [featureAccess.js](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\config\featureAccess.js) currently allows `admin` and `teacher`

Backend permission registry:

- [permission_registry.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\core\permission_registry.py) defines `audit.read` only for:
  - `super_admin`
  - `admin`
  - `compliance_admin`

Important mismatch:

- `/audit-logs` uses role-based access and still allows teachers
- compliance summary APIs use permission-based access and are narrower

This is one of the main audit-module authorization inconsistencies today.

## 7. Frontend Implementation

## 7.1 `AuditLogsPage.jsx`

File:

- [AuditLogsPage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\AuditLogsPage.jsx)

Current UI behavior:

- uses shared `EntityManager`
- read-only page
- supports filters for:
  - actor user id
  - entity type
  - resource type
  - action
  - severity
  - created from
  - created to
- lists:
  - actor
  - action
  - severity
  - entity
  - resource
  - entity id
  - detail
  - created at

Important limitation:

- the page does not surface `old_value` or `new_value`
- the page does not expose immutable-chain fields

## 7.2 `AdminCompliancePage.jsx`

File:

- [AdminCompliancePage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Admin\AdminCompliancePage.jsx)

Purpose:

- show compliance-oriented summary over audit activity

Current data source:

- `GET /api/v1/admin/analytics/audit-summary`

Current metrics displayed:

- total events in last 24h
- low severity count
- medium severity count
- high severity count
- top action types

This page is not a full audit explorer. It is a summary dashboard.

## 7.3 Route exposure

Frontend route:

- `/audit-logs`

Route guard:

- [AppRoutes.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\routes\AppRoutes.jsx)

Current effective access:

- `admin`
- `teacher`

This matches the feature config and the backend route guard, but it does not match the narrower permission-registry definition for `audit.read`.

## 8. Audit Producers Across The Platform

The audit module is not populated by one subsystem. It is written from many endpoints and services.

Observed producers include:

- auth service:
  - login
  - logout
  - login anomaly
- governance endpoints:
  - policy update
  - review decision
- recovery:
  - restore
- users:
  - role changes
- assignments:
  - archive actions
- submissions:
  - AI evaluation actions
- evaluations:
  - create, update, finalize, AI refresh
- notices and notifications
- review tickets
- event registrations
- similarity checks
- academic destructive action telemetry

This breadth is a strength, because the audit module already captures most of the high-value administrative and academic workflow surface.

## 9. Derived Analytics And Operational Dependencies

The audit module is not only for human inspection. Other modules derive platform metrics from it.

## 9.1 Compliance summary

File:

- [admin_analytics.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\admin_analytics.py)

Route:

- `GET /api/v1/admin/analytics/audit-summary`

Derived metrics:

- severity counts over last 24 hours
- top `action_type` values

## 9.2 System diagnostics

File:

- [admin_system.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\admin_system.py)

Derived metrics from audit logs:

- active sessions in last 24h via `action_type = login`
- error count in last 24h
- slow query count
- latest slow query rows

This means the system module depends on the audit module being complete and correctly populated.

## 9.3 Governance dashboard

Files:

- [governance.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\governance.py)
- [admin_governance.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\admin_governance.py)

Derived metrics:

- login anomalies in last 24h
- action-review lifecycle visibility

The audit module therefore acts as a data source for governance reporting.

## 10. Business Rules

### Rule 1: Audit events should be written through the shared helper

The intended canonical path is `log_audit_event(...)`.

### Rule 2: Immutable writes are best-effort

The system attempts to maintain an immutable chain, but the mutable audit write does not fail if immutable persistence fails.

### Rule 3: Severity is advisory but operationally meaningful

Severity drives:

- compliance summaries
- system error counting
- operator triage

### Rule 4: `action_type` is the main aggregation key

Compliance and system summaries group or filter by `action_type`, not only by `action`.

### Rule 5: Destructive telemetry belongs in audit history

Destructive action telemetry is not treated as separate ephemeral logs. It is persisted through the audit module.

## 11. Strengths Of Current Implementation

### Strong Area 1: Centralized write helper

The platform has one primary audit persistence function instead of each endpoint inventing its own log schema.

### Strong Area 2: Immutable chained copy exists

This is materially better than only having mutable operational logs.

### Strong Area 3: Audit data is operationally used

Audit history already powers:

- compliance summaries
- governance dashboards
- system health metrics

This means the module is not dead documentation or unused storage.

### Strong Area 4: Destructive workflows are now auditable at stage level

The addition of destructive-action telemetry makes governance-sensitive activity much more reconstructable.

## 12. Gaps And Risks

### Gap 1: Authorization policy is inconsistent

Current inconsistency:

- `/audit-logs` allows teachers
- `audit.read` permission is admin-oriented
- compliance pages are narrower than the raw log page

This should be resolved deliberately rather than left implicit.

### Gap 2: Immutable log chain is not operator-visible

There is no API or UI for:

- viewing immutable rows
- verifying chain integrity
- comparing mutable and immutable copies

### Gap 3: No retention enforcement implementation is visible here

Governance policy stores:

- `retention_days_audit`

But there is no visible purge or archival job in the current audited files enforcing audit retention.

### Gap 4: `old_value` and `new_value` are underused in UI

The data is available in the model and schema, but the main audit page does not surface it.

### Gap 5: Audit quality depends on producer discipline

Because writes are decentralized, consistency depends on each endpoint calling the helper with:

- the correct action
- useful detail
- correct severity
- meaningful before and after values

There is no strict global taxonomy enforcement in the current code.

### Gap 6: Slow-query audit production is not documented centrally

System dashboards consume `action_type = slow_query`, but the specific producer path is not obvious in this module surface.

That indicates an audit-producer documentation gap.

## 13. Architectural Issues

### Issue 1: Mutable and immutable audit layers are only loosely coupled

The immutable path is derived from the mutable write, but failures are swallowed.

This is pragmatic, but it means the immutable trail is not guaranteed.

### Issue 2: Audit is both event history and telemetry sink

The module currently stores:

- domain audit events
- security events
- governance events
- destructive action telemetry
- slow query operational signals

This is useful, but it mixes several concerns into one event store.

### Issue 3: Access model is not fully harmonized

The audit module is straddling:

- teacher-facing visibility
- admin compliance reporting
- governance admin control

That is defensible, but the policy needs to be explicit.

## 14. Testing Requirements

### Backend tests

- `log_audit_event(...)` writes mutable audit row
- immutable chained row is written when collection is available
- immutable write failure does not break mutable write
- audit list filters work correctly for:
  - actor
  - entity type
  - resource type
  - action
  - severity
  - date range
- destructive telemetry persists through audit path

### Integration tests

- governance-protected delete emits requested, blocked, and completed audit stages
- recovery restore writes both audit and recovery log rows
- compliance summary counts reflect inserted audit rows
- admin system health slow-query and error counts reflect audit data

### Frontend tests

- audit log page filter form sends correct query params
- audit log page is read-only
- compliance page renders severity and top-action summary
- access guard for `/audit-logs` matches intended policy once authorization is normalized

## 15. Recommended Cleanup Strategy

### Phase 1: Normalize authorization

Choose one explicit policy:

- either teachers should read only scoped audit history
- or audit visibility should be admin and compliance only

Then align:

- route guard
- feature access
- permission registry

### Phase 2: Expose immutable verification

Add either:

- immutable audit read API
- integrity verification endpoint
- compliance UI for hash-chain verification

### Phase 3: Standardize audit taxonomy

Create a documented taxonomy for:

- `action`
- `action_type`
- `severity`
- recommended `detail` patterns

This will improve summary quality and analytics reliability.

### Phase 4: Implement retention execution

If `retention_days_audit` is a real policy, a scheduled purge or archive process should exist and be documented.

### Phase 5: Improve UI depth

Enhance `AuditLogsPage.jsx` to optionally show:

- `old_value`
- `new_value`
- IP
- user agent
- raw telemetry payload for destructive actions

## Final Summary

The audit module in CAPS AI is already a substantial subsystem.

It currently provides:

- centralized audit persistence
- immutable chained audit copies
- filtered audit-log querying
- compliance summaries
- system-health metric derivation
- governance and destructive-action telemetry persistence

Its strongest qualities are:

- broad platform adoption
- a shared write helper
- useful cross-module operational value
- existing immutable-chain concept

Its main weaknesses are:

- inconsistent authorization semantics
- no visible immutable verification tools
- weakly standardized event taxonomy
- no clearly enforced retention execution path

The correct next step is to treat audit as a first-class platform data system, not only as a log table. That means tightening access policy, exposing chain verification, standardizing event semantics, and making retention behavior operationally real.