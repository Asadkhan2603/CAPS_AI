# Feature Suggestions

Generated: 2026-03-31

## Suggestions Based On Current Repo State

### 1. Add a master hierarchy preflight screen or admin banner

Why:

- the import pipeline exists but the workbook source is missing
- admins currently have no product-level signal that this canonical setup path is blocked

### 2. Add explicit product messaging for deferred direct messaging

Why:

- the repo still contains deferred messaging UI files
- the route currently redirects away from the feature

Suggestion:

- add a clear “not enabled” state in docs or admin config rather than leaving silent route redirection as the only signal

### 3. Add section-mapping audit history to the coordinator workflow

Why:

- section lock and unlock are important operational controls
- the current workflow could be stronger if coordinators could see recent mapping and lock history inline

### 4. Expand system health export beyond JSON

Why:

- the admin system page already supports JSON export
- CSV or summarized Excel-ready output would help operational review and audit handoff

### 5. Split oversized admin screens into clearer task-focused panels

Why:

- `AcademicStructurePage` and `StudentBulkWorkflow` are large and dense
- smaller panels would improve usability and simplify future maintenance
