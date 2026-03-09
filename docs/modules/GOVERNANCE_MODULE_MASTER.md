# Governance Module Master

## Module Tree

```text
Governance Module
|-- Governance Policies
|-- Review Approval Enforcement
|-- Admin Review Workflows
|-- Protected Destructive Actions
`-- Audit And Telemetry Integration
```

## Internal Entity And Flow Tree

```text
Protected action
`-- Policy check
    `-- Review approval enforcement
        |-- Allow execution
        `-- Block and log governance event
```

Primary implementation sources:

- `backend/app/services/governance.py`
- `backend/app/services/audit.py`
- `backend/app/api/v1/endpoints/admin_governance.py`
- `backend/app/api/v1/endpoints/audit_logs.py`
- `backend/app/schemas/governance.py`
- `frontend/src/pages/Admin/AdminGovernancePage.jsx`
- `frontend/src/services/adminGovernanceApi.js`
- `frontend/src/components/ui/EntityManager.jsx`
- `frontend/src/config/featureAccess.js`

Relevant operational references:

- `docs/ACADEMIC_SETUP_LOGIC_AUDIT.md`
- `docs/modules/ACADEMIC_MODULE_MASTER.md`

This document describes the governance module as implemented today, including policy controls, approval reviews, session monitoring, audit logging, and governance-aware destructive action enforcement.

## 1. Module Overview

The Governance Module is the institutional control layer of CAPS AI. It exists to ensure that sensitive administrative operations are:

- policy-driven
- reviewable
- auditable
- increasingly fail-safe

The module currently governs five main areas:

1. governance policy configuration
2. admin approval review queue
3. execution gating for protected actions
4. audit log persistence and visibility
5. device/session monitoring visibility

The system does not treat governance as a passive log-only subsystem. It already actively blocks some destructive actions unless governance approval has been satisfied.

## 2. Core Governance Concepts

### Governance Policy

The platform stores a single global governance policy under the `settings` collection using key:

- `governance_policy`

The policy currently controls:

- `two_person_rule_enabled`
- `role_change_approval_enabled`
- `retention_days_audit`
- `retention_days_sessions`

### Admin Action Review

Sensitive actions can require a review ticket before they are executed.

Supported review types:

- `destructive`
- `role_change`

Each review records:

- who requested it
- what action it applies to
- what entity it applies to
- why it was requested
- whether it was approved, rejected, or executed

### Governance Enforcement

Governance is enforced through:

- `enforce_review_approval(...)` in `backend/app/services/governance.py`

This function is not a UI-only convention. It actively blocks execution when policy requires approval but the review conditions are not satisfied.

### Audit Logging

Governance depends on durable audit logging through:

- `audit_logs`
- `audit_logs_immutable`

### Governance Telemetry

The platform now emits structured telemetry for destructive actions, including governance stages such as:

- `governance_blocked`
- `governance_completed`

## 3. Data Model And Collections

### `settings`

Purpose:

- stores global policy configuration

Relevant key:

- `key = "governance_policy"`

Governance value fields:

- `two_person_rule_enabled`
- `role_change_approval_enabled`
- `retention_days_audit`
- `retention_days_sessions`
- `updated_at`

### `admin_action_reviews`

Purpose:

- stores approval requests and lifecycle state for protected admin actions

Key fields:

- `_id`
- `review_type`
- `action`
- `entity_type`
- `entity_id`
- `reason`
- `metadata`
- `requested_by`
- `status`
- `reviewed_by`
- `reviewed_at`
- `review_note`
- `executed_by`
- `executed_at`
- `created_at`
- `updated_at`

Status lifecycle currently used:

- `pending`
- `approved`
- `rejected`
- `executed`

Indexes present:

- `(status, created_at)`
- `(entity_type, entity_id)`

### `audit_logs`

Purpose:

- stores mutable operational audit records used for reporting, filtering, and governance visibility

Key fields:

- `_id`
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

Relevant indexes:

- `(created_at)`
- `(resource_type, severity, created_at)`

### `audit_logs_immutable`

Purpose:

- stores append-only integrity-linked audit snapshots

Key fields:

- all primary audit fields
- `integrity_hash`
- `previous_hash`
- `source_audit_log_id`

Relevant indexes:

- `(created_at)`
- unique `(integrity_hash)`

### `user_sessions`

Purpose:

- stores device/session visibility used by governance session monitoring

Observed fields from governance listing logic:

- `_id`
- `user_id`
- `fingerprint`
- `ip_address`
- `last_seen_ip`
- `user_agent`
- `created_at`
- `last_seen_at`
- `rotated_at`
- `revoked_at`

## 4. Backend Services

### `get_governance_policy()`

Purpose:

- read current policy from `settings`

Behavior:

- falls back to defaults if no settings record exists
- normalizes booleans and retention day values

Defaults:

- `two_person_rule_enabled = false`
- `role_change_approval_enabled = false`
- `retention_days_audit = 365`
- `retention_days_sessions = 90`

### `set_governance_policy(payload)`

Purpose:

- update current policy in `settings`

Behavior:

- merges provided fields onto existing policy
- persists with `upsert=True`
- stamps `updated_at`

### `create_admin_review(...)`

Purpose:

- create a new approval request

Behavior:

- writes `pending` review row
- accepts optional metadata

### `approve_admin_review(...)`

Purpose:

- approve or reject an existing pending review

Behavior:

- rejects missing review
- rejects already processed review
- rejects self-approval by requester
- writes:
  - `status`
  - `reviewed_by`
  - `reviewed_at`
  - `review_note`
  - `updated_at`

### `enforce_review_approval(...)`

Purpose:

- block execution unless required governance conditions are satisfied

Behavior:

- only applies to admin role users
- chooses policy flag based on `review_type`
  - `role_change` uses `role_change_approval_enabled`
  - all others use `two_person_rule_enabled`
- returns `False` when policy is not enabled
- raises HTTP errors when policy is enabled but approval conditions fail
- marks the approved review as `executed` when successful
- returns `True` when a governance-gated action has been validly executed

Validation performed:

- missing `review_id`
- review not found
- review not approved
- requester trying to execute own review
- review type mismatch
- action or entity scope mismatch
- entity id mismatch

## 5. Audit And Telemetry Logic

### Audit Event Persistence

`log_audit_event(...)` writes to:

- `audit_logs`
- `audit_logs_immutable` if available

Immutable logging behavior:

- builds a canonical payload
- computes SHA-256 integrity hash
- chains hash to previous immutable record

This gives the governance model a basic tamper-evidence path.

### Destructive Action Telemetry

`log_destructive_action_event(...)` emits structured telemetry for protected destructive workflows.

Tracked fields:

- `event = "destructive_action.telemetry"`
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

Telemetry is:

- logged structurally through the logger
- also persisted into audit logs when possible
- fail-safe if audit persistence fails

### Governance Stages Currently Emitted

For protected destructive actions:

- request stage from endpoint layer
- `governance_blocked` from governance service
- `governance_completed` from governance service
- completion stage from endpoint layer

This is especially relevant in the academic setup module.

## 6. Backend API Endpoints

Governance APIs are mounted under:

- `/admin/governance`

### `GET /admin/governance/policy`

Purpose:

- fetch current governance policy

Access:

- `require_permission("system.read")`

### `PATCH /admin/governance/policy`

Purpose:

- update governance policy

Access:

- `require_permission("system.read")`

Side effects:

- policy update audit event is written

### `POST /admin/governance/reviews`

Purpose:

- create approval request

Access:

- `require_permission("system.read")`

### `GET /admin/governance/reviews`

Purpose:

- list governance reviews

Filters:

- `status`
- `limit`

Access:

- `require_permission("system.read")`

### `PATCH /admin/governance/reviews/{review_id}`

Purpose:

- approve or reject a review

Access:

- `require_permission("system.read")`

Side effects:

- writes audit log event for review decision

### `GET /admin/governance/dashboard`

Purpose:

- return governance summary metrics

Current metrics:

- `pending_reviews`
- `approved_reviews_24h`
- `login_anomalies_24h`
- `locked_accounts`
- `policy`
- `timestamp`

Access:

- `require_permission("system.read")`

### `GET /admin/governance/sessions`

Purpose:

- list active or revoked device sessions

Filters:

- `status`
- `user_id`
- `limit`

Access:

- `require_permission("system.read")`

### `GET /audit-logs`

This is not mounted under the governance prefix, but it is part of the governance visibility surface.

Purpose:

- list audit records

Filters:

- `actor_user_id`
- `entity_type`
- `resource_type`
- `action`
- `severity`
- `created_from`
- `created_to`
- pagination via `skip` and `limit`

Access:

- `require_roles(['admin', 'teacher'])`

Important note:

- audit log read access is broader than governance admin access
- this is a deliberate or inherited policy choice that should remain explicit

## 7. Frontend Implementation

### `AdminGovernancePage.jsx`

This is the main governance operations screen.

It implements:

- governance metrics cards
- governance policy form
- admin action review creation form
- review decision table
- session monitor table

#### Policy UI

Editable fields:

- `two_person_rule_enabled`
- `role_change_approval_enabled`
- `retention_days_audit`
- `retention_days_sessions`

#### Review Queue UI

Create-review fields:

- `review_type`
- `action`
- `entity_type`
- `entity_id`
- `reason`

Review filters:

- all
- pending
- approved
- rejected
- executed

Review actions:

- approve
- reject

#### Session Monitor UI

Shows:

- user
- status
- ip
- fingerprint
- last seen

Filters:

- active
- revoked
- all

### `adminGovernanceApi.js`

Provides frontend wrappers for:

- fetch policy
- update policy
- fetch dashboard
- fetch reviews
- create review
- decide review
- fetch sessions

### Delete Governance Wiring In Shared CRUD

Shared delete flows in `EntityManager.jsx` now support:

- `review_id`
- optional `review_metadata`
- prompt and retry UX when backend signals governance approval required

The prompt configuration is partially centralized in:

- `frontend/src/config/featureAccess.js`

This is currently used for governance-gated academic deletes.

## 8. Current Protected Actions

The governance pattern is currently wired into these known destructive academic operations:

- departments delete
- branches delete
- years delete
- courses delete
- classes/sections delete

There is also role-change governance infrastructure in policy and review types, but broader route-level role-change adoption is still partial.

Additional governance usage exists in:

- `users.py` for protected user actions

## 9. Business Rules

### Two-Person Rule

When enabled:

- destructive admin actions require approved `review_id`
- requester cannot self-execute

### Role Change Approval

When enabled:

- role change actions are expected to use review type `role_change`

### Review Decision Rules

- only pending reviews can be decided
- requester cannot approve own request
- approved review must match:
  - review type
  - action
  - entity type
  - entity id when applicable

### Execution Rules

- approved reviews become `executed` when consumed by protected action
- policy enforcement is role-aware and currently centered on admin role paths

## 10. Architecture Strengths

The governance module already has several strong foundations.

### Strong Areas

- policy stored separately from route code
- explicit approval review entity
- execution-time validation, not UI-only convention
- audit log persistence
- immutable audit chain support
- dashboard and session visibility
- structured destructive-action telemetry
- shared frontend prompt path for governance-gated deletes

These are not placeholders. They are already live operational mechanics.

## 11. Gaps And Risks

### Permission Naming vs Intent

Governance admin endpoints currently use:

- `require_permission("system.read")`

This is likely too broad semantically for mutation operations such as:

- updating policy
- approving reviews

The permission works, but the name does not express governance write intent clearly.

### Governance UI Coverage Is Partial

Shared CRUD pages can handle governance-gated delete prompts.

Remaining issue:

- custom delete UIs outside `EntityManager` still need explicit review wiring

### Governance Is Applied Selectively

Protected academic deletes use governance review.

But governance is not yet consistently applied to all sensitive destructive or administrative actions across the platform.

### Audit Log Access Scope

Audit log reads allow:

- admin
- teacher

This may be acceptable, but it broadens visibility of governance-relevant operational history beyond the governance admin surface.

### No Dedicated Governance Module Test Index In Docs

Governance behavior is covered indirectly by academic and telemetry tests, but it does not yet have a fully centralized governance test document.

## 12. Observability And Monitoring

The governance module currently contributes to observability through:

- audit logs
- immutable audit log chain
- governance dashboard metrics
- structured destructive-action telemetry
- session visibility

Dashboard metrics currently include:

- pending approvals
- approvals in last 24h
- login anomalies in last 24h
- locked accounts

This is sufficient for operational governance visibility, but still not a full governance analytics layer.

## 13. Testing Requirements

### Backend Tests

- policy default loading
- policy update merge behavior
- review creation
- approve pending review
- reject pending review
- requester cannot approve own review
- review type mismatch blocks execution
- scope mismatch blocks execution
- entity mismatch blocks execution
- missing `review_id` blocks execution when two-person rule is enabled
- approved review becomes `executed` after protected action

### Audit And Telemetry Tests

- destructive action request telemetry emitted
- governance blocked telemetry emitted
- governance completion telemetry emitted
- audit log persistence fallback does not break action execution
- immutable log chain write is non-fatal when unavailable

### Frontend Tests

- policy form saves and refreshes state
- review queue create flow works
- approve and reject actions refresh list
- governance prompt opens on backend review-required response
- `review_id` and metadata are passed correctly in delete retry flow

### Integration Tests

- governance policy change writes audit log
- review decision writes audit log
- governance-protected endpoint consumes approved review correctly
- dashboard counters reflect review state changes

## 14. Recommended Cleanup Strategy

### Phase 1: Clarify Governance Permissions

Introduce clearer governance-specific permission keys for:

- policy read
- policy write
- review read
- review decide
- session monitor access

### Phase 2: Expand Governance Coverage

Apply governance review consistently to:

- additional destructive admin actions
- sensitive role and security flows

### Phase 3: Unify UI Behavior

- extend governance prompt pattern to custom delete pages
- make review metadata usage explicit where business context matters

### Phase 4: Strengthen Governance Reporting

- build dedicated governance analytics views over audit logs
- add direct filters for telemetry stages and review lifecycle

### Phase 5: Tighten Audit Access Policy

Re-evaluate whether teachers should retain broad audit log access or only narrowed audit views.

## Final Summary

The governance module in CAPS AI is already real and operational.

It currently provides:

- policy control
- approval workflow
- execution gating
- audit persistence
- immutable audit chaining
- session visibility
- destructive-action telemetry

Its main weakness is not lack of implementation. The main weakness is uneven adoption across the rest of the platform and some coarse permission semantics.

The correct next step is broader and more uniform application of the governance framework that already exists.