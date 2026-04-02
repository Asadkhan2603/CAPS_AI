# Communication And Notices

## Purpose

This module manages announcements, notification-style updates, audience previewing, and the communication surfaces exposed in the frontend workspace.

## Data Model

Entities:

- notices
- notifications
- scope targeting records by college, batch, section, or subject

Important fields:

- `scope`
- `scope_ref_id`
- `priority`
- `expires_at`
- read-state metadata

## APIs

Primary endpoints:

- `/notices`
- `/notices/{notice_id}/read`
- `/notices/read`
- `/notices/process-scheduled`
- `/notifications`
- `/notifications/{notification_id}/read`
- `/admin/communication/preview-target`
- `/analytics/feed`

## Workflow

1. admin or teacher previews the target audience
2. notice is created with optional attachment and expiry
3. recipients see announcements and feed updates
4. read-state is tracked per user
5. scheduled processing handles expiring or queued notices

## Dependencies

- `backend/app/api/v1/endpoints/notices.py`
- `backend/app/api/v1/endpoints/notifications.py`
- `backend/app/api/v1/endpoints/admin_communication.py`
- `frontend/src/pages/Communication/AnnouncementsPage.jsx`
- `frontend/src/pages/Communication/FeedPage.jsx`
- `frontend/src/pages/NotificationsPage.jsx`
