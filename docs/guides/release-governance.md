# Release Governance

This guide starts Phase 4 item 3: release governance with explicit risk budgets and rollback criteria.

It is based on the current repo state:

- CI quality gates in `.github/workflows/ci.yml`
- backend smoke benchmarking in `scripts/perf_smoke.py`
- AI and similarity baseline planning in `scripts/ai_capacity_baseline.py`
- runtime health and alert surfaces in `/api/v1/admin/system/health`
- persisted minute-bucket health snapshots in `system_health_snapshots`
- dedicated operator dashboard in `/admin/observability`
- throttled system notifications for active operational alerts
- automated release-governance gate in `scripts/release_gate.py` and `.github/workflows/ci.yml`
- staged canary rollout controller in `scripts/canary_rollout.py`

## Scope

This guide defines:

- release classes
- mandatory pre-release checks
- risk budgets for application rollout
- rollback triggers
- rollback procedures
- post-release watch expectations

It does not replace deployment mechanics in `deployment.md`. It defines the operating rules for deciding whether a release should proceed, pause, or roll back.

## Release Classes

### Class 0: Docs-Only

Examples:

- markdown-only updates
- roadmap status updates
- guide corrections

Required checks:

- link/path sanity review

Rollback expectation:

- revert commit if published docs are materially wrong

### Class 1: Frontend-Only

Examples:

- UI copy and rendering changes
- route policy changes
- dashboard or admin page updates

Required checks:

- `npm run lint`
- `npm run test:ci`
- `npm run test:coverage`
- `npm run build`

Rollback expectation:

- revert if route access, rendering, or critical user journey breaks

### Class 2: Backend-Only

Examples:

- API behavior changes
- service-layer refactors
- scheduler or observability changes

Required checks:

- `python scripts/check_backend_safety.py`
- `python -m pytest -q backend/tests`
- safety-critical static analysis from CI
- `python scripts/perf_smoke.py`

Rollback expectation:

- revert if auth, governance, scheduler correctness, or perf smoke budgets fail

### Class 3: Data-Shape Or Workflow Change

Examples:

- `schema_version` rollout
- migration script introduction
- changes to AI job, evaluation, timetable, or academic entity write paths

Required checks:

- all Class 2 checks
- dry-run migration first
- apply migration in controlled order
- explicit rollback feasibility review before release

Rollback expectation:

- application rollback is allowed only if data writes remain backward-compatible
- if the write shape is not backward-compatible, stop rollout before apply or ship a forward-fix

### Class 4: Runtime Or Infra Change

Examples:

- CI gate changes
- scheduler cadence changes
- timeout, token, or provider-mode changes
- Kubernetes manifest or ingress changes

Required checks:

- relevant app checks from Class 1 and Class 2
- deployment validation from `deployment.md`
- admin health review after rollout

Rollback expectation:

- revert runtime config or deployment manifest immediately if health, latency, or scheduler behavior degrades

## Mandatory Go/No-Go Checks

Every non-docs release must satisfy these before production rollout:

1. GitHub Actions on the release commit are green.
2. `backend-static-analysis`, `backend`, `frontend`, `backend-perf-smoke`, and `release-governance-gate` are green.
3. `/api/v1/admin/system/health` shows no unresolved operational alert that already exceeds a defined risk budget.
4. Release notes identify whether the change is application-only, config/runtime, or data-shape.
5. The operator knows the exact rollback command or revert commit path before rollout.

## Automated Gate

Primary enforcement path:

- `python scripts/release_gate.py`

Supported modes:

- local in-process gate using `TestClient`
- deployed-environment gate using `--base-url` and `--bearer-token`

Current automated checks:

1. `/health` responds successfully
2. `/api/v1/admin/system/health` responds successfully
3. no critical alerts are present
4. snapshot-store retention remains bounded
5. operational alert routing is enabled

Default behavior:

- fails on `critical` alerts
- allows `high` and `medium` alerts only when explicitly overridden

Current CI enforcement:

- `.github/workflows/ci.yml` job: `release-governance-gate`

## Staged Rollout Control

Primary staged rollout path:

- `python scripts/canary_rollout.py backend prepare --image <image> --base-url <api-root> --bearer-token <token>`
- `python scripts/canary_rollout.py backend promote --image <image> --base-url <api-root> --bearer-token <token>`
- `python scripts/canary_rollout.py backend rollback --base-url <api-root> --bearer-token <token>`

The same script also supports `frontend` canary rollout control.

Current rollout model:

1. deploy canary deployment and canary ingress
2. move a bounded share of traffic with ingress canary weight
3. run the release gate against the deployed environment
4. promote only after the gate passes
5. rollback by forcing canary weight back to `0` and scaling the canary deployment down

## Current Risk Budgets

These budgets are intentionally tied to current runtime limits, not aspirational future scale.

### Perf Smoke Budgets

The release commit must keep the smoke suite under these thresholds unless the thresholds are intentionally re-baselined:

- `/health`: average and p95 must remain within the configured smoke threshold
- `/api/v1/admin/system/health`: average and p95 must remain within the configured smoke threshold
- `/api/v1/auth/login`: average and p95 must remain within the configured smoke threshold
- teacher submission list smoke path: average and p95 must remain within the configured smoke threshold
- admin section list smoke path: average and p95 must remain within the configured smoke threshold
- admin student create smoke path: average and p95 must remain within the configured smoke threshold
- teacher review workflow smoke path: average and p95 must remain within the configured smoke threshold

Source of truth:

- `scripts/perf_smoke.py`

### AI Queue Budgets

Derived from the current scheduler model:

- warning at `36` queued AI jobs
- critical at `90` queued AI jobs
- scheduler failover upper bound `90s`

Release rule:

- do not roll forward AI-affecting releases when queue depth is already above warning unless the release directly fixes that condition
- roll back or pause if queue depth crosses critical and does not recover during the watch window

### Similarity Budgets

Current planning limits:

- warning at `800` candidate submissions in one similarity run
- hard planning ceiling at `1000`

Release rule:

- do not enable broader similarity usage or batch backfills if expected candidate counts exceed the current bound

### Fallback And Provider Health Budget

Current provider mode is `openai+fallback`.

Release rule:

- fallback use is acceptable for resilience
- sustained fallback-heavy behavior after rollout is a release risk and must be treated as degraded capacity or provider-health pressure

Until explicit runtime counters are added, fallback-heavy behavior must be checked from logs and admin operations signals.

## Rollback Triggers

Roll back immediately when any of these occur after release and cannot be resolved quickly with a safe config change:

1. Auth regression blocks login, refresh, or `/auth/me`.
2. Governance or destructive-action safety behavior regresses.
3. Scheduler jobs duplicate, stall, or lose leader control.
4. Perf smoke thresholds fail on the release commit.
5. `/api/v1/admin/system/health` enters a critical alert state after rollout.
6. AI queue depth breaches critical and continues growing during the watch window.
7. A migration writes data the current release can read but the previous stable release cannot.

## Rollback Procedure

### Application Rollback

Use when the release changed code but not irreversible data shape.

Procedure:

1. stop forward rollout
2. revert the release commit or redeploy the last known good image
3. rerun health and smoke checks
4. confirm `/api/v1/admin/system/health` stabilizes

### Runtime Or Config Rollback

Use when the failure is caused by scheduler cadence, provider settings, ingress, or manifest config.

Procedure:

1. revert config or manifest change
2. redeploy affected component
3. validate scheduler leadership, health, and latency

### Data-Shape Rollback

Use only if backward compatibility has already been confirmed.

Procedure:

1. stop writes if needed
2. assess whether the previous release can read the new documents safely
3. if yes, revert application code only
4. if no, do not blindly roll back; ship a forward-fix or a compensating migration

Rule:

- schema changes are not automatically reversible just because the migration was small

## Release Watch Window

Minimum watch expectations after release:

- watch `/health`
- watch `/api/v1/admin/system/health`
- rerun or inspect `backend-perf-smoke`
- confirm queue pressure is not rising abnormally for AI-affecting releases
- confirm no new scheduler duplication or lock anomalies

Suggested minimum watch duration:

- Class 1 and Class 2: `15` minutes
- Class 3 and Class 4: `30` minutes

## Release Checklist

Before release:

1. classify the release
2. verify CI is green
3. run any required migration dry run
4. confirm rollback path
5. review admin health state

During release:

1. apply rollout in the smallest practical scope
2. verify health immediately
3. run `python scripts/release_gate.py --base-url <api-root> --bearer-token <token>` against the deployed environment
4. verify the most relevant user journey

After release:

1. watch health and alert state
2. inspect AI/scheduler behavior if touched
3. decide go, hold, or rollback within the watch window

## Current Gaps

This governance layer is now documented, runtime AI pressure metrics are live through `/api/v1/admin/system/health` with persisted snapshot history, an automated release gate enforces the current health budgets in CI and can be run against a live environment, and staged canary rollout control is now scriptable from the repo.

## Completion Criteria

Treat Phase 4 item 3 as complete only when all of the following are true:

1. release classes and required checks are documented against the real repo CI jobs and runtime surfaces
2. current risk budgets are explicit and mapped to observable runtime signals
3. operators can review current release risk from the admin system page and dedicated observability dashboard without inspecting raw API payloads
4. rollout control includes either:
   - automated canary / staged promotion support, or
   - an equivalent deployment controller with enforceable rollback gates

Current status:

- criteria `1` through `4` are met in the current worktree
