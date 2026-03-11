# CAPS AI Security Audit

## Security Posture Summary
- Core controls exist (JWT auth, RBAC dependencies, rate limiting, security headers).
- Current posture is **moderate risk** due to dependency vulnerabilities, weak hash usage in one path, and operational hardening gaps.
- Risk grading basis: exploitability + blast radius + current controls.

## Findings (Risk Ranked)

| Risk | Finding | Evidence | Why It Matters | Recommendation |
|---|---|---|---|---|
| High | Known vulnerable backend dependencies | `backend/requirements.txt:5-6,12` and `python -m pip_audit -r backend/requirements.txt` output (python-jose, python-multipart, nltk, pdfminer-six, ecdsa) | Public CVEs include auth/library and parser attack surface | Upgrade to patched versions; add dependency audit gate in CI with fail threshold |
| High | Known vulnerable frontend dependencies | `frontend/package.json:16,22` and `npm audit --omit=dev --json` output (`axios`, `react-router-dom`) | XSS/open redirect/SSRF/DoS advisories affect client and API usage | Bump `axios` to `1.13.6+`, `react-router-dom` to `6.30.3+`; lockfile refresh and CI audit |
| High | SHA1 used for idempotency fingerprint | `backend/app/api/v1/endpoints/submissions.py:253` | SHA1 is deprecated for security-sensitive hashing; flagged by Bandit `B324` | Replace with SHA-256 (`hashlib.sha256(...)`) or BLAKE2; keep deterministic format |
| Medium | Open self-registration policy can create uncontrolled user growth | Default policy: `backend/app/core/config.py:74-75`; registration logic: `backend/app/domains/auth/service.py:83-104` | In production, permissive registration may allow account sprawl or abuse if not controlled by invite workflow | Use `bootstrap_strict` in production and enforce allowlist/invite/captcha |
| Medium | Trust of forwarded headers for login telemetry/fingerprints | `backend/app/api/v1/endpoints/auth.py:40-41,49-51`; normalization in `auth/service.py:42-46` | `x-forwarded-for` can be spoofed unless trusted proxy chain is enforced | Terminate at trusted proxy and sanitize headers there; persist both proxy IP and client IP |
| Medium | Rate-limit actor identity includes client-controlled headers | `backend/app/core/rate_limit.py:27-35` | Spoofed IP/user-agent can reduce limiter effectiveness under some deployments | Trust only proxy-injected headers from known upstream; optionally use signed edge headers |
| Medium | Broad exception swallowing can hide security-relevant failures | Examples: `backend/app/services/audit.py:76`, `backend/app/api/v1/endpoints/ai.py:62`, `backend/app/services/background_jobs.py:85` | Silent failures reduce detectability of attack attempts and operational anomalies | Log warning/error with context before fallback; avoid `except Exception: pass` in critical paths |
| Medium | Session tokens stored in browser session storage | `frontend/src/services/apiClient.js:9-13,25-41`; usage in `frontend/src/context/AuthContext.jsx:49-58` | Better than localStorage persistence, but still exposed to XSS if frontend is compromised | Tighten CSP, sanitize dynamic rendering paths, evaluate httpOnly cookie strategy |
| Low | Placeholder secret values in Kubernetes manifest | `k8s-secrets.yaml:8-12` | Real deployments can be insecure if placeholders are not replaced | Enforce secret scanning and deployment-time validation for non-placeholder values |
| Low | Overly broad CORS methods/headers with credentials | `backend/app/main.py:41-44` | Combined with misconfigured origins, this can widen browser attack surface | Keep strict explicit origin list; narrow methods/headers to actual usage |

## Positive Controls Observed
- Password hashing uses PBKDF2 with high iteration count and constant-time compare (`backend/app/core/security.py:21-47`).
- Access and refresh token typing enforced (`backend/app/core/security.py:97-115`).
- Token blacklist check in auth middleware (`backend/app/core/security.py:118-137`).
- Security headers middleware enabled (`backend/app/main.py:85-90`).
- Governance delete contract checker exists and currently passes (`scripts/check_backend_safety.py`, local run output: "Backend safety checks passed.").

## Authorization Review Highlights
- Route-level permission guards are broadly applied (`require_roles` / `require_permission`), e.g.:
  - `backend/app/api/v1/endpoints/classes.py:85,133,169,215`
  - `backend/app/api/v1/endpoints/users.py:23,32,77,186`
- Frontend mirrors role checks at routing level (`frontend/src/routes/ProtectedRoute.jsx:22-30`) but backend remains source of truth.

## Security Fix Priority
1. Patch vulnerable packages (backend + frontend).
2. Replace SHA1 with SHA256 in submissions idempotency key generation.
3. Harden production registration policy and onboarding controls.
4. Replace broad exception swallowing with audited, structured logging.
5. Enforce trusted proxy header policy for IP-sensitive controls.

