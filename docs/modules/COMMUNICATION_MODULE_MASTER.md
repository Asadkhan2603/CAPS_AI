# Communication Module Master

## Module Tree

```text
Communication Module
|-- Notices
|-- Feed Aggregation
|-- Announcements UI
|-- Admin Audience Preview
`-- Notification Producer Integration
```

## Internal Entity And Flow Tree

```text
Notice
`-- Audience targeting
    `-- Scheduled fanout
        |-- Feed rendering
        `-- Notification creation
```

## 1. Module Overview

The Communication module in CAPS AI provides institution-facing announcement and activity distribution. It is the user-visible communication layer that sits above:

- notices
- feed aggregation
- notification fanout
- future-ready direct messaging UI

This module is not the same as the Notification module.

Current distinction:

- Communication is the human-facing publication and stream experience
- Notifications are alert records used for targeted or global system notices

Primary backend files:

- [notices.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\notices.py)
- [admin_communication.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\admin_communication.py)
- [background_jobs.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\background_jobs.py)

Primary frontend files:

- [AnnouncementsPage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Communication\AnnouncementsPage.jsx)
- [FeedPage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Communication\FeedPage.jsx)
- [MessagesPage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Communication\MessagesPage.jsx)
- [AdminCommunicationPage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Admin\AdminCommunicationPage.jsx)
- [CommunicationTabs.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\components\communication\CommunicationTabs.jsx)

The current module is partly mature and partly staged:

- notices and feed are real
- audience preview is real
- messages is currently a shell for future work

## 2. Core Communication Concepts

## 2.1 Notices

Notices are the main persisted communication object. They represent announcements that can be:

- college-wide
- year-scoped
- class or section-scoped
- subject-scoped

Notices can also include:

- priority
- expiration
- scheduling
- attachments

## 2.2 Feed

The feed is not its own backend entity. It is a frontend-assembled stream built from multiple sources:

- notices
- notifications
- assignments
- evaluations

This means feed is a projection layer, not a source-of-truth collection.

## 2.3 Notifications

Notice publication can trigger notification fanout. Communication therefore overlaps operationally with the Notification module, but the two are still separate layers.

## 2.4 Messages

The messaging UI exists, but it is currently future-ready rather than fully backed by a messaging backend contract.

## 3. Main Collection: `notices`

Schema/model files:

- [notice.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\schemas\notice.py)
- [notices.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\models\notices.py)

### Public notice shape

Current public fields:

- `id`
- `title`
- `message`
- `priority`
- `scope`
- `scope_ref_id`
- `expires_at`
- `images`
- `is_pinned`
- `scheduled_at`
- `read_count`
- `seen_by`
- `created_by`
- `is_active`
- `created_at`

### Field semantics

#### `priority`

Supported values:

- `normal`
- `urgent`

#### `scope`

Supported values:

- `college`
- `year`
- `class`
- `section`
- `subject`

Implementation note:

- backend normalizes `section` to `class`

That is another legacy naming leak in the communication area.

#### `scope_ref_id`

Reference id for scoped audiences such as:

- year id
- class/section id
- subject id

#### `images`

Attachment metadata stored after Cloudinary upload.

#### `scheduled_at`

Future publication time for scheduled notices.

#### `read_count` and `seen_by`

These fields exist in the data model, but current frontend read tracking does not fully use them as the primary mechanism.

## 4. Backend Logic Implemented

## 4.1 Notice publication permissions

File:

- [notices.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\notices.py)

Publishing is constrained through `_can_publish_scope(...)`.

Rules:

- admin can publish any scope
- teacher cannot publish `college` scope
- `year` scope requires `year_head`
- `class` or `section` scope requires `class_coordinator`
- `subject` scope is allowed for teachers

This is a relatively strong scope-based permission model for publishing.

## 4.2 Notice scope reference validation

Helper:

- `_validate_scope_ref_access(...)`

Behavior:

- validates referenced year/class/subject exists
- validates teacher coordinator ownership for class scope

This is one of the stronger backend validation paths in the communication module.

## 4.3 Student notice visibility

Helper:

- `_student_scope_visibility_ids(...)`

Behavior:

- resolves student profile by email or user id
- derives visible classes from:
  - `students.class_id`
  - `enrollments.class_id`
- derives visible years from classes
- derives visible subjects from assignments attached to visible classes

Student `GET /notices/` results are then filtered against those sets.

This works, but it also inherits the same duplicated membership-source problem seen elsewhere in the system.

## 4.4 Notice creation

### `POST /notices/`

Behavior:

- accepts multipart or JSON
- validates attachments and file sizes
- uploads notice files via Cloudinary service
- persists notice record
- audits creation
- triggers background notification fanout immediately if not scheduled

Attachment controls:

- max notice files
- max bytes per file
- allowed mime types

## 4.5 Notice listing

### `GET /notices/`

Supports:

- scope filter
- priority filter
- `include_expired`
- pagination

Behavior:

- only returns active notices
- excludes future scheduled notices unless now >= scheduled_at
- sorts by `created_at` descending
- optionally excludes expired notices
- applies student audience filtering for student users

## 4.6 Notice deletion

### `DELETE /notices/{notice_id}`

Behavior:

- teacher can delete only own notice
- admin can delete broadly
- deletes Cloudinary assets
- soft-deletes the notice using:
  - `is_active = false`
  - `is_deleted = true`
  - `deleted_at`
  - `deleted_by`
- audits the delete

This is safer than hard delete, but it still uses legacy `is_deleted` semantics.

## 4.7 Scheduled notice processing

### `POST /notices/process-scheduled`

Behavior:

- finds active notices scheduled for dispatch
- queues fanout for pending scheduled notices
- audits the scheduling run

## 4.8 Audience preview

File:

- [admin_communication.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\api\v1\endpoints\admin_communication.py)

### `POST /admin/communication/preview-target`

Purpose:

- preview estimated audience reach before publishing

Supports scopes:

- college
- year
- class
- subject

Permission:

- `announcements.publish`

This is an administrative planning utility, not an end-user communication artifact.

## 5. Background Communication Flow

File:

- [background_jobs.py](d:\VS CODE\MY PROJECT\CAPS_AI\backend\app\services\background_jobs.py)

Notices can fan out into notifications using:

- `_target_user_ids_for_notice(...)`
- `fanout_notice_notifications(...)`

Current supported targeting:

- college
- class
- year
- subject

This is the main point where Communication integrates with the Notification module.

## 6. Frontend Implementation

## 6.1 Announcements page

Frontend file:

- [AnnouncementsPage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Communication\AnnouncementsPage.jsx)

Capabilities:

- fetch and display notices
- filter by urgent, expiring, expired, mine
- search announcements
- publish new announcement via modal
- mark visible notices as read locally

Important behavior:

- students cannot use the `mine` filter
- teachers/admins can create announcements
- audience options are built from available years, sections, and subjects

## 6.2 Create announcement modal

Frontend file:

- [CreateAnnouncementModal.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\components\communication\CreateAnnouncementModal.jsx)

Capabilities:

- multi-step publish flow
- urgent flag
- attachment selection
- audience selection
- optional expiry

The modal supports attachment validation on the client before backend upload.

## 6.3 Feed page

Frontend file:

- [FeedPage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Communication\FeedPage.jsx)

Behavior:

- fetches:
  - `/notices/`
  - `/notifications/`
  - `/assignments/`
  - `/evaluations/`
- merges them into one chronological stream

This is a communication-oriented activity stream, not a direct representation of one backend collection.

## 6.4 Messages page

Frontend file:

- [MessagesPage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Communication\MessagesPage.jsx)

Current state:

- placeholder/future-ready UI
- conversation list and chat window shell
- no corresponding message backend endpoint in the current scanned code

This must be documented as staged UI, not as a fully implemented module.

## 6.5 Admin communication page

Frontend file:

- [AdminCommunicationPage.jsx](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\pages\Admin\AdminCommunicationPage.jsx)

Capabilities:

- link to announcements and feed
- audience preview utility

## 7. Frontend-only Read Tracking

File:

- [noticeReadTracker.js](d:\VS CODE\MY PROJECT\CAPS_AI\frontend\src\utils\noticeReadTracker.js)

Important implementation reality:

- notice read state is currently tracked in `localStorage`
- keys are per user:
  - `caps_ai_notice_read_{userId}`

This means:

- read/unread state is browser-local
- not synchronized across devices
- not reflected back into backend `read_count` or `seen_by`

This is one of the most important contract gaps in the communication module.

## 8. Permissions and Access Model

Frontend feature access:

- `communicationFeed`
- `communicationAnnouncements`
- `communicationMessages`
- `notifications`
- `notices`

All are currently exposed to:

- `admin`
- `teacher`
- `student`

Backend publication rules remain the real authority for who can publish what.

Key backend publishing permission:

- `announcements.publish`

Scope control is additionally enforced by teacher extension roles through notice publish helpers.

## 9. Strengths of Current Implementation

### Strength 1: Notices are a real backend domain

The announcement system is not fake UI. It has backend scope validation, scheduling, attachments, and audit events.

### Strength 2: Audience control is meaningful

Notices can target institution, year, class, or subject audiences.

### Strength 3: Fanout integration exists

Notices can automatically generate notification records for recipients.

### Strength 4: Feed aggregates communication and academic activity

This gives users one useful stream rather than forcing them to navigate multiple separate modules.

## 10. Gaps and Risks

### Gap 1: Messages UI is not backed by a real messaging domain

The page exists, but there is no matching backend message contract in the current scanned implementation.

### Gap 2: Read tracking is frontend-local

`isNoticeRead(...)` and related helpers use browser storage rather than backend persistence.

This conflicts with the data model fields:

- `read_count`
- `seen_by`

### Gap 3: Feed is assembled client-side

The feed merges multiple APIs in the browser, which is simple but not the most scalable or contract-stable design.

### Gap 4: Communication still depends on legacy academic entities

Notice scoping and preview use:

- `years`
- `classes`
- subject-linked assignments

The communication layer is therefore not yet aligned only to the canonical academic hierarchy.

### Gap 5: Deletion is not governance-gated

Notice delete is audited and soft-deleted, but there is no governance review flow comparable to hardened academic setup destructive actions.

## 11. Architectural Issues

### Issue 1: Communication and notification responsibilities overlap

Notices are communication records, but they also drive notification fanout.

That overlap is workable, but the product boundary should remain explicit:

- notices are authored communication artifacts
- notifications are delivery or alert artifacts

### Issue 2: Read semantics are split between frontend and backend

Backend has fields for read tracking, but frontend uses local-only read state.

This is a direct contract inconsistency.

### Issue 3: Feed is a projection, not a source of truth

That is acceptable, but it should remain explicitly documented so future developers do not treat the feed as a persistent backend entity.

### Issue 4: Legacy `class` terminology still leaks into scoped communication

The module accepts `section` in some places but normalizes to `class`. That mirrors the broader academic legacy issue.

## 12. Recommended Cleanup Strategy

### Short-term

- document Messages as placeholder UI
- document feed as a frontend aggregation layer
- either wire backend-backed notice read tracking or explicitly hide backend read-count fields from expectations

### Medium-term

- align notice read tracking to backend `seen_by` and `read_count`
- decide whether notice delete should be governance-gated
- consider a backend feed endpoint if feed performance or contract drift becomes an issue

### Long-term

Adopt a clearer communication architecture:

- notices as first-class authored artifacts
- notifications as alert delivery artifacts
- real direct messaging domain if messaging is required
- unified cross-device read tracking
- reduced dependence on legacy academic scope entities

## 13. Testing Requirements

Minimum automated coverage should include:

### Unit tests

- scope publish authorization rules
- scope reference validation for year/class/subject
- student visibility filtering by audience scope
- expiry and scheduling normalization

### API tests

- admin can publish college notices
- teacher cannot publish college notices
- year head can publish year-scoped notices
- class coordinator can publish only owned class-scoped notices
- student receives only visible notices
- scheduled notice processing queues eligible notices

### Integration tests

- notice create with attachments and fanout
- announcement page publish flow
- feed aggregation ordering
- admin audience preview matches publish-target logic

### Contract tests to add

- backend read tracking if `seen_by` becomes authoritative
- message module tests only after a real messaging backend exists

## 14. Final Summary

The Communication module is partially mature and already useful. Its real, implemented backbone is the Notice system, which supports:

- scoped publishing
- attachment upload
- scheduling
- audit logging
- notification fanout

The Feed page is also real, but it is a projection layer assembled client-side.

The weakest area is Messages, which is currently UI-first and not yet backed by a matching backend messaging domain.

The most important current contract gap is read tracking:

- backend notice records expose `read_count` and `seen_by`
- frontend currently tracks notice reads only in local browser storage

From an architecture standpoint, the correct path is:

- keep notices as the core communication artifact
- keep notifications separate as delivery artifacts
- fix read-state consistency
- treat feed as an aggregation projection
- only elevate messaging to a real module once backend persistence and authorization are implemented