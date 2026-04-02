# Improvement Roadmap

Generated: 2026-03-31

## Health Score

Repo reconstruction and operational readiness score: **81 / 100**

### Why not higher

- workbook-backed master hierarchy import is blocked by missing source input
- full backend suite local execution is brittle
- compatibility migration is still active
- some cleanup and hygiene surfaces remain unfinished

### Why not lower

- frontend validation is clean
- targeted backend validation is clean
- runtime matrix now passes
- route structure and docs are much more coherent than at the start of the audit

## Priority Roadmap

### P0

1. Restore or redefine the canonical workbook source used by `import_master_hierarchy.py`.
2. Fix backend test import paths so the full suite runs cleanly from documented local entry points.

### P1

1. Remove placeholder backend domain packages that do not contain real code.
2. Remove or archive deferred messaging UI files and the orphaned `Topbar.jsx`.
3. Extend `.gitignore` for generated output directories such as `artifacts`, `.runlogs`, and `test-results`.

### P2

1. Split oversized backend and frontend modules with the highest complexity concentration.
2. Continue reducing `class` compatibility naming where safe.
3. Resolve empty `docs/cleanup/` report stubs.

## Recommended Sequence

1. stabilize reproducibility
2. clean dead or placeholder modules
3. reduce complexity in the largest files
4. finish export-oriented validation and workbook recovery

## Current Recommendation

The repo is in a much better state for documentation-driven reconstruction than it was at the start of this work, but it should not be treated as fully reconstruction-complete until the workbook dependency and backend test invocation issues are resolved.
