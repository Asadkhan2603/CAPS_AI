# Governance Workflows Guide

## Purpose

This guide documents how governance works in CAPS AI as an execution control layer, not only as an audit or reporting concern. It explains how governance policy is stored, how approval reviews are created and decided, how protected actions are executed, where review identifiers are required, how telemetry is emitted, and where the frontend surfaces this workflow.

The real implementation spans backend policy storage, review records, enforcement checks, audit logging, destructive-action telemetry, and admin UI tools. The guide is based on the current code path in the backend governance service, admin governance endpoints, shared delete UI, and related admin pages.

## Governance Architecture Tree

```text
Governance
|- Policy Storage
|  `- settings.governance_policy
|- Review Records
|  `- admin_action_reviews
|- Enforcement Layer
|  `- enforce_review_approval(...)
|- Admin Governance API
|  |- /admin/governance/policy
|  |- /admin/governance/reviews
|  |- /admin/governance/dashboard
|  `- /admin/governance/sessions
|- Shared UI Review Flow
|  `- EntityManager delete retry with review_id
|- Admin Governance Console
|  `- AdminGovernancePage.jsx
|- Audit Integration
|  |- audit_logs
|  `- audit_logs_immutable
`- Destructive Action Telemetry
   `- destructive_action.telemetry events
```

## Scope In CAPS AI

Governance currently covers these responsibilities:

1. Storing and updating governance policy.
2. Creating approval records for protected admin actions.
3. Requiring a second approver when policy demands it.
4. Preventing self-approval of protected actions.
5. Marking approved reviews as executed when the protected action actually runs.
6. Writing audit records for governance policy changes and review decisions.
7. Emitting telemetry when destructive actions are requested, blocked, approved, and completed.
8. Providing an admin console for policy editing, review decisions, and session inspection.

Governance is strongest today around destructive operations and privileged admin-role changes. It is not yet uniformly applied to every mutating path in the repository.

## Primary Backend Files

Core backend implementation lives in:

- [governance.py](/backend/app/services/governance.py)
- [admin_governance.py](/backend/app/api/v1/endpoints/admin_governance.py)
- [audit.py](/backend/app/services/audit.py)
- [permission_registry.py](/backend/app/core/permission_registry.py)

Governance is consumed in protected endpoint files such as:

- [faculties.py](/backend/app/api/v1/endpoints/faculties.py)
- [departments.py](/backend/app/api/v1/endpoints/departments.py)
- [programs.py](/backend/app/api/v1/endpoints/programs.py)
- [specializations.py](/backend/app/api/v1/endpoints/specializations.py)
- [batches.py](/backend/app/api/v1/endpoints/batches.py)
- [semesters.py](/backend/app/api/v1/endpoints/semesters.py)
- [classes.py](/backend/app/api/v1/endpoints/classes.py) (sections)

## Primary Frontend Files

The governance UI and retry path live in:

- [AdminGovernancePage.jsx](/frontend/src/pages/Admin/AdminGovernancePage.jsx)
- [adminGovernanceApi.js](/frontend/src/services/adminGovernanceApi.js)
- [EntityManager.jsx](/frontend/src/components/ui/EntityManager.jsx)
- [featureAccess.js](/frontend/src/config/featureAccess.js)

`AdminGovernancePage.jsx` is the explicit governance console. `EntityManager.jsx` is the operational retry path for destructive actions that require prior review approval.

## Policy Model

Governance policy is stored in the `settings` collection under key `governance_policy`.

The active policy fields are:

- `two_person_rule_enabled`
- `role_change_approval_enabled`
- `retention_days_audit`
- `retention_days_sessions`

`get_governance_policy(...)` returns the current settings merged with defaults. `set_governance_policy(...)` upserts the policy document.

### Policy Meaning

`two_person_rule_enabled`
: Requires approved review records for destructive actions that use the generic destructive review path.

`role_change_approval_enabled`
: Requires approved review records for privileged role-change actions that use `review_type = role_change`.

`retention_days_audit`
: Administrative retention value for audit-related records.

`retention_days_sessions`
: Administrative retention value for session-monitoring records.

### Current Weakness

All admin governance endpoints currently use `require_permission("system.read")`, including policy updates and review decisions. That is too coarse for mutating governance operations. The runtime behavior works, but the permission boundary is weaker than it should be.

Relevant file:

- [admin_governance.py](/backend/app/api/v1/endpoints/admin_governance.py)

## Review Record Model

Governance approvals are stored in `admin_action_reviews`.

A created review record contains these operational fields:

- `review_type`
- `action`
- `entity_type`
- `entity_id`
- `reason`
- `metadata`
- `requested_by`
- `status`
- `created_at`
- `updated_at`

Decision and execution fields are added later:

- `reviewed_by`
- `reviewed_at`
- `review_note`
- `executed_by`
- `executed_at`

### Status Lifecycle

The normal status path is:

```text
pending -> approved -> executed
```

Alternative path:

```text
pending -> rejected
```

Once a review is no longer `pending`, it cannot be decided again. Once a protected action executes successfully through `enforce_review_approval(...)`, the review is moved from `approved` to `executed`.

## Review Types

The current code recognizes these review types:

`destructive`
: Used for delete-like or archive-like operations that must be approved under the two-person rule.

`role_change`
: Used for privileged role changes when the role-change approval policy is enabled.

These are surfaced in the admin UI as selectable review types.

## Governance Lifecycle

### 1. Create Review Request

An admin creates a review request through:

- `POST /admin/governance/reviews`

The backend writes a new `admin_action_reviews` record with:

- `status = pending`
- requester identity
- action and entity context
- reason and optional metadata

The frontend create form in [AdminGovernancePage.jsx](/frontend/src/pages/Admin/AdminGovernancePage.jsx) currently collects:

- review type
- action
- entity type
- entity id
- reason

### 2. Review Decision

A second admin decides the request through:

- `PATCH /admin/governance/reviews/{review_id}`

Decision payload includes:

- `approve: true | false`
- `note`

The backend enforces:

- review must exist
- review must still be pending
- requester cannot approve their own request

Possible results:

- `approved`
- `rejected`

### 3. Protected Action Execution

A protected endpoint receives a `review_id` and calls `enforce_review_approval(...)` before performing the mutation.

This function validates:

- whether the relevant governance policy is enabled
- whether a review id was supplied when required
- whether the review exists
- whether it is approved
- whether it matches the expected review type
- whether action matches
- whether entity type matches
- whether entity id matches when provided
- whether the approver is distinct from the requester

If validation succeeds, the review is marked `executed` and the protected action can continue.

### 4. Audit And Telemetry

Governance policy updates and review decisions are written to audit logs. Destructive action flow also emits telemetry stages for observability and compliance analysis.

## Enforcement Contract In Detail

The most important governance execution logic is in:

- [governance.py](/backend/app/services/governance.py)

### Function Behavior

`enforce_review_approval(...)` is not a generic logger. It is an execution gate.

Its behavior is:

1. Determine whether the actor is an admin.
2. Resolve the applicable governance policy flag based on `review_type`.
3. Return immediately if the policy is disabled.
4. Fail with `403` if review approval is required but `review_id` is missing.
5. Load the review record.
6. Validate approval status and review ownership.
7. Validate that review type, action, entity type, and entity id align with the requested operation.
8. Mark the review executed.
9. Emit governance-completed telemetry.

### Missing Review Id Behavior

If review approval is required and `review_id` is missing, the function raises:

```text
403 Governance approval required. Provide an approved review_id before completing this action.
```

This is now the fail-safe behavior expected by protected delete flows.

### Self-Approval Block

A requester cannot approve and execute their own protected action. The review must reflect a second person approving the request.

### Entity Matching

This is an important integrity control. A review for one entity cannot be reused to authorize a different entity, action, or review type. The backend checks all of these values before execution.

## Protected Action Coverage

Governance is currently wired most clearly into destructive academic setup actions.

Protected delete/archive flows include these endpoint families:

- faculties
- departments
- programs
- specializations
- batches
- semesters
- sections

These endpoints are expected to call `enforce_review_approval(...)` and accept `review_id` from the request path or query parameters depending on endpoint shape.

### Current Coverage Reality

Coverage is improved, but not universal.

What is strong now:

- shared academic setup destructive flows using `EntityManager`
- governance-aware delete retry path in the frontend
- backend fail-safe rejection when review id is missing
- telemetry around requested, blocked, and completed stages

What is still uneven:

- custom pages that do not use `EntityManager`
- some modules still have destructive actions without governance adoption
- not every privileged mutation uses a consistent approval workflow

## Audit Integration

Governance integrates with the audit subsystem through:

- [audit.py](/backend/app/services/audit.py)

Important audit events include:

`governance_policy_update`
: emitted when policy is changed

`admin_review_decision`
: emitted when a review is approved or rejected

Governance-related actions also benefit from the immutable audit-chain infrastructure described in:

- [AUDIT_MODULE_MASTER.md](/docs/modules/AUDIT_MODULE_MASTER.md)

## Destructive Action Telemetry

Destructive action telemetry captures operational detail around governance-sensitive mutations.

It is emitted through the audit service helper used by governance and protected endpoints.

### Key Stages

`requested`
: the action was initiated

`completed`
: the action finished

`governance_blocked`
: the action was blocked because governance approval was required but not satisfied

`governance_completed`
: the governance review was validated and executed

### Telemetry Captures

The telemetry payload can include:

- actor user id
- action
- entity type
- entity id
- stage
- whether `review_id` was supplied
- whether governance completed
- admin type metadata

This is the practical bridge between endpoint behavior and operational monitoring.

## Admin Governance API Catalog

The governance admin router currently exposes:

### Policy Endpoints

`GET /admin/governance/policy`
: fetch active governance policy

`PATCH /admin/governance/policy`
: update governance policy

### Review Endpoints

`POST /admin/governance/reviews`
: create a review request

`GET /admin/governance/reviews`
: list review records, optionally filtered by status

`PATCH /admin/governance/reviews/{review_id}`
: approve or reject a review request

### Dashboard And Sessions

`GET /admin/governance/dashboard`
: return governance dashboard metrics

`GET /admin/governance/sessions`
: return session data with optional `status` and `user_id` filters

## Dashboard Metrics

The governance dashboard returns:

- `timestamp`
- `policy`
- `pending_reviews`
- `approved_reviews_24h`
- `login_anomalies_24h`
- `locked_accounts`

This dashboard blends governance policy state with security and session signals.

## Session Governance And Monitoring

The sessions endpoint exposes data from `user_sessions` and enriches it with user identity details.

Fields returned per item can include:

- user id
- user name
- user email
- session status
- timestamps and session metadata

This supports operator workflows such as:

- identifying active sessions
- reviewing locked or suspicious session activity
- correlating anomalies with governance or admin actions

The session API is read-only monitoring in the current implementation.

## Frontend Governance Console

The main frontend governance console is:

- [AdminGovernancePage.jsx](/frontend/src/pages/Admin/AdminGovernancePage.jsx)

### Page Capabilities

The page currently supports:

1. loading governance dashboard metrics
2. loading and editing policy values
3. creating review requests
4. listing review requests
5. filtering reviews by status
6. approving or rejecting reviews
7. listing user sessions
8. filtering sessions by status

### Review Creation Form

The review creation UI collects:

- `review_type`
- `action`
- `entity_type`
- `entity_id`
- `reason`

### Review Decision Behavior

The page calls the decision API with fixed notes:

- `Approved in admin panel`
- `Rejected in admin panel`

That works functionally, but it is a weak operator note strategy. Real production governance normally requires meaningful reviewer justification.

## Shared Delete Retry Flow In EntityManager

The operational governance retry path for destructive CRUD is implemented in:

- [EntityManager.jsx](/frontend/src/components/ui/EntityManager.jsx)
- [featureAccess.js](/frontend/src/config/featureAccess.js)

### Flow

1. User requests delete in a shared CRUD page.
2. Backend rejects because governance approval is required.
3. Frontend detects the condition through explicit response flags or message fallback.
4. Frontend opens a modal prompting for `review_id`.
5. Optional review metadata can also be collected.
6. Frontend retries the delete request with `review_id` and optional metadata.

### Why This Matters

This is the most practical operator workflow currently implemented for governance-sensitive deletes. It keeps the UI in sync with the backend fail-safe contract.

### Coverage Limits

Only pages that use `EntityManager` automatically benefit from this behavior. Custom delete UIs still need their own governance prompt flow.

## Governance And Permission Model

Current governance permissions are not sufficiently granular.

### Current State

Governance endpoints use:

- `require_permission("system.read")`

That includes:

- reading policy
- updating policy
- creating reviews
- deciding reviews
- reading dashboard data
- reading sessions

### Problem

A permission named `system.read` should not be the final guard for mutating governance actions. This creates an authorization model that works technically but is logically weaker than the governance system itself.

### Recommended Direction

Split governance permissions into explicit capabilities such as:

- `governance.read`
- `governance.manage_policy`
- `governance.create_review`
- `governance.decide_review`
- `session.read_sensitive`

This change would align the authorization model with the actual governance responsibilities.

## Workflow Examples

### Example 1: Destructive Academic Delete

```text
1. Admin initiates delete on department.
2. Endpoint logs destructive action requested.
3. Governance enforcement requires approved destructive review.
4. If review_id missing, backend returns 403 and emits governance_blocked.
5. UI prompts user for review_id.
6. User retries with approved review_id.
7. Backend validates review and marks it executed.
8. Endpoint archives the entity.
9. Telemetry records governance_completed and destructive action completed.
```

### Example 2: Role Change Approval

```text
1. Admin creates role-change review request.
2. Separate admin approves request.
3. Protected role-change endpoint executes with review_id.
4. Governance validates type = role_change and matching action metadata.
5. Review moves to executed.
6. Audit logs preserve review decision and resulting privileged change.
```

## Known Gaps

1. Governance is not yet uniformly applied to all destructive or privileged mutations.
2. Custom pages outside `EntityManager` can still lag behind the shared governance retry flow.
3. Governance endpoints use `system.read`, which is too broad and semantically incorrect for mutation.
4. Reviewer notes are weak in the admin UI because fixed note strings are used for decisions.
5. Governance protects execution paths, but some modules still permit admin bypasses outside a clean review workflow.
6. There is no dedicated operator dashboard for destructive telemetry review beyond generic audit and admin metrics.

## Operational Recommendations

1. Raise the authorization bar on governance endpoints by splitting read and mutation permissions.
2. Require meaningful reviewer notes instead of default fixed text.
3. Expand governance enforcement to any remaining destructive endpoints not already covered.
4. Bring custom destructive UIs into the same retry-and-review flow used by `EntityManager`.
5. Add operator queries or dashboards for blocked and completed governance events.
6. Review any admin override path that can bypass the normal review lifecycle.

## Testing Requirements

Governance testing should cover four layers.

### Unit Tests

Validate:

- policy resolution by review type
- rejection when review id is missing
- rejection when entity/action/type mismatch occurs
- self-approval rejection
- successful executed-state transition

### Endpoint Tests

Validate:

- policy fetch and update
- review creation and decision flow
- protected deletes with and without `review_id`
- dashboard and session response shapes

### Frontend Tests

Validate:

- admin governance page load and save flow
- review create and decision interactions
- `EntityManager` governance modal behavior
- delete retry with `review_id`

### Audit And Telemetry Tests

Validate:

- governance policy updates emit audit records
- review decisions emit audit records
- missing review id emits `governance_blocked`
- successful reviewed execution emits `governance_completed`

## Related Documentation

- [GOVERNANCE_MODULE_MASTER.md](/docs/modules/GOVERNANCE_MODULE_MASTER.md)
- [AUDIT_MODULE_MASTER.md](/docs/modules/AUDIT_MODULE_MASTER.md)
- [RBAC_MODULE_MASTER.md](/docs/modules/RBAC_MODULE_MASTER.md)
- [SYSTEM_MODULE_MASTER.md](/docs/modules/SYSTEM_MODULE_MASTER.md)
- [testing.md](/docs/guides/testing.md)
- [api-contracts.md](/docs/guides/api-contracts.md)

## Summary

Governance in CAPS AI is an active execution-control system built on policy state, review records, backend enforcement, audit logging, and frontend retry flows. The most important technical fact is that governance is already wired into real protected actions and can block execution when approval is missing. The most important remaining weakness is not missing infrastructure. It is uneven adoption and weak permission semantics around the governance control plane itself.



