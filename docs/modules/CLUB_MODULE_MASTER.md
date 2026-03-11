# CLUB MODULE MASTER

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
Club Module
|-- Club Master Records
|-- Club Membership
|-- Club Applications
|-- Club Leadership Roles
`-- Club-Scoped Events
```

## Internal Entity And Flow Tree

```text
Club
|-- Applications
|-- Members
|-- Leadership assignments
`-- Events and participation flows
```

## 1. Module Overview

The club module is the student-engagement domain for CAPS AI. It manages the lifecycle of clubs, club membership discovery and joining, membership application review, club leadership assignment, club-scoped events, and club analytics.

This is not a cosmetic social feature. It is a structured operational module with:

- club master records
- lifecycle state transitions
- coordinator and president authority
- member and applicant subrecords
- club-scoped event integration
- analytics used by admin dashboards

In the current architecture, the club module is the parent domain for the event module. Events do not stand alone; they are created under clubs.

## 2. Domain Scope

### 2.1 What the module owns

The module directly owns:

- club creation and update
- club status transitions
- membership opening or closure
- student join flow
- approval-based membership applications
- member promotion and status management
- club analytics

The module indirectly governs:

- club events
- event registrations
- club-scoped announcements

### 2.2 What the module does not fully own

The module references, but does not own:

- `users` for coordinator and president identities
- `departments` through `department_id`
- `club_events` and `event_registrations` as downstream subdomains
- announcements under communication

## 3. Database Collections

### 3.1 `clubs`

Purpose:

- master record for each club

Key fields:

- `_id`
- `name`
- `slug`
- `description`
- `category`
- `department_id`
- `academic_year`
- `coordinator_user_id`
- `president_user_id`
- `status`
- `registration_open`
- `membership_type`
- `max_members`
- `logo_url`
- `banner_url`
- `created_by`
- `created_at`
- `updated_at`
- `archived_at`
- `is_active`

Relations:

- `department_id -> departments._id` or compatibility academic unit reference
- `coordinator_user_id -> users._id`
- `president_user_id -> users._id`

Unique logic:

- `slug` must be unique per `academic_year`
- this uniqueness is enforced in application logic during create

Status values:

- `draft`
- `pending_activation`
- `active`
- `registration_closed`
- `closed`
- `suspended`
- `archived`
- `dormant`

### 3.2 `club_members`

Purpose:

- active or historical membership state for students within a club

Key fields:

- `_id`
- `club_id`
- `student_user_id`
- `student_name`
- `student_email`
- `role`
- `status`
- `joined_at`
- `left_at`

Relations:

- `club_id -> clubs._id`
- `student_user_id -> users._id`

Role values:

- `member`
- `president`
- `vice_president`
- `core_member`

Status values:

- `active`
- `inactive`
- `removed`

Important rule:

- only one active `president` member is allowed per club

### 3.3 `club_applications`

Purpose:

- pending or reviewed join requests for clubs that require approval

Key fields:

- `_id`
- `club_id`
- `student_user_id`
- `student_name`
- `student_email`
- `status`
- `applied_at`
- `reviewed_by`
- `reviewed_at`

Relations:

- `club_id -> clubs._id`
- `student_user_id -> users._id`
- `reviewed_by -> users._id`

Status values:

- `pending`
- `approved`
- `rejected`

### 3.4 Downstream dependent collections

These are not the core club collections, but the club module depends on them:

- `club_events`
- `event_registrations`

These are documented in [EVENT_MODULE_MASTER.md](/docs/modules/EVENT_MODULE_MASTER.md).

## 4. Backend Logic Implemented

Primary backend file:

- [clubs.py](/backend/app/api/v1/endpoints/clubs.py)

Supporting schema/model files:

- [club.py](/backend/app/schemas/club.py)
- [clubs.py](/backend/app/models/clubs.py)

### 4.1 Club discovery

Endpoint:

- `GET /clubs/`

Behavior:

- visible to `admin`, `teacher`, and `student`
- supports filters:
  - `status`
  - `is_active`
  - `registration_open`
  - `academic_year`
  - `skip`
  - `limit`
- students do not see clubs in:
  - `draft`
  - `pending_activation`
  - `suspended`
  - `archived`
  - `dormant`

The endpoint also enriches club data with:

- coordinator name/email
- president name/email
- active member count

### 4.2 Club creation

Endpoint:

- `POST /clubs/`

Permission:

- `club:create`

Logic:

- validates coordinator exists and is a teacher
- validates president exists and is a student
- generates slug from explicit slug or name
- rejects duplicate slug within the same academic year
- sets timestamps and creator metadata
- preserves legacy `is_active` compatibility field

Activation constraints at create time:

- `active` requires a coordinator
- `registration_closed` also requires a coordinator and forces `registration_open = false`

### 4.3 Club update

Endpoint:

- `PATCH /clubs/{club_id}`

Permission:

- `club:update`

Additional scope enforcement:

- user must also pass `_can_manage_club(...)`

Club management rules:

- admin can manage all clubs
- teacher can manage if:
  - `coordinator_user_id` matches
  - or teacher has `club_coordinator` extension role
- students cannot update clubs through this path

### 4.4 Status transition engine

The module defines explicit allowed transitions:

- `draft -> pending_activation | active | suspended`
- `pending_activation -> active | suspended | archived`
- `active -> registration_closed | closed | suspended | archived | dormant`
- `registration_closed -> active | closed | suspended | archived | dormant`
- `closed -> active | suspended | archived | dormant`
- `suspended -> active | registration_closed | closed | archived`
- `dormant -> active | registration_closed | closed | archived`
- `archived -> none`

Additional state rules:

- only admin can set `suspended` or `archived`
- `registration_open` can be true only when status is in active states:
  - `active`
  - `registration_closed` is treated as active-like for list semantics, but registration is forced closed
- archiving is blocked if the club still has active events
- suspension is blocked if the club has open events

### 4.5 Join flow

Endpoint:

- `POST /clubs/{club_id}/join`

Role:

- student only

Logic:

- club must be active-like
- registration must be open
- student cannot already be an active or inactive member
- max member limit is enforced if configured

Membership modes:

- `open`
  - creates an active `club_members` record immediately
- `approval_required`
  - creates a `club_applications` record in `pending`

This is a clean split between direct joining and moderated joining.

### 4.6 Membership view

Endpoint:

- `GET /clubs/{club_id}/members`

Scope logic:

- club managers can view all members
- club president can view all members
- student who is not manager or president can only view their own membership row

This is broader than simple self-service but still scoped.

### 4.7 Membership update

Endpoint:

- `PATCH /clubs/{club_id}/members/{member_id}`

Permission:

- `club:update`

Additional scope:

- user must be club manager

Logic:

- supports role and status updates
- promoting a member to `president`:
  - blocks if another active president already exists
  - updates `clubs.president_user_id`
- setting member to `inactive` or `removed` sets `left_at`

### 4.8 Application review

Endpoints:

- `GET /clubs/{club_id}/applications`
- `PATCH /clubs/{club_id}/applications/{application_id}`

Behavior:

- managers and presidents can view club applications
- ordinary students can view only their own applications
- managers can review `pending` applications
- when approved:
  - a `club_members` record is created if one does not already exist

### 4.9 Club analytics

Endpoint:

- `GET /clubs/{club_id}/analytics`

Metrics computed:

- total members
- active members
- inactive members
- 30-day membership growth
- total events
- upcoming events
- completed events
- average attendance percentage
- pending applications

Important implementation detail:

- attendance percentage is approximated from event registration count vs total event capacity
- it is not based on a dedicated event attendance subsystem

## 5. Frontend Implementation

Primary frontend page:

- [ClubsPage.jsx](/frontend/src/pages/ClubsPage.jsx)

Secondary admin launcher:

- [AdminClubsPage.jsx](/frontend/src/pages/Admin/AdminClubsPage.jsx)

### 5.1 `ClubsPage.jsx`

This page is the actual club operations workspace.

Tabs implemented:

- Overview
- Members
- Events
- Announcements
- Analytics

Implemented behavior:

- search and status filter over clubs
- create club form for admin
- join club action for students
- status management buttons for managers
- registration open/close toggle
- membership application review
- embedded event creation and event registration modal
- analytics cards for selected club
- announcement links into communication hub

This page is both a club master UI and a club operations dashboard.

### 5.2 Create support

Frontend create form exposes:

- name
- category
- academic year
- membership type
- max members
- coordinator
- president
- status
- description

Not exposed in the current create UI:

- `department_id`
- `logo_url`
- `banner_url`
- explicit `registration_open` toggle at creation
- explicit slug override

### 5.3 Edit support

There is no structured club edit form.

Instead, the UI exposes action-style updates:

- activate
- close registration
- reopen
- close
- mark dormant
- suspend
- archive
- toggle registration

This means the backend supports rich update, but the frontend mostly uses operational buttons instead of a full edit surface.

### 5.4 Membership operations in UI

Implemented:

- member table
- applications table
- approve application
- reject application

Not implemented:

- direct member role editing from the standard member table
- member status editing beyond application approval path
- dedicated president reassignment flow

### 5.5 Club-linked events in UI

The clubs page includes an events tab that:

- creates events
- lists events
- opens registration modal for students

This overlaps with the dedicated [ClubEventsPage.jsx](/frontend/src/pages/ClubEventsPage.jsx) page.

## 6. API Surface

### 6.1 Club master endpoints

- `GET /clubs/`
- `POST /clubs/`
- `PATCH /clubs/{club_id}`

### 6.2 Membership endpoints

- `POST /clubs/{club_id}/join`
- `GET /clubs/{club_id}/members`
- `PATCH /clubs/{club_id}/members/{member_id}`

### 6.3 Application endpoints

- `GET /clubs/{club_id}/applications`
- `PATCH /clubs/{club_id}/applications/{application_id}`

### 6.4 Analytics endpoint

- `GET /clubs/{club_id}/analytics`

### 6.5 Closely related downstream endpoints

These belong to the event submodule but are operationally adjacent:

- `GET /club-events/`
- `POST /club-events/`
- `PUT /club-events/{event_id}`
- `DELETE /club-events/{event_id}`
- `GET /event-registrations/`
- `POST /event-registrations/`
- `POST /event-registrations/submit`

## 7. Business Rules

### 7.1 Coordinator and president identity rules

- coordinator must be a teacher
- president must be a student

### 7.2 Activation rules

- a club cannot become active without a coordinator
- registration can only be open when the club is active

### 7.3 Archive and suspend rules

- only admin can suspend or archive
- archive is blocked if club has active events
- suspend is blocked if club has open events

### 7.4 Membership rules

- join is student-only
- duplicate membership is blocked
- max member capacity is enforced if set
- open clubs auto-enroll members
- approval-required clubs create pending applications

### 7.5 President role rules

- only one active president member is allowed in a club
- promoting a member to president updates the club master record

## 8. Frontend vs Backend Gaps

### 8.1 No full club edit form

Backend supports update of:

- name
- slug
- description
- category
- department_id
- coordinator_user_id
- president_user_id
- membership_type
- max_members
- logo_url
- banner_url
- status
- registration_open

Frontend mostly exposes only status and registration toggles.

### 8.2 Department linkage is backend-only in practice

`department_id` exists in schema and backend storage, but it is not intentionally exposed in the main clubs UI.

### 8.3 Branding fields are backend-supported but not used

- `logo_url`
- `banner_url`

These are present in the schema but not exposed through the current clubs page.

### 8.4 Membership management is partial

Backend supports member role/status updates. Frontend mainly handles:

- membership application review

It does not expose a full member-administration surface.

### 8.5 Duplicate event experience

Event operations are embedded inside the clubs page and also exposed in a dedicated event page.

## 9. Architectural Issues

### 9.1 Club module mixes master data and operations

The clubs page is simultaneously:

- list view
- create club form
- membership management UI
- event workspace
- analytics workspace
- communication launcher

This is powerful, but it also makes the module broad and harder to evolve.

### 9.2 Active-state semantics are split

The module uses:

- canonical `status`
- compatibility `is_active`

This is workable but creates legacy semantics that can drift.

### 9.3 Department relation is weakly integrated

Clubs can reference `department_id`, but the clubs UI does not strongly integrate with the academic hierarchy.

### 9.4 Analytics are derived, not event-attendance native

Club analytics estimate attendance through registration totals and capacity. This is not the same as actual attendance tracking.

## 10. Risks and Bugs Identified

### 10.1 Slug uniqueness is app-enforced only

The duplicate slug check is implemented in code, not visibly enforced by a DB unique index in the reviewed files.

Risk:

- concurrent club creation can race

### 10.2 Teacher extension role is broad

A teacher with `club_coordinator` extension can manage clubs beyond direct coordinator ownership.

This may be intended, but it is broad enough that row-level scope should be reviewed carefully.

### 10.3 Partial edit exposure creates contract drift

Backend supports more club fields than frontend exposes. That increases the chance of hidden state and operator confusion.

### 10.4 Event coupling makes archive/suspend logic dependent on downstream consistency

Club archiving and suspension rely on club event state being correct. If event status is stale, governance of club state can be wrong.

## 11. Cleanup Strategy

### 11.1 Keep clubs as the parent domain for events

This is already the real model and should be documented explicitly.

### 11.2 Add a structured edit UI

Expose intentional editable fields:

- name
- category
- academic year
- department
- coordinator
- president
- membership type
- max members
- logo/banner if kept

### 11.3 Decide whether to keep compatibility `is_active`

If legacy UI paths no longer need it, phase it out in favor of `status` only.

### 11.4 Add stronger indexing

At minimum, make slug uniqueness durable at the database layer.

### 11.5 Separate concerns in frontend

Consider splitting:

- club master management
- membership management
- club event operations
- club analytics

into clearer subviews or dedicated pages.

## 12. Testing Requirements

### 12.1 Unit tests

- coordinator validation on create/update
- president validation on create/update
- slug uniqueness by academic year
- valid and invalid state transitions
- archive blocked by active events
- suspend blocked by open events
- open membership join flow
- approval-required join flow
- president uniqueness in member update

### 12.2 Integration tests

- admin creates club and activates it
- teacher coordinator updates own club but not unrelated club
- student joins open club
- student applies to approval-required club
- manager approves application and member is created
- student visibility filter hides non-discoverable clubs

### 12.3 Frontend tests

- status action buttons shown only to managers
- student join button only active for active clubs with open registration
- create club form only visible to admin
- analytics tab behavior by role
- application approve/reject actions update list state

## 13. Current Module Assessment

The club module is one of the more complete non-academic operational modules in the system. It has:

- a clear master entity
- role-based lifecycle control
- moderated membership flow
- club leadership assignment
- analytics
- direct integration into events and communication

Its main weaknesses are:

- incomplete frontend edit coverage
- weak department integration
- mixed `status` and `is_active` semantics
- duplicated event experience across club and event pages

As implemented today, it is a real operational module, not a placeholder. It is already suitable for managed club operations, provided the hidden field drift and duplicate UX surface are cleaned up.


