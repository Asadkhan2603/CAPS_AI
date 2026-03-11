# CAPS AI Final Audit Report

## 1. Project Health Score (0-100)
**68 / 100**

Scoring rationale:
- Functionality and baseline tests are strong.
- Core architecture and security controls are present.
- Score reduced by dependency vulnerabilities, scaling bottlenecks, documentation drift, and maintainability hotspots.

## 2. Top 10 Critical Issues
1. Backend vulnerable dependencies in auth/parser stack (`backend/requirements.txt:5-6,12`; pip_audit output).
2. Frontend vulnerable dependencies (`frontend/package.json:16,22`; npm audit output).
3. Weak SHA1 usage in submission AI bulk idempotency (`backend/app/api/v1/endpoints/submissions.py:253`).
4. Large in-memory query materialization (`background_jobs.py:47`, `admin_communication.py:33,51`).
5. Sequential notice fanout write loop (`backend/app/services/background_jobs.py:67-75`).
6. CPU-heavy similarity pipeline inside app worker (`similarity_pipeline.py:69-70`, `similarity_engine.py:25-29`).
7. Endpoint bloat in key modules (analytics/timetables/evaluations).
8. Inconsistent architecture layering (direct DB access in endpoints vs service abstraction in auth).
9. Documentation drift from canonical runtime (`README.md:104`, `scripts/README.md:5-15`, `backend/app/models/README.md:4-6`).
10. CI quality gates missing for SCA and coverage thresholds (`.github/workflows/ci.yml`).

## 3. Top 10 Quick Fixes
1. Upgrade vulnerable dependencies (backend + frontend) and regenerate lockfiles.
2. Replace SHA1 with SHA256 in submissions idempotency key.
3. Fix current flake8 violations (5 reported).
4. Cap and paginate high-volume DB reads (`to_list(length=5000+)` paths).
5. Batch notification fanout (`insert_many` + chunking).
6. Add CI job for `python -m pip_audit -r backend/requirements.txt`.
7. Add CI job for `npm audit --omit=dev` with policy thresholds.
8. Enforce backend/frontend coverage thresholds in CI.
9. Update stale READMEs and align naming to canonical hierarchy.
10. Remove or archive dead artifacts (`SidebarLegacy.jsx`, placeholder utility) after validation.

## 4. Long-Term Refactor Suggestions
1. Move from endpoint-centric to domain-module architecture (commands/queries/services).
2. Extract shared access-control logic into centralized service.
3. Introduce async worker queue for expensive AI/similarity/background fanout jobs.
4. Add migration/version framework for Mongo schema evolution.
5. Build read models for analytics/dashboard-heavy queries.
6. Reduce frontend mega-components with route-level data hooks and presentational splits.

## 5. Security Risk Summary
- **High**: dependency CVEs, SHA1 usage.
- **Medium**: header trust assumptions, broad exception swallowing, registration-policy hardening, session token exposure under XSS.
- **Low**: manifest placeholder secrets and broad CORS defaults.

Reference: see `audit/security.md`.

## 6. Performance Improvement Plan
- Immediate: query windowing/pagination, fanout batching, AI chat message retention bounds.
- Mid-term: queue offload similarity and heavy jobs, aggregation/read-model optimization.
- Long-term: SLO-based load testing and capacity planning.

Reference: see `audit/performance.md`.

## 7. Architecture Improvement Plan
- Standardize domain boundaries across all modules (not only auth).
- Normalize canonical naming (`sections` vs `classes`) in API/docs/UI internals.
- Introduce module-level contracts and shared policy helpers for access/governance.
- Remove residual legacy assumptions from indexes/docs/scripts.

Reference: see `audit/architecture.md`.

## 8. Technical Debt Summary
- High debt concentration:
  - Large endpoint files
  - Legacy naming compatibility residue
  - Partial abstraction strategy
  - Documentation divergence and ignored docs tree (`.gitignore:65`)

Debt impact:
- Slower onboarding, higher regression risk, and scaling friction.

## 9. Recommended Roadmap (Phase-wise)

### Phase 0 (0-1 week): Stabilize and Secure
1. Patch dependencies and eliminate SHA1 usage.
2. Clean flake8 failures.
3. Add SCA + coverage CI gates.

### Phase 1 (1-3 weeks): Performance and Reliability
1. Fix top `to_list` hotspots with paging/chunking.
2. Parallelize/batch notice fanout.
3. Add endpoint and scheduler observability metrics with alerting.

### Phase 2 (3-6 weeks): Structural Refactor
1. Extract shared access-control/governance utilities.
2. Split monolithic endpoints into submodules.
3. Introduce service layer for academic/AI/communication domains.

### Phase 3 (6-10 weeks): Data and Documentation Integrity
1. Introduce migration/version strategy for Mongo data shapes.
2. Remove legacy schema/index artifacts where safe.
3. Align and version docs (stop ignoring actionable docs, refresh READMEs/module docs).

### Phase 4 (Continuous): Scale Readiness
1. Load/perf regression tests in CI/CD.
2. Capacity planning for AI and similarity workloads.
3. Release governance with risk budgets and rollback criteria.

