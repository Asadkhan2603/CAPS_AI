# EVENT MODULE MASTER

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
Event Module
|-- Club Events
|-- Event Registrations
|-- Payment Proof Uploads
|-- Event Capacity And Closure
`-- Club Ownership Rules
```

## Internal Entity And Flow Tree

```text
Club
`-- Event
    `-- Registration
        |-- Optional payment proof
        `-- Status and closure handling
```

## 1. Module Overview

The event module in CAPS AI is implemented as a club-scoped event management system, not as a university-wide standalone event platform. Its purpose is to let authorized club managers create events, open or close registrations, collect student registrations, optionally require payment proof, and track participation-related status.

This module is operationally split into two backend domains:

- `club_events`: the event definition and lifecycle record
- `event_registrations`: the student registration record for a specific event

The module is tightly coupled to the clubs system:

- every event belongs to a club
- event management rights are derived from club ownership or coordination
- student-created events are constrained through club president ownership and start in `draft`

This means the event module should be understood as `club events + event registrations`, not as a generic central events office model.

## 2. Core Domain Model

### 2.1 Primary Entities

The implemented entities are:

- `ClubEvent`
- `EventRegistration`

There is no separate generic `Event`, `Venue`, `Speaker`, `Ticket`, or `EventAttendance` aggregate.

### 2.2 Relationships

- one `club` can own many `club_events`
- one `club_event` can have many `event_registrations`
- one `student user` can register for many events
- one student can have at most one active registration per event under the current duplicate-prevention logic

### 2.3 Ownership and Control

Event control depends on the parent club:

- `admin` can manage all events
- `teacher` can manage events if:
  - `club.coordinator_user_id == current_user.id`, or
  - the teacher has the `club_coordinator` extension role
- `student` can create or manage only if:
  - `club.president_user_id == current_user.id`

Important nuance:

- student-created events are forced into `draft`
- teacher and admin creation can directly start in `open` or `closed` depending on registration settings

## 3. Database Collections

### 3.1 `club_events`

Purpose:

- stores event master data and event lifecycle state

Key fields:

- `_id`
- `club_id`
- `title`
- `description`
- `event_type`
- `visibility`
- `registration_start`
- `registration_end`
- `event_date`
- `capacity`
- `registration_enabled`
- `approval_required`
- `payment_required`
- `payment_qr_image_url`
- `payment_amount`
- `certificate_enabled`
- `status`
- `result_summary`
- `created_by`
- `created_at`
- `is_deleted`
- `deleted_at`
- `deleted_by`

Relations:

- `club_id -> clubs._id`
- `created_by -> users._id`

Business meaning of important fields:

- `event_type`: constrained to `workshop | competition | seminar | cultural | internal`
- `visibility`: constrained to `public | members_only`
- `status`: constrained to `draft | open | closed | completed | archived`
- `approval_required`: registration enters `pending` instead of `registered`
- `payment_required`: payment fields become mandatory for registration

Constraints enforced in code:

- club must exist before event creation
- club must not be suspended
- capacity must be between `1` and `5000`
- payment-required events must include:
  - `payment_qr_image_url`
  - `payment_amount`
- archived events are soft-deleted, not physically removed

Unique constraints:

- no unique Mongo constraint is defined in the code for `club_id + title`
- duplicate event titles are therefore possible

### 3.2 `event_registrations`

Purpose:

- stores per-student registration state for a specific event

Key fields:

- `_id`
- `event_id`
- `student_user_id`
- `enrollment_number`
- `full_name`
- `email`
- `year`
- `course_branch`
- `class_name`
- `phone_number`
- `whatsapp_number`
- `payment_qr_code`
- `payment_receipt_original_filename`
- `payment_receipt_stored_filename`
- `payment_receipt_mime_type`
- `payment_receipt_size_bytes`
- `student_name`
- `student_email`
- `status`
- `attendance_status`
- `certificate_issued`
- `created_at`

Relations:

- `event_id -> club_events._id`
- `student_user_id -> users._id`

Business meaning of important fields:

- `status`: `registered | pending | approved | rejected | cancelled`
- `attendance_status`: `present | absent`
- `certificate_issued`: simple boolean flag, not a separate certificate domain

Constraints enforced in code:

- one student cannot create another active registration for the same event if an existing registration is in:
  - `registered`
  - `pending`
  - `approved`
- registration is allowed only when:
  - event exists
  - event `status == open`
  - `registration_enabled == true`
  - current time is within registration window if start/end exist
  - effective confirmed count is below capacity

Unique constraints:

- no explicit Mongo unique index is defined in the opened code
- duplicate prevention is application-enforced, not database-enforced

### 3.3 Filesystem Storage

The module also depends on local disk storage:

- payment receipts are stored under `uploads/event_registrations`

Accepted receipt files:

- `.png`
- `.jpg`
- `.jpeg`
- `.pdf`

Maximum upload size:

- `10 MB`

This is operationally significant because the module is not yet durable under multi-instance or ephemeral-disk deployments.

## 4. Backend Logic Implemented

### 4.1 Event Listing

Endpoint:

- `GET /club-events/`

Behavior:

- visible to `admin`, `teacher`, `student`
- supports filtering by:
  - `club_id`
  - `status`
  - `skip`
  - `limit`
- excludes deleted records using `is_deleted`

### 4.2 Event Creation

Endpoint:

- `POST /club-events/`

Logic:

- loads target club
- rejects missing club
- rejects suspended club
- evaluates `_can_manage_event`
- validates payment configuration when `payment_required = true`
- determines initial status:
  - student creator -> `draft`
  - otherwise:
    - `open` if registration enabled
    - `closed` if registration disabled
- writes `created_by` and `created_at`
- writes audit entry

### 4.3 Event Update

Endpoint:

- `PUT /club-events/{event_id}`

Logic:

- event must exist
- current user must still be event manager through club ownership rules
- if reducing capacity:
  - new capacity cannot be lower than existing `registered + approved` count
- if setting status to `open`:
  - parent club must still be `active`
- if turning `registration_enabled` off:
  - event status is forced to `closed`
- payment rules are revalidated

Notable implementation detail:

- create and delete paths emit audit entries
- update path does not appear to emit a matching audit event in the opened code

### 4.4 Event Delete / Archive

Endpoint:

- `DELETE /club-events/{event_id}`

Logic:

- admin only
- soft-archives event by setting:
  - `is_deleted = true`
  - `status = archived`
  - `deleted_at`
  - `deleted_by`
- emits audit event

This is an archive flow, not a hard delete.

### 4.5 Registration Validation

Shared helper:

- `_validate_and_prepare_registration(event_id, student_user_id)`

Checks:

- event exists
- duplicate active registration does not already exist
- registration is enabled
- event status is `open`
- capacity not exceeded
- registration start time not in future
- registration end time not passed

Additional logic:

- if registration deadline has already passed and event is still `open`, backend automatically closes the event before rejecting the registration

### 4.6 Registration Creation

Endpoints:

- `POST /event-registrations/`
- `POST /event-registrations/submit`

Differences:

- `/event-registrations/` is JSON-based
- `/event-registrations/submit` is multipart and supports receipt file upload

Common logic:

- student-only
- status becomes:
  - `pending` if event requires approval
  - `registered` otherwise
- `certificate_issued = false`
- audit action `register_event`
- event may auto-close if it becomes full

Payment-specific logic:

- JSON flow requires `payment_qr_code` when payment is required
- multipart flow can also include receipt file metadata

### 4.7 Registration Listing

Endpoint:

- `GET /event-registrations/`

Scope logic:

- `student`: sees only own registrations
- `teacher`: sees registrations only for events belonging to clubs they manage through coordinator ownership lookup
- `admin`: sees all

Important mismatch:

- event management in `club_events.py` allows teacher access either by:
  - direct coordinator ownership, or
  - `club_coordinator` extension
- registration listing helper in `event_registrations.py` appears to scope teachers only by direct `coordinator_user_id`

This is a real backend scope inconsistency.

### 4.8 Auto Close Logic

Helper:

- `_auto_close_event_if_full(event_id)`

Behavior:

- when confirmed registrations reach capacity, the event is automatically moved to `closed`

This keeps the event state aligned with registration saturation without requiring a manual admin or teacher action.

## 5. Business Rules

### 5.1 Event State Rules

- student-created club events must begin as `draft`
- an event cannot be opened if its club is suspended
- disabling registration forces event status to `closed`
- archived events are treated as removed from normal operations

### 5.2 Capacity Rules

- event capacity must be between `1` and `5000`
- capacity cannot be reduced below current confirmed participation count
- full events auto-close

### 5.3 Registration Rules

- only students can create registrations
- one student can hold only one active registration per event
- registration is blocked outside configured registration window
- registration is blocked when event is not `open`
- registration is blocked when `registration_enabled` is false

### 5.4 Approval Rules

- if `approval_required = true`, new registrations are stored as `pending`
- if `approval_required = false`, new registrations are stored as `registered`

Important gap:

- the opened code shows the `pending` state, but no approval or rejection API was confirmed in the registration endpoint file opened during this review

### 5.5 Payment Rules

- if `payment_required = true`, the event must define payment configuration
- registration requires payment reference input
- multipart registration can additionally upload receipt proof
- payment proof is informational evidence, not integrated transaction verification

### 5.6 Certificate Rules

- `certificate_enabled` exists on the event
- `certificate_issued` exists on the registration

Important gap:

- no certificate generation, issuance workflow, or verification endpoint was observed in the reviewed files

## 6. API Endpoints

### 6.1 Club Events

- `GET /club-events/`
  - list events
- `POST /club-events/`
  - create event
- `PUT /club-events/{event_id}`
  - update event
- `DELETE /club-events/{event_id}`
  - archive event

### 6.2 Event Registrations

- `GET /event-registrations/`
  - list registrations subject to role scope
- `POST /event-registrations/`
  - JSON registration submission
- `POST /event-registrations/submit`
  - multipart registration submission with optional receipt upload

### 6.3 Missing or Unconfirmed APIs

Not confirmed in the reviewed code:

- approve registration
- reject registration
- cancel registration
- mark attendance
- issue certificate

If these flows are needed, they are either unimplemented or implemented outside the opened module files and should not be assumed as active functionality.

## 7. Frontend Implementation

### 7.1 `ClubEventsPage.jsx`

Primary purpose:

- dedicated event management page

Implemented behavior:

- lists club events through `EntityManager`
- filters by:
  - club
  - status
- supports event create with a reduced create form:
  - `club_id`
  - `title`
  - `description`
  - `event_date`
  - `capacity`
- supports row actions:
  - open/close
  - archive/restore
  - view enrollments
- students get a `Register Now` button routing to event registration page

Important frontend/backend mismatch:

- backend event schema supports many fields:
  - `event_type`
  - `visibility`
  - `registration_start`
  - `registration_end`
  - `registration_enabled`
  - `approval_required`
  - `payment_required`
  - `payment_qr_image_url`
  - `payment_amount`
  - `certificate_enabled`
  - `result_summary`
- `ClubEventsPage.jsx` create form exposes only a minimal subset

### 7.2 `EventRegistrationsPage.jsx`

Primary purpose:

- student event registration and registration record browsing

Implemented behavior:

- loads event list for selection
- supports query-param deep link via `event_id`
- student-only registration form
- multipart submission with optional receipt upload
- paginated table of registration records

Form fields captured in UI:

- event
- enrollment number
- full name
- email
- year
- course branch
- section
- phone number
- WhatsApp number
- payment QR code
- payment receipt file

Important note:

- many of these fields are denormalized snapshots typed by the student
- the UI does not derive them from the canonical academic structure

### 7.3 `ClubsPage.jsx`

This page also contains event logic:

- loads club events
- allows club-context event creation
- opens student registration modal
- shows event registration summaries in club context

This means the events UX is duplicated:

- one dedicated events page
- one embedded events area inside clubs

That duplication should be treated as an architectural concern, not as a feature advantage.

## 8. Frontend vs Backend Gaps

### 8.1 Event Create/Edit Exposure Is Incomplete

Backend supports many event configuration fields, but the dedicated event management UI exposes only a small subset.

Missing in create UI:

- `event_type`
- `visibility`
- `registration_start`
- `registration_end`
- `registration_enabled`
- `approval_required`
- `payment_required`
- `payment_qr_image_url`
- `payment_amount`
- `certificate_enabled`

### 8.2 Event Update UI Is Action-Based, Not Field-Based

Backend has a full update schema, but frontend mainly exposes status toggles instead of structured edit.

### 8.3 Registration Approval Flow Is Not Surfaced

The backend models and status values imply approval workflow, but the reviewed frontend pages do not expose:

- approve
- reject
- pending queue management

### 8.4 Duplicate UX Surface

Events can be interacted with in:

- `ClubEventsPage.jsx`
- `ClubsPage.jsx`

This creates overlap in behavior and maintenance cost.

### 8.5 Registration Data Is Manual and Denormalized

The UI asks students to type:

- year
- course branch
- section

Instead of deriving these from enrollment or academic structure records.

## 9. Bugs and Risks Identified

### 9.1 Teacher Scope Mismatch

There is a likely mismatch between:

- `_can_manage_event` in `club_events.py`
- `_teacher_managed_event_ids` in `event_registrations.py`

The event manager check includes teacher extension-role logic, but registration listing appears narrower.

Impact:

- a teacher allowed to manage an event may still not be able to see its registrations

### 9.2 Update Audit Gap

Create and delete paths write audit records, but update path did not visibly do so in the reviewed file.

Impact:

- material event configuration changes may not be audit-complete

### 9.3 Local File Storage Risk

Receipt files are written to local disk under `uploads/event_registrations`.

Impact:

- not durable across pod restart or multi-instance deployment
- not safe for horizontally scaled production architecture

### 9.4 Application-Level Duplicate Prevention Only

Registration uniqueness is enforced by query logic, not by database unique constraint.

Impact:

- concurrent registration requests may still race without a DB-level guard

### 9.5 Denormalized Student Event Metadata

Registration stores:

- `year`
- `course_branch`
- `class_name`

as freeform text.

Impact:

- inconsistent reporting values
- weak integration with academic structure

## 10. Architectural Issues

### 10.1 Events Are Club-Scoped, Not Institution-Scoped

This is currently correct for the implementation, but it means the module cannot yet serve:

- university central fest management
- department-wide academic seminar office
- room/venue scheduling
- cross-club institutional program governance

without substantial extension.

### 10.2 Event Registration Is Not Integrated With Core Academic Identity

Registration identity depends partly on:

- `student_user_id`
- manually entered student profile fields

instead of being fully derived from:

- student master record
- enrollment
- section

### 10.3 Event Attendance Is Not a First-Class Aggregate

`attendance_status` exists inside registration, but there is no separate event attendance subsystem.

That is acceptable for a lightweight club module, but not for large institutional event operations.

### 10.4 Clubs and Events Are Too Tightly Interwoven in Frontend

The current UI blurs module boundaries:

- clubs page contains events behavior
- dedicated events page also exists

This makes ownership of the event workflow unclear.

## 11. Cleanup Strategy

### 11.1 Keep Current Canonical Scope Clear

Document and maintain the event module as:

- `club events + event registrations`

Do not present it as a generic institution-wide events platform until the architecture actually supports that.

### 11.2 Normalize Teacher Scope Logic

Make registration visibility use the same management rules as event mutation:

- direct coordinator ownership
- extension-role based club coordination where intended

### 11.3 Add Structured Edit UI

Expose the backend-supported event fields intentionally in the UI, or explicitly hide unsupported fields and document why.

### 11.4 Remove Duplicate Event UX

Choose one of:

- keep `ClubEventsPage.jsx` as the canonical event workspace and simplify `ClubsPage.jsx`
- keep events embedded in `ClubsPage.jsx` and demote the standalone page

Do not maintain both as peer workflows long term.

### 11.5 Replace Local Disk Receipt Storage

Move event receipt storage to durable object storage.

### 11.6 Add True Workflow Endpoints If Needed

If approval and certificates are real requirements, add explicit APIs and UI for:

- approve registration
- reject registration
- cancel registration
- mark attendance
- issue certificate

## 12. Testing Requirements

### 12.1 Unit Tests

- event creation permission by role
- student-president draft default behavior
- payment-required event validation
- capacity reduction blocked below confirmed registrations
- registration blocked when event closed
- registration blocked when event not in window
- duplicate registration rejection
- auto-close when full
- teacher registration visibility scope

### 12.2 Integration Tests

- create event through club manager flow
- student register through multipart flow with receipt
- admin archive event
- teacher visibility for managed event registrations
- student deep link from `/club-events` to `/event-registrations?event_id=...`

### 12.3 Concurrency Tests

- simultaneous registrations for last available slot
- duplicate same-student submissions in parallel

### 12.4 Storage Tests

- receipt type validation
- receipt size validation
- upload cleanup behavior on failure

## 13. Current Module Assessment

The event module is functional and materially implemented. It supports:

- event creation
- event lifecycle management
- student registrations
- capacity control
- payment-proof attachment
- audit on creation and archive

Its main limitations are architectural rather than missing basics:

- it is club-scoped, not institution-wide
- UI coverage is narrower than backend capability
- teacher scope logic appears inconsistent
- local storage makes uploaded receipts operationally fragile

As implemented today, the module is appropriate for club event operations. It is not yet a full university event management platform.
