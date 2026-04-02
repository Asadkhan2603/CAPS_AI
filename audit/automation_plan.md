# Automation Plan

Generated: 2026-03-31

## Current Automated Gates

From `.github/workflows/ci.yml` and local validation, the repo currently automates:

- tracked-file secret scanning
- backend static analysis
- backend tests with coverage gate
- backend performance smoke
- release governance gate
- frontend lint
- frontend tests
- frontend coverage gate
- frontend build
- frontend bundle budget check
- academic hierarchy merge gate
- delivery smoke checks
- runtime matrix validation

## Repo-Based Findings

### 1. Automation coverage is strong, but local reproducibility is weaker than CI design

Evidence:

- many gates exist in CI
- local full backend suite invocation currently fails due import-path assumptions

Action:

- make the documented local test entry point match CI expectations

### 2. Workbook dependency needs an explicit preflight gate

Evidence:

- import script hardcodes `exports/Master_copy.xlsx`
- the file is absent

Action:

- add a small workbook presence and schema check before attempting dry-run import

### 3. Output artifact hygiene should be automated better

Evidence:

- generated folders such as `artifacts`, `.runlogs`, and `test-results` are present in the repo workspace
- `.gitignore` does not currently list all of them

Action:

- extend `.gitignore`
- add a cleanup or validation check for generated output directories

## Recommended Next Automation Steps

1. Make backend test invocation path-independent.
2. Add a preflight script for workbook availability and required sheet names.
3. Add a repo-hygiene check for empty audit or cleanup stubs.
4. Keep bundle budgets and deploy smoke as required release gates.
5. Consider a targeted route smoke check for admin onboarding and student bulk import.
