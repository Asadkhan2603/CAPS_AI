# CAPS AI System Audit Report

Date: 2026-02-23
Branch: main
Scope: Full-stack audit and upgrade of the current repository implementation.

## Scope Clarification
- Requested stack in prompt: Node.js + Express + MongoDB.
- Actual project stack audited: FastAPI (Python) + MongoDB (Motor) + React (Vite).
- This report audits the **actual codebase** while preserving API compatibility.

## Severity Legend
- Critical: immediate production/security risk.
- High: major correctness/security/scalability risk.
- Medium: maintainability/performance risk.
- Low: polish/documentation/debt.

## 1) Backend Audit (FastAPI + MongoDB)

| ID | Area | Finding | Severity | Recommended Fix | Priority |
|---|---|---|---|---|---|
| BE-01 | Rate limiting | No global abuse throttling for auth and mutating endpoints. | High | Add centralized rate-limit middleware keyed by client+path. | P0 |
| BE-02 | DB indexing | Only partial index creation existed; several hot query paths lacked explicit indexes. | High | Add startup index bootstrap for users/notices/assignments/submissions/evaluations/notifications/audit logs. | P0 |
| BE-03 | Error envelope | Error responses lacked uniform success flag; shape partly inconsistent across handlers. | Medium | Keep `detail` backward-compatible, add `success: false` and `error_id` uniformly in exception handlers. | P1 |
| BE-04 | Notice attachments | Upload support required strong validation + metadata-only persistence. | High | Enforce MIME/size/count server-side and store only URL/public_id/name/size/mime_type. | P0 |
| BE-05 | Attachment cleanup | No notice delete path to perform Cloudinary cleanup. | Medium | Add notice delete endpoint with ownership checks and Cloudinary cleanup loop. | P1 |
| BE-06 | Security headers | Baseline had several headers, but missing strict transport and COOP hardening. | Low | Add Strict-Transport-Security and Cross-Origin-Opener-Policy. | P2 |

## 2) Database Design Audit (MongoDB)

| ID | Area | Finding | Severity | Recommended Fix | Priority |
|---|---|---|---|---|---|
| DB-01 | Notice extensibility | Future-ready communication fields not present in notice payload mapping. | Medium | Add non-breaking defaults: `is_pinned`, `scheduled_at`, `read_count`, `seen_by`. | P1 |
| DB-02 | Query scalability | Notice list endpoints rely on filters that benefit from compound indexes. | High | Add `is_active+created_at`, `scope+scope_ref_id` indexes. | P0 |
| DB-03 | Referential flexibility | Several refs are string IDs without FK constraints (Mongo norm) and require strict app checks. | Medium | Keep app-level validation (already present) and enforce in all mutating routes. | P1 |

## 3) Cloudinary Integration Audit

| ID | Area | Finding | Severity | Recommended Fix | Priority |
|---|---|---|---|---|---|
| CLD-01 | Validation | Upload validation must be enforced server-side independent of UI. | High | Validate MIME/count/size in backend upload parser. | P0 |
| CLD-02 | Data storage | Risk of accidental binary/base64 persistence if not controlled. | High | Only persist metadata in `notices.images`; never store binary/base64. | P0 |
| CLD-03 | Cleanup | Failed create could leave orphan Cloudinary assets. | Medium | Roll back uploaded assets on create failure. | P1 |
| CLD-04 | Deletion | Deleting notice must remove remote assets to avoid storage leak. | Medium | Add cleanup loop in notice delete flow. | P1 |

## 4) Frontend Audit (React)

| ID | Area | Finding | Severity | Recommended Fix | Priority |
|---|---|---|---|---|---|
| FE-01 | Communication UX | Legacy ERP-style forms and scope confusion previously existed. | Medium | Audience-first modal, searchable audience selector, progressive steps. | P1 |
| FE-02 | Upload UX | Needed preview/remove/progress and disabled publish during upload. | High | Implement attachment picker with preview, remove action, progress bar. | P0 |
| FE-03 | Rendering performance | Feed and announcement cards re-render frequently with large lists. | Medium | Memoize card components and lazy-load images. | P1 |
| FE-04 | Compatibility | Existing routes `/notices`, `/notifications` must keep working. | Medium | Redirect legacy routes to communication hub pages. | P1 |

## 5) Communication Module Audit

| ID | Area | Finding | Severity | Recommended Fix | Priority |
|---|---|---|---|---|---|
| COM-01 | Scope mapping UX | Users should not see raw `scope_ref_id`. | High | Use audience selector; map to `scope/scope_ref_id` internally. | P0 |
| COM-02 | Feed consistency | Feed events need a single chronological, badge-based rendering strategy. | Medium | Aggregate notices/notifications/assignments/evaluations and sort by timestamp. | P1 |
| COM-03 | Attachment display | Cards required balanced media handling and non-image support. | Medium | Banner preview + modal for images; file links for non-images. | P1 |

## 6) Security Audit

| ID | Area | Finding | Severity | Recommended Fix | Priority |
|---|---|---|---|---|---|
| SEC-01 | API abuse | No request throttling baseline. | High | Add centralized rate limiter for auth + mutating routes. | P0 |
| SEC-02 | Upload attack surface | File type spoofing/oversized files required strict checks. | High | Enforce MIME + size + count on server; reject invalid uploads. | P0 |
| SEC-03 | Sensitive data leakage | Auth/session paths generally protected; must preserve no-secret responses. | Medium | Keep standardized error handling with trace IDs only; no secret payloads. | P1 |
| SEC-04 | CORS policy | CORS is configurable and dev-friendly; production requires strict origin controls. | Medium | Document production-safe CORS and avoid wildcard methods/headers in prod deployment policies. | P2 |

## Implemented Upgrades in This Iteration

### Backend
- Added centralized in-memory rate limiting middleware for auth + mutating routes.
- Added startup index bootstrap for hot collections/queries.
- Hardened error envelope (`success: false`, `detail`, `error_id`) while preserving compatibility.
- Added Cloudinary settings in config/env and metadata-only upload service.
- Added future-ready notice fields (non-breaking defaults): `is_pinned`, `scheduled_at`, `read_count`, `seen_by`.
- Added notice delete endpoint with role checks and Cloudinary cleanup.

### Frontend
- Added attachment support in announcement creation:
  - up to 3 files
  - preview (images)
  - remove before publish
  - upload progress
  - publish lock while uploading
- Multipart publish path for announcements (`images` key).
- Announcement card enhancement:
  - image banner preview
  - `+N more` overlay
  - modal image viewer
  - non-image attachment links
  - lazy loading
- Memoization added to feed/announcement cards for render efficiency.

## Remaining Recommendations (Next Phase)
- Add persistent/distributed rate limiter (Redis) for multi-instance deployments.
- Add signed/owner-scoped delete API for notice attachments (if partial attachment deletion is needed).
- Add read tracking mutation endpoints to fully operationalize `read_count`/`seen_by`.
- Add backend pagination metadata envelope (`total`, `has_more`) in a backward-compatible opt-in mode.
- Add OpenAPI examples for multipart notice creation with attachments.

## Implementation Priority Summary
- P0 (Immediate): BE-01, BE-02, BE-04, DB-02, CLD-01, CLD-02, COM-01, FE-02, SEC-01, SEC-02
- P1 (Near-term): BE-03, BE-05, DB-01, CLD-03, CLD-04, FE-01, FE-03, FE-04, COM-02, COM-03, SEC-03
- P2 (Planned): BE-06, SEC-04
