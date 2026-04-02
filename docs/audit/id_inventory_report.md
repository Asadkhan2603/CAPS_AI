# ID Inventory Report

## Summary
- Total IDs found: 47 canonical/runtime ID fields in active code paths, plus 11 route-only aliases that still resolve to Mongo document `_id` values.
- Entity types: users, RBAC roles, RBAC permissions, RBAC scopes, user sessions, universities, faculties, departments, programs, specializations, batches, semesters, sections/classes, groups, subjects, course offerings, class slots, students, enrollments, assignments, submissions, evaluations, review tickets, audit logs, admin action reviews, clubs, club memberships, club applications, club events, event registrations, notices, notifications, internship sessions, AI chats, AI evaluation runs, AI jobs, scheduler locks, request tracing, JWT tokens.
- High-risk IDs: `_id`, `id`, overloaded `faculty_id` / `department_id` / `program_id` / `specialization_id`, aliased `class_id` / `section_id`, ambiguous `student_id`, polymorphic `entity_id` and `scope_ref_id`, RBAC `year_id`, auth `sub` / `jti` / `refresh_jti`, governance `review_id`, session `fingerprint`.

## ID Catalog

| ID Field | Entity | Type | Format | Used In | Exposed To UI | Safe To Replace | Recommended Display |
|----------|--------|------|--------|---------|---------------|-----------------|---------------------|
| `_id` | All Mongo collections | Database primary key | Mongo ObjectId | Backend models, CRUD endpoints, indexes, route params, services | Indirectly via `id` | No | Keep internal only |
| `id` | All public API entities | External/public ID wrapper over `_id` | Stringified ObjectId | API responses, frontend row keys, routing, form state | Yes | UI only | Entity label plus secondary code where helpful |
| `university_id` | University | External/public business ID | Custom string like `MEDICAPS` | University model/schema, faculty lineage, academic UI | Yes | Usually no | University name with code in parentheses |
| `university_master_id` | Faculty/Department lineage | Foreign key to university business ID | Custom string | Faculty/department records, master hierarchy import, lineage sync | Yes | API/UI only | University name or `university_id` label |
| `faculty_id` | Faculty record and many child records | Overloaded: business ID on faculty, foreign key elsewhere | Custom `FAC-*` or ObjectId string | Faculty entity, departments, batches, semesters, sections, user scopes | Yes | Conditional | Faculty name; keep raw only for backend relations |
| `faculty_master_id` | Department/Program/Specialization lineage | Foreign key to faculty business ID | Custom `FAC-*` string | Master hierarchy lineage, API serializers, imports | Yes | UI/API only | Faculty name plus faculty code |
| `department_id` | Department record and many child records | Overloaded: business ID on department, foreign key elsewhere | Custom `DEP-*` or ObjectId string | Programs, users, scopes, batches, semesters, sections, clubs | Yes | Conditional | Department name plus department code |
| `department_master_id` | Program/Specialization lineage | Foreign key to department business ID | Custom `DEP-*` string | Master hierarchy lineage, serializers, imports | Yes | UI/API only | Department name plus code |
| `program_id` | Program record and many child records | Overloaded: business ID on program, foreign key elsewhere | Custom `PRG-*` or ObjectId string | Specializations, batches, semesters, sections, users, academic batching | Yes | Conditional | Program name plus program code |
| `program_master_id` | Specialization lineage | Foreign key to program business ID | Custom `PRG-*` string | Specialization lineage, import logic, migration-safe lookups | Yes | UI/API only | Program name plus code |
| `specialization_id` | Specialization record and many child records | Overloaded: business ID on specialization, foreign key elsewhere | Custom `SPC-*` or ObjectId string | Batches, semesters, sections, users, academic batching | Yes | Conditional | Specialization name plus code |
| `batch_id` | Batch and child academic records | Foreign key | Stringified ObjectId | Semesters, sections, groups, offerings, users, RBAC year-scope resolution | Yes | UI only | Batch name / code / academic span |
| `semester_id` | Semester and child academic records | Foreign key | Stringified ObjectId | Sections, groups, offerings, academic filters, user profile scope | Yes | Yes for UI/API read models | Semester label like `Semester 3` |
| `year_id` | RBAC scope | Internal scope ID / pseudo foreign key | Numeric year string or ObjectId string | RBAC scopes, scope filters, batch-scope resolution | Yes in RBAC admin | No in storage | `2024 intake`, `2nd Year`, or resolved batch span |
| `class_id / section_id` | Section enrollment and timetable domain | Foreign key with legacy aliasing | Stringified ObjectId | Students, enrollments, assignments, timetables, attendance, user scope | Yes | UI only | Section name plus faculty/batch context |
| `group_id` | Group and group-scoped academic records | Foreign key | Stringified ObjectId | Students, course offerings, group UI, validations | Yes | UI only | Group code/name |
| `subject_id` | Subject and teaching records | Foreign key | Stringified ObjectId | Assignments, course offerings, timetables, subject-teacher maps | Yes | UI only | Subject name plus code |
| `course_offering_id` | Course offering | Database primary key / foreign key | Stringified ObjectId | Class slots, attendance, timetable helpers, offering tables | Yes | UI only | Subject + teacher + section + term |
| `class_slot_id` | Class slot | Database primary key / foreign key | Stringified ObjectId | Attendance records, slot lookup maps, teacher schedules | Yes | UI only | Day + time + subject/section |
| `assignment_id / exam_id` | Assignment and AI chat scope | Database primary key / foreign key | Stringified ObjectId | Submissions, similarity, evaluations, AI chat history, teacher evaluation flow | Yes | UI only | Assignment title + subject + due date |
| `submission_id` | Submission | Database primary key / foreign key | Stringified ObjectId | Evaluations, AI jobs, similarity, history, teacher review flow | Yes | UI only | Student name + assignment title + submitted time |
| `evaluation_id` | Evaluation | Database primary key / foreign key | Stringified ObjectId | Review tickets, AI evaluation runs, evaluation lifecycle | Yes | UI only | Student + assignment + grade/status |
| `timetable_id / template_timetable_id` | Timetable | Database primary key / foreign key | Stringified ObjectId | Timetable CRUD, publish/lock flow, template copy | Yes | UI only | Section + semester + shift + version |
| `club_id` | Club, membership, application, event | Database primary key / foreign key | Stringified ObjectId | Clubs, club events, memberships, applications, analytics | Yes | UI only | Club name |
| `event_id` | Club event / event registration | Database primary key / foreign key | Stringified ObjectId | Event registrations, student history, club event management | Yes | UI only | Event title + date |
| `scope_ref_id` | Notice targeting | Polymorphic foreign key | Stringified ObjectId | Notices, communication preview, announcement targeting | Yes | UI/API read models only | Resolved audience label by scope type |
| `entity_id` | Audit log / governance review | Polymorphic internal system ID | Stringified ObjectId or custom literal like `global` | Audit logs, destructive action telemetry, governance approvals | Yes | No in storage | Pair with `entity_type` and resolved entity label |
| `student_id` | Student profile, attendance, enrollment, internship | Ambiguous: student profile PK, FK, and sometimes roll-number input | Usually ObjectId string, but attendance accepts roll number as input | Attendance, enrollments, student interventions, internship sessions, AI chat | Yes | High risk; UI only after resolution | Student name + roll number |
| `student_user_id` | Student auth user relation | Foreign key | Stringified ObjectId | Evaluations, clubs, event registrations, submissions, internship sessions | Yes | UI only | Student full name + email |
| `teacher_user_id` | Teacher auth user relation | Foreign key | Stringified ObjectId | Course offerings, evaluations, timetables | Yes | UI only | Teacher full name + email |
| `user_id / actor_id` | Generic user relation | Foreign key / internal alias | Stringified ObjectId | RBAC scopes, user sessions, governance session filters, AI ops service calls | Yes | UI only | User full name + email + role |
| `actor_user_id` | Audit and AI evaluation actor | Foreign key with security significance | Stringified ObjectId | Audit logs, AI evaluation runs, destructive action telemetry | Yes | UI only; keep raw internally | Actor name + email + role |
| `created_by / deleted_by / requested_by / reviewed_by / executed_by` | Legacy actor fields without `_user_id` suffix | Foreign key | Stringified ObjectId | Notices, notifications, clubs, club events, admin action reviews, soft-delete metadata | Partially | UI only | User full name + email; do not expose raw IDs |
| `requested_by_user_id / resolved_by_user_id / assigned_by_user_id / marked_by_user_id / finalized_by_user_id / owner_user_id / created_by_user_id` | Workflow actor references | Foreign key | Stringified ObjectId | Review tickets, enrollments, attendance, evaluations, interventions, timetables | Yes | UI only | User full name + role |
| `target_user_id` | Notification target | Foreign key | Stringified ObjectId | Notifications API, create form, alert center cards | Yes | UI only | Target user name + email |
| `class_coordinator_user_id / coordinator_user_id / president_user_id` | Role assignment relations | Foreign key | Stringified ObjectId | Sections, clubs, permission checks, UI ownership logic | Yes | UI only | Assigned person name + email |
| `role_id` | RBAC role assignment | Foreign key / internal system ID | Stringified ObjectId | Admin users, role lookup, permission sync, auth hydration | Mostly backend, some admin UI fetches | No | Role name + code |
| `permission_id` | RBAC permission relation | Foreign key / internal system ID | Stringified ObjectId | Role-permission links, user overrides, permission sync | No direct UI | No | Permission key + name |
| `review_id` | Admin action review | Database primary key / governance token | Stringified ObjectId | Governance routes, destructive delete query params, review execution | Yes in admin tooling | No | Review action + entity + status |
| `public_id` | Cloudinary notice attachment | External provider ID | Custom random string like `notice-<rand>-<rand>` | Notice attachments, delete calls, attachment keys | Only in attachment payloads | No | Attachment name or URL only |
| `jti / refresh_jti` | JWT / refresh session token | Internal security ID | UUID hex string | JWT payloads, token blacklist, session rotation, logout | Not intentionally shown to users | No | Never display |
| `sub` | JWT subject | Internal security ID | Stringified user ObjectId | Access/refresh token payloads, current-user hydration, rate limiter actor key | Not intentionally shown to users | No | Never display |
| `request_id` | Request observability | Internal operational ID | UUID string | Middleware logs, response headers, developer panel, run logs | Yes in developer tooling | No | Keep as trace/debug token |
| `trace_id` | Request tracing | Internal operational ID | UUID string | Middleware logs, response headers, developer panel, error envelopes | Yes in developer tooling | No | Keep as trace/debug token |
| `error_id` | Error correlation | Internal operational ID | Custom string like `err_<hex>` | Rate-limit errors, error envelopes, frontend error handling, developer panel | Yes in error tooling | No | Keep as support/debug token |
| `scheduler_lock_id` | Scheduler leadership lock | Internal system ID | Configured custom string | Settings, scheduler lock documents, leader election | No | No | Keep internal |
| `fingerprint` | User session/device fingerprint | Internal security ID | SHA-256 hex string | Auth sessions, anomaly detection, governance session monitor | Yes, truncated in admin UI | No | Masked/truncated only |

## Key Observations

### 1. IDs Exposed Directly to UI
- Audit logs render raw `actor_user_id` and `entity_id` directly in the admin table.
- Governance sessions fall back to raw `user_id` when `user_name` and `user_email` are missing.
- Governance review records expose raw `requested_by`, `reviewed_by`, and `executed_by` with no resolver fields.
- Notifications fall back to raw `target_user_id` if the user lookup is missing.
- Evaluations fall back to raw `submission_id`, `student_user_id`, and `teacher_user_id`.
- Event registrations can fall back to raw `event_id`; club event and club member views can fall back to raw `club_id` and `student_user_id`.
- Attendance, enrollments, assignments, course offerings, class slots, submissions, students, groups, semesters, and timetable helpers all contain fallback paths that render raw relation IDs when lookup maps are absent.
- `class_coordinator_user_id` is rendered directly in sections when name lookup fails.
- Developer tooling intentionally exposes `request_id`, `trace_id`, and `error_id`.

### 2. Safe Replacements
- UI-only replacement is safe for relation IDs that already have lookup data or accompanying names: `teacher_user_id`, `student_user_id`, `subject_id`, `section_id`, `batch_id`, `semester_id`, `club_id`, `event_id`, `assignment_id`, `submission_id`, `evaluation_id`, `course_offering_id`, `class_slot_id`, `target_user_id`.
- Audit/governance actor fields can safely be replaced in UI and read-model responses with user labels while preserving the raw value internally.
- `scope_ref_id` is safe to replace in UI once resolved against its `scope`.
- Business IDs on master entities (`university_id`, `faculty_id`, `department_id`, `program_id`, `specialization_id`) are already meaningful enough for admin views; child records should show labels instead of the raw foreign keys.

### 3. Unsafe / Critical IDs
- `_id` and public `id` are the backbone of CRUD routes, joins, and frontend state keys; do not change their storage semantics.
- `sub`, `jti`, `refresh_jti`, `fingerprint`, `request_id`, `trace_id`, `error_id`, and `scheduler_lock_id` are security/operational identifiers and must remain internal.
- `review_id` is part of the destructive-action approval flow and should not be replaced or hidden from the workflow itself.
- `role_id` and `permission_id` are core RBAC relation keys and should stay internal even if the UI shows role codes and permission keys.
- `entity_id` must remain raw internally because it is polymorphic and paired with `entity_type` for audit/governance checks.
- `student_id` is unsafe to replace blindly because some endpoints accept either student document ID or roll number during resolution.
- `year_id` is unsafe to reinterpret globally because RBAC treats it as either a numeric intake year or a batch ObjectId.

### 4. Inconsistent Naming
- `class_id` and `section_id` are the same concept and are normalized together in enrollments, students, timetables, and UI filters.
- `faculty_id`, `department_id`, `program_id`, and `specialization_id` are overloaded:
  master entity rows use them as business/public IDs, while child collections use the same names as foreign keys to document IDs.
- User actor references are inconsistent: some collections use `*_user_id`, others use `created_by`, `deleted_by`, `requested_by`, `reviewed_by`, or `executed_by`.
- Route params are not uniform even when they all resolve to document `_id` values: `university_doc_id`, `offering_id`, `slot_id`, `member_id`, `application_id`, `ticket_id`, `job_id`, `review_id`.
- `exam_id` in AI chat is effectively assignment-scoped, but it is named differently from `assignment_id`.

### 5. Security Concerns
- Audit logs expose raw actor/resource identifiers to the frontend without guaranteed name resolution.
- Governance session monitoring exposes a device `fingerprint` and may expose raw `user_id` when user hydration fails.
- JWT payloads store raw `sub` and `jti`; these should never become user-facing replacement targets.
- Raw document IDs are frequently shipped to the frontend even when the UI later resolves them to names, increasing accidental leakage risk in logs, browser storage, and screenshots.
- Announcement cards do not use `created_by`; they try to use friendly author-name fields that the notice read model does not provide, causing an information gap instead of a safe human-readable label.

## Replacement Strategy (DO NOT APPLY YET)

For each entity:
- user -> `full_name + email`
- role -> `name + code`
- permission -> `name + key`
- RBAC scope -> `department_name` and resolved year label
- audit logs -> `actor_name + role`, `entity_label + entity_type`
- governance reviews -> requester/reviewer/executor names plus action/entity summary
- university -> `university_name + university_id`
- faculty -> `faculty_name + faculty_code`
- department -> `department_name + department_code`
- program -> `program_name + program_code`
- specialization -> `specialization_name + specialization_code`
- batch -> `name + code` or academic span label
- semester -> `label`
- section/class -> `name + faculty_name` or `name + batch/semester`
- group -> `name/code`
- subject -> `name + code`
- course offering -> `subject_name + teacher_name + section_name`
- class slot -> `day + start_time + subject_name`
- student profile -> `full_name + roll_number`
- student user relation -> `full_name + email`
- teacher user relation -> `full_name + email`
- assignment/exam -> `title + subject_name`
- submission -> `student_name + assignment_title + created_at`
- evaluation -> `student_name + assignment_title + status/grade`
- club -> `name`
- event -> `title + event_date`
- notice target -> resolved audience label from `scope` + `scope_ref_id`
- notification target -> `full_name + email`
- review ticket -> `evaluation summary + requester/resolver`
- attachment `public_id` -> file name only in UI; keep `public_id` internal
- observability IDs (`request_id`, `trace_id`, `error_id`) -> keep as debug tokens
- auth IDs (`sub`, `jti`, `refresh_jti`, `fingerprint`) -> keep internal only

## FINAL INSTRUCTION

DO NOT MODIFY ANY CODE.
WAIT FOR NEXT INSTRUCTION:
User will specify which IDs to replace and where.
