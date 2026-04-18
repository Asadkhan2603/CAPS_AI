# MFA SMS and WebAuthn Operations Guide

## Canonical MFA API Surface

### Login-time MFA
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/mfa/verify`
- `POST /api/v1/auth/mfa/sms/challenge/send`
- `POST /api/v1/auth/mfa/sms/challenge/resend`
- `POST /api/v1/auth/mfa/webauthn/authenticate/begin`
- `POST /api/v1/auth/mfa/webauthn/authenticate/finish`

### Security settings / setup
- `GET /api/v1/auth/security-settings/me`
- `POST /api/v1/auth/mfa/totp/enable`
- `POST /api/v1/auth/mfa/totp/confirm`
- `POST /api/v1/auth/mfa/totp/disable`
- `POST /api/v1/auth/mfa/sms/enroll/send`
- `POST /api/v1/auth/mfa/sms/enroll/verify`
- `POST /api/v1/auth/mfa/sms/disable`
- `POST /api/v1/auth/mfa/webauthn/register/begin`
- `POST /api/v1/auth/mfa/webauthn/register/finish`
- `GET /api/v1/auth/mfa/webauthn/credentials`
- `DELETE /api/v1/auth/mfa/webauthn/credentials/{credential_id}`
- `POST /api/v1/auth/mfa/webauthn/disable`

## Frontend Source of Truth

The production UI should treat `GET /api/v1/auth/security-settings/me` as the status contract for MFA state.

Relevant fields:
- `mfa_enabled`
- `mfa_methods`
- `primary_method`
- `method_status`
- `webauthn_credentials`
- `recovery_codes_remaining`

The live setup/removal UI is in [SecurityTab.jsx](/D:/VS%20CODE/CAPS_AI/frontend/src/components/auth/SecurityTab.jsx).
The live login-time MFA flow is in [LoginPage.jsx](/D:/VS%20CODE/CAPS_AI/frontend/src/pages/LoginPage.jsx) and [AuthContext.jsx](/D:/VS%20CODE/CAPS_AI/frontend/src/context/AuthContext.jsx).

## SMS MFA Configuration

Required settings for production SMS delivery:
- `SMS_MFA_ENABLED=true`
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_FROM_NUMBER` or `TWILIO_MESSAGING_SERVICE_SID`

Behavior notes:
- In non-production, missing Twilio configuration falls back to development-mode responses with `otp_dev`.
- In production, missing Twilio configuration returns a controlled `503` error with explicit detail.
- Enrollment and login challenge responses expose masked phone numbers plus resend/expiry metadata for UI display.

## WebAuthn Configuration

Required settings:
- `WEBAUTHN_RP_ID`
- `WEBAUTHN_RP_ORIGINS`
- `WEBAUTHN_RP_NAME`

Operational rules:
- `WEBAUTHN_RP_ID` must match the relying-party domain the browser considers valid.
- `WEBAUTHN_RP_ORIGINS` must be exact browser origins, comma-separated.
- Local development typically uses:
  - `WEBAUTHN_RP_ID=localhost`
  - `WEBAUTHN_RP_ORIGINS=http://localhost:5173`
- Production should use only public HTTPS origins for the deployed portal.
- Do not leave production origins blank; registration and login MFA will be rejected as incomplete configuration.

## Hardening Expectations

Production sign-off for SMS/WebAuthn assumes:
- pending MFA tokens expire and are bound to server-side pending state
- SMS resend windows and verification attempt caps are enforced
- WebAuthn challenges are expiry-bound and tied to the pending MFA session
- WebAuthn origins are validated against `WEBAUTHN_RP_ORIGINS`
- unknown credentials and invalid challenges fail with explicit errors
- sign counters are updated only when authentication verification succeeds
