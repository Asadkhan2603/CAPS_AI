# Test Cases

Generated: 2026-03-31

## Automated Cases Run In This Audit Phase

- `pytest backend/tests/test_academic_permissions.py -q`
- `python scripts/check_backend_safety.py`
- `python scripts/check_runtime_matrix.py`
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run test:ci`
- `npm --prefix frontend run lint`
- `npm --prefix frontend run build`
- `npm --prefix frontend run check:bundle`

## Existing Repo Test Coverage Signals

### Backend

Covered areas visible from the current test suite:

- auth and session flows
- academic permission boundaries
- academic setup rules
- timetable workflows
- destructive action telemetry
- master hierarchy import and hardening
- admin recovery

### Frontend

Covered areas visible from the current Vitest suite:

- permissions helpers
- quick search helpers
- academic batch identity helpers
- student bulk template helpers
- navigation group logic
- API client behavior
- timetable helper logic

## Gaps Found During This Phase

### 1. Full backend suite entry is brittle

Observed failure:

- `pytest backend/tests -q` and `pytest tests -q` fail collection due `backend.*` imports

Add test case:

- a documented one-command local backend test invocation should be verified in CI or pre-commit docs

### 2. Rate-limit middleware behavior is not validated by the broad suite path

Reason:

- middleware disables itself under pytest for stability

Add test case:

- explicit middleware tests that force rate limiting on

### 3. Workbook source presence is not validated before local runbook use

Add test case:

- a fast preflight check for required workbook presence and sheet names

### 4. Deferred messaging state should stay explicit

Add test case:

- route test proving `/communication/messages` still redirects and does not silently break

## Recommended Manual Cases

1. Login, refresh token rotation, and logout from the browser.
2. Student bulk import preview and commit with both create and map flows.
3. Section lock and unlock by coordinator versus admin.
4. Admin system health page auto-refresh with snapshot export.
5. Master hierarchy import recovery once the workbook source is restored.
