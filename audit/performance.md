# CAPS AI Performance Audit

## Current Baseline
- Backend test run time: `85 passed in 86.86s` (functional baseline only, not load profile).
- Frontend production build successful; largest chunks:
  - `charts-vendor` 363.70 kB (gzip 107.58 kB)
  - `react-vendor` 164.35 kB
  - `motion-vendor` 127.00 kB
  - Evidence: `npm run build` output (2026-03-11 local run)

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

