# NOTIFICATION MODULE MASTER

## Module Tree

```text
Notification Module
|-- Notification API
|-- Notice Fanout Producers
|-- Similarity Alert Producers
|-- Read State Support
`-- Feed And History Consumers
```

## Internal Entity And Flow Tree

```text
Producer event
`-- Notification record
    |-- Backend unread/read state
    `-- Frontend feed and history visibility
```

## 1. Module Overview

The notification module is the lightweight alert-delivery layer of CAPS AI. It stores global and user-targeted alert records that can be surfaced in feed and history views.

This module is narrower than the broader communication domain:

- communication handles notices, feed composition, and announcement workflows
- notifications handle alert records with recipient visibility and read state

The module is real on the backend, but thin on the frontend. CAPS AI currently has notification APIs and stored records, but not a true standalone notification center.

Primary backend files:

- [notifications.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\api\v1\endpoints\notifications.py)
- [notifications.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\services\notifications.py)

Primary frontend files:

- [NotificationsPage.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\NotificationsPage.jsx)
- [FeedPage.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\Communication\FeedPage.jsx)
- [HistoryPage.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\HistoryPage.jsx)

Important implementation reality:

- `NotificationsPage.jsx` redirects to `/communication/feed`
- notifications are mostly consumed as feed/history rows rather than managed as a first-class UI object

## 2. Data Model

Schema/model files:

- [notification.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\schemas\notification.py)
- [notifications.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\models\notifications.py)

### 2.1 Collection

Primary collection:

- `notifications`

### 2.2 Public fields

Notifications expose:

- `id`
- `title`
- `message`
- `priority`
- `scope`
- `target_user_id`
- `created_by`
- `is_read`
- `created_at`

### 2.3 Field semantics

#### `title`

Short alert headline.

#### `message`

Alert body text.

#### `priority`

Free string priority field.

Observed values in current code:

- `normal`
- `urgent`

This is not a strict enum, so producer drift is possible.

#### `scope`

Free string context label describing where or why the notification exists.

Observed usage includes:

- `global`
- `notice`
- `similarity`

Scope is descriptive metadata. It is not the access-control mechanism.

#### `target_user_id`

Optional per-user recipient id.

Behavior:

- `None` means globally visible
- otherwise visible only to the target user, except admin override paths

#### `is_read`

Recipient read state.

New notifications always start as unread.

## 3. Backend Logic Implemented

### 3.1 List notifications

Endpoint:

- `GET /notifications/`

Access control:

- `admin`
- `teacher`
- `student`

Query behavior:

- returns notifications where:
  - `target_user_id == None`
  - or `target_user_id == current_user._id`

Supported filters:

- `is_read`
- `scope`
- `skip`
- `limit`

This is a recipient-scoped endpoint, not a raw admin dump of the entire notification table.

### 3.2 Create notification

Endpoint:

- `POST /notifications/`

Access control:

- `admin`
- `teacher`

Behavior:

- delegates creation to shared `create_notification(...)`
- writes audit event after creation

Stored create fields:

- title
- message
- priority
- scope
- target_user_id
- created_by
- `is_read = false`
- `created_at`

### 3.3 Mark notification as read

Endpoint:

- `PATCH /notifications/{notification_id}/read`

Access control:

- `admin`
- `teacher`
- `student`

Behavior:

- loads the notification
- if it is user-targeted:
  - target user can mark it read
  - admin can override and mark any targeted notification as read
- if unauthorized, returns 403

Current limitation:

- this is one-way
- there is no mark-unread path

## 4. Shared Creation Service

Service file:

- [notifications.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\services\notifications.py)

Shared function:

- `create_notification(...)`

This service centralizes notification writes and is the correct architectural pattern for a cross-cutting alert module.

Behavior:

- trims title
- trims message
- stores priority and scope verbatim
- stores target user id and creator id
- sets `is_read = false`
- sets `created_at`

This keeps notification producers thin and consistent.

## 5. System Producers of Notifications

Notifications are not only manually created through the notification API.

### 5.1 Notice fanout

Producer path:

- [background_jobs.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\services\background_jobs.py)

Behavior:

- scheduled or immediate notice fanout creates notification rows for resolved recipients

This is one of the main real producers of notification records.

### 5.2 Similarity alerts

Producer path:

- [similarity.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\api\v1\endpoints\similarity.py)

Behavior:

- creates urgent notifications for integrity-related events

This makes the notification module a system alert bus for plagiarism/similarity signals, not just a generic message table.

## 6. API Endpoints

Base path:

- `/notifications`

### Implemented endpoints

- `GET /notifications/`
  - list visible notifications for current user
- `POST /notifications/`
  - create notification
- `PATCH /notifications/{notification_id}/read`
  - mark notification as read

### Missing endpoints

Not currently implemented:

- get single notification
- update notification
- delete notification
- archive notification
- bulk mark read
- mark unread
- notification preference settings

## 7. Frontend Implementation

### 7.1 `NotificationsPage.jsx`

Current behavior:

- redirects to `/communication/feed`

This means the product route exists, but the notification center page does not.

### 7.2 `FeedPage.jsx`

Behavior:

- fetches `/notifications/`
- merges notifications with:
  - notices
  - assignments
  - evaluations

Notifications are displayed as chronological activity events, not as interactive notification objects.

### 7.3 `HistoryPage.jsx`

Behavior:

- fetches `/notifications/`
- displays notifications in history tables
- shows read state
- contributes to unread notification counts in the student history summary

Important gap:

- history shows `is_read`
- but does not expose the backend read action

## 8. Frontend vs Backend Gaps

### 8.1 No dedicated notification center

The route exists, but the page redirects elsewhere.

### 8.2 No explicit mark-as-read UI

Backend supports:

- `PATCH /notifications/{id}/read`

Frontend does not intentionally expose this interaction.

### 8.3 No manual create UI

Backend allows admin/teacher notification creation, but there is no dedicated frontend create workflow.

### 8.4 Feed treats notifications as generic activity

This is useful for chronology, but weakens notification-specific interactions like:

- unread triage
- filtering
- acknowledgement

## 9. Business Rules

### Rule 1: Notifications are global or user-targeted

Visibility is determined by:

- `target_user_id == None`
- or `target_user_id == current_user._id`

### Rule 2: Read state is recipient-aware

Users can mark their own targeted notifications as read.

Admins can override for targeted records.

### Rule 3: New notifications start unread

The shared creation service always sets:

- `is_read = false`

### Rule 4: Scope is contextual metadata

`scope` describes the category or origin context, but does not directly authorize access.

## 10. Recovery and Operational Characteristics

The notification collection is included in recovery tooling.

Observed in:

- [admin_recovery.py](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\backend\app\api\v1\endpoints\admin_recovery.py)
- [AdminRecoveryPage.jsx](d:\VS%20CODE\MY%20PROJECT\CAPS_AI\frontend\src\pages\Admin\AdminRecoveryPage.jsx)

Implication:

- the module is expected to support soft-delete-style recovery semantics operationally

Current gap:

- the notification endpoint itself does not implement delete or archive
- recovery support therefore exists at the platform layer, not through a notification lifecycle API

## 11. Risks and Bugs Identified

### 11.1 No notification center despite route exposure

The product appears to expose notifications as a module, but the route is only a redirect.

### 11.2 Scope is weakly typed

`scope` is a free string, so producers can diverge over time.

### 11.3 No lifecycle controls

There is no explicit API for:

- archive
- delete
- retention
- expiry

### 11.4 No bulk recipient interaction

Missing common user operations:

- mark all read
- bulk read
- unread-only filtering in UI

### 11.5 No consumption telemetry

Notification reads are not surfaced as a stronger analytics or audit interaction stream.

## 12. Architectural Issues

### 12.1 Backend is ahead of frontend

The backend has a clean minimal notification API and shared creation service. The frontend still treats notifications as a secondary feed/history source.

### 12.2 Producer contract is too loose

Notifications are created from:

- manual API create
- notice fanout
- similarity alerts

That is functionally fine, but the producer taxonomy relies on weak `scope` and `priority` strings rather than a stronger typed contract.

### 12.3 Notifications overlap with feed but are not the same thing

The feed is a merged projection of multiple modules. Notifications are one of its sources.

This distinction matters:

- `notifications` are stored alert records
- `feed` is a presentation-layer aggregate

### 12.4 No retention policy

The module currently has no formal strategy for:

- pruning old notifications
- archiving stale alerts
- expiring obsolete system alerts

## 13. Cleanup Strategy

### Short-term

- add explicit mark-as-read actions in UI
- add unread filtering in the frontend
- keep using the shared creation service

### Medium-term

- decide whether `/notifications` should become a real page
- formalize `priority` and `scope`
- add bulk read operations if product needs them

### Long-term

Adopt a clearer notification design:

- typed categories
- dedicated notification center
- unread counters and acknowledgement flows
- retention and archival policy
- explicit producer conventions for system-generated alerts

## 14. Testing Requirements

### Unit tests

- creation service trims title/message
- creation service sets unread default
- mark-read ownership logic

### API tests

- user sees global notifications
- user sees own targeted notifications
- user does not see other users' targeted notifications
- user can mark own notification as read
- non-admin cannot mark another user's targeted notification as read
- admin can mark any targeted notification as read

### Integration tests

- notice fanout creates notification rows
- similarity alerts create urgent notifications
- feed includes notifications in chronological output
- history page reflects backend read state correctly

### Future tests if module expands

- bulk mark read
- unread counters
- typed scope validation
- retention behavior

## 15. Current Module Assessment

The notification module is a valid backend subsystem with multiple real producers and a clean shared creation service.

Strengths:

- supports global and targeted alerts
- has real read/unread state
- is used by notice fanout and similarity alerting
- already appears in feed and history views

Weaknesses:

- no true notification center
- no explicit read UI
- weakly typed scope and priority
- no lifecycle or retention strategy

As implemented today, notifications are a real storage and delivery layer, but the user-facing experience is still an incomplete shell around that backend capability.