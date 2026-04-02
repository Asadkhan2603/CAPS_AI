# Clubs And Events

## Purpose

This module manages non-academic student activity through clubs, club memberships, applications, events, and event registrations.

## Data Model

Entities:

- clubs
- club members
- club applications
- club events
- event registrations

## APIs

Primary endpoints:

- `/clubs`
- `/clubs/{club_id}/join`
- `/clubs/{club_id}/members`
- `/clubs/{club_id}/members/{member_id}`
- `/clubs/{club_id}/applications`
- `/clubs/{club_id}/applications/{application_id}`
- `/clubs/{club_id}/analytics`
- `/club-events`
- `/event-registrations`
- `/event-registrations/submit`

## Workflow

1. admin or authorized user creates a club
2. users apply or join
3. club leadership reviews membership state
4. events are created
5. registrations are submitted and tracked

## Dependencies

- `backend/app/api/v1/endpoints/clubs.py`
- `backend/app/api/v1/endpoints/club_events.py`
- `backend/app/api/v1/endpoints/event_registrations.py`
- `frontend/src/pages/ClubsPage.jsx`
- `frontend/src/pages/ClubEventsPage.jsx`
- `frontend/src/pages/EventRegistrationsPage.jsx`
