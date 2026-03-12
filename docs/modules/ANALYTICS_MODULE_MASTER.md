# Analytics Module Master

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
Analytics Module
|-- Live Analytics API
|-- Admin Snapshot Analytics
|-- Compliance Metrics
|-- Dashboard Projections
`-- Caching And Snapshot Services
```

## Internal Entity And Flow Tree

```text
Operational collections
`-- Aggregation and projection helpers
    |-- Role-scoped analytics
    |-- Admin analytics snapshots
    `-- Dashboard and compliance views
```

## 1. Module Overview

The Analytics module provides read-oriented metrics, summaries, and derived operational insight across CAPS AI. It is not a single dashboard. It is a cross-cutting backend capability used by:

- role-based dashboard summary cards
- teacher section health tiles
- admin platform metrics
- compliance audit summaries
- legacy academic-structure analytics payloads
- snapshot history and platform trend retention

Primary backend files:

- [analytics.py](/backend/app/api/v1/endpoints/analytics.py)
- [admin_analytics.py](/backend/app/api/v1/endpoints/admin_analytics.py)
- [analytics_snapshot.py](/backend/app/services/analytics_snapshot.py)

Primary frontend consumers:

- [AnalyticsPage.jsx](/frontend/src/pages/AnalyticsPage.jsx)
- [DashboardPage.jsx](/frontend/src/pages/DashboardPage.jsx)
- [AdminAnalyticsPage.jsx](/frontend/src/pages/Admin/AdminAnalyticsPage.jsx)
- [AdminCompliancePage.jsx](/frontend/src/pages/Admin/AdminCompliancePage.jsx)
- [TeacherClassTiles.jsx](/frontend/src/components/ui/TeacherClassTiles.jsx)

The module has two distinct layers:

1. Live role-scoped analytics:
   - `/analytics/*`
2. Admin platform and snapshot analytics:
   - `/admin/analytics/*`

This distinction matters because the module mixes:

- lightweight count-based metrics
- cached snapshot metrics
- heavy, tree-shaped, in-memory analytical payloads

## 2. Main Responsibilities

The current analytics module serves five responsibilities.

### 2.1 Role-based summaries

Return small dashboard summary payloads for:

- students
- teachers
- admins

### 2.2 Teacher section health analytics

Build section health tiles for teachers based on:

- enrollment counts
- assignment counts
- late submissions
- similarity alerts
- risk-student heuristics

### 2.3 Platform-level admin analytics

Expose high-level operational counts and cached metrics for administrators.

### 2.4 Audit/compliance summaries

Surface recent audit severity counts and top actions.

### 2.5 Snapshot history

Persist daily summarized platform metrics to `analytics_snapshots`.

## 3. Collections and Data Sources Used

The Analytics module is a reader over many collections rather than an owner of one business entity.

### Primary analytics-owned collection

#### `analytics_snapshots`

Used by:

- `compute_platform_snapshot(...)`
- `get_daily_snapshot(...)`
- `get_snapshot_history(...)`

Purpose:

- store daily summarized platform metrics
- support cached platform analytics instead of recomputing everything on every request

Stored fields include:

- `date`
- `users_total`
- `active_students`
- `daily_active_users`
- `login_count_24h`
- `assignment_completion_pct`
- `club_participation_pct`
- `event_attendance_pct`
- `pending_review_tickets`
- `active_clubs`
- `events_this_week`
- `updated_at`

### Key source collections read by analytics

The module reads heavily from:

- `users`
- `students`
- `enrollments`
- `assignments`
- `submissions`
- `evaluations`
- `similarity_logs`
- `notices`
- `clubs`
- `club_members`
- `club_events`
- `event_registrations`
- `audit_logs`
- `subjects`
- `classes`
- `courses`
- `years`

The last three are important because they show that parts of analytics still depend on the legacy academic hierarchy.

## 4. Backend Logic Implemented

## 4.1 Common analytics helpers

The general analytics endpoint file includes reusable helpers:

- `_bounded_cap(...)`
- `_safe_object_ids(...)`
- `_to_utc_datetime(...)`
- `_get_cached_json(...)`
- `_set_cached_json(...)`
- `_distinct_values(...)`
- `_count_by_field(...)`

These are meaningful improvements over completely ad hoc analytics queries.

What they do:

- impose scan caps
- normalize ObjectId handling
- reduce repeated query boilerplate
- use Redis for response caching
- prefer aggregation when available, then fall back to bounded in-memory grouping

This is the strongest part of the module design.

## 4.2 `/analytics/summary`

This endpoint returns different summary payloads by role.

### Student summary

Metrics:

- `total_submissions`
- `total_evaluations`
- `pending_reviews`

### Teacher summary

Metrics:

- `my_assignments`
- `my_submissions`
- `my_evaluations`
- `my_similarity_flags`
- `my_notices`

### Admin summary

Metrics:

- `users`
- `courses`
- `years`
- `classes`
- `subjects`
- `students`
- `assignments`
- `submissions`
- `evaluations`
- `similarity_flags`
- `notices`
- `clubs`
- `club_events`

Caching:

- role and user-scoped Redis cache key:
  - `analytics:summary:{role}:{user_id}`

## 4.3 Teacher section analytics

Endpoints:

- `GET /analytics/teacher/classes`
- `GET /analytics/teacher/sections`

`/teacher/classes` is explicitly documented in code as a legacy alias.

The real logic is `_teacher_section_tiles(...)`.

It builds a health tile per section using:

- classes where the teacher is coordinator
- extra classes inferred from assignments created by the teacher
- subject names attached to assignments
- enrollment rows
- direct student rows from `students.class_id`
- submissions
- similarity logs
- evaluation-derived risk flags

Health status is derived from thresholds:

- `risk`
- `attention`
- `healthy`

This is useful operationally, but it depends on several denormalized and duplicated data sources.

## 4.4 `/analytics/academic-structure`

This endpoint builds a nested analytical tree:

- university
- courses
- years
- classes
- students
- subjects

Important facts:

- it still uses legacy data lineage `courses -> years -> classes` (storage-only compatibility)
- it is paginated by class count
- it builds a large in-memory response tree after multiple reads
- it merges membership from both `enrollments` and `students.class_id`

This endpoint is structurally analytical, not canonical academic setup.

Current frontend note:

- the current [AcademicStructurePage.jsx](/frontend/src/pages/AcademicStructurePage.jsx) does not use this endpoint anymore
- it now loads canonical academic setup entities directly

That means `/analytics/academic-structure` is now a compatibility or reporting path, not the authoritative academic structure UI source.

## 4.5 Admin analytics overview

Endpoint:

- `GET /admin/analytics/overview`

Returns platform counts such as:

- total users
- active students
- active clubs
- pending review tickets
- assignments total
- submissions total
- events this week
- system errors in last 24 hours

Permission:

- `analytics.read`

## 4.6 Platform snapshot analytics

Endpoints:

- `GET /admin/analytics/platform`
- `POST /admin/analytics/snapshots/run-daily`
- `GET /admin/analytics/snapshots/history`

Service:

- `compute_platform_snapshot(...)`
- `get_daily_snapshot(...)`
- `get_snapshot_history(...)`

The platform endpoint prefers:

1. Redis snapshot
2. `analytics_snapshots` collection
3. fresh computation

This is the cleanest analytics path in the module because it separates expensive summary computation from request-time UI rendering.

## 4.7 Audit summary analytics

Endpoint:

- `GET /admin/analytics/audit-summary`

Permissions:

- `audit.read`

Returns:

- low / medium / high severity counts for last 24 hours
- total count
- top action types

This endpoint is consumed by the compliance UI rather than the main analytics page.

## 5. Frontend Implementation

## 5.1 General analytics page

Frontend file:

- [AnalyticsPage.jsx](/frontend/src/pages/AnalyticsPage.jsx)

Behavior:

- calls `/analytics/summary`
- displays returned metrics as stat cards
- plots all summary values as a simple bar chart

This page is generic by design. It does not offer drill-down or advanced filtering.

## 5.2 Dashboard integration

Frontend file:

- [DashboardPage.jsx](/frontend/src/pages/DashboardPage.jsx)

Uses analytics for:

- summary cards
- teacher section tiles via `getTeacherSectionsAnalytics()`

This means analytics is operationally embedded in the main product landing experience.

## 5.3 Admin analytics page

Frontend file:

- [AdminAnalyticsPage.jsx](/frontend/src/pages/Admin/AdminAnalyticsPage.jsx)

Calls:

- `/admin/analytics/overview`
- `/admin/analytics/platform`

It renders platform KPIs, but the UI is currently thin. It does not yet expose snapshot history or deeper drill-down.

## 5.4 Compliance page

Frontend file:

- [AdminCompliancePage.jsx](/frontend/src/pages/Admin/AdminCompliancePage.jsx)

Calls:

- `/admin/analytics/audit-summary`

This is effectively a specialized analytics consumer for governance/compliance rather than a separate analytics subsystem.

## 5.5 Teacher section tiles

Frontend file:

- [TeacherClassTiles.jsx](/frontend/src/components/ui/TeacherClassTiles.jsx)

This is one of the more operationally useful analytics consumers because it turns analytical aggregates into actionable teaching status.

## 6. Permissions and Access Model

General analytics:

- route access allows `admin`, `teacher`, `student`
- backend `require_roles(...)` applies per endpoint

Admin analytics:

- protected by `analytics.read`

Audit summary:

- protected by `audit.read`

Important architectural point:

- analytics is not a single permission domain
- some analytics are general role-based reads
- some analytics are privileged admin observability endpoints

## 7. Caching Strategy

### Redis response caching

Used for:

- `/analytics/summary`
- `/analytics/academic-structure`
- daily snapshots

Config dependency:

- `settings.analytics_cache_ttl_seconds`

### Snapshot persistence

Daily platform analytics are also stored in MongoDB via:

- `analytics_snapshots`

This is a good design because it reduces repeated recomputation for stable metrics.

## 8. Strengths of Current Implementation

### Strength 1: Distinct live vs snapshot analytics layers exist

The admin snapshot path is cleaner than ad hoc analytics-only pages.

### Strength 2: Redis caching is already integrated

The module is not fully uncached request-time computation.

### Strength 3: Helper-based aggregation approach

The module includes reusable helpers for:

- distinct extraction
- grouped counts
- bounded scanning

### Strength 4: Analytics is operationally useful

It is not just a vanity chart layer. It feeds:

- teacher workload visibility
- dashboard cards
- compliance summaries

## 9. Performance and Design Risks

### Risk 1: Heavy in-memory stitching remains in key endpoints

`/analytics/teacher/sections` and `/analytics/academic-structure` still materialize and join multiple datasets in application memory.

### Risk 2: Scan caps reduce risk but do not solve scalability

The code uses bounded caps such as:

- 5,000
- 25,000
- 100,000

That is safer than unlimited scans, but it still means correctness and completeness can degrade as data grows.

### Risk 3: Dual student membership source of truth leaks into analytics

The analytics module combines:

- `enrollments.class_id`
- `students.class_id`

This means analytics can inherit structural inconsistencies from the academic and enrollment modules.

### Risk 4: Legacy academic model still powers analytical tree endpoints

`/analytics/academic-structure` depends on:

- `courses`
- `years`
- `classes`

This conflicts with the canonical academic model that now centers on:

- faculty
- department
- program
- specialization
- batch
- semester
- section

### Risk 5: Some metrics are semantically weak

Example:

- teacher `my_notices` counts all active notices, not necessarily notices authored by or relevant to that teacher

### Risk 6: Admin snapshot UI expects fields that are not currently produced

[AdminAnalyticsPage.jsx](/frontend/src/pages/Admin/AdminAnalyticsPage.jsx) renders:

- `review_ticket_sla_hours`

But `compute_platform_snapshot(...)` does not currently produce that field.

The UI falls back gracefully to `0`, but this is still a contract drift.

## 10. Architectural Issues

### Issue 1: Analytics is doing both reporting and structure modeling

The module should primarily report on the system, but `/analytics/academic-structure` effectively constructs a hierarchy projection.

That is better treated as:

- a reporting view model
- or a dedicated analytical projection

not as a substitute academic source of truth.

### Issue 2: Legacy and canonical academic models are mixed

Analytics still uses legacy academic entities heavily. This creates documentation drift and future migration cost.

### Issue 3: The module is partly optimized and partly hand-stitched

Some parts:

- snapshot caching
- aggregate helpers

are relatively mature.

Other parts:

- tree construction
- multi-collection joins in Python

remain heavy and fragile at scale.

### Issue 4: Analytics contract is under-documented in frontend

Several pages depend on analytics responses, but the API payloads are not centrally typed or documented for frontend consumption.

## 11. Recommended Cleanup Strategy

### Short-term

- document analytics response contracts explicitly
- remove or fill missing UI fields such as `review_ticket_sla_hours`
- keep using Redis cache for summary endpoints
- mark `/analytics/academic-structure` as legacy analytical projection if it is no longer used by the canonical UI

### Medium-term

- migrate analytical structure views from legacy `courses/years/classes` to canonical hierarchy if they still matter
- reduce dependence on `students.class_id` as a parallel membership source
- replace large in-memory joins with aggregation pipelines or materialized projections where feasible

### Long-term

Adopt a clearer analytics architecture:

- transactional modules own business data
- analytics builds read models or snapshots
- dashboards consume stable analytics contracts
- heavy analytical trees use precomputed or aggregated views, not request-time stitching

## 12. Testing Requirements

Minimum automated coverage should include:

### Unit tests

- `_bounded_cap(...)`
- `_safe_object_ids(...)`
- `_distinct_values(...)` fallback behavior
- `_count_by_field(...)` aggregate and fallback behavior

### API tests

- role-based summary payload correctness for student, teacher, admin
- teacher section analytics scoping
- academic-structure analytics pagination behavior
- admin overview permission enforcement
- audit summary permission enforcement

### Performance and regression tests

- cache hit and miss behavior
- snapshot compute and retrieval path
- high-cardinality section analytics correctness within caps
- academic-structure response shape stability

### Contract tests to add

- verify admin analytics UI fields all exist in platform snapshot payload
- verify `/analytics/teacher/classes` remains a true compatibility alias for `/analytics/teacher/sections`

## 13. Final Summary

The Analytics module is already a real subsystem, not a cosmetic dashboard layer. It powers multiple operational experiences across student, teacher, admin, and compliance views.

Its strongest parts are:

- Redis-backed summary caching
- daily platform snapshots
- reusable aggregation helpers
- teacher section health metrics

Its weakest parts are:

- heavy in-memory analytical stitching
- dependence on legacy academic entities
- duplicated student membership logic
- minor but important frontend/backend contract drift

From an architectural perspective, the correct direction is:

- preserve analytics as a dedicated read-model layer
- move heavy structure analytics away from legacy academic entities
- stabilize payload contracts for frontend consumers
- keep request-time analytics narrow and push broader analytics into cached or snapshot-backed views

