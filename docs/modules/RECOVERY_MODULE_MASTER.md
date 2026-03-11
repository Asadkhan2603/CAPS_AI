# RECOVERY MODULE MASTER

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
Recovery Module
|-- Deleted Record Discovery
|-- Allowlisted Collection Restore
|-- Restore Logging
`-- Admin Recovery UI
```

## Internal Entity And Flow Tree

```text
Soft-deleted record
`-- Recovery listing
    `-- Restore request
        `-- Audit and recovery logging
```

## 1. Module Overview

The recovery module is the admin-facing restore layer for soft-deleted records. It is not a backup-and-restore system. It does not perform snapshot rollback, point-in-time recovery, or multi-record dependency repair. It simply finds archived rows in approved collections and clears their delete markers.

This module is operationally important because many CAPS AI entities use soft-delete rather than hard delete. Recovery provides a controlled way to re-activate those rows.

The recovery model is:

- list recoverable items from selected collections
- restore one item by clearing delete markers
- write audit and recovery tracking records

## 2. Actual Scope

Primary backend file:

- [admin_recovery.py](/backend/app/api/v1/endpoints/admin_recovery.py)

Primary frontend page:

- [AdminRecoveryPage.jsx](/frontend/src/pages/Admin/AdminRecoveryPage.jsx)

Current scope is limited to a fixed allowlist of collections.

Supported recovery collections:

- `courses`
- `departments`
- `branches`
- `years`
- `classes`
- `notices`
- `notifications`
- `clubs`
- `club_events`
- `assignments`
- `submissions`
- `evaluations`
- `review_tickets`

Important implication:

- recovery is not generic across all collections
- only explicitly whitelisted collections can be restored
- legacy collections remain supported here even though their API routes are retired

## 3. Recovery Model

### 3.1 What “deleted” means

The recovery backend uses shared helpers from:

- [soft_delete.py](/backend/app/core/soft_delete.py)

Current authoritative delete signal:

- `deleted_at != null`

Legacy compatibility:

- recovery queries can still include legacy `is_deleted = true` markers

This matters because the repo still contains mixed soft-delete semantics:

- newer academic setup uses canonical:
  - `is_active`
  - `deleted_at`
  - `deleted_by`
- some older modules still also or primarily use:
  - `is_deleted`

### 3.2 What restore does

Restore uses:

- `build_restore_update(restored_by=...)`

This clears deletion markers and writes restore metadata.

The helper also writes:

- `restored_at`
- `restored_by`

and clears:

- `deleted_at`
- `deleted_by`
- legacy `is_deleted`

### 3.3 What recovery does not do

The module does not:

- restore Mongo snapshots
- restore one record plus all of its dependents
- validate relational consistency after restore
- re-run domain-specific activation workflows
- check whether the restored row conflicts with current live data

This is record-level marker restoration only.

## 4. Backend Logic Implemented

### 4.1 List recovery items

Endpoint:

- `GET /admin/recovery`

Permission:

- `system.read`

Parameters:

- `collection`
- `limit`

Behavior:

- validates requested collection against whitelist
- when no collection is passed, iterates all supported collections
- loads rows using `build_soft_deleted_query(include_legacy_marker=True)`
- returns:
  - timestamp
  - `items` grouped by collection
  - `summary` counts

Returned item fields:

- `id`
- `name`
- `is_deleted`
- `is_active`
- `deleted_at`
- `deleted_by`

Name resolution is generic:

- `name`
- `title`
- `full_name`
- fallback `-`

This is convenient, but also generic and lossy.

### 4.2 Restore item

Endpoint:

- `PATCH /admin/recovery/{collection}/{item_id}/restore`

Permission:

- `system.read`

Behavior:

- validates collection against allowlist
- loads current row
- applies restore update
- writes audit event:
  - `action = restore`
  - `action_type = restore`
- writes `recovery_logs` row if that collection exists

Response:

- `success`
- `collection`
- `id`
- `message`

Important security issue:

- restore currently uses `system.read`
- restore should be a stronger permission than read

## 5. Data Stores and Supporting Collections

### 5.1 Recoverable domain collections

Recovery touches the whitelisted business collections listed above.

### 5.2 `recovery_logs`

If available, restore also appends a row to:

- `recovery_logs`

Fields written:

- `collection`
- `entity_id`
- `action`
- `performed_by`
- `created_at`

This is an operational log, not the primary source of truth for deletion state.

### 5.3 `audit_logs`

Restore actions also write audit records through:

- [audit.py](/backend/app/services/audit.py)

This gives restore operations compliance visibility.

## 6. Frontend Implementation

Frontend page:

- [AdminRecoveryPage.jsx](/frontend/src/pages/Admin/AdminRecoveryPage.jsx)

### 6.1 What the page does

Implemented behavior:

- select collection from supported list
- load recoverable rows from backend
- show summary count
- restore a selected row
- refresh after restore

Displayed fields:

- id
- name
- is_deleted
- is_active
- deleted_by
- deleted_at

### 6.2 Current UX characteristics

The page is intentionally operational, not polished:

- one collection at a time
- no dependency graph
- no preview of what restore affects downstream
- no search
- no bulk restore

### 6.3 Sidebar and route exposure

The recovery page is reachable through:

- `/admin/recovery`

and linked in the admin sidebar.

## 7. Business Rules

### 7.1 Allowlist-only restoration

Only approved collections can be restored.

### 7.2 Soft-delete only

Recovery only works when data still exists and is merely archived.

If a module performs hard delete, recovery cannot help.

### 7.3 Permission model

Current implemented permission:

- `system.read`

This is operationally weak for a mutating action.

### 7.4 Audit trail

Restore attempts that succeed create:

- audit record
- recovery log row when `recovery_logs` is present

## 8. Frontend vs Backend Gaps

### 8.1 No dependency preview

The frontend does not tell the operator whether a restore will bring back an entity that is still inconsistent with current state.

Examples:

- restoring a class while related students, offerings, or slots remain archived or mismatched
- restoring a club while its events remain archived

### 8.2 No search or filtering beyond collection

Recovery UI is collection-scoped only.

Missing useful controls:

- search by name
- search by id
- sort by deleted_at
- filter by deleted_by

### 8.3 No confirmation or impact warning

Restore is one-click from the table action.

That is operationally thin for an admin mutation.

## 9. Architectural Issues

### 9.1 Recovery guarantees are only as strong as delete consistency

Because the repo still has mixed delete semantics across modules, recovery quality varies by collection.

Examples:

- academic setup entities are increasingly standardized
- notices and club events still rely on legacy `is_deleted` patterns
- some modules like groups and class slots are not in the recovery allowlist at all

### 9.2 Restore is not dependency-aware

The module restores a single row without checking:

- parent existence
- child consistency
- uniqueness collisions
- whether downstream live records now conflict

### 9.3 Permission semantics are too coarse

Using `system.read` for restore means a read-oriented permission also authorizes mutation.

This should be split.

## 10. Risks and Bugs Identified

### 10.1 Restore permission is too weak

Current backend uses:

- `system.read`

for both listing and restoring.

Risk:

- users meant only to inspect recovery state can also mutate it

### 10.2 Mixed soft-delete contracts

Recovery can query both canonical and legacy delete markers, but that also means semantics are uneven across collections.

Risk:

- restore behavior is predictable only if the source collection follows the expected soft-delete contract

### 10.3 Unsupported but soft-deleted collections exist

Some collections in the repo use soft-delete-like behavior but are not part of recovery allowlist.

Examples from the repo surface:

- groups
- class_slots
- some newer academic entities not listed in recovery allowlist

Risk:

- operational inconsistency

### 10.4 No relationship validation on restore

Restoring a row may re-enable an object whose parent is still deleted or whose children were restructured after archival.

## 11. Cleanup Strategy

### 11.1 Split recovery permissions

Introduce separate permissions such as:

- `system.recovery.read`
- `system.recovery.restore`

### 11.2 Restrict allowlist to truly standardized collections

Only collections with well-defined soft-delete semantics should remain in generic recovery tooling.

### 11.3 Add dependency-aware restore checks

Before restoring, check for:

- missing required parents
- conflicting active duplicates
- incompatible downstream state

### 11.4 Improve operator UI

Add:

- search
- deleted date sorting
- deleted-by filter
- confirmation dialog
- restore impact summary

### 11.5 Expand or narrow collection coverage intentionally

Decide deliberately whether modules like:

- groups
- class_slots
- additional academic setup collections

should join recovery allowlist or stay excluded.

## 12. Testing Requirements

### 12.1 Unit tests

- list rejects unsupported collection
- restore rejects unsupported collection
- restore clears canonical delete markers
- restore clears legacy `is_deleted`
- audit event written on restore
- recovery log row written when collection exists

### 12.2 Integration tests

- end-to-end restore from admin recovery API
- recoverable collections list output
- restored row disappears from recovery list
- restored row becomes visible again in normal module list endpoints

### 12.3 Frontend tests

- collection switching reloads table
- restore action triggers API call
- summary metrics update after restore
- error handling on failed restore

## 13. Current Module Assessment

The recovery module is useful and real, but narrow.

Strengths:

- simple operational restore path exists
- whitelisted collection model limits accidental scope
- restore writes both audit and recovery logs
- compatible with canonical and legacy soft-delete markers

Weaknesses:

- permission model is too coarse
- restore is not dependency-aware
- UI is thin and operator-light
- collection support is inconsistent relative to actual soft-delete usage across the repo

As implemented today, the module is a practical admin recovery tool for soft-deleted rows. It is not a full resilience or data-repair system, and it should not be described that way.

