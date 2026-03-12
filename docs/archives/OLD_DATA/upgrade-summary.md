# CAPS AI Upgrade Summary

Date: 2026-02-23

## What Was Improved
- Completed baseline safety commit before upgrade work.
- Introduced backend rate limiting for auth and mutating requests.
- Added startup index bootstrap for key MongoDB access paths.
- Extended notice model for future-ready communication features.
- Implemented production-safe notice attachment uploads via Cloudinary.
- Added announcement attachment UX in frontend with previews and progress.
- Improved communication card rendering performance with memoization and lazy image loading.

## What Was Refactored
- Consolidated upload concerns into `backend/app/services/cloudinary_uploads.py`.
- Centralized DB index creation in `backend/app/core/indexes.py`.
- Added dedicated rate limit middleware in `backend/app/core/rate_limit.py`.
- Improved Notice endpoint internals for dual JSON + multipart compatibility.

## Security Upgrades
- Added request throttling middleware.
- Enforced strict server-side upload validation (MIME/type/count/size).
- Added Cloudinary rollback on failed notice creation.
- Added cloud asset cleanup on notice deletion.
- Added additional security headers (`Strict-Transport-Security`, `Cross-Origin-Opener-Policy`).
- Preserved role-based authorization checks for all notice operations.

## Performance Improvements
- Added MongoDB indexes for hot query patterns.
- Added stable sort and indexed list path for notices.
- Reduced frontend re-renders with memoized feed and announcement cards.
- Enabled lazy loading for announcement images.

## New Capabilities
- Notice attachments (images + documents) with Cloudinary metadata-only storage.
- Announcement card media banner + modal viewer + file links.
- Notice delete flow with attachment cleanup.
- Notice future fields prepared without breaking existing data:
  - `is_pinned`
  - `scheduled_at`
  - `read_count`
  - `seen_by`

## Compatibility Notes
- Existing notice API path remains `/api/v1/notices/`.
- Existing JSON notice creation remains supported.
- Existing notices without `images` continue to work (`images: []`).
- Role permissions remain unchanged.

## Future Recommendations
1. Replace in-memory rate limiting with Redis-backed distributed limiter.
2. Add pinned/scheduled/read-tracking mutation endpoints.
3. Add pagination metadata contract (`total`, `has_more`) in opt-in mode.
4. Add integration tests for multipart uploads and cloud cleanup behavior.
5. Add deployment checklist for strict production CORS origin set.
