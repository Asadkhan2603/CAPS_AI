# Student Grievance System With Tracking, Escalation, and Forwarding

## Summary
Build a native grievance module where students submit complaints from their portal, track live progress, read public replies, and add follow-ups. Each grievance starts with the student’s class coordinator, auto-escalates to the scoped HOD after 24 hours if unresolved, then auto-escalates to the scoped Dean after another 24 hours.

This plan is now decision-complete for v1.

Locked defaults:
- class coordinator is the first-stage owner
- HOD and Dean reuse existing scoped admin RBAC roles
- one grievance stays as one thread through all stages
- students can track status and public replies
- staff can add internal-only notes
- coordinator/HOD/Dean can forward to any teacher or admin
- forwarding assigns a resolver but does not transfer stage ownership
- forwarding does not pause or reset the 24-hour SLA
- if routing fails, fallback queue goes to `academic_admin`
- initial grievance supports one optional attachment; comments are text-only in v1
- resolved grievances can be reopened by the student

## Key Changes
### Core workflow
- Add a dedicated grievance collection, schema, serializer, and API router.
- Store:
  - `student_user_id`, `student_id`
  - `section_id`, `department_id`
  - `category`, `title`, `description`, optional initial attachment
  - `current_stage` as `coordinator|hod|dean`
  - `status` as `open|in_progress|resolved|reopened|routing_failed`
  - `stage_due_at`, `resolved_at`, `resolved_by_user_id`
  - `assigned_resolver_user_id`, `forwarded_by_user_id`, `forwarded_at`
  - unified timeline/activity entries for submit, comment, note, forward, escalate, resolve, reopen

### Routing and ownership
- On create, resolve student context from existing `users -> students -> section/class -> department` links.
- First-stage owner is `sections.class_coordinator_user_id`.
- HOD and Dean access comes from existing scoped admin RBAC assignments on `department_id`.
- HOD/Dean operate as scoped queue owners; the acting admin is recorded on each action.
- If no valid owner exists at any stage, mark as `routing_failed` and surface it to `academic_admin`.

### Escalation and forwarding
- Extend the existing scheduler/background-job pattern with a grievance escalation job.
- Escalation rule:
  - `coordinator` unresolved for 24h -> `hod`
  - `hod` unresolved for next 24h -> `dean`
- On escalation:
  - update `current_stage`
  - set fresh `stage_due_at` for the new stage
  - clear `assigned_resolver_user_id`
  - append activity log entry
  - create notifications for next-stage actors
- Forwarding rule:
  - coordinator/HOD/Dean can assign a specific teacher or admin as helper resolver
  - helper can comment and work on the grievance
  - helper does not become stage owner
  - stage SLA continues running unchanged

### Visibility and actions
- Students:
  - create grievance
  - view only their own grievances
  - see full public timeline, stage, due state, and public replies
  - add public follow-up comments
  - reopen a resolved grievance
- Class coordinators:
  - access only grievances for their scoped class/section
  - add public replies, internal notes, forward, resolve
- HOD admins:
  - access only grievances in their scoped `department_id`
  - add public replies, internal notes, forward, resolve
- Dean admins:
  - access only grievances in their scoped `department_id`
  - add public replies, internal notes, forward, resolve
- Forwarded resolver:
  - can access only grievances explicitly assigned to them
  - can add work comments
  - cannot take over unrelated queue access

### API and frontend
- Add endpoints:
  - `POST /grievances`
  - `GET /grievances/mine`
  - `GET /grievances/inbox`
  - `GET /grievances/{id}`
  - `POST /grievances/{id}/comments`
  - `POST /grievances/{id}/internal-notes`
  - `POST /grievances/{id}/forward`
  - `PATCH /grievances/{id}/status`
  - `POST /grievances/{id}/reopen`
- Add frontend pages:
  - student grievance page with create form, list, detail timeline, public thread
  - coordinator grievance inbox
  - HOD grievance inbox
  - Dean grievance inbox
- Detail view should show:
  - current stage
  - overdue/time remaining
  - forwarded resolver if present
  - public discussion
  - internal notes for staff only
  - complete event timeline

## Test Plan
- Student submits grievance and sees it in `My Grievances`.
- Grievance routes to class coordinator from the student’s mapped section.
- Coordinator-stage grievance auto-escalates after 24 hours if unresolved.
- HOD-stage grievance auto-escalates after another 24 hours if unresolved.
- Resolved grievance stops escalation.
- Student sees public replies from coordinator, HOD, and Dean.
- Student does not see internal notes.
- Student can reopen a resolved grievance.
- Non-coordinator teachers cannot access coordinator inbox by default.
- HOD and Dean inboxes only show grievances inside matching `department_id` scope.
- Forwarding assigns a teacher/admin helper and notifies them.
- Forwarding does not reset or pause the SLA timer.
- Forwarded resolver can act only on grievances explicitly assigned to them.
- Missing-recipient cases land in `academic_admin` fallback queue.

## Assumptions
- “Teacher grievance page” means class coordinator grievance inbox.
- Student-visible tracking includes timeline, stage changes, forwarded helper display, and public replies.
- Comment attachments are out of scope for v1; only the initial grievance may include one attachment.
- Existing notifications, audit logging, scheduler infrastructure, section mapping, and RBAC scope helpers are reused instead of creating separate infrastructure.
