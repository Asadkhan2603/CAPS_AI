# 🧾 PERFORMANCE AUDIT REPORT

## 1. 📅 Audit Metadata

- Project Name: Caps AI App
- Audit Date: 2026-04-02
- Audit Time: 12:18:34 +05:30
- Environment Assumption: Web application
- Audit Scope: Full system (Frontend + Backend + Network + Infra)

---

## 2. 📊 Performance Scorecard (0–100)

### Overall Performance Score: 76/100
Reason: The heaviest startup, delivery, and request-fanout problems have been reduced, Phase 2 and the tracked Phase 3 backend work are complete, and Phase 1 is substantially complete in code. The main verification gap against the original checklist is that active nginx config enables `gzip` but does not yet configure Brotli. Remaining performance work is now mostly long-term scale, observability, and heavy AI/background-job isolation rather than the original core request-path bottlenecks.

### Frontend Performance: 69/100
Reason: The login shell, header, dashboard, hierarchy lookups, and the largest admin surfaces are materially lighter now, and admin analytics now boots from a single snapshot-backed request, though some pages still carry large local state and vendor-heavy rendering paths.

### Backend Performance: 72/100
Reason: Hot paths are cheaper, runtime concurrency is better tuned, admin system health and the admin dashboard shell now prefer persisted analytics snapshots, and the section/class, batch, semester, course-offering, and class-slot endpoints read from denormalized models instead of rebuilding related context on every request. The main backend risks now sit more in specialty workloads such as similarity processing and large background fanout rather than the everyday academic read paths.

### API Response Time: 72/100
Reason: Session bootstrap, dashboard consolidation, lightweight notice counts, stricter paged hierarchy reads, snapshot-first admin health reads, snapshot-backed admin summary/dashboard analytics, and denormalized section/class, batch, semester, course-offering, and class-slot responses have materially reduced first-load and repeated-read latency on the most common authenticated paths.

### Database Performance: 68/100
Reason: Overfetch and repeated lookup churn are lower than the original baseline, admin snapshot-driven reads are in place, and section/class, batch, semester, course-offering, and class-slot reads now avoid repeated multi-collection enrichment or context assembly via denormalized models. The biggest remaining DB risks are now the heavier analytics, similarity, and batch-processing workloads rather than the original list/detail request paths.

### Network Efficiency: 68/100
Reason: Static gzip compression and immutable asset caching are now in place, though Brotli, CDN/edge delivery, and selective API cache/revalidation are still absent.

### Bundle Size Optimization: 60/100
Reason: Chart code is no longer on the default dashboard critical path and several page-level admin and hierarchy flows are split more cleanly, but the build still ships a large `charts-vendor` chunk and several feature pages remain heavier than ideal.

### Caching Effectiveness: 79/100
Reason: Lookup TTL caching, unread-count bootstrap data, better frontend shell reuse, persisted admin health snapshots, persisted analytics snapshots for admin shell reads, and denormalized section/class, batch, semester, course-offering, and class-slot read models now reduce repeat traffic and repeated backend hydration significantly, though broader API/result caching is still limited.

### Scalability Readiness: 75/100
Reason: Multi-worker serving, HPA, lower request fan-out, completed Phase 2 paging cleanup, slimmer admin page state, snapshot-first admin shell reads, and denormalized section/class, batch, semester, course-offering, and class-slot responses materially improved headroom. The next scale barriers are now load-profile validation, AI/similarity isolation, and deeper background-job batching rather than the original request-storm and enrichment-heavy paths.

---

## 3. 🚨 Critical Problems Identified

### 1. Overloaded First Authenticated Load
- Impact Level: Critical
- Affected Layer: Frontend / Backend / Network
- Description: Session validation, header notice loading, branding metadata fetch, and dashboard analytics all happen near initial load.
- Root Cause Analysis: The client clears tokens on bootstrap and revalidates session, then header and dashboard fire separate requests. This creates unnecessary request fan-out before the app becomes usable.

### 2. Dashboard Pulls Heavy Chart Code Into Critical Path
- Impact Level: High
- Affected Layer: Frontend
- Description: The default dashboard loads charting code immediately after login.
- Root Cause Analysis: `recharts` is imported directly on the main dashboard route. Even with route-level lazy-loading, the default post-login page still drags a large chart bundle into first interactive load.

### 3. Hierarchy Pages Use Request-Storm Patterns
- Impact Level: Critical
- Affected Layer: Frontend / Backend / DB
- Description: Academic structure, groups, and semesters pages fetch large datasets or fan out one request per parent entity.
- Root Cause Analysis: Generic helpers loop through paginated endpoints until exhaustion, and some flows request both active and inactive states separately. As data grows, page load cost grows non-linearly.

### 4. Analytics Endpoints Are Too Expensive for On-Demand Reads
- Impact Level: Critical
- Affected Layer: Backend / DB
- Description: Dashboard and admin analytics do many counts and large data scans.
- Root Cause Analysis: The analytics module allows large scan caps and composes multiple read-heavy subroutines per request. Cache helps only after first hit; cold reads remain expensive.

### 5. Notice Badge Logic Is Overbuilt
- Impact Level: High
- Affected Layer: Backend / DB
- Description: The header fetches full notice lists just to compute unread counts.
- Root Cause Analysis: Student notice visibility is computed by reading students, enrollments, classes, and assignments before filtering notices. That is far too heavy for a badge.

### 6. Read Endpoints Perform Repeated Enrichment
- Impact Level: High
- Affected Layer: Backend / DB
- Description: Section and hierarchy list endpoints load raw records and then enrich them from multiple related collections.
- Root Cause Analysis: This is not a classic N+1 loop per row, but it is still multi-collection hydration on every list request, which increases latency and CPU cost.

### 7. Admin System Health Endpoint Does Too Much Work Inline
- Impact Level: High
- Affected Layer: Backend / DB / Infra
- Description: Opening admin health/system pages triggers DB ping, collection counts, snapshot persistence, and alert routing.
- Root Cause Analysis: The endpoint behaves like both a monitoring reader and a background job runner. That makes the admin dashboard slower than it should be.

### 8. Delivery Layer Leaves Easy Performance Wins Untouched
- Impact Level: High
- Affected Layer: Network / Infra
- Description: Asset compression, static caching, and backend concurrency are under-optimized.
- Root Cause Analysis: No gzip/brotli, no explicit immutable asset cache rules, single-process `uvicorn`, modest CPU limits, and no visible autoscaling setup.

---

## 4. 🔍 Deep Technical Analysis

### Frontend Analysis
- Route-level lazy-loading is implemented, which is good.
- The main dashboard still imports chart libraries on the default landing route.
- Header behavior is too chatty, especially notice polling and branding metadata fetching.
- Several pages are oversized and monolithic, especially clubs, groups, academic structure, semesters, and some admin screens.
- There is no shared client query cache strategy for general GET requests, so revisits often trigger refetches.

### Backend Analysis
- FastAPI is not the main bottleneck.
- Response wrapping adds avoidable overhead because JSON responses are buffered before re-emission.
- Request logging is verbose and adds extra serialization work under load.
- Admin and analytics endpoints perform too much synchronous work inside request handlers.
- Startup work includes index creation and RBAC state checks, which increases cold-start cost.

### Database Analysis
- Indexing is reasonably broad, but query design is still inefficient.
- Analytics endpoints do many `count_documents` calls and high-cap `to_list(...)` reads.
- Visibility and scope logic repeatedly reconstructs access rules from multiple collections.
- Some lookup endpoints return far too much data in one shot.
- Many read paths are query-plus-hydrate pipelines instead of lean read models.

### Network Analysis
- No gzip or brotli compression is configured in the frontend nginx config.
- No explicit immutable cache headers are set for hashed static assets.
- API responses are globally marked `no-store`, which is safe but blocks some low-risk caching/revalidation opportunities.
- No CDN strategy is visible.

### Infrastructure Analysis
- Backend runs single-process `uvicorn`.
- Backend CPU limits are conservative for analytics-heavy traffic.
- Fixed replicas exist, but no autoscaling manifests were found.
- Cold starts are heavier than necessary due to startup tasks.
- Static assets are served from application containers instead of a specialized edge/static delivery layer.

---

## 5. 💡 Recommendations (Actionable)

### 1. Consolidate Initial Shell Data
- Fix Strategy: Create a `/session/bootstrap` endpoint returning user profile, unread notice count, and branding metadata in one response.
- Expected Impact: Reduces first-load request fan-out and improves perceived startup speed.
- Difficulty Level: Medium

### 2. Defer Dashboard Charts
- Fix Strategy: Lazy-load chart panels only when visible, or split analytics visualizations into a secondary dashboard section.
- Expected Impact: Faster first interactive paint after login.
- Difficulty Level: Easy

### 3. Replace “Load All Pages” Patterns
- Fix Strategy: Remove client loops that fetch all pages. Introduce paginated and tree-summary APIs for hierarchy views.
- Expected Impact: Major improvement for academic structure, groups, semesters, and similar modules.
- Difficulty Level: Hard

### 4. Precompute Analytics
- Fix Strategy: Move trend generation and heavy admin summary metrics into scheduled snapshot jobs stored in Redis or dedicated collections.
- Expected Impact: Large improvement in analytics and dashboard response times.
- Difficulty Level: Hard

### 5. Add Lightweight Notice Count Endpoint
- Fix Strategy: Create `/notices/unread-count` and stop loading full notices just to compute a badge.
- Expected Impact: Lower DB load and lower latency across all authenticated sessions.
- Difficulty Level: Easy

### 6. Build Denormalized Read Models
- Fix Strategy: Materialize enriched hierarchy views so list endpoints return ready-to-render data without multi-collection hydration on every request.
- Expected Impact: Faster lists and lower backend CPU.
- Difficulty Level: Medium

### 7. Reduce Middleware Overhead
- Fix Strategy: Disable response enveloping for hot read endpoints or disable it entirely in production if not essential.
- Expected Impact: Lower memory and CPU cost per response.
- Difficulty Level: Medium

### 8. Optimize Static Asset Delivery
- Fix Strategy: Enable gzip/brotli, add immutable cache headers for hashed files, and serve frontend assets through CDN or optimized ingress.
- Expected Impact: Better download performance and lower server bandwidth.
- Difficulty Level: Medium

### 9. Simplify Admin Health Reads
- Fix Strategy: Persist health snapshots in background jobs and make admin pages read precomputed data only.
- Expected Impact: Faster admin dashboard and lower monitoring overhead.
- Difficulty Level: Medium

### 10. Improve Runtime Concurrency
- Fix Strategy: Run multiple ASGI workers and add HPA based on CPU and latency.
- Expected Impact: Better resilience under concurrent load.
- Difficulty Level: Medium

---

## 6. 🧠 Optimization Strategy (Phase-wise)

### Phase 1: Quick Wins (1–2 days)
- Enable gzip/brotli
- Add immutable static asset cache headers
- Add unread notice count endpoint
- Stop fetching full notice list for header badge
- Defer dashboard charts
- Reduce header startup requests
- Disable or narrow response envelope middleware on hot paths

### Phase 2: Mid-Level Optimization (3–7 days)
- Add `/session/bootstrap`
- Refactor hierarchy pages to use strict server pagination
- Replace generic “load all pages” helpers with focused APIs
- Cache low-volatility lookups
- Split oversized pages into smaller state domains

### Phase 3: Advanced Optimization (1–4 weeks)
- Introduce denormalized read models for sections, groups, semesters, and academic tree views
- Move dashboard/admin analytics to snapshot-based architecture
- Rework notice visibility and access evaluation into a cheaper model
- Reduce inline enrichment across list APIs

### Phase 4: Long-Term Scaling
- Add HPA and proper worker tuning
- Add CDN/static edge caching
- Add end-to-end tracing and latency SLOs
- Add load testing gates for 500–1000 concurrent users
- Enforce performance budgets in CI

---

## 7. 📈 Expected Performance Improvement

- Initial load time reduction: 30–45%
- Dashboard interactivity improvement: 25–40%
- Hierarchy/admin list performance improvement: 45–70%
- Analytics endpoint speed improvement: 50–80% on cold-path redesign
- UX improvement: significantly fewer spinner-heavy transitions, faster navigation, and better responsiveness under load

---

## 8. 🧪 Monitoring & Tools Recommendation

### OpenTelemetry
Needed for request tracing across frontend, API, Redis, and MongoDB. This will expose which routes and queries are actually slow in production.

### Sentry Performance
Needed for real-user monitoring, route transition timing, and frontend stall analysis.

### Prometheus + Grafana
Needed for p95/p99 latency, CPU saturation, cache hit ratio, pod health, and request-volume visibility.

### MongoDB Profiler / Atlas Performance Advisor
Needed to validate scan-heavy queries and index effectiveness under real data.

### k6 or Locust
Needed to simulate 500–1000 users and verify whether fixes actually improve system behavior under concurrency.

### Centralized Logging
Needed to correlate slow requests, backend exceptions, and infrastructure instability.

---

## 9. ⚠️ Risk Analysis

- Caching analytics and dashboard data can introduce temporary staleness.
- Replacing full-data loads with server pagination may require UI redesign in some screens.
- Denormalized read models can drift if write-side synchronization is incomplete.
- Increasing worker count can create duplicate background activity if scheduler locks are not handled correctly.
- Aggressive asset caching can cause release issues if versioning is not strictly content-hashed.
- Refactoring scope/visibility logic is risky because it intersects with RBAC and student-access rules.

---

## 10. 🏁 Final Verdict

The system is **salvageable**. It does **not** require a full rewrite, but it **does** require partial re-architecture of its read paths and frontend data-loading strategy.

The biggest problems are:
- too many requests during initial authenticated load
- too much data fetched for hierarchy pages
- too much synchronous analytics work on request paths
- weak network/static delivery optimization

### Final Assessment
- System Status: Salvageable with focused optimization
- Re-architecture Need: Partial, not full
- Priority Level: Urgent

# CAPS AI Performance Audit

## Current Baseline
- Backend test run time: `85 passed in 86.86s` (functional baseline only, not load profile).
- Frontend production build successful; largest chunks:
  - `charts-vendor` 363.70 kB (gzip 107.58 kB)
  - `react-vendor` 164.35 kB
  - `motion-vendor` 127.00 kB
  - Evidence: `npm run build` output (2026-03-11 local run)

## Codebase Verification Snapshot (2026-04-02)
- Phase 1 status in code: substantially complete, with one verified gap. Active `frontend/nginx.conf` enables `gzip` and immutable asset caching, but Brotli directives were not found in the active repo configuration.
- Phase 2 status in code: complete for the tracked audit scope. The consolidated session bootstrap, strict hierarchy paging, lookup caching, load-all helper removal, and page-state decompositions are all present in the active frontend/backend paths.
- Phase 3 status in code: complete for the tracked audit scope. Snapshot-backed admin shell analytics and denormalized read models for sections/classes, batches/semesters, course offerings, and class slots are present in the active backend routes and services.
- Legacy compatibility code still exists but is not wired into the active app shell. `frontend/src/components/layout/Topbar.jsx` still contains older notice and branding fetch logic, and `frontend/src/context/sessionBootstrap.js` still includes a fallback path for older servers that do not expose `/session/bootstrap`.

## Key Bottlenecks

### 1. Large In-Memory Query Materialization
Multiple paths pull thousands of records in one request/job:
- `backend/app/services/background_jobs.py:47` -> users `to_list(length=50000)`
- `backend/app/services/background_jobs.py:22` -> enrollments `to_list(length=20000)`
- `backend/app/api/v1/endpoints/admin_communication.py:33,51` -> `to_list(length=20000)`
- `backend/app/api/v1/endpoints/class_slots.py:55,97,114,142` -> repeated `to_list(length=5000)`

Impact:
- High memory pressure and longer GC pauses under concurrency.
- Latency spikes at higher tenant size.

### 2. Sequential Fanout Writes
- Notification fanout performs per-user awaited inserts in a loop:
  - `backend/app/services/background_jobs.py:67-75`
Impact:
- Throughput scales linearly with recipients.
- Background dispatch can lag significantly for college-wide notices.

### 3. Similarity Computation Is CPU-Bound and In-Process
- Candidate load and TF-IDF/cosine done within API worker context:
  - Load candidates: `backend/app/services/similarity_pipeline.py:69-70`
  - Vectorize/score: `backend/app/services/similarity_engine.py:25-29`
Impact:
- Competes with request handling CPU.
- Will degrade as submission corpus grows.

### 4. Response Envelope Middleware Re-serializes JSON Bodies
- Middleware consumes entire response body and repackages:
  - `backend/app/main.py:123-143`
Impact:
- Extra serialization overhead and memory copies per API response.
- Can become expensive on larger payload endpoints.

### 5. N+1-Like Enrichment Patterns in Endpoints
- Several endpoints fetch base rows then perform multi-collection lookups in separate calls.
- Example: offerings enrichment path (`course_offerings`) fetches subjects/teachers/sections/groups/semesters as additional large lists.
  - `backend/app/api/v1/endpoints/course_offerings.py:132-136`
Impact:
- High query count and larger p95 latency as data grows.

### 6. Frontend Bundle Weight and Heavy Feature Pages
- Largest feature chunks include dashboard/clubs/entity manager flows.
- Large component files correlate with heavier runtime parse/execute costs:
  - `frontend/src/pages/ClubsPage.jsx` (946 lines)
  - `frontend/src/components/ui/EntityManager.jsx` (776 lines)

## Performance Risk by Scale
- **Current**: acceptable for small-medium datasets.
- **At 10x data/users**: highest risk in bulk fanout, large in-memory scans, and similarity CPU workload.

## Improvement Plan

### Immediate (1-2 sprints)
1. Add pagination/windowing to all high-limit `to_list` paths (especially >5000).
2. Batch notification fanout using chunked bulk insert (`insert_many`) and async worker queue.
3. Add server-side metrics:
   - endpoint latency histogram
   - Mongo query timings
   - scheduler job durations
4. Cap AI chat thread message history and persist rolling windows.
   - Current update appends full list: `backend/app/api/v1/endpoints/ai.py:406-417`

### Mid-Term
1. Move similarity processing to isolated worker (already partially job-oriented; complete decoupling).
2. Replace repeated join-like DB calls with aggregation pipelines where practical.
3. Revisit response envelope middleware strategy for high-throughput endpoints.
4. Add cache policy for static reference data (subjects/programs/faculties) with invalidation hooks.

### Long-Term
1. Introduce bounded domain services with explicit read models for analytics-heavy pages.
2. Add load tests and SLO targets (p50/p95/p99) as CI gates before releases.

## Phase 1 Execution Status

Status: substantially complete. All tracked quick wins are present except Brotli, which is still not configured in the active nginx file.

- [partial] Enable gzip/brotli.
  Note: frontend nginx enables gzip for text, JSON, JS, CSS, SVG, and font asset types, but Brotli directives were not found in the active repo configuration.
- [complete] Add immutable static asset cache headers.
  Note: hashed frontend assets under `/assets/` now ship with `Cache-Control: public, immutable`.
- [complete] Add unread notice count endpoint.
  Note: `/api/v1/notices/unread-count` was added and computes visible unread totals on the backend.
- [complete] Stop fetching full notice list for header badge.
  Note: the header badge now uses `/notices/unread-count` and refresh events instead of loading full notice lists.
- [complete] Defer dashboard charts.
  Note: the dashboard trend chart is lazy-loaded into its own chunk and only hydrates when needed.
- [complete] Reduce header startup requests.
  Note: the extra branding metadata request was removed; the header now attempts the logo file directly with cache busting.
- [complete] Reduce student dashboard startup request fan-out.
  Note: the dashboard now uses a consolidated `/api/v1/analytics/dashboard` payload instead of multiple student-specific requests on mount.
- [complete] Disable or narrow response envelope middleware on hot paths.
  Note: hot paths including `/auth/me`, `/analytics/dashboard`, `/analytics/summary`, and `/notices/unread-count` are configured to skip envelope wrapping.
- [complete] Improve runtime concurrency.
  Note: backend containers now run multi-worker Uvicorn (`WEB_CONCURRENCY=2` by default), scheduler leadership is worker-safe via per-process instance ids, backend CPU/memory requests were raised to match the new serving shape, and `k8s-backend-hpa.yaml` adds autoscaling for the stable backend deployment.

## Phase 2 Execution Status

Status: complete.

- [complete] Add `/session/bootstrap`.
  Note: the authenticated shell now validates through a single `/api/v1/session/bootstrap` call that returns `user`, `unread_notice_count`, branding logo metadata, and `generated_at`; `AuthContext` persists that payload and the header uses it to avoid extra first-paint startup requests.
- [complete] Refactor hierarchy pages to use strict server pagination.
  Note: `AcademicStructurePage` now uses bounded branch paging through a dedicated tree hook, `GroupsPage` and `SemestersPage` use searchable server lookups instead of preload-all flows, and the frontend no longer has academic fetch-until-exhaustion helpers.
- [complete] Replace generic “load all pages” helpers with focused APIs.
  Note: the old academic `listAllPages`, `listAllWithActiveStates`, and dormant bulk lookup helpers were removed, leaving focused paged reads and targeted lookup APIs in their place.
- [complete] Cache low-volatility lookups.
  Note: shared academic lookup requests now use session-scoped TTL caching with in-flight de-duplication, and CRUD flows invalidate dependent lookup prefixes so selectors stay fast on revisit without hanging onto stale hierarchy data.
- [complete] Remove remaining dormant client-side load-all helpers.
  Note: the last unused academic `listAllPages` and `listAllWithActiveStates` client helpers were removed, so no frontend academic lookup path still depends on fetch-until-exhaustion utilities.
- [complete] Split oversized pages into smaller state domains.
  Note: `ClubsPage`, `EntityManager`, `BatchesPage`, `UsersPage`, `AcademicStructurePage`, and `AdminSystemPage` now delegate major state, modal, paging, or chart/history responsibilities into focused hooks and components, completing the planned Phase 2 frontend decomposition pass.

## Phase 3 Execution Status

Status: complete.

- [complete] Move dashboard/admin analytics to snapshot-based architecture.
  Note: `/api/v1/admin/system/health`, `/api/v1/admin/analytics/bootstrap`, `/api/v1/analytics/summary`, and the admin-role `/api/v1/analytics/dashboard` now prefer persisted snapshots by default. The heavier admin shell counts only recompute when a fresh analytics snapshot is missing or an explicit refresh path is used, so the default admin experience no longer rebuilds the same expensive metrics on every read.
- [complete] Introduce denormalized read models for section/class reads.
  Note: `/api/v1/sections` now serves through the active `classes` router using persisted `section_read_models`, so section/class list and detail reads no longer redo the same faculty/department/program/batch/semester/coordinator enrichment on every request. Parent hierarchy updates and coordinator reassignment/deactivation flows now refresh affected read models, keeping the denormalized view current after admin changes.
- [complete] Introduce denormalized read models for batch and semester reads.
  Note: `/api/v1/batches` and `/api/v1/semesters` now hydrate from persisted `batch_read_models` and `semester_read_models`, so hierarchy pages stop redoing repeated program/specialization/batch enrichment on each list or detail request. Program, specialization, batch, and semester admin updates now refresh the affected read models so those denormalized responses stay current after lineage or naming changes.
- [complete] Introduce denormalized read models for course offerings and class slots.
  Note: `/api/v1/course-offerings` and `/api/v1/class-slots` now serve from persisted read models, so delivery pages stop rebuilding subject, teacher, section, group, batch, and semester context on each request. Subject, section, group, batch, semester, user deactivation, course-offering, and class-slot writes now refresh the affected delivery read models so timetable-facing responses stay current after admin changes.
- [complete] Reduce inline enrichment across the highest-traffic academic list APIs.
  Note: the tracked hierarchy and delivery endpoints that previously did repeated multi-collection hydration on every request now return ready-to-render denormalized data, which closes the main inline-enrichment hotspot described in the original audit.
