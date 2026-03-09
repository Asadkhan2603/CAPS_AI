# Auth Module Master

## Module Tree

```text
Auth Module
|-- Registration
|-- Login
|-- Refresh Token Rotation
|-- Logout And Blacklist
|-- Session Validation
|-- Password Security
`-- Profile Session Context
```

## Internal Entity And Flow Tree

```text
User credentials
`-- Access token issuance
    `-- Refresh token issuance
        `-- Session validation via /auth/me
            `-- Logout and revocation
```

Primary implementation sources:

- `backend/app/api/v1/endpoints/auth.py`
- `backend/app/domains/auth/service.py`
- `backend/app/domains/auth/repository.py`
- `backend/app/core/security.py`
- `backend/app/schemas/auth.py`
- `backend/app/schemas/user.py`
- `backend/app/models/users.py`
- `frontend/src/context/AuthContext.jsx`
- `frontend/src/services/apiClient.js`
- `frontend/src/pages/LoginPage.jsx`
- `frontend/src/pages/RegisterPage.jsx`

Related references:

- `docs/modules/RBAC_MODULE_MASTER.md`
- `docs/modules/GOVERNANCE_MODULE_MASTER.md`
- `backend/tests/test_auth.py`
- `backend/app/core/config.py`

## 1. Module Overview

The auth module is responsible for:

- account bootstrap and registration policy
- login and JWT issuance
- refresh-token rotation
- logout and token revocation
- current-user resolution
- password change
- self-profile update
- avatar upload and authorized avatar retrieval

It is the entry point for all authenticated behavior in CAPS AI. It does not decide full authorization policy on its own. Authentication proves identity and carries base claims. Authorization is then enforced through the RBAC layer in `security.py` and `permission_registry.py`.

The implemented model is:

- stateless access token for request authentication
- rotating refresh token for session continuation
- blacklist-based token revocation
- optional persistent session tracking through `user_sessions`
- browser storage in `sessionStorage`, not `localStorage`

That last point is operationally important. The current frontend intentionally treats auth as browser-tab-session state, with extra client-side idle and max-session expiry.

## 2. Authentication Architecture

### Backend Layers

The backend auth flow is split into three layers.

1. endpoint layer
   - `backend/app/api/v1/endpoints/auth.py`
   - exposes HTTP routes
   - handles request metadata such as IP, device fingerprint, and user agent

2. domain service layer
   - `backend/app/domains/auth/service.py`
   - owns registration policy, login, refresh, logout, anomaly detection, and session rotation behavior

3. crypto / token layer
   - `backend/app/core/security.py`
   - owns password hashing, token encode/decode, blacklist checks, and current-user resolution

### Frontend Layers

The frontend auth flow is split into:

1. `AuthContext`
   - session state and auth lifecycle
2. `apiClient`
   - bearer token injection
   - automatic refresh attempt on `401`
3. route guards
   - `ProtectedRoute`
   - feature-level UX gating

Backend remains the final authority. Frontend checks only improve navigation and UX.

## 3. User Identity Model

### Base Roles

The core role field is:

- `admin`
- `teacher`
- `student`

### Admin Types

Admin users may also carry:

- `super_admin`
- `admin`
- `academic_admin`
- `compliance_admin`

The public user model defaults legacy admins with missing `admin_type` to effective `admin` at serialization and permission resolution time.

### Extended Roles

The user schema allows extension roles:

- `year_head`
- `class_coordinator`
- `club_coordinator`
- `club_president`

These extensions are part of the auth payload and RBAC decision surface. They are not a substitute for the base role.

### Role Scope

`UserOut` also includes `role_scope`, currently modeled for:

- `class_coordinator`
- `club_president`

Class coordinator scope can include:

- `faculty_id`
- `department_id`
- `program_id`
- `specialization_id`
- `department_code`
- `course_id`
- `year_id`
- `batch_id`
- `semester_id`
- `class_id`

This is the mechanism intended for row-aware authority, although backend enforcement is still uneven across modules.

## 4. Password Security

### Hashing Algorithm

Passwords are hashed with:

- `PBKDF2-HMAC-SHA256`
- 390000 iterations
- 16-byte random salt

Stored format:

`pbkdf2_sha256$<iterations>$<salt_hex>$<digest_hex>`

### Verification Behavior

Verification in `security.py`:

- rejects malformed hashes
- rejects unsupported algorithm labels
- uses constant-time digest comparison through `hmac.compare_digest`

This is a reasonable current implementation for password hashing.

### Current Gap

There is no password history, password reuse protection, or password reset email flow in the current code path.

## 5. JWT Token Model

### Access Token

Access tokens contain:

- `jti`
- `token_type = access`
- `sub`
- `email`
- `role`
- `admin_type`
- `extended_roles`
- `exp`

Default expiry:

- controlled by `ACCESS_TOKEN_EXPIRE_MINUTES`
- example defaults:
  - `.env.example`: `60`
  - `.env.production`: `15`

### Refresh Token

Refresh tokens contain the same identity claims plus:

- `token_type = refresh`

Default expiry:

- controlled by `REFRESH_TOKEN_EXPIRE_DAYS`
- default example: `7`

### Token Type Enforcement

`decode_access_token(...)` validates the expected token type. That prevents:

- using refresh token where access token is expected
- using access token where refresh token is expected

### Token Subject Resolution

`get_current_user(...)`:

1. decodes access token
2. checks blacklist by `jti`
3. loads current user from database by `sub`

This means the DB user document is authoritative over token claims after authentication. The token is not blindly trusted as the complete user object.

## 6. Registration Policy

Registration policy is configurable through:

- `AUTH_REGISTRATION_POLICY`

Supported modes:

- `open`
- `single_admin_open`
- `bootstrap_strict`

### `bootstrap_strict`

Behavior:

- if any admin already exists, self-registration is closed
- first account must be `admin`

Error conditions:

- `"Self-registration is closed. Contact super admin."`
- `"First account must be admin."`

### `single_admin_open`

Behavior:

- first admin can self-register
- once an admin exists, new admin self-registration is closed
- non-admin roles may still be allowed through this policy path

### `open`

Behavior:

- unrestricted self-registration from policy perspective

### Current Operational Meaning

The registration page in the frontend is built as a bootstrap-only flow for creating the first super admin. That aligns best with `bootstrap_strict`, even though the backend still supports broader modes.

## 7. Login Flow

### Request Path

`POST /auth/login`

Payload:

- `email`
- `password`

### Login Validation Sequence

1. normalize email to lowercase and trim
2. load user by email
3. check lockout state
4. verify password hash
5. reject inactive users
6. clear prior failed login counters
7. mint access token
8. mint refresh token
9. create or update session tracking context
10. detect new-device or new-network anomaly

### Lockout Logic

Controlled by:

- `ACCOUNT_LOCKOUT_MAX_ATTEMPTS`
- `ACCOUNT_LOCKOUT_WINDOW_MINUTES`
- `ACCOUNT_LOCKOUT_DURATION_MINUTES`

Behavior:

- failed attempts are counted inside the configured rolling window
- if threshold is hit, `lockout_until` is set
- failed count is then reset

Login during lockout returns:

- `423 Locked`

Wrong credentials return:

- `401 Invalid email or password`

### Inactive User Handling

If `is_active` is false:

- login fails with `403 User is inactive`

## 8. Refresh Flow

### Request Path

`POST /auth/refresh`

Payload:

- `refresh_token`

### Refresh Behavior

1. decode refresh token
2. reject if refresh `jti` is blacklisted
3. load active session by `refresh_jti`
4. load user
5. mint new access token
6. mint new refresh token
7. blacklist old refresh token
8. rotate session to the new `refresh_jti`

This is refresh-token rotation, not static long-lived refresh reuse.

### Session Rotation Fields

Session rotation updates:

- `refresh_jti`
- `rotated_at`
- `last_seen_at`
- `last_seen_ip`
- `fingerprint`
- `user_agent`

### Security Value

This design reduces replay value of an old refresh token after successful rotation.

## 9. Logout And Revocation

### Request Path

`POST /auth/logout`

Behavior:

- requires access token
- optionally accepts refresh token body

Logout flow:

1. decode current access token
2. blacklist access token `jti`
3. if refresh token provided:
   - decode refresh token
   - blacklist refresh token `jti`
   - revoke matching session in `user_sessions`
4. write logout audit event

Response:

- `{ "success": true, "message": "Logged out" }`

### Important Limitation

If the frontend logs out without sending a refresh token, the access token is revoked but the refresh session may remain active until expiry or later revocation.

The current frontend does send refresh token on logout when available, so the normal browser path is correct.

## 10. Session Tracking And Anomaly Detection

### Session Store

The auth repository uses `user_sessions` when present. Session rows include:

- `user_id`
- `refresh_jti`
- `fingerprint`
- `ip_address`
- `last_seen_ip`
- `user_agent`
- `created_at`
- `last_seen_at`
- `rotated_at`
- `revoked_at`

### Device Fingerprinting

Fingerprint seed is:

- explicit `x-device-fingerprint` header if provided
- otherwise derived from `user_agent|ip_address`

Stored fingerprint is a SHA-256 digest.

### Anomaly Detection

On login, the service looks at recent active sessions and flags:

- `new_device`
- `new_network`

Network comparison:

- IPv4 compares same `/24` prefix by string split
- IPv6 compares first 19 characters

If anomaly is detected, an audit event is logged with:

- `action = login_anomaly`
- `severity = high`

### Governance Tie-In

Admin governance pages already expose session monitoring and login anomaly counts. That means auth is partially integrated with governance observability, not isolated from it.

## 11. Current User And Authorization Bridge

### `/auth/me`

`GET /auth/me` returns:

- public user identity
- role
- admin type
- extension roles
- role scope
- profile
- avatar URL metadata
- must-change-password flag

This endpoint is the session validation anchor used by the frontend on app load.

### Why It Matters

The frontend does not trust the stored user object forever. On reload it validates the token by calling `/auth/me`. If this fails:

- storage is cleared
- user is effectively logged out

## 12. Self-Service Account Endpoints

### Change Password

Route:

- `POST /auth/change-password`

Rules:

- current password must match
- new password must differ from current password
- successful change sets:
  - new `hashed_password`
  - `must_change_password = false`

Current limitation:

- existing access and refresh tokens are not forcibly rotated or revoked on password change

That is a real security gap. Password change updates credentials, but it does not currently invalidate all existing sessions.

### Update Profile

Route:

- `PATCH /auth/profile`

Editable fields:

- `full_name`
- contact and demographic profile fields
- professional/bio fields

Behavior:

- merges profile fields into the existing `profile` object
- rejects empty update body

### Avatar Upload

Route:

- `POST /auth/profile/avatar`

Rules:

- allowed extensions:
  - `.png`
  - `.jpg`
  - `.jpeg`
  - `.webp`
- max size:
  - `3 MB`
- empty files rejected
- existing avatar files for the user are deleted before storing the new one

Storage:

- local filesystem under `uploads/profiles`

### Avatar Retrieval

Route:

- `GET /auth/profile/avatar/{user_id}`

Access:

- admin can view any avatar
- non-admin can view only their own avatar

Important implication:

- avatar delivery is authorization-gated, not public static hosting

## 13. Frontend Session Model

### Storage Location

Frontend auth state is stored in:

- `sessionStorage`

Keys:

- `caps_ai_token`
- `caps_ai_refresh_token`
- `caps_ai_user`

This is intentionally not persisted to `localStorage`.

### Consequence

Closing the browser tab or browser session clears auth storage in typical browser behavior. This is why login should not survive full browser session teardown, unlike the earlier localStorage-based behavior many SPAs use.

### Storage Versioning

`AuthContext` uses:

- `caps_ai_auth_storage_version`

If the version changes:

- client auth storage is cleared

This is a simple migration/invalidation mechanism for frontend auth state shape changes.

### Client-Side Session Expiry

Client auth layer also enforces:

- idle timeout
- max session duration

Defaults:

- idle timeout: `30 minutes`
- max session: `8 hours`

Configurable via:

- `VITE_AUTH_IDLE_TIMEOUT_MINUTES`
- `VITE_AUTH_MAX_SESSION_HOURS`

Behavior:

- activity events refresh `LAST_ACTIVITY_AT`
- periodic timer checks expiry every 15 seconds
- expired client session clears browser auth state

This is a frontend convenience control. Backend token expiry is still independent and authoritative.

## 14. Frontend Refresh And API Behavior

### Bearer Injection

`apiClient` adds:

- `Authorization: Bearer <token>`
- `X-Trace-Id`
- `X-Request-Id`

### Automatic Refresh

On `401`:

- skip retry for auth routes themselves
- if refresh token exists:
  - call `/auth/refresh`
  - store new access token
  - store new refresh token if returned
  - replay original request

If refresh fails:

- clear auth storage

This gives the app silent session continuation until refresh path fails or client-side expiry triggers.

### API Trace Buffer

`apiClient` also keeps an in-memory trace buffer of recent requests, including:

- method
- URL
- status
- duration
- trace id
- request id
- error id

This is not auth logic by itself, but it helps auth troubleshooting.

## 15. Frontend Pages

### `LoginPage.jsx`

Implements:

- email/password login
- animated branded UI
- optional Google sign-in redirect generation

Important current state:

- Google button is only a redirect helper
- there is no backend Google OAuth callback or token exchange implementation in the current repo
- if env vars are missing, button shows informational toast

So Google sign-in UX exists visually, but full server-side social auth is not implemented.

### `RegisterPage.jsx`

Implements:

- bootstrap super admin creation flow
- auto-login after successful registration

Page behavior assumes:

- role is fixed to `admin`
- admin type is fixed to `super_admin`

This is intentionally narrower than the backend schema, because the page is meant for bootstrap, not ongoing self-service provisioning.

## 16. Data Collections Used

### `users`

Purpose:

- canonical identity store

Key auth fields:

- `email`
- `hashed_password`
- `role`
- `admin_type`
- `extended_roles`
- `role_scope`
- `is_active`
- `must_change_password`
- `failed_login_attempts`
- `last_failed_login_at`
- `lockout_until`
- `avatar_filename`
- `avatar_updated_at`

Constraints:

- unique email index ensured in auth repository

### `token_blacklist`

Purpose:

- stores revoked token JTIs when DB collection is available

Fields:

- `jti`
- `token_type`
- `user_id`
- `blacklisted_at`
- `expires_at`

Also mirrored into Redis through `redis_store`.

### `user_sessions`

Purpose:

- persistent refresh-session tracking
- anomaly detection input
- governance session monitoring input

Fields:

- `refresh_jti`
- `fingerprint`
- `ip_address`
- `last_seen_ip`
- `user_agent`
- `created_at`
- `last_seen_at`
- `rotated_at`
- `revoked_at`

## 17. API Endpoints

### Public / Bootstrap

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/refresh`

### Authenticated Self-Service

- `POST /auth/logout`
- `GET /auth/me`
- `POST /auth/change-password`
- `PATCH /auth/profile`
- `POST /auth/profile/avatar`
- `GET /auth/profile/avatar/{user_id}`

## 18. Current Strengths

### Strong Current Areas

- PBKDF2 password hashing with salt and constant-time comparison
- typed JWT access vs refresh separation
- refresh token rotation
- token blacklist support in Redis and Mongo
- session anomaly detection
- client session storage moved to `sessionStorage`
- client idle timeout and max-session timeout
- bootstrap-aware registration policy
- authorized avatar retrieval

## 19. Current Gaps And Risks

### Password Change Does Not Revoke Existing Sessions

This is the most important current auth gap.

Changing password:

- updates stored password hash
- does not revoke all access tokens
- does not revoke all refresh sessions

That means pre-existing sessions may remain usable until token expiry or refresh-cycle failure.

### No Full Social Login Implementation

Login page presents Google sign-in UX, but the backend has no matching OAuth callback or provider integration. This is partial product wiring, not end-to-end auth capability.

### Registration Policy And Frontend Intent Are Not Fully Collapsed

Backend still supports:

- `open`
- `single_admin_open`
- `bootstrap_strict`

Frontend register page is bootstrap-specific. That is fine operationally, but the product contract is broader than the visible UI.

### Session Persistence Is Browser-Dependent

Because storage is in `sessionStorage`, browser close behavior is good for security, but some browser restore/session-reopen features may still preserve session data depending on user settings. The model is better than `localStorage`, not absolutely equivalent to server-issued session cookies.

### Local Avatar Storage Is Not Durable

Avatar uploads are stored on local disk:

- `uploads/profiles`

That is not durable under horizontal scaling or stateless container replacement unless shared storage is mounted.

### No Forgot Password / Reset Flow

Current auth supports:

- login
- register
- change password while authenticated

It does not support:

- email reset token
- forgot password
- forced reset link

### Token Revocation Depends On Supporting Stores

Blacklist and session tracking degrade if:

- Redis is unavailable
- DB collections are absent

The code handles this gracefully, but guarantees are weaker in degraded mode.

## 20. Testing Requirements

### Core Backend Tests

Required coverage:

- register first admin
- reject duplicate email
- login success
- login failure
- lockout after repeated failures
- inactive user blocked
- refresh rotation and old refresh revocation
- logout blacklists access and refresh tokens
- `/auth/me` rejects blacklisted token
- password change rejects wrong current password
- password change requires new password different from current

### Session / Governance Tests

Required coverage:

- session row creation on login
- anomaly logging for new device or network
- session revoke on logout
- session rotate on refresh

### Frontend Tests

Required coverage:

- sessionStorage use instead of localStorage
- `AuthContext` clears expired sessions
- `apiClient` refresh retry path
- logout clears browser storage
- register bootstrap flow auto-login

### Existing Test Surface

Current repo already includes:

- `backend/tests/test_auth.py`

That suite covers basic register/login/me and some role-access behavior, but it is not yet a complete auth hardening suite.

## 21. Recommended Cleanup Strategy

### Phase 1

- revoke all active sessions on password change
- add explicit auth tests for refresh rotation and blacklist enforcement

### Phase 2

- separate bootstrap registration policy from general public registration contract
- disable or hide register page outside bootstrap mode

### Phase 3

- either implement full Google OAuth backend flow or remove the button from production builds

### Phase 4

- move avatar storage to durable object storage
- add forgot-password and reset-token flow if product requires self-service recovery

## Final Summary

The auth module is already stronger than a minimal SPA login implementation. It has:

- PBKDF2 password hashing
- JWT access and refresh separation
- refresh token rotation
- blacklist-backed revocation
- session tracking
- anomaly logging
- client idle and max-session expiry

The main issues are not missing core login. They are contract and lifecycle gaps:

- password change does not invalidate existing sessions
- Google sign-in is UI-only
- avatar storage is not durable for scaled deployments
- self-service recovery is incomplete

The current correct mental model is:

- authentication is JWT-based
- refresh sessions are tracked and rotated
- frontend session is intentionally tab-scoped through `sessionStorage`
- backend remains the final authority through `/auth/me` and token validation