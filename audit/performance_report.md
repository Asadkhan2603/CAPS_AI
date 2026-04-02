# Performance Report

Generated: 2026-03-31

## Validation Summary

- `npm --prefix frontend run build`: passed
- `npm --prefix frontend run check:bundle`: passed
- existing artifact `artifacts/perf-smoke-report.json` from 2026-03-30 reports all thresholds within budget
- existing artifact `artifacts/deploy-smoke-report.json` from 2026-03-30 reports healthy local backend and frontend dist checks

## Observed Performance Signals

### Frontend bundle budgets

Validated bundle budgets:

- `charts-vendor`: 355.18 KiB / 390 KiB
- `react-vendor`: 160.85 KiB / 180 KiB
- `motion-vendor`: 124.02 KiB / 140 KiB
- `app-entry`: 81.26 KiB / 90 KiB
- `app-styles`: 86.34 KiB / 95 KiB
- `total-js`: 1303.18 KiB / 1400 KiB
- `total-css`: 86.34 KiB / 100 KiB

Conclusion:

- current budgets pass
- charting and vendor chunks have limited remaining headroom

### Backend perf smoke artifact

Selected values from `artifacts/perf-smoke-report.json`:

- `health_check`: avg 2.77 ms, p95 4.73 ms
- `admin_system_health`: avg 4.15 ms, p95 5.22 ms
- `auth_login`: avg 225.79 ms, p95 236.18 ms
- `teacher_review_workflow`: avg 10.06 ms, p95 10.43 ms

Conclusion:

- the baseline artifact indicates strong local in-process performance
- login is the slowest of the sampled paths but still within configured thresholds

## Repo-Based Findings

### 1. Some central modules are too large for easy performance tuning

Measured file sizes:

- `backend/app/api/v1/endpoints/analytics.py`: 1679 lines
- `frontend/src/pages/AcademicStructurePage.jsx`: 998 lines
- `frontend/src/components/students/StudentBulkWorkflow.jsx`: 733 lines

Impact:

- large files make it harder to isolate expensive branches
- page-level render and data-loading behavior becomes harder to reason about

### 2. Admin system health is read-heavy and write-heavy at the same time

Evidence:

- `/admin/system/health` reads DB state, audit summaries, scheduler lock, and observability
- it also persists a system health snapshot on each call

Impact:

- the endpoint is powerful, but frequent polling multiplies both read cost and write cost

Recommended fix:

- preserve the endpoint
- consider splitting live health from persisted snapshot writes if load increases

### 3. Analytics and dashboard growth need monitoring

Evidence:

- `charts-vendor` is the largest frontend budgeted chunk
- analytics code is concentrated in a very large backend module

Recommended fix:

- keep charts isolated to analytics surfaces
- avoid importing analytics-heavy dependencies into more general routes

## Current Verdict

Performance is healthy for the current validated baseline. The next risks are architectural scaling risks, not active budget or smoke-check failures.
