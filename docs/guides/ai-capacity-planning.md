# AI Capacity Planning

This guide starts Phase 4 capacity planning for AI and similarity workloads using the current runtime model in the repository.

## Scope

The baseline covers:

- durable AI job pickup cadence
- OpenAI runtime budget defaults
- similarity workload bounds
- scheduler leadership constraints

It does not yet model:

- real provider token quotas
- real production concurrency
- historical queue depth distributions
- cluster-level CPU and memory headroom

## Runtime Metrics Surface

The baseline is no longer script-only.

Current runtime metrics now surface through `/api/v1/admin/system/health` under `observability.ai_metrics`, including:

- queued AI jobs
- running AI jobs
- failed AI jobs
- oldest queued AI job age
- AI generations in the last 15 minutes
- AI fallback count and fallback rate in the last 15 minutes
- last similarity candidate count and duration
- max similarity candidate count in the last 15 minutes
- bounded 15-minute history points for queue depth, fallback rate, and similarity candidate pressure
- persisted minute-bucket snapshots in `system_health_snapshots` for cross-refresh and cross-deployment operator review

The admin system page now renders live, persisted, and browser-local history views, the dedicated observability page provides a focused operator dashboard for those signals, and throttled system notifications route active operational alerts to `system.read` operators. Release and capacity checks no longer depend on raw JSON inspection alone.

## Current Baseline

As of the current runtime:

- AI jobs are processed by the in-process scheduler leader
- AI job polling runs every `10s` by default
- each scheduler tick picks up at most `3` jobs
- queue pickup ceiling is therefore `18` jobs per minute in the best case
- OpenAI timeout is `20s`
- OpenAI max output tokens are capped at `400`
- similarity uses assignment-local TF-IDF cosine scoring
- similarity candidate selection currently caps at `1000` submissions per run
- scheduler failover is bounded by the leader lock TTL, currently `90s`

These numbers are emitted directly by:

- [ai_capacity_baseline.py](../../scripts/ai_capacity_baseline.py)

Run it with:

```bash
python scripts/ai_capacity_baseline.py
python scripts/ai_capacity_baseline.py --json
```

## Operational Interpretation

### AI queue

The current queue model is safe for moderate operator-triggered workloads, but it is still single-leader and single-process.

Practical baseline:

- warning if queued AI jobs exceed `36`
- critical if queued AI jobs exceed `90`

Reasoning:

- `36` queued jobs is roughly two minutes of best-case pickup capacity
- `90` queued jobs is roughly five minutes of best-case pickup capacity
- actual service time can be lower because some jobs contain multiple submissions or slow provider calls

### Similarity runs

Similarity remains CPU-heavy because TF-IDF vectorization and cosine similarity run inside the app worker.

Practical baseline:

- warning if a single similarity run approaches `800` candidate submissions
- treat `1000` candidates as the hard planning ceiling for the current implementation

## Capacity Risks

1. Queue depth alone understates cost because bulk AI jobs can fan into multiple submissions.
2. Similarity work remains CPU-bound inside the API deployment path.
3. Scheduler leadership failover can delay queue progress for up to the lock TTL if a leader dies abruptly.
4. Provider fallback protects correctness, but fallback-heavy operation still indicates capacity or provider-health pressure.

## Completion Criteria

Treat Phase 4 item 2 as complete only when all of the following are true:

1. The runtime baseline script and backend capacity constants are aligned and versioned in code.
2. `/api/v1/admin/system/health` exposes live AI pressure metrics, bounded live history, persisted history, and snapshot-store retention status.
3. The admin system page and dedicated observability dashboard render those signals in a way an operator can review without inspecting raw JSON.
4. Queue depth, oldest queued age, fallback rate, and similarity candidate thresholds are documented as explicit operational budgets.
5. Those budgets are watched outside the admin page by dedicated dashboards and alert routing.

Current status:

- criteria `1` through `5` are met in the current worktree

## Remaining Work

1. Capture production-like queue depth, oldest queued age, fallback rate, and similarity candidate distributions over time.
2. Decide whether `system_health_snapshots` remains Mongo-backed or moves to a dedicated time-series store later.
3. Decide whether AI/similarity workloads stay in the API process or move to a dedicated worker deployment.
