# Review Ticket Module Master

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
Review Ticket Module
|-- Evaluation Reopen Requests
|-- Ticket Status Lifecycle
|-- Admin Decision Paths
`-- Evaluation Finalization Interaction
```

## Internal Entity And Flow Tree

```text
Finalized evaluation
`-- Review ticket request
    `-- Admin decision
        `-- Reopen or reject outcome
```

Primary implementation sources:

- [review_tickets.py](/backend/app/api/v1/endpoints/review_tickets.py)
- [review_tickets.py](/backend/app/models/review_tickets.py)
- [review_ticket.py](/backend/app/schemas/review_ticket.py)
- [evaluations.py](/backend/app/api/v1/endpoints/evaluations.py)
- [audit.py](/backend/app/services/audit.py)
- [admin_analytics.py](/backend/app/api/v1/endpoints/admin_analytics.py)
- [analytics_snapshot.py](/backend/app/services/analytics_snapshot.py)

Primary frontend surfaces:

- [ReviewTicketsPage.jsx](/frontend/src/pages/ReviewTicketsPage.jsx)
- [AppRoutes.jsx](/frontend/src/routes/AppRoutes.jsx)
- [featureAccess.js](/frontend/src/config/featureAccess.js)
- [AdminAnalyticsPage.jsx](/frontend/src/pages/Admin/AdminAnalyticsPage.jsx)

Related references:

- [EXAM_MODULE_MASTER.md](/docs/modules/EXAM_MODULE_MASTER.md)
- [AUDIT_MODULE_MASTER.md](/docs/modules/AUDIT_MODULE_MASTER.md)
- [GOVERNANCE_MODULE_MASTER.md](/docs/modules/GOVERNANCE_MODULE_MASTER.md)

This document describes the review ticket module as implemented today.

In CAPS AI, review tickets are not a generic enterprise ticketing engine. They are a specific workflow for requesting the reopening of a finalized evaluation so it can be edited again.

## 1. Module Overview

The Review Ticket Module is a narrow exception-handling workflow around evaluations.

Its purpose is to let a teacher ask an admin to reopen a locked evaluation when the teacher believes a correction or reconsideration is required.

The current workflow is:

1. teacher creates reopen request for a finalized evaluation
2. admin reviews request
3. admin approves or rejects
4. if approved, the target evaluation is unfinalized

This makes review tickets a control mechanism over the evaluation finalization boundary.

Important implementation reality:

- review tickets are scoped only to evaluations
- there is no generic workflow abstraction for assignments, notices, users, or clubs
- the module uses role gates, not governance approval reviews

That means review tickets solve one real operational problem, but they are not yet a generalized approval or dispute subsystem.

## 2. Core Domain Concept

The module represents one business intent:

- request reopen of a finalized evaluation

A review ticket is created only when:

- an evaluation exists
- that evaluation belongs to the requesting teacher
- that evaluation is already finalized

The review ticket then becomes the admin’s decision object for whether reopening is allowed.

This is closer to a grading dispute or correction request than to a helpdesk ticket.

## 3. Data Model And Collections

## 3.1 `review_tickets`

Purpose:

- store reopen requests for finalized evaluations

Schema:

- [review_ticket.py](/backend/app/schemas/review_ticket.py)

Public model mapping:

- [review_tickets.py](/backend/app/models/review_tickets.py)

Current stored fields:

- `evaluation_id`
- `requested_by_user_id`
- `reason`
- `status`
- `resolved_by_user_id`
- `resolved_at`
- `created_at`

Exposed output fields:

- `id`
- `evaluation_id`
- `requested_by_user_id`
- `reason`
- `status`
- `resolved_by_user_id`
- `resolved_at`
- `created_at`

Status values currently typed:

- `pending`
- `approved`
- `rejected`

Relations:

- `evaluation_id` references `evaluations`
- `requested_by_user_id` references `users`
- `resolved_by_user_id` references `users`

Important missing fields:

- no ticket title
- no priority
- no comments thread
- no SLA timestamps
- no escalation owner
- no category beyond evaluation reopen
- no explicit decision note separate from the original reason

The record is intentionally minimal.

## 3.2 Related collections used by the module

### `evaluations`

Purpose in this workflow:

- ticket target entity
- approval side effect updates `evaluations.is_finalized`

### `audit_logs`

Purpose in this workflow:

- store ticket creation and decision events

### `recovery_logs`

Review tickets are listed in generic recovery tooling, which means the system expects them to be recoverable if soft-delete semantics are later applied. Current review ticket endpoint code, however, does not define delete behavior.

## 4. Backend Logic Implemented

## 4.1 Listing review tickets

File:

- [review_tickets.py](/backend/app/api/v1/endpoints/review_tickets.py)

Route:

- `GET /api/v1/review-tickets/`

Behavior:

- accepts filters:
  - `status`
  - `evaluation_id`
  - `skip`
  - `limit`
- admin can see all matching tickets
- teacher can only see tickets where:
  - `requested_by_user_id = current teacher`

This is the main visibility boundary in the module.

## 4.2 Ticket creation

Route:

- `POST /api/v1/review-tickets/`

Access:

- teacher only

Validation rules:

- referenced evaluation must exist
- requesting teacher must own the evaluation
- evaluation must already be finalized
- there must not already be a pending ticket for the same evaluation

On success, the module inserts:

- `evaluation_id`
- `requested_by_user_id`
- `reason`
- `status = pending`
- `resolved_by_user_id = None`
- `resolved_at = None`
- `created_at`

Audit side effect:

- writes audit event:
  - `action = create_reopen_request`
  - `entity_type = review_ticket`

## 4.3 Ticket approval

Route:

- `PATCH /api/v1/review-tickets/{ticket_id}/approve`

Access:

- admin only

Validation rules:

- ticket must exist
- ticket status must still be `pending`

Approval side effects:

1. target evaluation is updated:
   - `is_finalized = False`
2. ticket is updated:
   - `status = approved`
   - `resolved_by_user_id = current admin`
   - `resolved_at = now`
   - `reason = payload.reason if provided else original reason`

Audit side effect:

- writes:
  - `action = approve_reopen_request`
  - `entity_type = review_ticket`

Important implementation detail:

- approval only unfinalizes the evaluation
- it does not record a separate reopen reason on the evaluation itself

## 4.4 Ticket rejection

Route:

- `PATCH /api/v1/review-tickets/{ticket_id}/reject`

Access:

- admin only

Validation rules:

- ticket must exist
- ticket status must still be `pending`

Rejection side effects:

- ticket becomes:
  - `status = rejected`
  - `resolved_by_user_id = current admin`
  - `resolved_at = now`
  - `reason = payload.reason if provided else original reason`

Audit side effect:

- writes:
  - `action = reject_reopen_request`
  - `entity_type = review_ticket`

Evaluation side effect:

- none

## 4.5 Related override path outside the ticket module

File:

- [evaluations.py](/backend/app/api/v1/endpoints/evaluations.py)

Related route:

- `PATCH /api/v1/evaluations/{evaluation_id}/override-unfinalize`

Behavior:

- admin can directly unfinalize an evaluation with a reason
- this bypasses review ticket creation entirely

This is a very important architectural fact.

The review ticket module is not the only way to reopen evaluations.

Implication:

- review tickets are a structured workflow
- but admin override route is still a direct escape hatch

## 5. Business Rules

### Rule 1: Tickets apply only to finalized evaluations

If the evaluation is not locked, ticket creation is rejected.

### Rule 2: Teachers can request reopen only for their own evaluations

Teachers cannot raise reopen requests for evaluations owned by other teachers.

### Rule 3: Only one pending ticket per evaluation is allowed

This is enforced at the endpoint level by searching for an existing pending row.

### Rule 4: Only admins can resolve tickets

Teachers can create and list their own tickets, but they cannot approve or reject them.

### Rule 5: Approval reopens the evaluation

Approval does not modify marks. It only clears the finalization lock.

### Rule 6: Rejection leaves the evaluation unchanged

Rejected requests are terminal for that ticket.

### Rule 7: The module is role-gated, not governance-gated

Review tickets do not currently use:

- governance approval reviews
- two-person rule
- `review_id`

This is a separate approval pattern from the governance module.

## 6. API Surface

File:

- [review_tickets.py](/backend/app/api/v1/endpoints/review_tickets.py)

### `GET /review-tickets/`

Purpose:

- list review tickets with optional filters

Access:

- `admin`
- `teacher`

Teacher visibility:

- only own tickets

### `POST /review-tickets/`

Purpose:

- create reopen request for a finalized evaluation

Access:

- `teacher`

### `PATCH /review-tickets/{ticket_id}/approve`

Purpose:

- approve reopen request and unfinalize evaluation

Access:

- `admin`

### `PATCH /review-tickets/{ticket_id}/reject`

Purpose:

- reject reopen request

Access:

- `admin`

Not implemented:

- delete
- update after creation
- ticket comments
- close or cancel
- reopen after rejection
- bulk actions

## 7. Frontend Implementation

## 7.1 `ReviewTicketsPage.jsx`

File:

- [ReviewTicketsPage.jsx](/frontend/src/pages/ReviewTicketsPage.jsx)

Teacher capabilities:

- load ticket list
- filter by status
- create reopen request
- select evaluation from dropdown

Admin capabilities:

- load ticket list
- approve ticket
- reject ticket

Displayed columns:

- evaluation id
- status
- reason
- requested by
- created at

Important limitations:

- ticket table does not show:
  - `resolved_by_user_id`
  - `resolved_at`
- teacher create form pulls evaluations from `/evaluations/` without an `is_finalized=true` filter
- dropdown labels use raw evaluation id plus marks and grade, not richer student or assignment context

## 7.2 Route and access

Frontend route:

- `/review-tickets`

Feature access:

- [featureAccess.js](/frontend/src/config/featureAccess.js)
- `allowedRoles: ['admin', 'teacher']`

This matches the backend route guard for listing.

## 8. Analytics And Operational Dependencies

## 8.1 Admin overview counters

File:

- [admin_analytics.py](/backend/app/api/v1/endpoints/admin_analytics.py)

Current metric:

- `pending_review_tickets`

This means review tickets already feed control-plane summaries.

## 8.2 Analytics snapshots

File:

- [analytics_snapshot.py](/backend/app/services/analytics_snapshot.py)

Snapshot metric:

- `pending_review_tickets`

This extends ticket visibility into platform snapshots.

## 8.3 Frontend analytics drift

File:

- [AdminAnalyticsPage.jsx](/frontend/src/pages/Admin/AdminAnalyticsPage.jsx)

Observed issue:

- the page expects `review_ticket_sla_hours`
- current analytics sources shown here do not produce that metric

This is a current UI/API contract gap tied partly to the review ticket domain.

## 9. Strengths Of Current Implementation

### Strong Area 1: Clear narrow workflow

The module has one concrete business purpose and implements it coherently.

### Strong Area 2: Approval side effect is explicit

Approving a ticket has a well-defined result:

- unfinalize evaluation

### Strong Area 3: Teacher visibility is scoped

Teachers only see tickets they created.

### Strong Area 4: Audit integration exists

Ticket creation and decisions are already logged through the audit module.

## 10. Gaps And Risks

### Gap 1: No generic review system

Despite the name, review tickets are only evaluation reopen requests.

If future modules need review tickets, this implementation will not scale without redesign.

### Gap 2: Duplicate reopen mechanism exists

Admin can bypass ticket workflow via:

- `PATCH /evaluations/{evaluation_id}/override-unfinalize`

This reduces the review ticket module’s authority as the canonical reopen path.

### Gap 3: No explicit decision note field

Approval and rejection overwrite or reuse `reason`, which mixes:

- teacher request rationale
- admin decision rationale

These should be separate fields.

### Gap 4: No SLA or escalation model

Yet analytics UI already implies SLA expectations.

The data model does not currently support:

- first response time
- resolution deadline
- overdue state

### Gap 5: No dependency on governance review controls

This may be acceptable, but it means review tickets and governance reviews are parallel approval systems with different semantics.

### Gap 6: No delete or archive semantics

Review tickets appear in recovery tooling, but the review ticket module itself does not define delete behavior.

That is a system-contract inconsistency.

## 11. Architectural Issues

### Issue 1: Review tickets are workflow-specific but named generically

The name suggests a generic review queue, but the implementation is evaluation-reopen only.

### Issue 2: Direct admin override weakens ticket centrality

If admins can always unfinalize directly, tickets become optional rather than canonical.

### Issue 3: Ticket state machine is too small for institutional process

Current states:

- pending
- approved
- rejected

Missing potentially useful states:

- cancelled
- expired
- under_review
- executed

### Issue 4: Rich context is absent

Ticket records do not store:

- assignment id
- student id
- teacher id separate from requester if needed
- evaluation summary snapshot

This forces the UI to resolve context elsewhere or show only ids.

## 12. Testing Requirements

### Backend tests

- teacher can create ticket only for own finalized evaluation
- create rejects non-finalized evaluation
- create rejects duplicate pending ticket
- admin can approve pending ticket
- admin can reject pending ticket
- teacher cannot approve or reject
- approval unfinalizes evaluation
- rejection leaves evaluation finalized

### Integration tests

- finalized evaluation -> teacher ticket create -> admin approve -> teacher can edit evaluation again
- finalized evaluation -> teacher ticket create -> admin reject -> teacher remains blocked
- audit log rows are created for ticket create and decision
- pending ticket counts appear in admin analytics overview and snapshot

### Frontend tests

- teacher sees create form, admin does not
- admin sees approve and reject actions
- teacher list is scoped to own tickets
- evaluation dropdown should ideally exclude non-finalized evaluations once improved

## 13. Recommended Cleanup Strategy

### Phase 1: Clarify module scope

Decide whether this module is:

- evaluation-reopen only
- or the beginning of a generic review request system

If it remains narrow, rename the documentation and UI language accordingly.

### Phase 2: Separate request and decision reasons

Add fields such as:

- `request_reason`
- `decision_reason`

This will improve audit quality and operator clarity.

### Phase 3: Choose a canonical reopen path

Either:

- require review tickets for reopen except emergency super-admin override
- or explicitly document direct override as the primary path

Current dual-path behavior is operationally ambiguous.

### Phase 4: Improve analytics contract

If the analytics UI wants SLA metrics, the ticket model needs:

- resolution timestamps
- age calculations
- overdue logic

### Phase 5: Improve UI context

Display richer ticket context:

- student
- assignment
- grade
- finalized timestamp
- resolved by
- resolved at

## Final Summary

The review ticket module in CAPS AI is a focused administrative workflow for reopening finalized evaluations.

It currently provides:

- teacher-created reopen requests
- admin approval or rejection
- automatic unfinalization of approved evaluations
- audit logging
- pending ticket counts in admin analytics

Its strongest quality is clarity of purpose.

Its main weaknesses are:

- generic naming for a narrow workflow
- a duplicate direct override path
- sparse ticket metadata
- no SLA or escalation model
- no integration with the broader governance approval framework

The correct next step is to decide whether review tickets should stay narrow and explicit or evolve into a real platform-wide review workflow system. Right now they are effective, but intentionally limited.


