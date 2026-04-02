# Security Report

Generated: 2026-03-31

## Validation Summary

- `python scripts/check_secrets.py --tracked-only`: no likely secrets detected in tracked files
- backend safety checks: passed
- auth and security middleware were inspected directly in code

## Confirmed Security Strengths

### HTTP and response hardening

The backend adds:

- request and trace IDs
- `X-Content-Type-Options`
- `X-Frame-Options`
- HSTS
- referrer policy
- permissions policy
- no-store headers for API routes
- standardized JSON error envelopes with error IDs

### Auth token handling

- frontend keeps the access token in memory
- refresh token is issued via HTTP-only cookie
- backend supports refresh rotation and logout invalidation flows

### Runtime validation

`backend/app/core/config.py` rejects unsafe runtime configuration in non-development mode for:

- default JWT secret
- default bulk student temp password
- partial Cloudinary configuration

## Repo-Based Findings

### 1. Tracked environment configuration is still a hygiene risk

Evidence:

- `backend/.env.production` is present in the repo
- it contains production-facing auth and password-related settings
- `backend/.env` exists locally in the workspace

Impact:

- even placeholder or local values in tracked env files create confusion about what should be repo-managed versus secret-managed
- bulk student temp password handling deserves stricter deployment discipline than a tracked file implies

Recommended fix:

- keep production values in deployment secret stores only
- keep tracked env files placeholder-only and minimal
- document the secure source of truth for deployment config

### 2. The secret scanner is conservative and can miss configuration hygiene issues

Evidence:

- `check_secrets.py` focuses on explicit token patterns and suspicious assignments
- the scan passed even though tracked env configuration still warrants manual review

Impact:

- “no likely secrets detected” is not the same as “config hygiene is complete”

Recommended fix:

- keep the scanner
- add a policy check that flags tracked production env files or high-risk config keys regardless of value style

### 3. Rate limiting is intentionally disabled under pytest

Evidence:

- `RateLimitMiddleware` disables itself during pytest runs

Impact:

- this is useful for test stability
- but it means automated tests do not validate rate-limit behavior unless explicitly targeted

Recommended fix:

- keep the pytest bypass
- add focused middleware tests for rate-limited paths

### 4. Avatar access control is sensibly restricted

Evidence:

- `/auth/profile/avatar/{user_id}` only allows admin or self access

Impact:

- profile media retrieval does not appear overly permissive

## Current Verdict

The application security posture is reasonably strong in code, especially around headers, cookies, and runtime validation. The main remaining risk is repo configuration hygiene, not a demonstrated auth bypass.
