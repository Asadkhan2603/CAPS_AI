# code_recreate.md

This file contains critical CAPS_AI recreate code snapshots from the current repository state.
Generated on: 2026-03-03 (A33ia-CalcuPMa).

## Included Files
- PROJECT_RECREATE_GUIDE.md
- README.md
- docs/AZURE_AKS_MIGRATION.md
- docs/DEPLOYMENT_CHECKLIST.md
- docker-compose.yml
- k8s-namespace.yaml
- k8s-secrets.yaml
- k8s-secrets.azure.example.yaml
- k8s-configmap.yaml
- k8s-configmap.azure.yaml
- k8s-uploads-pvc.yaml
- k8s-uploads-pvc.azure.yaml
- k8s-redis.yaml
- k8s-redis.azure.yaml
- k8s-mongodb.yaml
- k8s-mongodb.azure.yaml
- k8s-backend.yaml
- k8s-backend.azure.yaml
- k8s-frontend.yaml
- k8s-frontend.azure.yaml
- k8s-ingress.yaml
- k8s-ingress.azure.yaml
- backend/.env.example
- backend/.env.production
- frontend/.env.example
- frontend/.env.production
- backend/app/main.py
- backend/app/services/scheduler.py
- backend/app/core/rate_limit.py
- backend/app/api/v1/endpoints/analytics.py
- frontend/nginx.conf
- frontend/src/services/apiClient.js
- frontend/src/context/ToastContext.jsx
- scripts/migrate_to_azure_aks.ps1
- scripts/seed_minimum_stack.ps1
- scripts/smoke_check_stack.ps1
- scripts/README.md
- backend/tests/test_health.py

## PROJECT_RECREATE_GUIDE.md
~~~markdown
# PROJECT_RECREATE_GUIDE (Master)

Status: authoritative recreate + validation guide for CAPS_AI.
Last updated: 2026-03-03 (Asia/Calcutta).

## 1. Master rule (mandatory)
Whenever any repository code/config/infra changes:
1. Update this file in the same commit.
2. Update `code_recreate.md` in the same commit.
3. Add a new entry in the change log section with:
   - date/time
   - changed files
   - reason
   - validation commands and results

If this rule is skipped, the recreate baseline is considered stale.

## 2. Current source of truth
- Local orchestration: `docker-compose.yml`
- Kubernetes manifests: `k8s-*.yaml` at repo root
- Backend health endpoint: `GET /health` from `backend/app/main.py`
- Frontend API base: `VITE_API_BASE_URL=/api/v1` (production), proxied by `frontend/nginx.conf`
- Scheduler behavior: singleton-safe leadership lock in `backend/app/services/scheduler.py`

## 3. Recreate after full Docker wipe (local)
From repo root:

```powershell
docker compose up -d --build
docker compose ps
```

Required checks:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
Invoke-WebRequest -UseBasicParsing http://localhost:5173
```

Expected:
- backend health `200` with `{"status":"ok"}`
- frontend root `200`
- mongodb/redis/backend/frontend containers `Up`

## 4. Auth smoke validation (local)
Create/login bootstrap admin:

```powershell
$register = @{
  full_name = "Local Admin"
  email = "admin.local@example.com"
  password = "Password123!"
  role = "admin"
} | ConvertTo-Json

Invoke-WebRequest -UseBasicParsing `
  -Uri "http://localhost:8000/api/v1/auth/register" `
  -Method POST -ContentType "application/json" -Body $register

$login = @{ email = "admin.local@example.com"; password = "Password123!" } | ConvertTo-Json
Invoke-WebRequest -UseBasicParsing `
  -Uri "http://localhost:8000/api/v1/auth/login" `
  -Method POST -ContentType "application/json" -Body $login
```

## 5. Kubernetes deploy + hard validation
Use a real context first:

```powershell
kubectl config get-contexts
kubectl config use-context <ctx>
kubectl cluster-info
```

Server-side validation:

```powershell
kubectl create namespace caps-ai --dry-run=client -o yaml | kubectl apply -f -
kubectl apply --dry-run=server -f k8s-secrets.yaml -f k8s-configmap.yaml -f k8s-uploads-pvc.yaml -f k8s-redis.yaml -f k8s-mongodb.yaml -f k8s-backend.yaml -f k8s-frontend.yaml -f k8s-ingress.yaml
```

Deploy:

```powershell
kubectl apply -f k8s-namespace.yaml -f k8s-secrets.yaml -f k8s-configmap.yaml -f k8s-uploads-pvc.yaml -f k8s-redis.yaml -f k8s-mongodb.yaml -f k8s-backend.yaml -f k8s-frontend.yaml -f k8s-ingress.yaml
kubectl -n caps-ai rollout status deployment/redis --timeout=300s
kubectl -n caps-ai rollout status statefulset/mongodb --timeout=300s
kubectl -n caps-ai rollout status deployment/backend --timeout=300s
kubectl -n caps-ai rollout status deployment/frontend --timeout=300s
kubectl -n caps-ai get pods,svc,ingress,pvc
```

## 6. AKS deployment path (Azure Student Premium)
Use Azure variants:
- `k8s-backend.azure.yaml`
- `k8s-frontend.azure.yaml`
- `k8s-redis.azure.yaml`
- `k8s-ingress.azure.yaml`
- `k8s-configmap.azure.yaml`
- `k8s-secrets.azure.example.yaml`
- `k8s-uploads-pvc.azure.yaml`
- `k8s-mongodb.azure.yaml`
- `scripts/migrate_to_azure_aks.ps1`

Prerequisites:
- AKS cluster is reachable via current `kubectl` context.
- AKS is attached to ACR (`az aks update --attach-acr ...`).
- `az`, `kubectl`, and `docker` are installed.

One-command migration:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/migrate_to_azure_aks.ps1 `
  -SubscriptionId "<SUBSCRIPTION_ID>" `
  -ResourceGroup "caps-ai-rg" `
  -AksName "caps-ai-aks" `
  -AcrName "<UNIQUE_ACR_NAME>" `
  -IngressHost "caps-ai.your-domain.com" `
  -JwtSecret "<AT_LEAST_64_CHAR_SECRET>" `
  -Location "centralindia"
```

Script behavior:
- optionally bootstraps RG + ACR + AKS and attaches ACR
- builds and pushes backend/frontend images to ACR
- renders manifests to `out/azure-manifests`
- validates via `kubectl apply --dry-run=client`
- applies manifests and runs rollout checks

Render-only mode (no apply):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/migrate_to_azure_aks.ps1 `
  -SubscriptionId "<SUBSCRIPTION_ID>" `
  -ResourceGroup "caps-ai-rg" `
  -AksName "caps-ai-aks" `
  -AcrName "<UNIQUE_ACR_NAME>" `
  -IngressHost "caps-ai.your-domain.com" `
  -JwtSecret "<AT_LEAST_64_CHAR_SECRET>" `
  -SkipApply
```

## 7. Kubernetes image strategy (critical)
For Docker Desktop local cluster, manifests must reference local compose image names:
- `caps_ai-backend:latest`
- `caps_ai-frontend:latest`
- `imagePullPolicy: IfNotPresent`

If pods show `ImagePullBackOff`:

```powershell
docker images | findstr caps_ai
kubectl -n caps-ai describe pod -l app=backend
kubectl -n caps-ai describe pod -l app=frontend
```

## 8. Architecture integrity invariants
1. Health probes must target `/health`, never permission-protected admin health routes.
2. Frontend API calls in production/K8s must resolve through `/api/v1` route.
3. Scheduler may run with backend replicas, but must enforce distributed lock leadership.
4. Upload path for backend pods must use PVC mount (`/app/uploads`) for durability.
5. Rate limiter must use Redis/Mongo backends in prod/staging; in-memory fallback is non-prod only.

## 9. Regression checks (must run before release)
Local:

```powershell
docker compose ps
```

Backend:

```powershell
cd backend
pytest -q
```

Frontend:

```powershell
cd frontend
npm run lint
npm test -- --run
npm run build
```

Seed + smoke scripts:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/seed_minimum_stack.ps1
powershell -ExecutionPolicy Bypass -File scripts/smoke_check_stack.ps1
```

K8s:

```powershell
kubectl -n caps-ai get deploy,statefulset,pods,svc,ingress,pvc
```

## 10. Known runtime note
`frontend/src/context/ToastContext.jsx` uses `crypto.randomUUID()` directly.
In non-secure execution contexts (certain browser automation runtimes), this can throw.
Local real browser on `http://localhost` generally works, but this is still a portability risk.

## 11. Master change log
### 2026-03-03
- Changed:
  - `k8s-backend.yaml`
  - `k8s-frontend.yaml`
- Reason:
  - Persisted Kubernetes local-image strategy to prevent `ImagePullBackOff` on Docker Desktop.
  - Set deployment images to `caps_ai-backend:latest` and `caps_ai-frontend:latest`.
- Validation:
  - `kubectl apply --dry-run=server -f k8s-backend.yaml -f k8s-frontend.yaml` passed.
  - `kubectl apply -f k8s-backend.yaml -f k8s-frontend.yaml` applied.
  - `kubectl -n caps-ai rollout status deployment/backend --timeout=300s` passed.
  - `kubectl -n caps-ai rollout status deployment/frontend --timeout=300s` passed.
  - `kubectl -n caps-ai get deploy backend frontend` -> ready replicas met desired.

### 2026-03-03 (AKS variants)
- Changed:
  - `k8s-backend.azure.yaml`
  - `k8s-frontend.azure.yaml`
  - `k8s-ingress.azure.yaml`
  - `PROJECT_RECREATE_GUIDE.md`
  - `code_recreate.md`
- Reason:
  - Added Azure-ready deployment variants with ACR and ingress host/TLS placeholders.
- Validation:
  - `kubectl apply --dry-run=client -f k8s-backend.azure.yaml -f k8s-frontend.azure.yaml -f k8s-ingress.azure.yaml` passed.

### 2026-03-03 (AKS complete migration package)
- Changed:
  - `k8s-configmap.azure.yaml`
  - `k8s-secrets.azure.example.yaml`
  - `k8s-uploads-pvc.azure.yaml`
  - `k8s-mongodb.azure.yaml`
  - `scripts/migrate_to_azure_aks.ps1`
  - `scripts/README.md`
  - `docs/AZURE_AKS_MIGRATION.md`
  - `docs/DEPLOYMENT_CHECKLIST.md`
  - `PROJECT_RECREATE_GUIDE.md`
  - `code_recreate.md`
- Reason:
  - Added end-to-end AKS migration automation and Azure-safe manifests for storage/config/secrets.
- Validation:
  - `kubectl apply --dry-run=client -f k8s-namespace.yaml -f k8s-secrets.azure.example.yaml -f k8s-configmap.azure.yaml -f k8s-uploads-pvc.azure.yaml -f k8s-redis.yaml -f k8s-mongodb.azure.yaml -f k8s-backend.azure.yaml -f k8s-frontend.azure.yaml -f k8s-ingress.azure.yaml` passed.
  - `powershell -NoProfile -Command "& { ./scripts/migrate_to_azure_aks.ps1 -? }"` passed (script parses).

### 2026-03-03 (AKS node-pool hardening + workload isolation)
- Changed:
  - `k8s-backend.azure.yaml`
  - `k8s-frontend.azure.yaml`
  - `k8s-mongodb.azure.yaml`
  - `k8s-redis.azure.yaml`
  - `scripts/migrate_to_azure_aks.ps1`
  - `docs/AZURE_AKS_MIGRATION.md`
  - `scripts/README.md`
  - `PROJECT_RECREATE_GUIDE.md`
  - `code_recreate.md`
- Reason:
  - Eliminated B-series usage for system node pools and removed single-pool topology risk by enforcing dedicated pools:
    - `syspool` (System, non-B, tainted `CriticalAddonsOnly=true:NoSchedule`)
    - `nodepool1` (User, app workloads)
  - Added Azure-specific Redis manifest and workload `nodeSelector: pool=user` in Azure manifests.
  - Updated migration script to enforce this topology by default (with override flags).
- Validation:
  - `az aks nodepool list -g caps-ai-rg-sea --cluster-name caps-ai-aks-sea -o table` -> `syspool`=`System` (`Standard_D2s_v3`, count=2), `nodepool1`=`User` (`Standard_B2s_v2`, count=1).
  - `kubectl get nodes -o custom-columns=NAME:.metadata.name,POOL:.metadata.labels.kubernetes\\.azure\\.com/agentpool,TAINTS:.spec.taints` -> syspool nodes tainted `CriticalAddonsOnly=true:NoSchedule`.
  - `kubectl -n caps-ai get pods -o wide` -> backend/frontend/redis/mongodb all `Running` on user pool node.
  - `curl -k https://20.197.115.29/health -H "Host: caps-ai.example.com"` -> `200`.

## 12. Code snapshot file
All critical recreate code/config snapshots are stored in:
- `code_recreate.md`
~~~

## README.md
~~~markdown
# CAPS AI

Enterprise academic governance and AI-assisted evaluation platform.

Master plan reference:
- `PROJECT_RECREATE_GUIDE.md` (authoritative master)
- `DOC'S/PROJECT_RECREATE_GUIDE.md` (pointer)

## Current Implementation Status

Completed backend phases (roadmap-aligned):
- Phase 1: Foundation setup, auth, RBAC, health APIs
- Phase 2: Academic core CRUD, role extensions, enrollment mapping
- Phase 3: Assignments, submissions, evaluation lock workflow
- Phase 4: AI suggestion pipeline and similarity engine
- Phase 5: Analytics, notices, clubs/events, registration constraints
- Phase 6 (in progress): hardening and release readiness

## Project Structure

- `backend/` FastAPI services, endpoints, schemas, models, tests
- `frontend/` React (Vite) SaaS dashboard frontend
- `DOC'S/` authoritative roadmap and planning documents
- `docs/` supplementary notes

## Prerequisites

- Python 3.11+
- Node.js 20+
- MongoDB on `mongodb://localhost:27017`

## Backend Run

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend URLs:
- API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

## Frontend Run

```bash
cd frontend
npm install
copy .env.example .env
npm run dev -- --host 0.0.0.0 --port 5173
```

Frontend URL:
- App: `http://localhost:5173`

## Test Commands

Use project virtualenv Python to avoid global-package conflicts:

```bash
cd backend
.venv\Scripts\python.exe -m pytest -q
```

Frontend quality checks:

```bash
cd frontend
npm run lint
npm run test:ci
npm run build
```

## Core API Domains

- Auth and users: `/api/v1/auth`, `/api/v1/users`
- Academic structure: `/courses`, `/years`, `/sections`, `/students`, `/subjects`
  - Legacy alias: `/classes` is supported for backward compatibility, but `/sections` is the canonical path for new integrations.
- Academic operations: `/assignments`, `/submissions`, `/evaluations`
- Intelligence: `/similarity`, AI submission evaluation via `/submissions/{id}/ai-evaluate`
- Institutional modules: `/analytics`, `/notices`, `/notifications`, `/clubs`, `/club-events`, `/event-registrations`
- Governance: `/audit-logs`, `/enrollments`

## Security Baseline

- JWT auth with role and extension-role checks
- PBKDF2-SHA256 password hashing
- File type and upload size validation
- CORS-configured local origins
- Security response headers (`X-Content-Type-Options`, `X-Frame-Options`, etc.)

## Azure AKS Deployment

- Migration guide: `docs/AZURE_AKS_MIGRATION.md`
- One-command AKS migration script: `scripts/migrate_to_azure_aks.ps1`
~~~

## docs/AZURE_AKS_MIGRATION.md
~~~markdown
# Azure AKS Migration Guide

This guide is the production path for deploying CAPS_AI to Azure using AKS + ACR.

## 1. Prerequisites

- Azure subscription with AKS/ACR quota (Student Premium is supported).
- Local tools installed:
  - `az`
  - `kubectl`
  - `docker`
- Domain name for ingress host (example: `caps-ai.your-domain.com`).
- TLS flow:
  - NGINX ingress controller installed in cluster.
  - `cert-manager` and `ClusterIssuer` available if using automatic TLS.

## 2. Azure manifests

Use these Azure-specific files:

- `k8s-backend.azure.yaml`
- `k8s-frontend.azure.yaml`
- `k8s-redis.azure.yaml`
- `k8s-ingress.azure.yaml`
- `k8s-configmap.azure.yaml`
- `k8s-secrets.azure.example.yaml`
- `k8s-uploads-pvc.azure.yaml`
- `k8s-mongodb.azure.yaml`

## 3. One-command migration

Run from repo root:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/migrate_to_azure_aks.ps1 `
  -SubscriptionId "<SUBSCRIPTION_ID>" `
  -ResourceGroup "caps-ai-rg" `
  -AksName "caps-ai-aks" `
  -AcrName "<UNIQUE_ACR_NAME>" `
  -IngressHost "caps-ai.your-domain.com" `
  -JwtSecret "<AT_LEAST_64_CHAR_SECRET>" `
  -Location "centralindia"
```

What the script does:

1. Logs into Azure if needed.
2. Ensures resource group, ACR, AKS (unless `-SkipInfrastructure`).
3. Ensures production node-pool topology (unless `-SkipPoolHardening`):
   - dedicated `System` pool (default: `syspool`, non-B SKU, tainted `CriticalAddonsOnly=true:NoSchedule`)
   - dedicated `User` pool (default: `nodepool1`) for app workloads.
4. Attaches ACR to AKS.
5. Builds and pushes backend/frontend images.
6. Renders manifests into `out/azure-manifests`.
7. Validates manifests (`--dry-run=client`).
8. Applies manifests and waits for rollouts (unless `-SkipApply`).

## 4. Useful flags

- `-SkipInfrastructure`: AKS/ACR already created.
- `-SkipPoolHardening`: skip system/user node-pool enforcement.
- `-SkipBuildPush`: use existing images in ACR with selected `-ImageTag`.
- `-SkipApply`: render only; do not deploy.
- `-ImageTag "v1"`: explicit tag instead of timestamp.
- `-TlsSecretName "caps-ai-tls"` and `-ClusterIssuer "letsencrypt-prod"` to control TLS names.
- `-IngressClassName "nginx"` if using a specific ingress class.
- `-SystemPoolName/-SystemPoolVmSize/-SystemPoolCount` to tune dedicated system pool.
- `-UserPoolName/-UserPoolVmSize/-UserPoolCount` to tune dedicated user pool.

## 5. DNS and ingress

After deploy, resolve ingress endpoint:

```powershell
kubectl -n caps-ai get ingress caps-ai-ingress
```

Point your DNS A/CNAME record for `IngressHost` to the reported ingress endpoint.

## 6. Post-deploy validation

```powershell
kubectl -n caps-ai get deploy,statefulset,pods,svc,ingress,pvc
kubectl -n caps-ai rollout status deployment/backend --timeout=300s
kubectl -n caps-ai rollout status deployment/frontend --timeout=300s
```

Then test:

- `https://<IngressHost>/health` should return backend health via ingress pathing checks.
- Frontend login flow should reach `/api/v1/auth/login`.

## 7. Security notes

- Do not commit real secrets into `k8s-secrets.azure.example.yaml`.
- Use Azure Key Vault + CSI driver for long-term secret management.
- Rotate `JWT_SECRET` and cloud provider keys if exposed.
- For strict production HA (3+ system nodes), request higher quota if your subscription limits prevent that topology.
~~~

## docs/DEPLOYMENT_CHECKLIST.md
~~~markdown
# CAPS AI Deployment Checklist

## 1. Environment

- Set backend `.env` values:
  - `MONGODB_URL`
  - `MONGODB_DB`
  - `JWT_SECRET` (non-default)
  - `ACCESS_TOKEN_EXPIRE_MINUTES`
  - `OPENAI_API_KEY` (if AI provider enabled)
  - `CORS_ORIGINS` (production frontend origins)

## 2. Backend Validation

- Install dependencies in virtualenv.
- Run tests:
  - `.venv\Scripts\python.exe -m pytest -q`
- Verify startup:
  - `GET /health` returns `{"status":"ok"}`
- Verify docs:
  - `/docs` loads.

## 3. Frontend Validation

- Set `VITE_API_BASE_URL` to deployed backend URL.
- Run production build:
  - `npm run build`
- Smoke test login and dashboard routes.

## 4. Security Checks

- Confirm strong JWT secret is configured.
- Confirm CORS allows only intended origins.
- Confirm security response headers exist on API responses.
- Confirm role-based access checks with admin/teacher/student test users.

## 5. Operational Smoke Tests

- Auth bootstrap flow:
  - Register first admin (bootstrap only) -> login -> me
- Auth provisioning flow (required after bootstrap):
  - Login as admin -> create teacher/student via `/api/v1/users` -> login as created user -> me
- Auth closure validation:
  - Attempt `/api/v1/auth/register` for any role after first admin exists -> expect `403`
- Assignment lifecycle: create/open/close
- Submission upload and AI evaluate
- Similarity run and flagged notification path
- Evaluation finalize and admin override path
- Notice publishing and expiry behavior
- Club event registration duplicate/capacity rules

## 6. Release Notes

- Record commit hash for deployed version.
- Record DB backup/snapshot reference.
- Record known warnings and mitigations.

## 7. Azure AKS Checklist

- Confirm `az`, `kubectl`, `docker` are installed.
- Run AKS migration script:
  - `powershell -ExecutionPolicy Bypass -File scripts/migrate_to_azure_aks.ps1 ...`
- Verify rendered manifests in `out/azure-manifests`.
- Verify ACR image tags match deployed backend/frontend image refs.
- Verify ingress DNS points to AKS load balancer endpoint.
~~~

## docker-compose.yml
~~~yaml
services:
  mongodb:
    image: mongo:7
    container_name: caps-ai-mongodb
    restart: unless-stopped
    ports:
      - "27017:27017"
    volumes:
      - mongo_data:/data/db

  redis:
    image: redis:7-alpine
    container_name: caps-ai-redis
    restart: unless-stopped
    ports:
      - "6379:6379"

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: caps-ai-backend
    restart: unless-stopped
    env_file:
      - ./backend/.env.production
    depends_on:
      - mongodb
      - redis
    ports:
      - "8000:8000"
    volumes:
      - ./uploads:/app/uploads

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: caps-ai-frontend
    restart: unless-stopped
    depends_on:
      - backend
    ports:
      - "5173:80"

volumes:
  mongo_data:
~~~

## k8s-namespace.yaml
~~~yaml
apiVersion: v1
kind: Namespace
metadata:
  name: caps-ai
  labels:
    app: caps-ai
~~~

## k8s-secrets.yaml
~~~yaml
apiVersion: v1
kind: Secret
metadata:
  name: backend-secrets
  namespace: caps-ai
type: Opaque
stringData:
  JWT_SECRET: "CHANGE_ME_WITH_A_LONG_RANDOM_SECRET_AT_LEAST_64_CHARS"
  OPENAI_API_KEY: ""
  CLOUDINARY_CLOUD_NAME: ""
  CLOUDINARY_API_KEY: ""
  CLOUDINARY_API_SECRET: ""
~~~

## k8s-secrets.azure.example.yaml
~~~yaml
apiVersion: v1
kind: Secret
metadata:
  name: backend-secrets
  namespace: caps-ai
type: Opaque
stringData:
  JWT_SECRET: "__JWT_SECRET__"
  OPENAI_API_KEY: "__OPENAI_API_KEY__"
  CLOUDINARY_CLOUD_NAME: "__CLOUDINARY_CLOUD_NAME__"
  CLOUDINARY_API_KEY: "__CLOUDINARY_API_KEY__"
  CLOUDINARY_API_SECRET: "__CLOUDINARY_API_SECRET__"
~~~

## k8s-configmap.yaml
~~~yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: caps-ai
data:
  ENVIRONMENT: "production"
  APP_NAME: "CAPS AI API"
  APP_VERSION: "1.0.0"
  API_PREFIX: "/api/v1"
  MONGODB_URL: "mongodb://mongodb:27017"
  MONGODB_DB: "caps_ai"
  JWT_ALGORITHM: "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES: "15"
  REFRESH_TOKEN_EXPIRE_DAYS: "7"
  ACCOUNT_LOCKOUT_MAX_ATTEMPTS: "5"
  ACCOUNT_LOCKOUT_WINDOW_MINUTES: "15"
  ACCOUNT_LOCKOUT_DURATION_MINUTES: "30"
  AUTH_REGISTRATION_POLICY: "bootstrap_strict"
  OPENAI_MODEL: "gpt-4o-mini"
  OPENAI_TIMEOUT_SECONDS: "20"
  OPENAI_MAX_OUTPUT_TOKENS: "400"
  SIMILARITY_THRESHOLD: "0.8"
  RATE_LIMIT_MAX_REQUESTS: "100"
  RATE_LIMIT_WINDOW_SECONDS: "60"
  RESPONSE_ENVELOPE_ENABLED: "true"
  REDIS_ENABLED: "true"
  REDIS_URL: "redis://redis:6379/0"
  ANALYTICS_CACHE_TTL_SECONDS: "300"
  SCHEDULER_ENABLED: "true"
  SCHEDULER_LOCK_ID: "caps_ai_scheduler_primary"
  SCHEDULER_LOCK_TTL_SECONDS: "90"
  SCHEDULER_LOCK_RENEW_SECONDS: "20"
  SCHEDULED_NOTICE_POLL_SECONDS: "60"
  ANALYTICS_SNAPSHOT_HOUR_UTC: "0"
  ANALYTICS_SNAPSHOT_MINUTE_UTC: "15"
  CORS_ORIGINS: "https://caps-ai.example.com,http://localhost:5173,http://127.0.0.1:5173"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: frontend-config
  namespace: caps-ai
data:
  VITE_API_BASE_URL: "/api/v1"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
  namespace: caps-ai
data:
  nginx.conf: |
    upstream api {
      server backend:8000;
    }

    server {
      listen 80;
      server_name _;
      client_max_body_size 50M;

      root /usr/share/nginx/html;
      index index.html index.htm;

      location /api/v1 {
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
      }

      location / {
        try_files $uri $uri/ /index.html;
      }

      error_page 404 /index.html;
    }
~~~

## k8s-configmap.azure.yaml
~~~yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: backend-config
  namespace: caps-ai
data:
  ENVIRONMENT: "production"
  APP_NAME: "CAPS AI API"
  APP_VERSION: "1.0.0"
  API_PREFIX: "/api/v1"
  MONGODB_URL: "mongodb://mongodb:27017"
  MONGODB_DB: "caps_ai"
  JWT_ALGORITHM: "HS256"
  ACCESS_TOKEN_EXPIRE_MINUTES: "15"
  REFRESH_TOKEN_EXPIRE_DAYS: "7"
  ACCOUNT_LOCKOUT_MAX_ATTEMPTS: "5"
  ACCOUNT_LOCKOUT_WINDOW_MINUTES: "15"
  ACCOUNT_LOCKOUT_DURATION_MINUTES: "30"
  AUTH_REGISTRATION_POLICY: "bootstrap_strict"
  OPENAI_MODEL: "gpt-4o-mini"
  OPENAI_TIMEOUT_SECONDS: "20"
  OPENAI_MAX_OUTPUT_TOKENS: "400"
  SIMILARITY_THRESHOLD: "0.8"
  RATE_LIMIT_MAX_REQUESTS: "100"
  RATE_LIMIT_WINDOW_SECONDS: "60"
  RESPONSE_ENVELOPE_ENABLED: "true"
  REDIS_ENABLED: "true"
  REDIS_URL: "redis://redis:6379/0"
  ANALYTICS_CACHE_TTL_SECONDS: "300"
  SCHEDULER_ENABLED: "true"
  SCHEDULER_LOCK_ID: "caps_ai_scheduler_primary"
  SCHEDULER_LOCK_TTL_SECONDS: "90"
  SCHEDULER_LOCK_RENEW_SECONDS: "20"
  SCHEDULED_NOTICE_POLL_SECONDS: "60"
  ANALYTICS_SNAPSHOT_HOUR_UTC: "0"
  ANALYTICS_SNAPSHOT_MINUTE_UTC: "15"
  CORS_ORIGINS: "https://caps-ai.example.com,http://localhost:5173,http://127.0.0.1:5173"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: frontend-config
  namespace: caps-ai
data:
  VITE_API_BASE_URL: "/api/v1"
---
apiVersion: v1
kind: ConfigMap
metadata:
  name: nginx-config
  namespace: caps-ai
data:
  nginx.conf: |
    upstream api {
      server backend:8000;
    }

    server {
      listen 80;
      server_name _;
      client_max_body_size 50M;

      root /usr/share/nginx/html;
      index index.html index.htm;

      location /api/v1 {
        proxy_pass http://api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
      }

      location / {
        try_files $uri $uri/ /index.html;
      }

      error_page 404 /index.html;
    }
~~~

## k8s-uploads-pvc.yaml
~~~yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: backend-uploads
  namespace: caps-ai
spec:
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 20Gi
~~~

## k8s-uploads-pvc.azure.yaml
~~~yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: backend-uploads
  namespace: caps-ai
spec:
  storageClassName: azurefile-csi
  accessModes:
    - ReadWriteMany
  resources:
    requests:
      storage: 20Gi
~~~

## k8s-redis.yaml
~~~yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: caps-ai
  labels:
    app: redis
spec:
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
      name: redis
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: caps-ai
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          ports:
            - containerPort: 6379
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "250m"
          livenessProbe:
            tcpSocket:
              port: 6379
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            tcpSocket:
              port: 6379
            initialDelaySeconds: 5
            periodSeconds: 5
~~~

## k8s-redis.azure.yaml
~~~yaml
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: caps-ai
  labels:
    app: redis
spec:
  selector:
    app: redis
  ports:
    - port: 6379
      targetPort: 6379
      name: redis
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
  namespace: caps-ai
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      nodeSelector:
        pool: user
      containers:
        - name: redis
          image: redis:7-alpine
          ports:
            - containerPort: 6379
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "250m"
          livenessProbe:
            tcpSocket:
              port: 6379
            initialDelaySeconds: 10
            periodSeconds: 10
          readinessProbe:
            tcpSocket:
              port: 6379
            initialDelaySeconds: 5
            periodSeconds: 5
~~~

## k8s-mongodb.yaml
~~~yaml
apiVersion: v1
kind: Service
metadata:
  name: mongodb
  namespace: caps-ai
  labels:
    app: mongodb
spec:
  selector:
    app: mongodb
  ports:
    - port: 27017
      targetPort: 27017
      name: mongodb
  clusterIP: None
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mongodb
  namespace: caps-ai
spec:
  serviceName: mongodb
  replicas: 1
  selector:
    matchLabels:
      app: mongodb
  template:
    metadata:
      labels:
        app: mongodb
    spec:
      containers:
        - name: mongodb
          image: mongo:7
          ports:
            - containerPort: 27017
              name: mongodb
          volumeMounts:
            - name: data
              mountPath: /data/db
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "500m"
          livenessProbe:
            tcpSocket:
              port: 27017
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            tcpSocket:
              port: 27017
            initialDelaySeconds: 5
            periodSeconds: 5
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
~~~

## k8s-mongodb.azure.yaml
~~~yaml
apiVersion: v1
kind: Service
metadata:
  name: mongodb
  namespace: caps-ai
  labels:
    app: mongodb
spec:
  selector:
    app: mongodb
  ports:
    - port: 27017
      targetPort: 27017
      name: mongodb
  clusterIP: None
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: mongodb
  namespace: caps-ai
spec:
  serviceName: mongodb
  replicas: 1
  selector:
    matchLabels:
      app: mongodb
  template:
    metadata:
      labels:
        app: mongodb
    spec:
      nodeSelector:
        pool: user
      containers:
        - name: mongodb
          image: mongo:7
          ports:
            - containerPort: 27017
              name: mongodb
          volumeMounts:
            - name: data
              mountPath: /data/db
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "500m"
          livenessProbe:
            tcpSocket:
              port: 27017
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            tcpSocket:
              port: 27017
            initialDelaySeconds: 5
            periodSeconds: 5
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        storageClassName: managed-csi
        accessModes: ["ReadWriteOnce"]
        resources:
          requests:
            storage: 10Gi
~~~

## k8s-backend.yaml
~~~yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: caps-ai
  labels:
    app: backend
spec:
  selector:
    app: backend
  type: ClusterIP
  ports:
    - port: 8000
      targetPort: 8000
      protocol: TCP
      name: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: caps-ai
spec:
  replicas: 2
  selector:
    matchLabels:
      app: backend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: backend
    spec:
      containers:
        - name: backend
          image: caps_ai-backend:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
              name: http
          envFrom:
            - configMapRef:
                name: backend-config
            - secretRef:
                name: backend-secrets
          volumeMounts:
            - name: uploads
              mountPath: /app/uploads
          resources:
            requests:
              memory: "512Mi"
              cpu: "250m"
            limits:
              memory: "1Gi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 2
      volumes:
        - name: uploads
          persistentVolumeClaim:
            claimName: backend-uploads
      initContainers:
        - name: wait-for-mongodb
          image: busybox:latest
          command: ['sh', '-c', 'until nc -z mongodb 27017; do echo waiting for mongodb; sleep 2; done;']
        - name: wait-for-redis
          image: busybox:latest
          command: ['sh', '-c', 'until nc -z redis 6379; do echo waiting for redis; sleep 2; done;']
~~~

## k8s-backend.azure.yaml
~~~yaml
apiVersion: v1
kind: Service
metadata:
  name: backend
  namespace: caps-ai
  labels:
    app: backend
spec:
  selector:
    app: backend
  type: ClusterIP
  ports:
    - port: 8000
      targetPort: 8000
      protocol: TCP
      name: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: caps-ai
spec:
  replicas: 1
  selector:
    matchLabels:
      app: backend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: backend
    spec:
      nodeSelector:
        pool: user
      containers:
        - name: backend
          image: capsai91890.azurecr.io/caps-ai-backend:bx-20260303
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
              name: http
          envFrom:
            - configMapRef:
                name: backend-config
            - secretRef:
                name: backend-secrets
          volumeMounts:
            - name: uploads
              mountPath: /app/uploads
          resources:
            requests:
              memory: "384Mi"
              cpu: "100m"
            limits:
              memory: "1Gi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 2
      volumes:
        - name: uploads
          persistentVolumeClaim:
            claimName: backend-uploads
      initContainers:
        - name: wait-for-mongodb
          image: busybox:latest
          command: ["sh", "-c", "until nc -z mongodb 27017; do echo waiting for mongodb; sleep 2; done;"]
        - name: wait-for-redis
          image: busybox:latest
          command: ["sh", "-c", "until nc -z redis 6379; do echo waiting for redis; sleep 2; done;"]
~~~

## k8s-frontend.yaml
~~~yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: caps-ai
  labels:
    app: frontend
spec:
  selector:
    app: frontend
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 80
      protocol: TCP
      name: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: caps-ai
spec:
  replicas: 2
  selector:
    matchLabels:
      app: frontend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: frontend
    spec:
      containers:
        - name: frontend
          image: caps_ai-frontend:latest
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 80
              name: http
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "250m"
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 2
~~~

## k8s-frontend.azure.yaml
~~~yaml
apiVersion: v1
kind: Service
metadata:
  name: frontend
  namespace: caps-ai
  labels:
    app: frontend
spec:
  selector:
    app: frontend
  type: ClusterIP
  ports:
    - port: 80
      targetPort: 80
      protocol: TCP
      name: http
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: frontend
  namespace: caps-ai
spec:
  replicas: 1
  selector:
    matchLabels:
      app: frontend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: frontend
    spec:
      nodeSelector:
        pool: user
      containers:
        - name: frontend
          image: YOUR_ACR_LOGIN_SERVER.azurecr.io/caps-ai-frontend:v1
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 80
              name: http
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "250m"
          livenessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /
              port: 80
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 2
~~~

## k8s-ingress.yaml
~~~yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: caps-ai-ingress
  namespace: caps-ai
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
    - hosts:
        - caps-ai.example.com
      secretName: caps-ai-tls
  rules:
    - host: caps-ai.example.com
      http:
        paths:
          - path: /api/v1
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
~~~

## k8s-ingress.azure.yaml
~~~yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: caps-ai-ingress
  namespace: caps-ai
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - caps-ai.example.com
      secretName: caps-ai-tls
  rules:
    - host: caps-ai.example.com
      http:
        paths:
          - path: /health
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8000
          - path: /api/v1
            pathType: Prefix
            backend:
              service:
                name: backend
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: frontend
                port:
                  number: 80
~~~

## backend/.env.example
~~~
ENVIRONMENT=development
MONGODB_URL=mongodb://localhost:27017
MONGODB_DB=caps_ai
JWT_SECRET=replace_with_a_long_random_secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
ACCOUNT_LOCKOUT_MAX_ATTEMPTS=5
ACCOUNT_LOCKOUT_WINDOW_MINUTES=15
ACCOUNT_LOCKOUT_DURATION_MINUTES=30
AUTH_REGISTRATION_POLICY=single_admin_open
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=20
OPENAI_MAX_OUTPUT_TOKENS=400
SIMILARITY_THRESHOLD=0.8
RATE_LIMIT_MAX_REQUESTS=120
RATE_LIMIT_WINDOW_SECONDS=60
RESPONSE_ENVELOPE_ENABLED=false
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379/0
ANALYTICS_CACHE_TTL_SECONDS=120
SCHEDULER_ENABLED=false
SCHEDULER_LOCK_ID=caps_ai_scheduler_primary
SCHEDULER_LOCK_TTL_SECONDS=90
SCHEDULER_LOCK_RENEW_SECONDS=20
SCHEDULED_NOTICE_POLL_SECONDS=60
ANALYTICS_SNAPSHOT_HOUR_UTC=0
ANALYTICS_SNAPSHOT_MINUTE_UTC=15
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_cloudinary_api_key
CLOUDINARY_API_SECRET=your_cloudinary_api_secret
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://192.168.2.70:5173
~~~

## backend/.env.production
~~~
ENVIRONMENT=production
APP_NAME=CAPS AI API
APP_VERSION=1.0.0
API_PREFIX=/api/v1

MONGODB_URL=mongodb://mongodb:27017
MONGODB_DB=caps_ai

JWT_SECRET=CHANGE_ME_WITH_A_LONG_RANDOM_SECRET_AT_LEAST_64_CHARS
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

ACCOUNT_LOCKOUT_MAX_ATTEMPTS=5
ACCOUNT_LOCKOUT_WINDOW_MINUTES=15
ACCOUNT_LOCKOUT_DURATION_MINUTES=30
AUTH_REGISTRATION_POLICY=bootstrap_strict

OPENAI_API_KEY=
OPENAI_MODEL=gpt-4o-mini
OPENAI_TIMEOUT_SECONDS=20
OPENAI_MAX_OUTPUT_TOKENS=400

SIMILARITY_THRESHOLD=0.8
RATE_LIMIT_MAX_REQUESTS=100
RATE_LIMIT_WINDOW_SECONDS=60
RESPONSE_ENVELOPE_ENABLED=true
REDIS_ENABLED=true
REDIS_URL=redis://redis:6379/0
ANALYTICS_CACHE_TTL_SECONDS=300
SCHEDULER_ENABLED=true
SCHEDULER_LOCK_ID=caps_ai_scheduler_primary
SCHEDULER_LOCK_TTL_SECONDS=90
SCHEDULER_LOCK_RENEW_SECONDS=20
SCHEDULED_NOTICE_POLL_SECONDS=60
ANALYTICS_SNAPSHOT_HOUR_UTC=0
ANALYTICS_SNAPSHOT_MINUTE_UTC=15

CLOUDINARY_CLOUD_NAME=
CLOUDINARY_API_KEY=
CLOUDINARY_API_SECRET=

CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
~~~

## frontend/.env.example
~~~
VITE_API_BASE_URL=http://localhost:8000/api/v1
~~~

## frontend/.env.production
~~~
VITE_API_BASE_URL=/api/v1
~~~

## backend/app/main.py
~~~python
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from uuid import uuid4
import logging
import time

from app.api.v1.router import api_router

from app.core.config import settings
from app.core.indexes import ensure_indexes
from app.core.observability import (
    new_error_id,
    request_id_ctx,
    setup_logging,
    trace_id_ctx,
)
from app.core.rate_limit import RateLimitMiddleware
from app.core.response import error_envelope, is_enveloped_payload, success_envelope
from app.services.scheduler import app_scheduler

setup_logging(settings.log_level)
logger = logging.getLogger("caps_api")

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.rate_limit_max_requests,
    window_seconds=settings.rate_limit_window_seconds,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        trace_id = request.headers.get("x-trace-id") or str(uuid4())
        request_id_token = request_id_ctx.set(request_id)
        trace_id_token = trace_id_ctx.set(trace_id)
        started = time.perf_counter()
        logger.info(
            {
                "event": "request.start",
                "request_id": request_id,
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query or ""),
                "client_ip": request.client.host if request.client else None,
            }
        )
        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.exception(
                {
                    "event": "request.unhandled_exception",
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                }
            )
            raise
        duration_ms = int((time.perf_counter() - started) * 1000)

        response.headers["X-Request-Id"] = request_id
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        logger.info(
            {
                "event": "request.end",
                "request_id": request_id,
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )
        request_id_ctx.reset(request_id_token)
        trace_id_ctx.reset(trace_id_token)
        return response


app.add_middleware(SecurityHeadersMiddleware)


class ResponseEnvelopeMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        headers = {k: v for k, v in dict(response.headers).items() if k.lower() != "content-length"}
        if (
            not settings.response_envelope_enabled
            or request.url.path in {"/health", "/"}
            or not request.url.path.startswith(settings.api_prefix)
            or response.status_code >= 400
            or "application/json" not in (response.headers.get("content-type") or "")
        ):
            return response

        body = b""
        async for chunk in response.body_iterator:
            body += chunk

        if not body:
            payload = success_envelope(data=None, trace_id=trace_id_ctx.get() or None)
        else:
            try:
                import json

                decoded = json.loads(body.decode("utf-8"))
                if is_enveloped_payload(decoded):
                    return JSONResponse(status_code=response.status_code, content=decoded, headers=headers)
                payload = success_envelope(data=decoded, trace_id=trace_id_ctx.get() or None)
            except Exception:
                return JSONResponse(
                    status_code=response.status_code,
                    content=success_envelope(data={"raw": body.decode("utf-8", errors="replace")}, trace_id=trace_id_ctx.get() or None),
                    headers=headers,
                )
        return JSONResponse(status_code=response.status_code, content=payload, headers=headers)


app.add_middleware(ResponseEnvelopeMiddleware)

app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
async def startup_tasks() -> None:
    await ensure_indexes()
    await app_scheduler.start()


@app.on_event("shutdown")
async def shutdown_tasks() -> None:
    await app_scheduler.stop()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    error_id = new_error_id()
    logger.warning(
        {
            "event": "http.error",
            "error_id": error_id,
            "request_id": request_id_ctx.get() or None,
            "trace_id": trace_id_ctx.get() or None,
            "status_code": exc.status_code,
            "method": request.method,
            "path": request.url.path,
            "detail": exc.detail,
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_envelope(
            message=str(exc.detail) if isinstance(exc.detail, str) else "HTTP error",
            trace_id=trace_id_ctx.get() or None,
            error_id=error_id,
            detail=exc.detail,
        ),
        headers={"X-Error-Id": error_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    error_id = new_error_id()
    logger.warning(
        {
            "event": "http.validation_error",
            "error_id": error_id,
            "request_id": request_id_ctx.get() or None,
            "trace_id": trace_id_ctx.get() or None,
            "status_code": 422,
            "method": request.method,
            "path": request.url.path,
            "detail": exc.errors(),
        }
    )
    return JSONResponse(
        status_code=422,
        content=error_envelope(
            message="Validation failed",
            trace_id=trace_id_ctx.get() or None,
            error_id=error_id,
            detail=exc.errors(),
        ),
        headers={"X-Error-Id": error_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    error_id = new_error_id()
    logger.exception(
        {
            "event": "http.unhandled_error",
            "error_id": error_id,
            "request_id": request_id_ctx.get() or None,
            "trace_id": trace_id_ctx.get() or None,
            "status_code": 500,
            "method": request.method,
            "path": request.url.path,
        }
    )
    return JSONResponse(
        status_code=500,
        content=error_envelope(
            message="Internal server error",
            trace_id=trace_id_ctx.get() or None,
            error_id=error_id,
            detail="Internal server error",
        ),
        headers={"X-Error-Id": error_id},
    )


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict:
    return {"message": "CAPS AI API is running"}
~~~

## backend/app/services/scheduler.py
~~~python
from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.core.config import settings
from app.core.database import db
from app.services.background_jobs import (
    dispatch_scheduled_notice_notifications,
    run_daily_analytics_snapshot_job,
)

logger = logging.getLogger("caps_scheduler")


def _next_daily_run_utc(*, hour: int, minute: int) -> datetime:
    now = datetime.now(timezone.utc)
    candidate = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if candidate <= now:
        candidate = candidate + timedelta(days=1)
    return candidate


class AppScheduler:
    def __init__(self) -> None:
        self._enabled = settings.scheduler_enabled
        self._instance_id = (os.getenv("HOSTNAME") or "").strip() or f"scheduler-{os.getpid()}"
        self._lock_id = (settings.scheduler_lock_id or "caps_ai_scheduler_primary").strip()
        self._lock_ttl_seconds = max(30, settings.scheduler_lock_ttl_seconds)
        self._lock_renew_seconds = max(
            5,
            min(settings.scheduler_lock_renew_seconds, max(5, self._lock_ttl_seconds // 2)),
        )
        self._running = False
        self._is_leader = False
        self._leader_task: asyncio.Task[Any] | None = None
        self._job_tasks: list[asyncio.Task[Any]] = []
        self._last_notice_dispatch_at: datetime | None = None
        self._last_snapshot_at: datetime | None = None
        self._last_notice_dispatch_count = 0

    async def start(self) -> None:
        if not self._enabled or self._running:
            return
        self._running = True
        self._leader_task = asyncio.create_task(self._leader_election_loop(), name="scheduler-leader-loop")
        logger.info(
            {
                "event": "scheduler.started",
                "instance_id": self._instance_id,
                "lock_id": self._lock_id,
                "lock_ttl_seconds": self._lock_ttl_seconds,
                "lock_renew_seconds": self._lock_renew_seconds,
                "scheduled_notice_poll_seconds": settings.scheduled_notice_poll_seconds,
                "snapshot_hour_utc": settings.analytics_snapshot_hour_utc,
                "snapshot_minute_utc": settings.analytics_snapshot_minute_utc,
            }
        )

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._leader_task is not None:
            self._leader_task.cancel()
            await asyncio.gather(self._leader_task, return_exceptions=True)
            self._leader_task = None
        await self._stop_job_tasks()
        await self._release_leader_lock()
        self._is_leader = False
        logger.info({"event": "scheduler.stopped"})

    def status(self) -> dict[str, Any]:
        return {
            "enabled": self._enabled,
            "running": self._running,
            "is_leader": self._is_leader,
            "instance_id": self._instance_id,
            "lock_id": self._lock_id,
            "lock_ttl_seconds": self._lock_ttl_seconds,
            "lock_renew_seconds": self._lock_renew_seconds,
            "scheduled_notice_poll_seconds": settings.scheduled_notice_poll_seconds,
            "snapshot_time_utc": f"{settings.analytics_snapshot_hour_utc:02d}:{settings.analytics_snapshot_minute_utc:02d}",
            "last_notice_dispatch_at": self._last_notice_dispatch_at,
            "last_notice_dispatch_count": self._last_notice_dispatch_count,
            "last_snapshot_at": self._last_snapshot_at,
        }

    async def _leader_election_loop(self) -> None:
        while self._running:
            is_leader = False
            try:
                is_leader = await self._try_acquire_or_renew_leadership()
            except asyncio.CancelledError:  # pragma: no cover - cancellation path
                raise
            except Exception:
                logger.exception(
                    {
                        "event": "scheduler.leader_election.error",
                        "instance_id": self._instance_id,
                    }
                )

            if is_leader and not self._is_leader:
                self._is_leader = True
                await self._start_job_tasks()
                logger.info(
                    {
                        "event": "scheduler.leader_acquired",
                        "instance_id": self._instance_id,
                        "lock_id": self._lock_id,
                    }
                )
            elif not is_leader and self._is_leader:
                self._is_leader = False
                await self._stop_job_tasks()
                logger.warning(
                    {
                        "event": "scheduler.leader_lost",
                        "instance_id": self._instance_id,
                        "lock_id": self._lock_id,
                    }
                )

            await asyncio.sleep(self._lock_renew_seconds)

    async def _start_job_tasks(self) -> None:
        if self._job_tasks:
            return
        self._job_tasks = [
            asyncio.create_task(self._scheduled_notice_loop(), name="scheduled-notice-loop"),
            asyncio.create_task(self._daily_snapshot_loop(), name="daily-snapshot-loop"),
        ]
        logger.info({"event": "scheduler.jobs_started", "instance_id": self._instance_id})

    async def _stop_job_tasks(self) -> None:
        if not self._job_tasks:
            return
        for task in self._job_tasks:
            task.cancel()
        await asyncio.gather(*self._job_tasks, return_exceptions=True)
        self._job_tasks.clear()
        logger.info({"event": "scheduler.jobs_stopped", "instance_id": self._instance_id})

    async def _try_acquire_or_renew_leadership(self) -> bool:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=self._lock_ttl_seconds)
        lock_collection = db.scheduler_locks

        doc = await lock_collection.find_one_and_update(
            {
                "_id": self._lock_id,
                "$or": [
                    {"owner_id": self._instance_id},
                    {"expires_at": {"$lte": now}},
                ],
            },
            {
                "$set": {
                    "owner_id": self._instance_id,
                    "expires_at": expires_at,
                    "heartbeat_at": now,
                }
            },
            return_document=ReturnDocument.AFTER,
        )
        if doc and doc.get("owner_id") == self._instance_id:
            return True

        try:
            await lock_collection.insert_one(
                {
                    "_id": self._lock_id,
                    "owner_id": self._instance_id,
                    "expires_at": expires_at,
                    "heartbeat_at": now,
                    "created_at": now,
                }
            )
            return True
        except DuplicateKeyError:
            return False

    async def _release_leader_lock(self) -> None:
        try:
            await db.scheduler_locks.delete_one({"_id": self._lock_id, "owner_id": self._instance_id})
        except Exception:
            logger.exception(
                {
                    "event": "scheduler.release_lock.error",
                    "instance_id": self._instance_id,
                    "lock_id": self._lock_id,
                }
            )

    async def _scheduled_notice_loop(self) -> None:
        sleep_for = max(15, settings.scheduled_notice_poll_seconds)
        while self._running and self._is_leader:
            try:
                count = await dispatch_scheduled_notice_notifications()
                self._last_notice_dispatch_at = datetime.now(timezone.utc)
                self._last_notice_dispatch_count = count
            except Exception:
                logger.exception({"event": "scheduler.notice_dispatch.error"})
            await asyncio.sleep(sleep_for)

    async def _daily_snapshot_loop(self) -> None:
        while self._running and self._is_leader:
            try:
                next_run = _next_daily_run_utc(
                    hour=max(0, min(23, settings.analytics_snapshot_hour_utc)),
                    minute=max(0, min(59, settings.analytics_snapshot_minute_utc)),
                )
                wait_seconds = max(1.0, (next_run - datetime.now(timezone.utc)).total_seconds())
                await asyncio.sleep(wait_seconds)
                if not self._running or not self._is_leader:
                    break
                await run_daily_analytics_snapshot_job()
                self._last_snapshot_at = datetime.now(timezone.utc)
            except Exception:
                logger.exception({"event": "scheduler.daily_snapshot.error"})
                await asyncio.sleep(30)


app_scheduler = AppScheduler()
~~~

## backend/app/core/rate_limit.py
~~~python
from __future__ import annotations

import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from typing import Deque

from fastapi import HTTPException, status
from jose import JWTError, jwt
from pymongo import ReturnDocument
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from app.core.database import db
from app.core.config import settings
from app.core.redis_store import redis_store


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60) -> None:
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._mongo_indexes_ready = False
        self._events: dict[str, Deque[float]] = defaultdict(deque)
        self._last_local_prune_at = 0.0

    @staticmethod
    def _client_ip(request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for", "").strip()
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("x-real-ip", "").strip()
        if real_ip:
            return real_ip
        return request.client.host if request.client else "unknown"

    @staticmethod
    def _user_actor(request: Request) -> str:
        authorization = request.headers.get("authorization", "")
        if authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1].strip()
            if token:
                try:
                    payload = jwt.decode(
                        token,
                        settings.jwt_secret,
                        algorithms=[settings.jwt_algorithm],
                        options={"verify_aud": False},
                    )
                    subject = payload.get("sub")
                    if subject:
                        return f"user:{subject}"
                except JWTError:
                    pass
        ip = RateLimitMiddleware._client_ip(request)
        user_agent = request.headers.get("user-agent", "")[:80]
        return f"ip:{ip}:ua:{user_agent}"

    def _key(self, request: Request) -> str:
        actor = self._user_actor(request)
        method = request.method.upper()
        return f"{actor}:{method}:{request.url.path}"

    async def _increment_via_mongo(self, key: str) -> int | None:
        counters = getattr(db, "rate_limit_counters", None)
        if counters is None:
            return None

        if not self._mongo_indexes_ready:
            try:
                await counters.create_index("expires_at", expireAfterSeconds=0)
                await counters.create_index("created_at")
                self._mongo_indexes_ready = True
            except Exception:
                return None

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=max(2, self.window_seconds * 2))
        bucket_id = int(time.time() // self.window_seconds)
        doc_id = f"{bucket_id}:{key}"

        try:
            updated = await counters.find_one_and_update(
                {"_id": doc_id},
                {
                    "$inc": {"count": 1},
                    "$setOnInsert": {
                        "created_at": now,
                        "expires_at": expires_at,
                    },
                },
                upsert=True,
                return_document=ReturnDocument.AFTER,
            )
        except Exception:
            return None

        if not updated:
            return None
        return int(updated.get("count") or 0)

    def _increment_via_local_memory(self, key: str) -> int:
        now = time.monotonic()
        events = self._events[key]

        while events and now - events[0] > self.window_seconds:
            events.popleft()

        events.append(now)
        self._prune_local_state(now)
        return len(events)

    def _prune_local_state(self, now: float) -> None:
        # Local fallback is only for non-production; prune aggressively to cap key growth.
        if now - self._last_local_prune_at < max(5, self.window_seconds):
            return
        stale_after = now - self.window_seconds
        stale_keys = [key for key, events in self._events.items() if not events or events[-1] < stale_after]
        for key in stale_keys:
            self._events.pop(key, None)
        self._last_local_prune_at = now

    def _assert_within_limit(self, count: int) -> None:
        if count > self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail='Too many requests. Please retry shortly.',
            )

    async def dispatch(self, request: Request, call_next):
        # Only rate limit mutating routes and auth endpoints to reduce abuse risk.
        method = request.method.upper()
        path = request.url.path
        should_limit = method in {'POST', 'PUT', 'PATCH', 'DELETE'} or '/auth/' in path
        if not should_limit:
            return await call_next(request)

        key = self._key(request)
        redis_count = await redis_store.increment_with_ttl(
            f"ratelimit:{key}",
            self.window_seconds,
        )
        if redis_count is not None:
            self._assert_within_limit(redis_count)
            return await call_next(request)

        mongo_count = await self._increment_via_mongo(key)
        if mongo_count is not None:
            self._assert_within_limit(mongo_count)
            return await call_next(request)

        if settings.environment in {"production", "staging"}:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail='Rate limiter backend unavailable. Please retry shortly.',
            )

        local_count = self._increment_via_local_memory(key)
        self._assert_within_limit(local_count)
        return await call_next(request)
~~~

## backend/app/api/v1/endpoints/analytics.py
~~~python
from collections import defaultdict
from datetime import datetime, timezone
from math import ceil
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import settings
from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.redis_store import redis_store
from app.core.security import require_roles

router = APIRouter()

ANALYTICS_DEFAULT_PAGE_SIZE = 200
ANALYTICS_MAX_PAGE_SIZE = 500
ANALYTICS_SMALL_SCAN_CAP = 5_000
ANALYTICS_MEDIUM_SCAN_CAP = 25_000
ANALYTICS_LARGE_SCAN_CAP = 100_000


def _bounded_cap(*, minimum: int, estimate: int, maximum: int) -> int:
    return min(maximum, max(minimum, estimate))


def _safe_object_ids(raw_ids: list[Any]) -> list[Any]:
    object_ids: list[Any] = []
    for raw in raw_ids:
        if raw is None:
            continue
        try:
            object_ids.append(parse_object_id(str(raw)))
        except HTTPException:
            continue
    return object_ids


def _to_utc_datetime(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


async def _get_cached_json(key: str):
    return await redis_store.get_json(key)


async def _set_cached_json(key: str, payload: dict):
    await redis_store.set_json(
        key,
        payload,
        ttl_seconds=max(30, settings.analytics_cache_ttl_seconds),
    )


async def _distinct_values(
    collection,
    field: str,
    query: dict[str, Any],
    *,
    fallback_cap: int = ANALYTICS_MEDIUM_SCAN_CAP,
) -> list[Any]:
    distinct = getattr(collection, 'distinct', None)
    if callable(distinct):
        try:
            values = await distinct(field, query)
            return [value for value in values if value is not None]
        except Exception:
            pass

    rows = await collection.find(query, {field: 1}).to_list(length=max(1, fallback_cap))
    values: list[Any] = []
    seen: set[str] = set()
    for row in rows:
        value = row.get(field)
        if isinstance(value, list):
            for nested in value:
                if nested is None:
                    continue
                marker = str(nested)
                if marker not in seen:
                    seen.add(marker)
                    values.append(nested)
            continue
        if value is None:
            continue
        marker = str(value)
        if marker not in seen:
            seen.add(marker)
            values.append(value)
    return values


async def _count_by_field(
    collection,
    *,
    query: dict[str, Any],
    field: str,
    fallback_cap: int = ANALYTICS_LARGE_SCAN_CAP,
) -> dict[str, int]:
    aggregate = getattr(collection, 'aggregate', None)
    if callable(aggregate):
        try:
            pipeline = [
                {'$match': query},
                {'$group': {'_id': f'${field}', 'count': {'$sum': 1}}},
            ]
            rows = await aggregate(pipeline).to_list(length=fallback_cap)
            grouped: dict[str, int] = {}
            for row in rows:
                key = row.get('_id')
                if key is not None:
                    grouped[str(key)] = int(row.get('count') or 0)
            return grouped
        except Exception:
            pass

    rows = await collection.find(query, {field: 1}).to_list(length=max(1, fallback_cap))
    grouped: dict[str, int] = {}
    for row in rows:
        key = row.get(field)
        if key is None:
            continue
        key_text = str(key)
        grouped[key_text] = grouped.get(key_text, 0) + 1
    return grouped


def _empty_academic_structure_payload(*, page: int, page_size: int, total_classes: int = 0) -> dict:
    total_pages = max(1, ceil(total_classes / page_size)) if page_size else 1
    return {
        'university': {
            'id': 'UNI001',
            'name': settings.app_name,
            'location': 'Indore, India',
        },
        'courses': [],
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_classes': total_classes,
            'total_pages': total_pages,
        },
    }


@router.get('/summary')
async def analytics_summary(
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    role = current_user.get('role')
    user_id = str(current_user.get('_id'))
    cache_key = f'analytics:summary:{role}:{user_id}'
    cached = await _get_cached_json(cache_key)
    if cached:
        return cached

    if role == 'student':
        total_submissions = await db.submissions.count_documents({'student_user_id': user_id})
        total_evaluations = await db.evaluations.count_documents({'student_user_id': user_id})
        pending = await db.submissions.count_documents({'student_user_id': user_id, 'status': 'submitted'})
        payload = {
            'role': role,
            'summary': {
                'total_submissions': total_submissions,
                'total_evaluations': total_evaluations,
                'pending_reviews': pending,
            },
        }
        await _set_cached_json(cache_key, payload)
        return payload

    if role == 'teacher':
        my_assignments = await db.assignments.count_documents({'created_by': user_id})
        my_assignment_ids = [str(item) for item in await _distinct_values(db.assignments, '_id', {'created_by': user_id})]
        my_submissions = 0
        my_similarity_flags = 0
        if my_assignment_ids:
            my_submissions = await db.submissions.count_documents({'assignment_id': {'$in': my_assignment_ids}})
            my_similarity_flags = await db.similarity_logs.count_documents(
                {'is_flagged': True, 'source_assignment_id': {'$in': my_assignment_ids}}
            )
        my_evaluations = await db.evaluations.count_documents({'teacher_user_id': user_id})
        my_notices = await db.notices.count_documents({'is_active': True})
        payload = {
            'role': role,
            'summary': {
                'my_assignments': my_assignments,
                'my_submissions': my_submissions,
                'my_evaluations': my_evaluations,
                'my_similarity_flags': my_similarity_flags,
                'my_notices': my_notices,
            },
        }
        await _set_cached_json(cache_key, payload)
        return payload

    payload = {
        'role': role,
        'summary': {
            'users': await db.users.count_documents({}),
            'courses': await db.courses.count_documents({}),
            'years': await db.years.count_documents({}),
            'classes': await db.classes.count_documents({}),
            'subjects': await db.subjects.count_documents({}),
            'students': await db.students.count_documents({}),
            'assignments': await db.assignments.count_documents({}),
            'submissions': await db.submissions.count_documents({}),
            'evaluations': await db.evaluations.count_documents({}),
            'similarity_flags': await db.similarity_logs.count_documents({'is_flagged': True}),
            'notices': await db.notices.count_documents({'is_active': True}),
            'clubs': await db.clubs.count_documents({'is_active': True}),
            'club_events': await db.club_events.count_documents({}),
        },
    }
    await _set_cached_json(cache_key, payload)
    return payload


async def _teacher_section_tiles(
    current_user=Depends(require_roles(['teacher'])),
) -> dict:
    user_id = str(current_user.get('_id'))
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid user context')

    now = datetime.now(timezone.utc)
    classes = await db.classes.find(
        {'class_coordinator_user_id': user_id, 'is_active': True},
        {'name': 1, 'year_id': 1},
    ).to_list(length=ANALYTICS_SMALL_SCAN_CAP)
    teacher_assignment_classes = await _distinct_values(
        db.assignments,
        'class_id',
        {'created_by': user_id},
        fallback_cap=ANALYTICS_MEDIUM_SCAN_CAP,
    )
    extra_class_object_ids = _safe_object_ids([str(value) for value in teacher_assignment_classes if value])
    extra_classes = []
    if extra_class_object_ids:
        extra_classes = await db.classes.find(
            {'_id': {'$in': extra_class_object_ids}, 'is_active': True},
            {'name': 1, 'year_id': 1},
        ).to_list(length=ANALYTICS_SMALL_SCAN_CAP)

    class_by_id = {str(item.get('_id')): item for item in classes}
    for class_doc in extra_classes:
        class_by_id[str(class_doc.get('_id'))] = class_doc

    class_ids = sorted([class_id for class_id in class_by_id.keys() if class_id])
    if not class_ids:
        return {'items': []}

    assignments_cap = _bounded_cap(
        minimum=ANALYTICS_SMALL_SCAN_CAP,
        estimate=len(class_ids) * 600,
        maximum=ANALYTICS_LARGE_SCAN_CAP,
    )
    assignment_docs = await db.assignments.find(
        {'class_id': {'$in': class_ids}},
        {'_id': 1, 'class_id': 1, 'status': 1, 'due_date': 1, 'subject_id': 1},
    ).to_list(length=assignments_cap)

    assignments_by_class: dict[str, list[dict[str, Any]]] = defaultdict(list)
    assignment_to_class: dict[str, str] = {}
    subject_ids: set[str] = set()
    for row in assignment_docs:
        class_id = row.get('class_id')
        assignment_obj_id = row.get('_id')
        if not class_id or assignment_obj_id is None:
            continue
        class_id_text = str(class_id)
        assignment_id = str(assignment_obj_id)
        assignments_by_class[class_id_text].append(row)
        assignment_to_class[assignment_id] = class_id_text
        subject_id = row.get('subject_id')
        if subject_id:
            subject_ids.add(str(subject_id))

    subject_by_id: dict[str, dict[str, Any]] = {}
    subject_object_ids = _safe_object_ids(list(subject_ids))
    if subject_object_ids:
        subject_docs = await db.subjects.find(
            {'_id': {'$in': subject_object_ids}, 'is_active': True},
            {'name': 1},
        ).to_list(length=_bounded_cap(minimum=1_000, estimate=len(subject_object_ids) * 2, maximum=ANALYTICS_SMALL_SCAN_CAP))
        subject_by_id = {str(item.get('_id')): item for item in subject_docs if item.get('_id')}

    enrollment_cap = _bounded_cap(
        minimum=ANALYTICS_SMALL_SCAN_CAP,
        estimate=len(class_ids) * 400,
        maximum=ANALYTICS_LARGE_SCAN_CAP,
    )
    enrollment_rows = await db.enrollments.find(
        {'class_id': {'$in': class_ids}},
        {'class_id': 1, 'student_id': 1},
    ).to_list(length=enrollment_cap)
    direct_student_rows = await db.students.find(
        {'class_id': {'$in': class_ids}, 'is_active': True},
        {'class_id': 1, '_id': 1},
    ).to_list(length=enrollment_cap)

    class_student_ids: dict[str, set[str]] = defaultdict(set)
    for row in enrollment_rows:
        class_id = row.get('class_id')
        student_id = row.get('student_id')
        if class_id and student_id:
            class_student_ids[str(class_id)].add(str(student_id))
    for row in direct_student_rows:
        class_id = row.get('class_id')
        student_id = row.get('_id')
        if class_id and student_id:
            class_student_ids[str(class_id)].add(str(student_id))

    assignment_ids = sorted(assignment_to_class.keys())
    submission_to_class: dict[str, str] = {}
    submissions_count_by_assignment: dict[str, int] = {}
    similarity_count_by_assignment: dict[str, int] = {}
    risk_students_by_class: dict[str, set[str]] = defaultdict(set)

    if assignment_ids:
        submissions_cap = _bounded_cap(
            minimum=ANALYTICS_MEDIUM_SCAN_CAP,
            estimate=len(assignment_ids) * 250,
            maximum=ANALYTICS_LARGE_SCAN_CAP,
        )
        submission_rows = await db.submissions.find(
            {'assignment_id': {'$in': assignment_ids}},
            {'_id': 1, 'assignment_id': 1},
        ).to_list(length=submissions_cap)
        for row in submission_rows:
            assignment_id = row.get('assignment_id')
            submission_obj_id = row.get('_id')
            if not assignment_id:
                continue
            assignment_key = str(assignment_id)
            submissions_count_by_assignment[assignment_key] = submissions_count_by_assignment.get(assignment_key, 0) + 1
            if submission_obj_id is not None:
                class_id = assignment_to_class.get(assignment_key)
                if class_id:
                    submission_to_class[str(submission_obj_id)] = class_id

        similarity_count_by_assignment = await _count_by_field(
            db.similarity_logs,
            query={'is_flagged': True, 'source_assignment_id': {'$in': assignment_ids}},
            field='source_assignment_id',
            fallback_cap=_bounded_cap(
                minimum=ANALYTICS_SMALL_SCAN_CAP,
                estimate=len(assignment_ids) * 50,
                maximum=ANALYTICS_LARGE_SCAN_CAP,
            ),
        )

        submission_ids = list(submission_to_class.keys())
        if submission_ids:
            risky_cap = _bounded_cap(
                minimum=ANALYTICS_SMALL_SCAN_CAP,
                estimate=len(submission_ids) * 2,
                maximum=ANALYTICS_LARGE_SCAN_CAP,
            )
            risky_rows = await db.evaluations.find(
                {
                    'submission_id': {'$in': submission_ids},
                    '$or': [{'grand_total': {'$lt': 40}}, {'attendance_percent': {'$lt': 70}}],
                },
                {'submission_id': 1, 'student_user_id': 1},
            ).to_list(length=risky_cap)
            for row in risky_rows:
                submission_id = row.get('submission_id')
                student_user_id = row.get('student_user_id')
                class_id = submission_to_class.get(str(submission_id)) if submission_id else None
                if class_id and student_user_id:
                    risk_students_by_class[class_id].add(str(student_user_id))

    items = []
    for class_id, class_doc in class_by_id.items():
        assignment_docs_for_class = assignments_by_class.get(class_id, [])
        assignment_ids_for_class = [str(item.get('_id')) for item in assignment_docs_for_class if item.get('_id')]
        total_students = len(class_student_ids.get(class_id, set()))
        active_assignments = sum(1 for item in assignment_docs_for_class if item.get('status') == 'open')

        late_submissions_count = 0
        for assignment in assignment_docs_for_class:
            assignment_id_obj = assignment.get('_id')
            assignment_id = str(assignment_id_obj) if assignment_id_obj is not None else ''
            due = _to_utc_datetime(assignment.get('due_date'))
            if due and due < now and assignment_id:
                submitted = submissions_count_by_assignment.get(assignment_id, 0)
                late_submissions_count += max(0, total_students - submitted)

        similarity_alert_count = sum(similarity_count_by_assignment.get(assignment_id, 0) for assignment_id in assignment_ids_for_class)
        risk_student_count = len(risk_students_by_class.get(class_id, set()))

        if risk_student_count >= 3 or similarity_alert_count >= 3 or late_submissions_count >= 5:
            health_status = 'risk'
        elif risk_student_count >= 1 or similarity_alert_count >= 1 or late_submissions_count >= 1:
            health_status = 'attention'
        else:
            health_status = 'healthy'

        class_subject_ids = sorted({str(item.get('subject_id')) for item in assignment_docs_for_class if item.get('subject_id')})
        class_subject_names = [subject_by_id.get(subject_id, {}).get('name', subject_id) for subject_id in class_subject_ids]

        items.append(
            {
                'class_id': class_id,
                'class_name': class_doc.get('name', class_id),
                'year_id': class_doc.get('year_id'),
                'total_students': total_students,
                'active_assignments': active_assignments,
                'late_submissions_count': late_submissions_count,
                'similarity_alert_count': similarity_alert_count,
                'risk_student_count': risk_student_count,
                'health_status': health_status,
                'subjects': class_subject_names,
            }
        )

    items.sort(key=lambda row: str(row.get('class_name') or ''))
    return {'items': items}


@router.get('/teacher/classes')
async def teacher_class_tiles(
    current_user=Depends(require_roles(['teacher'])),
) -> dict:
    # Legacy compatibility alias; canonical path is /teacher/sections.
    return await _teacher_section_tiles(current_user=current_user)


@router.get('/teacher/sections')
async def teacher_section_tiles(
    current_user=Depends(require_roles(['teacher'])),
) -> dict:
    return await _teacher_section_tiles(current_user=current_user)


@router.get('/academic-structure')
async def academic_structure(
    page: int = Query(1, ge=1),
    page_size: int = Query(ANALYTICS_DEFAULT_PAGE_SIZE, ge=1, le=ANALYTICS_MAX_PAGE_SIZE),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    role = current_user.get('role')
    user_id = str(current_user.get('_id'))
    cache_key = f'analytics:academic-structure:{role}:{user_id}:{page}:{page_size}'
    cached = await _get_cached_json(cache_key)
    if cached:
        return cached

    user_email = str(current_user.get('email') or '').lower()
    class_query: dict[str, Any] = {'is_active': True}

    if role == 'teacher':
        class_query['class_coordinator_user_id'] = user_id

    if role == 'student':
        student_docs_for_email = await db.students.find(
            {'is_active': True, 'email': user_email},
            {'_id': 1, 'class_id': 1},
        ).to_list(length=ANALYTICS_SMALL_SCAN_CAP)
        student_ids = {str(row.get('_id')) for row in student_docs_for_email if row.get('_id')}
        allowed_class_ids = {str(row.get('class_id')) for row in student_docs_for_email if row.get('class_id')}
        if student_ids:
            enrolled_class_ids = await _distinct_values(
                db.enrollments,
                'class_id',
                {'student_id': {'$in': list(student_ids)}},
                fallback_cap=ANALYTICS_MEDIUM_SCAN_CAP,
            )
            allowed_class_ids.update(str(value) for value in enrolled_class_ids if value)

        allowed_class_object_ids = _safe_object_ids(list(allowed_class_ids))
        if not allowed_class_object_ids:
            payload = _empty_academic_structure_payload(page=page, page_size=page_size, total_classes=0)
            await _set_cached_json(cache_key, payload)
            return payload
        class_query['_id'] = {'$in': allowed_class_object_ids}

    total_classes = await db.classes.count_documents(class_query)
    if total_classes == 0:
        payload = _empty_academic_structure_payload(page=page, page_size=page_size, total_classes=0)
        await _set_cached_json(cache_key, payload)
        return payload

    skip = (page - 1) * page_size
    class_cursor = db.classes.find(
        class_query,
        {'name': 1, 'course_id': 1, 'year_id': 1, 'class_coordinator_user_id': 1},
    )
    if hasattr(class_cursor, 'sort'):
        class_cursor = class_cursor.sort('name', 1)
    if hasattr(class_cursor, 'skip'):
        class_cursor = class_cursor.skip(skip)
    if hasattr(class_cursor, 'limit'):
        class_cursor = class_cursor.limit(page_size)
    classes = await class_cursor.to_list(length=page_size)
    if not classes:
        payload = _empty_academic_structure_payload(page=page, page_size=page_size, total_classes=total_classes)
        await _set_cached_json(cache_key, payload)
        return payload

    class_ids = [str(item.get('_id')) for item in classes if item.get('_id')]
    enrollment_cap = _bounded_cap(
        minimum=ANALYTICS_SMALL_SCAN_CAP,
        estimate=page_size * 400,
        maximum=ANALYTICS_LARGE_SCAN_CAP,
    )
    enrollments = await db.enrollments.find(
        {'class_id': {'$in': class_ids}},
        {'class_id': 1, 'student_id': 1},
    ).to_list(length=enrollment_cap)

    students = await db.students.find(
        {'class_id': {'$in': class_ids}, 'is_active': True},
        {'_id': 1, 'full_name': 1, 'roll_number': 1, 'email': 1, 'class_id': 1},
    ).to_list(length=enrollment_cap)

    students_by_id = {str(item.get('_id')): item for item in students if item.get('_id')}
    enrolled_student_ids = {str(item.get('student_id')) for item in enrollments if item.get('student_id')}
    missing_student_ids = enrolled_student_ids - set(students_by_id.keys())
    missing_student_object_ids = _safe_object_ids(list(missing_student_ids))
    if missing_student_object_ids:
        extra_students = await db.students.find(
            {'_id': {'$in': missing_student_object_ids}, 'is_active': True},
            {'_id': 1, 'full_name': 1, 'roll_number': 1, 'email': 1, 'class_id': 1},
        ).to_list(length=enrollment_cap)
        for row in extra_students:
            row_id = row.get('_id')
            if row_id is not None:
                students_by_id[str(row_id)] = row

    class_student_ids: dict[str, set[str]] = defaultdict(set)
    for row in enrollments:
        class_id = row.get('class_id')
        student_id = row.get('student_id')
        if class_id and student_id:
            class_student_ids[str(class_id)].add(str(student_id))
    for row in students_by_id.values():
        class_id = row.get('class_id')
        row_id = row.get('_id')
        if class_id and row_id:
            class_student_ids[str(class_id)].add(str(row_id))

    assignments = await db.assignments.find(
        {'class_id': {'$in': class_ids}},
        {'class_id': 1, 'subject_id': 1},
    ).to_list(
        length=_bounded_cap(
            minimum=ANALYTICS_SMALL_SCAN_CAP,
            estimate=page_size * 400,
            maximum=ANALYTICS_LARGE_SCAN_CAP,
        )
    )
    class_subject_ids: dict[str, set[str]] = defaultdict(set)
    for row in assignments:
        class_id = row.get('class_id')
        subject_id = row.get('subject_id')
        if class_id and subject_id:
            class_subject_ids[str(class_id)].add(str(subject_id))

    subject_ids = {subject_id for values in class_subject_ids.values() for subject_id in values}
    subject_by_id: dict[str, dict[str, Any]] = {}
    subject_object_ids = _safe_object_ids(list(subject_ids))
    if subject_object_ids:
        subjects = await db.subjects.find(
            {'_id': {'$in': subject_object_ids}, 'is_active': True},
            {'name': 1, 'code': 1},
        ).to_list(length=_bounded_cap(minimum=ANALYTICS_SMALL_SCAN_CAP, estimate=len(subject_object_ids) * 2, maximum=ANALYTICS_MEDIUM_SCAN_CAP))
        subject_by_id = {str(item.get('_id')): item for item in subjects if item.get('_id')}

    course_ids = {str(item.get('course_id')) for item in classes if item.get('course_id')}
    year_ids = {str(item.get('year_id')) for item in classes if item.get('year_id')}

    course_object_ids = _safe_object_ids(list(course_ids))
    courses = await db.courses.find({'_id': {'$in': course_object_ids}, 'is_active': True}).to_list(
        length=_bounded_cap(minimum=ANALYTICS_SMALL_SCAN_CAP, estimate=len(course_object_ids) * 2, maximum=ANALYTICS_MEDIUM_SCAN_CAP)
    ) if course_object_ids else []

    year_object_ids = _safe_object_ids(list(year_ids))
    years = await db.years.find({'_id': {'$in': year_object_ids}, 'is_active': True}).to_list(
        length=_bounded_cap(minimum=ANALYTICS_SMALL_SCAN_CAP, estimate=len(year_object_ids) * 2, maximum=ANALYTICS_MEDIUM_SCAN_CAP)
    ) if year_object_ids else []

    coordinator_ids = {str(item.get('class_coordinator_user_id')) for item in classes if item.get('class_coordinator_user_id')}
    coordinator_object_ids = _safe_object_ids(list(coordinator_ids))
    coordinator_users = await db.users.find(
        {'_id': {'$in': coordinator_object_ids}},
        {'full_name': 1},
    ).to_list(length=_bounded_cap(minimum=ANALYTICS_SMALL_SCAN_CAP, estimate=len(coordinator_object_ids) * 2, maximum=ANALYTICS_MEDIUM_SCAN_CAP)) if coordinator_object_ids else []

    student_emails = {str(item.get('email') or '').lower() for item in students_by_id.values() if item.get('email')}
    users_by_email: dict[str, str] = {}
    if student_emails:
        user_rows = await db.users.find(
            {'email': {'$in': list(student_emails)}},
            {'_id': 1, 'email': 1},
        ).to_list(length=_bounded_cap(minimum=ANALYTICS_SMALL_SCAN_CAP, estimate=len(student_emails) * 2, maximum=ANALYTICS_MEDIUM_SCAN_CAP))
        users_by_email = {
            str(item.get('email') or '').lower(): str(item.get('_id'))
            for item in user_rows
            if item.get('_id') and item.get('email')
        }

    users_by_id = {str(item.get('_id')): item for item in coordinator_users if item.get('_id')}
    students_by_student_id = {str(item.get('_id')): item for item in students_by_id.values() if item.get('_id')}

    student_user_by_student_id: dict[str, str] = {}
    candidate_user_ids: set[str] = set()
    for student in students_by_student_id.values():
        student_id = str(student.get('_id'))
        email = str(student.get('email') or '').lower()
        mapped_user_id = users_by_email.get(email)
        if mapped_user_id:
            student_user_by_student_id[student_id] = mapped_user_id
            candidate_user_ids.add(mapped_user_id)

    submissions_count_by_user: dict[str, int] = {}
    regs_count_by_user: dict[str, int] = {}
    if candidate_user_ids:
        query = {'student_user_id': {'$in': list(candidate_user_ids)}}
        submissions_count_by_user = await _count_by_field(
            db.submissions,
            query=query,
            field='student_user_id',
            fallback_cap=_bounded_cap(
                minimum=ANALYTICS_MEDIUM_SCAN_CAP,
                estimate=len(candidate_user_ids) * 200,
                maximum=ANALYTICS_LARGE_SCAN_CAP,
            ),
        )
        regs_count_by_user = await _count_by_field(
            db.event_registrations,
            query=query,
            field='student_user_id',
            fallback_cap=_bounded_cap(
                minimum=ANALYTICS_MEDIUM_SCAN_CAP,
                estimate=len(candidate_user_ids) * 100,
                maximum=ANALYTICS_LARGE_SCAN_CAP,
            ),
        )

    course_by_id = {str(item.get('_id')): item for item in courses if item.get('_id')}
    year_by_id = {str(item.get('_id')): item for item in years if item.get('_id')}

    tree: dict[str, dict[str, Any]] = {}
    for class_doc in classes:
        class_id = str(class_doc.get('_id'))
        course_id = str(class_doc.get('course_id') or '')
        year_id = str(class_doc.get('year_id') or '')
        if not class_id or not course_id or not year_id:
            continue

        course = course_by_id.get(course_id)
        year = year_by_id.get(year_id)
        if not course or not year:
            continue

        course_node = tree.setdefault(
            course_id,
            {
                'id': course_id,
                'name': course.get('name') or 'Course',
                'years': {},
            },
        )
        year_node = course_node['years'].setdefault(
            year_id,
            {
                'id': year_id,
                'name': year.get('label') or f"Year {year.get('year_number')}",
                'classes': [],
            },
        )

        teacher_name = 'Unassigned'
        coordinator_id = str(class_doc.get('class_coordinator_user_id') or '')
        if coordinator_id and coordinator_id in users_by_id:
            teacher_name = users_by_id[coordinator_id].get('full_name') or 'Unassigned'

        student_items = []
        for student_id in sorted(class_student_ids.get(class_id, set())):
            student = students_by_student_id.get(student_id)
            if not student:
                continue
            mapped_user_id = student_user_by_student_id.get(student_id, '')
            student_items.append(
                {
                    'id': student_id,
                    'name': student.get('full_name'),
                    'rollNo': student.get('roll_number'),
                    'logs': {
                        'assignment_submissions': submissions_count_by_user.get(mapped_user_id, 0),
                        'event_registrations': regs_count_by_user.get(mapped_user_id, 0),
                    },
                }
            )

        subject_items = []
        for subject_id in sorted(class_subject_ids.get(class_id, set())):
            subject_doc = subject_by_id.get(subject_id)
            if subject_doc:
                subject_items.append(
                    {
                        'id': subject_id,
                        'name': subject_doc.get('name') or subject_id,
                        'code': subject_doc.get('code'),
                    }
                )

        year_node['classes'].append(
            {
                'id': class_id,
                'name': class_doc.get('name') or class_id,
                'coordinator': teacher_name,
                'students': student_items,
                'subjects': subject_items,
            }
        )

    course_items = []
    for course in tree.values():
        year_items = []
        for year in course['years'].values():
            year_items.append(
                {
                    'id': year['id'],
                    'name': year['name'],
                    'classes': year['classes'],
                }
            )
        year_items.sort(key=lambda item: str(item.get('name') or ''))
        course_items.append(
            {
                'id': course['id'],
                'name': course['name'],
                'years': year_items,
            }
        )
    course_items.sort(key=lambda item: str(item.get('name') or ''))

    payload = {
        'university': {
            'id': 'UNI001',
            'name': settings.app_name,
            'location': 'Indore, India',
        },
        'courses': course_items,
        'pagination': {
            'page': page,
            'page_size': page_size,
            'total_classes': total_classes,
            'total_pages': max(1, ceil(total_classes / page_size)),
        },
    }
    await _set_cached_json(cache_key, payload)
    return payload
~~~

## frontend/nginx.conf
~~~nginx
server {
    listen 80;
    server_name _;

    root /usr/share/nginx/html;
    index index.html;

    location /api/v1 {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location / {
        try_files $uri /index.html;
    }
}
~~~

## frontend/src/services/apiClient.js
~~~javascript
import axios from 'axios';

export const TOKEN_KEY = 'caps_ai_token';
export const REFRESH_TOKEN_KEY = 'caps_ai_refresh_token';
const MAX_TRACE_ENTRIES = 100;
const traceEntries = [];

function makeTraceId() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function pushTraceEntry(entry) {
  traceEntries.unshift(entry);
  if (traceEntries.length > MAX_TRACE_ENTRIES) {
    traceEntries.pop();
  }
}

function isEnvelope(payload) {
  return (
    payload &&
    typeof payload === 'object' &&
    Object.prototype.hasOwnProperty.call(payload, 'success') &&
    Object.prototype.hasOwnProperty.call(payload, 'data') &&
    Object.prototype.hasOwnProperty.call(payload, 'error')
  );
}

export function getRecentApiTraceEntries() {
  return [...traceEntries];
}

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1'
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  const traceId = makeTraceId();
  const startedAt = Date.now();
  config.headers['X-Trace-Id'] = traceId;
  config.headers['X-Request-Id'] = traceId;
  config.metadata = { traceId, startedAt };
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => {
    const method = String(response.config?.method || 'GET').toUpperCase();
    const url = response.config?.url || '';
    const startedAt = response.config?.metadata?.startedAt || Date.now();
    const traceId = response.headers?.['x-trace-id'] || response.config?.metadata?.traceId || '-';
    const requestId = response.headers?.['x-request-id'] || traceId;
    const errorId = response.headers?.['x-error-id'] || response.data?.error_id || '';
    pushTraceEntry({
      at: new Date().toISOString(),
      method,
      url,
      status: response.status,
      durationMs: Date.now() - startedAt,
      traceId,
      requestId,
      errorId
    });
    if (isEnvelope(response.data)) {
      response.data = response.data.data;
    }
    return response;
  },
  async (error) => {
    const response = error?.response;
    const config = error?.config || {};
    const method = String(config.method || 'GET').toUpperCase();
    const url = config.url || '';
    const startedAt = config.metadata?.startedAt || Date.now();
    const traceId = response?.headers?.['x-trace-id'] || config.metadata?.traceId || '-';
    const requestId = response?.headers?.['x-request-id'] || traceId;
    const errorId = response?.headers?.['x-error-id'] || response?.data?.error_id || '';
    pushTraceEntry({
      at: new Date().toISOString(),
      method,
      url,
      status: response?.status || 0,
      durationMs: Date.now() - startedAt,
      traceId,
      requestId,
      errorId
    });
    if (response && isEnvelope(response?.data)) {
      const envelope = response.data;
      error.response.data = {
        ...error.response.data,
        detail: envelope?.error?.detail ?? envelope?.error?.message ?? 'Request failed',
        error_id: envelope?.error?.error_id || errorId
      };
    }

    const originalRequest = error?.config;
    const statusCode = response?.status;
    const isAuthPath =
      typeof originalRequest?.url === 'string' &&
      (originalRequest.url.includes('/auth/login') ||
        originalRequest.url.includes('/auth/refresh') ||
        originalRequest.url.includes('/auth/logout'));

    if (statusCode === 401 && originalRequest && !originalRequest._retry && !isAuthPath) {
      originalRequest._retry = true;
      const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
      if (refreshToken) {
        try {
          const refreshResponse = await axios.post(
            `${apiClient.defaults.baseURL}/auth/refresh`,
            { refresh_token: refreshToken }
          );
          const refreshPayload = isEnvelope(refreshResponse?.data) ? refreshResponse.data.data : refreshResponse?.data;
          const nextAccessToken = refreshPayload?.access_token;
          const nextRefreshToken = refreshPayload?.refresh_token;
          if (nextAccessToken) {
            localStorage.setItem(TOKEN_KEY, nextAccessToken);
            originalRequest.headers = originalRequest.headers || {};
            originalRequest.headers.Authorization = `Bearer ${nextAccessToken}`;
          }
          if (nextRefreshToken) {
            localStorage.setItem(REFRESH_TOKEN_KEY, nextRefreshToken);
          }
          return apiClient(originalRequest);
        } catch {
          localStorage.removeItem(TOKEN_KEY);
          localStorage.removeItem(REFRESH_TOKEN_KEY);
          localStorage.removeItem('caps_ai_user');
        }
      }
    }
    return Promise.reject(error);
  }
);
~~~

## frontend/src/context/ToastContext.jsx
~~~javascript
import { createContext, useCallback, useContext, useMemo, useState } from 'react';

const ToastContext = createContext(null);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const pushToast = useCallback(
    (payload) => {
      const id = crypto.randomUUID();
      const toast = {
        id,
        title: payload.title || 'Notice',
        description: payload.description || '',
        variant: payload.variant || 'info'
      };
      setToasts((prev) => [toast, ...prev]);
      setTimeout(() => removeToast(id), payload.duration ?? 3200);
    },
    [removeToast]
  );

  const value = useMemo(() => ({ toasts, pushToast, removeToast }), [toasts, pushToast, removeToast]);

  return <ToastContext.Provider value={value}>{children}</ToastContext.Provider>;
}

export function useToastContext() {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToastContext must be used inside ToastProvider');
  }
  return context;
}
~~~

## scripts/migrate_to_azure_aks.ps1
~~~powershell
param(
  [Parameter(Mandatory = $true)][string]$SubscriptionId,
  [Parameter(Mandatory = $true)][string]$ResourceGroup,
  [Parameter(Mandatory = $true)][string]$AksName,
  [Parameter(Mandatory = $true)][string]$AcrName,
  [Parameter(Mandatory = $true)][string]$IngressHost,
  [Parameter(Mandatory = $true)][string]$JwtSecret,
  [string]$Location = "centralindia",
  [string]$NodeVmSize = "Standard_B2s_v2",
  [string]$SystemPoolName = "syspool",
  [string]$SystemPoolVmSize = "Standard_D2s_v3",
  [int]$SystemPoolCount = 2,
  [string]$UserPoolName = "nodepool1",
  [string]$UserPoolVmSize = "Standard_B2s_v2",
  [int]$UserPoolCount = 1,
  [string]$Namespace = "caps-ai",
  [int]$BackendReplicas = 1,
  [int]$FrontendReplicas = 1,
  [string]$ImageTag = "",
  [string]$TlsSecretName = "caps-ai-tls",
  [string]$ClusterIssuer = "letsencrypt-prod",
  [string]$IngressClassName = "nginx",
  [string]$OpenAiApiKey = "",
  [string]$CloudinaryCloudName = "",
  [string]$CloudinaryApiKey = "",
  [string]$CloudinaryApiSecret = "",
  [string]$OutputDir = "out/azure-manifests",
  [switch]$SkipInfrastructure,
  [switch]$SkipPoolHardening,
  [switch]$SkipBuildPush,
  [switch]$UseClassicDockerPush,
  [switch]$SkipApply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Write-Step {
  param([string]$Message)
  Write-Host "==> $Message" -ForegroundColor Cyan
}

function Require-Command {
  param([string]$Name)
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
    throw "Required command '$Name' not found. Install it and retry."
  }
}

function Ensure-Directory {
  param([string]$Path)
  if (-not (Test-Path $Path)) {
    New-Item -Path $Path -ItemType Directory | Out-Null
  }
}

function Render-TextFile {
  param(
    [string]$SourcePath,
    [string]$DestinationPath,
    [hashtable]$Replacements
  )

  $content = Get-Content -Raw -Path $SourcePath
  foreach ($entry in $Replacements.GetEnumerator()) {
    $content = $content.Replace([string]$entry.Key, [string]$entry.Value)
  }
  Set-Content -Path $DestinationPath -Value $content -Encoding ascii
}

function Run-OrThrow {
  param(
    [string]$Exe,
    [string[]]$Args
  )

  & $Exe @Args
  if ($LASTEXITCODE -ne 0) {
    throw "Command failed: $Exe $($Args -join ' ')"
  }
}

function Resolve-AzCommand {
  $resolved = Get-Command az -ErrorAction SilentlyContinue
  if ($resolved) {
    return $resolved.Source
  }
  $fallback = "C:\\Program Files\\Microsoft SDKs\\Azure\\CLI2\\wbin\\az.cmd"
  if (Test-Path $fallback) {
    return $fallback
  }
  throw "Azure CLI not found. Install Azure CLI or add az to PATH."
}

function Test-AzResourceExists {
  param(
    [string]$AzExe,
    [string]$ResourceArgs
  )

  $cmd = '"' + $AzExe + '" ' + $ResourceArgs + ' -o none >nul 2>nul'
  cmd /c $cmd | Out-Null
  return ($LASTEXITCODE -eq 0)
}

if ([string]::IsNullOrWhiteSpace($ImageTag)) {
  $ImageTag = Get-Date -Format "yyyyMMddHHmmss"
}

if ($JwtSecret.Length -lt 64) {
  throw "JwtSecret must be at least 64 characters."
}

$AzExe = Resolve-AzCommand
Require-Command -Name "kubectl"
Require-Command -Name "docker"

Write-Step "Using subscription $SubscriptionId"
$null = & $AzExe account show --query id -o tsv 2>$null
if ($LASTEXITCODE -ne 0) {
  Write-Step "No active Azure login detected; opening login flow"
  Run-OrThrow -Exe $AzExe -Args @("login")
}

Run-OrThrow -Exe $AzExe -Args @("account", "set", "--subscription", $SubscriptionId)

if (-not $SkipInfrastructure) {
  Write-Step "Ensuring resource group $ResourceGroup"
  Run-OrThrow -Exe $AzExe -Args @("group", "create", "--name", $ResourceGroup, "--location", $Location, "-o", "none")

  Write-Step "Ensuring ACR $AcrName"
  if (-not (Test-AzResourceExists -AzExe $AzExe -ResourceArgs "acr show --name $AcrName --resource-group $ResourceGroup")) {
    Run-OrThrow -Exe $AzExe -Args @("acr", "create", "--name", $AcrName, "--resource-group", $ResourceGroup, "--location", $Location, "--sku", "Basic", "-o", "none")
  }

  Write-Step "Ensuring AKS $AksName"
  if (-not (Test-AzResourceExists -AzExe $AzExe -ResourceArgs "aks show --name $AksName --resource-group $ResourceGroup")) {
    Run-OrThrow -Exe $AzExe -Args @(
      "aks", "create",
      "--name", $AksName,
      "--resource-group", $ResourceGroup,
      "--location", $Location,
      "--node-count", "1",
      "--node-vm-size", $NodeVmSize,
      "--generate-ssh-keys",
      "-o", "none"
    )
  }

  Write-Step "Attaching ACR to AKS"
  Run-OrThrow -Exe $AzExe -Args @(
    "aks", "update",
    "--name", $AksName,
    "--resource-group", $ResourceGroup,
    "--attach-acr", $AcrName,
    "-o", "none"
  )
}

if (-not $SkipPoolHardening) {
  Write-Step "Ensuring dedicated system pool $SystemPoolName"
  if (-not (Test-AzResourceExists -AzExe $AzExe -ResourceArgs "aks nodepool show --resource-group $ResourceGroup --cluster-name $AksName --name $SystemPoolName")) {
    Run-OrThrow -Exe $AzExe -Args @(
      "aks", "nodepool", "add",
      "--resource-group", $ResourceGroup,
      "--cluster-name", $AksName,
      "--name", $SystemPoolName,
      "--mode", "System",
      "--node-count", "$SystemPoolCount",
      "--node-vm-size", $SystemPoolVmSize,
      "--node-taints", "CriticalAddonsOnly=true:NoSchedule",
      "--labels", "pool=system", "role=critical",
      "--max-pods", "110",
      "-o", "none"
    )
  } else {
    Run-OrThrow -Exe $AzExe -Args @(
      "aks", "nodepool", "update",
      "--resource-group", $ResourceGroup,
      "--cluster-name", $AksName,
      "--name", $SystemPoolName,
      "--mode", "System",
      "--node-taints", "CriticalAddonsOnly=true:NoSchedule",
      "--labels", "pool=system", "role=critical",
      "-o", "none"
    )
    Run-OrThrow -Exe $AzExe -Args @(
      "aks", "nodepool", "scale",
      "--resource-group", $ResourceGroup,
      "--cluster-name", $AksName,
      "--name", $SystemPoolName,
      "--node-count", "$SystemPoolCount",
      "-o", "none"
    )
  }

  Write-Step "Ensuring user pool $UserPoolName"
  if (-not (Test-AzResourceExists -AzExe $AzExe -ResourceArgs "aks nodepool show --resource-group $ResourceGroup --cluster-name $AksName --name $UserPoolName")) {
    Run-OrThrow -Exe $AzExe -Args @(
      "aks", "nodepool", "add",
      "--resource-group", $ResourceGroup,
      "--cluster-name", $AksName,
      "--name", $UserPoolName,
      "--mode", "User",
      "--node-count", "$UserPoolCount",
      "--node-vm-size", $UserPoolVmSize,
      "--labels", "pool=user", "role=apps",
      "-o", "none"
    )
  } else {
    Run-OrThrow -Exe $AzExe -Args @(
      "aks", "nodepool", "update",
      "--resource-group", $ResourceGroup,
      "--cluster-name", $AksName,
      "--name", $UserPoolName,
      "--mode", "User",
      "--labels", "pool=user", "role=apps",
      "-o", "none"
    )
    Run-OrThrow -Exe $AzExe -Args @(
      "aks", "nodepool", "scale",
      "--resource-group", $ResourceGroup,
      "--cluster-name", $AksName,
      "--name", $UserPoolName,
      "--node-count", "$UserPoolCount",
      "-o", "none"
    )
  }
}

Write-Step "Getting AKS credentials"
Run-OrThrow -Exe $AzExe -Args @(
  "aks", "get-credentials",
  "--name", $AksName,
  "--resource-group", $ResourceGroup,
  "--overwrite-existing"
)

$acrLoginServer = (& $AzExe acr show --name $AcrName --resource-group $ResourceGroup --query loginServer -o tsv).Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($acrLoginServer)) {
  throw "Failed to resolve ACR login server."
}

$backendImage = "$acrLoginServer/caps-ai-backend:$ImageTag"
$frontendImage = "$acrLoginServer/caps-ai-frontend:$ImageTag"

if (-not $SkipBuildPush) {
  Write-Step "Logging into ACR"
  Run-OrThrow -Exe $AzExe -Args @("acr", "login", "--name", $AcrName)

  if ($UseClassicDockerPush) {
    Write-Step "Building backend image $backendImage"
    Run-OrThrow -Exe "docker" -Args @("build", "-t", $backendImage, "backend")

    Write-Step "Building frontend image $frontendImage"
    Run-OrThrow -Exe "docker" -Args @("build", "-t", $frontendImage, "frontend")

    Write-Step "Pushing backend image"
    Run-OrThrow -Exe "docker" -Args @("push", $backendImage)

    Write-Step "Pushing frontend image"
    Run-OrThrow -Exe "docker" -Args @("push", $frontendImage)
  } else {
    Write-Step "Checking Docker buildx availability"
    Run-OrThrow -Exe "docker" -Args @("buildx", "version")

    Write-Step "Building and pushing backend image with buildx: $backendImage"
    Run-OrThrow -Exe "docker" -Args @("buildx", "build", "--platform", "linux/amd64", "-t", $backendImage, "--push", "backend")

    Write-Step "Building and pushing frontend image with buildx: $frontendImage"
    Run-OrThrow -Exe "docker" -Args @("buildx", "build", "--platform", "linux/amd64", "-t", $frontendImage, "--push", "frontend")
  }
}

Write-Step "Rendering Azure manifests to $OutputDir"
Ensure-Directory -Path $OutputDir

$baseFiles = @{
  "k8s-namespace.yaml" = "01-namespace.yaml"
  "k8s-redis.azure.yaml" = "02-redis.yaml"
}

foreach ($entry in $baseFiles.GetEnumerator()) {
  Copy-Item -Path $entry.Key -Destination (Join-Path $OutputDir $entry.Value) -Force
}

Render-TextFile -SourcePath "k8s-secrets.azure.example.yaml" -DestinationPath (Join-Path $OutputDir "03-secrets.yaml") -Replacements @{
  "__JWT_SECRET__" = $JwtSecret
  "__OPENAI_API_KEY__" = $OpenAiApiKey
  "__CLOUDINARY_CLOUD_NAME__" = $CloudinaryCloudName
  "__CLOUDINARY_API_KEY__" = $CloudinaryApiKey
  "__CLOUDINARY_API_SECRET__" = $CloudinaryApiSecret
}

Render-TextFile -SourcePath "k8s-configmap.azure.yaml" -DestinationPath (Join-Path $OutputDir "04-configmap.yaml") -Replacements @{
  "https://caps-ai.example.com" = "https://$IngressHost"
}

Copy-Item -Path "k8s-uploads-pvc.azure.yaml" -Destination (Join-Path $OutputDir "05-uploads-pvc.yaml") -Force
Copy-Item -Path "k8s-mongodb.azure.yaml" -Destination (Join-Path $OutputDir "06-mongodb.yaml") -Force

$backendTemplate = Get-Content -Raw -Path "k8s-backend.azure.yaml"
$backendTemplate = $backendTemplate -replace '(?m)^(\s*image:\s*)(\S*caps-ai-backend:\S+)\s*$', "`$1$backendImage"
$backendTemplate = $backendTemplate -replace '(?m)^(\s*replicas:\s*)\d+\s*$', "`$1$BackendReplicas"
Set-Content -Path (Join-Path $OutputDir "07-backend.yaml") -Value $backendTemplate -Encoding ascii

$frontendTemplate = Get-Content -Raw -Path "k8s-frontend.azure.yaml"
$frontendTemplate = $frontendTemplate -replace '(?m)^(\s*image:\s*)(\S*caps-ai-frontend:\S+)\s*$', "`$1$frontendImage"
$frontendTemplate = $frontendTemplate -replace '(?m)^(\s*replicas:\s*)\d+\s*$', "`$1$FrontendReplicas"
Set-Content -Path (Join-Path $OutputDir "08-frontend.yaml") -Value $frontendTemplate -Encoding ascii

Render-TextFile -SourcePath "k8s-ingress.azure.yaml" -DestinationPath (Join-Path $OutputDir "09-ingress.yaml") -Replacements @{
  "caps-ai.example.com" = $IngressHost
  "caps-ai-tls" = $TlsSecretName
  "letsencrypt-prod" = $ClusterIssuer
  "ingressClassName: nginx" = "ingressClassName: $IngressClassName"
}

$manifestBatch = @(
  (Join-Path $OutputDir "01-namespace.yaml"),
  (Join-Path $OutputDir "03-secrets.yaml"),
  (Join-Path $OutputDir "04-configmap.yaml"),
  (Join-Path $OutputDir "05-uploads-pvc.yaml"),
  (Join-Path $OutputDir "02-redis.yaml"),
  (Join-Path $OutputDir "06-mongodb.yaml"),
  (Join-Path $OutputDir "07-backend.yaml"),
  (Join-Path $OutputDir "08-frontend.yaml"),
  (Join-Path $OutputDir "09-ingress.yaml")
)

Write-Step "Client-side manifest validation"
Run-OrThrow -Exe "kubectl" -Args @("apply", "--dry-run=client", "-f", $manifestBatch[0], "-f", $manifestBatch[1], "-f", $manifestBatch[2], "-f", $manifestBatch[3], "-f", $manifestBatch[4], "-f", $manifestBatch[5], "-f", $manifestBatch[6], "-f", $manifestBatch[7], "-f", $manifestBatch[8])

if (-not $SkipApply) {
  Write-Step "Applying manifests"
  Run-OrThrow -Exe "kubectl" -Args @("apply", "-f", $manifestBatch[0], "-f", $manifestBatch[1], "-f", $manifestBatch[2], "-f", $manifestBatch[3], "-f", $manifestBatch[4], "-f", $manifestBatch[5], "-f", $manifestBatch[6], "-f", $manifestBatch[7], "-f", $manifestBatch[8])

  Write-Step "Waiting for rollouts"
  Run-OrThrow -Exe "kubectl" -Args @("-n", $Namespace, "rollout", "status", "deployment/redis", "--timeout=300s")
  Run-OrThrow -Exe "kubectl" -Args @("-n", $Namespace, "rollout", "status", "statefulset/mongodb", "--timeout=300s")
  Run-OrThrow -Exe "kubectl" -Args @("-n", $Namespace, "rollout", "status", "deployment/backend", "--timeout=300s")
  Run-OrThrow -Exe "kubectl" -Args @("-n", $Namespace, "rollout", "status", "deployment/frontend", "--timeout=300s")

  Write-Step "Final resource status"
  Run-OrThrow -Exe "kubectl" -Args @("-n", $Namespace, "get", "deploy,statefulset,pods,svc,ingress,pvc")
}

if (-not $SkipPoolHardening) {
  Write-Step "Node pool topology"
  Run-OrThrow -Exe $AzExe -Args @(
    "aks", "nodepool", "list",
    "--resource-group", $ResourceGroup,
    "--cluster-name", $AksName,
    "-o", "table"
  )
}

$ingressIp = kubectl -n $Namespace get ingress caps-ai-ingress -o jsonpath="{.status.loadBalancer.ingress[0].ip}" 2>$null
$ingressHostName = kubectl -n $Namespace get ingress caps-ai-ingress -o jsonpath="{.status.loadBalancer.ingress[0].hostname}" 2>$null

Write-Host ""
Write-Host "Azure AKS migration complete." -ForegroundColor Green
Write-Host "Rendered manifests: $OutputDir"
Write-Host "Backend image:  $backendImage"
Write-Host "Frontend image: $frontendImage"
if (-not [string]::IsNullOrWhiteSpace($ingressIp)) {
  Write-Host "Ingress IP:      $ingressIp"
}
if (-not [string]::IsNullOrWhiteSpace($ingressHostName)) {
  Write-Host "Ingress Hostname: $ingressHostName"
}
Write-Host "DNS host target: $IngressHost"
~~~

## scripts/seed_minimum_stack.ps1
~~~powershell
param(
  [string]$BaseUrl = "http://localhost:8000/api/v1",
  [string]$AdminEmail = "admin.seed@caps.local",
  [string]$AdminPassword = "Admin@12345",
  [string]$TeacherEmail = "coordinator.seed@caps.local",
  [string]$TeacherPassword = "Teacher@12345",
  [string]$StudentEmail = "student.seed@caps.local",
  [string]$StudentPassword = "Student@12345"
)

$ErrorActionPreference = "Stop"

function Unwrap-Api {
  param([object]$Response)
  if ($null -eq $Response) { return $null }
  if ($Response.PSObject.Properties.Name -contains "success" -and $Response.success -eq $true -and $Response.PSObject.Properties.Name -contains "data") {
    return $Response.data
  }
  return $Response
}

function Invoke-Api {
  param(
    [string]$Method,
    [string]$Path,
    [object]$Body = $null,
    [string]$Token = $null
  )
  $headers = @{}
  if ($Token) { $headers["Authorization"] = "Bearer $Token" }
  $uri = "$BaseUrl$Path"
  try {
    if ($null -ne $Body) {
      $json = $Body | ConvertTo-Json -Depth 15
      $resp = Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers -ContentType "application/json" -Body $json
    } else {
      $resp = Invoke-RestMethod -Method $Method -Uri $uri -Headers $headers
    }
    return (Unwrap-Api -Response $resp)
  } catch {
    $status = $_.Exception.Response.StatusCode.value__
    $raw = ""
    if ($_.ErrorDetails -and $_.ErrorDetails.Message) { $raw = $_.ErrorDetails.Message }
    throw "API $Method $Path failed ($status): $raw"
  }
}

function Get-OrCreateUser {
  param(
    [string]$FullName,
    [string]$Email,
    [string]$Password,
    [string]$Role
  )
  try {
    $login = Invoke-Api -Method "POST" -Path "/auth/login" -Body @{
      email = $Email
      password = $Password
    }
    return $login
  } catch {
    $registerPayload = @{
      full_name = $FullName
      email = $Email
      password = $Password
      role = $Role
      extended_roles = @()
    }
    if ($Role -eq "admin") { $registerPayload.admin_type = "academic_admin" }
    $null = Invoke-Api -Method "POST" -Path "/auth/register" -Body $registerPayload
    return (Invoke-Api -Method "POST" -Path "/auth/login" -Body @{
      email = $Email
      password = $Password
    })
  }
}

function Find-ByField {
  param(
    [array]$Rows,
    [string]$Field,
    [string]$Value
  )
  foreach ($row in $Rows) {
    if ($row.$Field -eq $Value) { return $row }
  }
  return $null
}

Write-Host "==> Seeding minimum CAPS stack data..."

$adminAuth = Get-OrCreateUser -FullName "Seed Admin" -Email $AdminEmail -Password $AdminPassword -Role "admin"
$adminToken = $adminAuth.access_token
$adminUser = $adminAuth.user

$teacherAuth = Get-OrCreateUser -FullName "Seed Coordinator Teacher" -Email $TeacherEmail -Password $TeacherPassword -Role "teacher"
$teacherUser = $teacherAuth.user

$studentAuth = Get-OrCreateUser -FullName "Seed Student" -Email $StudentEmail -Password $StudentPassword -Role "student"
$studentUser = $studentAuth.user

$courses = Invoke-Api -Method "GET" -Path "/courses/?skip=0&limit=100" -Token $adminToken
$course = Find-ByField -Rows $courses -Field "code" -Value "BTECH-CSE"
if (-not $course) {
  $course = Invoke-Api -Method "POST" -Path "/courses/" -Token $adminToken -Body @{
    name = "B.Tech Computer Science"
    code = "BTECH-CSE"
    description = "Seeded course for baseline checks"
  }
}

$years = Invoke-Api -Method "GET" -Path "/years/?course_id=$($course.id)&skip=0&limit=100" -Token $adminToken
$year = $null
foreach ($item in $years) {
  if ($item.year_number -eq 4) { $year = $item; break }
}
if (-not $year) {
  $year = Invoke-Api -Method "POST" -Path "/years/" -Token $adminToken -Body @{
    course_id = $course.id
    year_number = 4
    label = "Fourth Year"
  }
}

$classes = Invoke-Api -Method "GET" -Path "/sections/?course_id=$($course.id)&year_id=$($year.id)&skip=0&limit=100" -Token $adminToken
$class = Find-ByField -Rows $classes -Field "name" -Value "CSE-4-A"
if (-not $class) {
  $class = Invoke-Api -Method "POST" -Path "/sections/" -Token $adminToken -Body @{
    course_id = $course.id
    year_id = $year.id
    name = "CSE-4-A"
    faculty_name = "Engineering"
    branch_name = "Computer Science"
    class_coordinator_user_id = $teacherUser.id
  }
}

# Ensure teacher has class coordinator extension and this class scope (best effort).
try {
  $null = Invoke-Api -Method "PATCH" -Path "/users/$($teacherUser.id)/extensions" -Token $adminToken -Body @{
    extended_roles = @("class_coordinator")
    role_scope = @{
      class_coordinator = @{
        class_id = $class.id
      }
    }
  }
} catch {
  Write-Host "WARN: Could not assign class coordinator extension via API. Continuing with baseline seed."
}

# Ensure class links to teacher as coordinator.
try {
  $class = Invoke-Api -Method "PUT" -Path "/sections/$($class.id)" -Token $adminToken -Body @{
    class_coordinator_user_id = $teacherUser.id
  }
} catch {
  Write-Host "WARN: Could not update class coordinator on section. Continuing."
}

$subjects = Invoke-Api -Method "GET" -Path "/subjects/?skip=0&limit=100" -Token $adminToken
$subject = Find-ByField -Rows $subjects -Field "code" -Value "CSE401"
if (-not $subject) {
  $subject = Invoke-Api -Method "POST" -Path "/subjects/" -Token $adminToken -Body @{
    name = "Machine Learning"
    code = "CSE401"
    description = "Seeded subject for timetable validation"
  }
}

$students = Invoke-Api -Method "GET" -Path "/students/?skip=0&limit=100" -Token $adminToken
$studentProfile = Find-ByField -Rows $students -Field "roll_number" -Value "EN22CS9999"
if (-not $studentProfile) {
  $studentProfile = Invoke-Api -Method "POST" -Path "/students/" -Token $adminToken -Body @{
    full_name = $studentUser.full_name
    roll_number = "EN22CS9999"
    email = $studentUser.email
    class_id = $class.id
  }
}

$enrollments = Invoke-Api -Method "GET" -Path "/enrollments/?class_id=$($class.id)&skip=0&limit=100" -Token $adminToken
$alreadyEnrolled = $false
foreach ($en in $enrollments) {
  if ($en.student_id -eq $studentProfile.id) { $alreadyEnrolled = $true; break }
}
if (-not $alreadyEnrolled) {
  $null = Invoke-Api -Method "POST" -Path "/enrollments/" -Token $adminToken -Body @{
    class_id = $class.id
    student_id = $studentProfile.id
  }
}

# Ensure one published timetable exists for this section and semester.
$classTimetables = Invoke-Api -Method "GET" -Path "/timetables/class/$($class.id)?status=published" -Token $adminToken
$hasPublished = $false
foreach ($tt in $classTimetables) {
  if ($tt.semester -eq "8") { $hasPublished = $true; break }
}
if (-not $hasPublished) {
  $draft = Invoke-Api -Method "POST" -Path "/timetables/" -Token $adminToken -Body @{
    class_id = $class.id
    semester = "8"
    shift_id = "shift_1"
    days = @("Monday","Tuesday","Wednesday","Thursday","Friday")
    entries = @(
      @{
        day = "Monday"
        slot_key = "p1"
        subject_id = $subject.id
        teacher_user_id = $teacherUser.id
        room_code = "CSE-LAB-1"
        session_type = "theory"
      }
    )
  }
  $null = Invoke-Api -Method "POST" -Path "/timetables/$($draft.id)/publish" -Token $adminToken
}

Write-Host ""
Write-Host "Seed complete."
Write-Host "Admin:   $AdminEmail / $AdminPassword"
Write-Host "Teacher: $TeacherEmail / $TeacherPassword"
Write-Host "Student: $StudentEmail / $StudentPassword"
~~~

## scripts/smoke_check_stack.ps1
~~~powershell
param(
  [string]$BaseUrl = "http://localhost:8000/api/v1",
  [string]$AdminEmail = "admin.seed@caps.local",
  [string]$AdminPassword = "Admin@12345",
  [string]$StudentEmail = "student.seed@caps.local",
  [string]$StudentPassword = "Student@12345"
)

$ErrorActionPreference = "Stop"

function Unwrap-Api {
  param([object]$Response)
  if ($null -eq $Response) { return $null }
  if ($Response.PSObject.Properties.Name -contains "success" -and $Response.success -eq $true -and $Response.PSObject.Properties.Name -contains "data") {
    return $Response.data
  }
  return $Response
}

function Invoke-Api {
  param(
    [string]$Method,
    [string]$Url,
    [object]$Body = $null,
    [hashtable]$Headers = @{}
  )
  if ($null -ne $Body) {
    $json = $Body | ConvertTo-Json -Depth 12
    $resp = Invoke-RestMethod -Method $Method -Uri $Url -Headers $Headers -ContentType "application/json" -Body $json
  } else {
    $resp = Invoke-RestMethod -Method $Method -Uri $Url -Headers $Headers
  }
  return (Unwrap-Api -Response $resp)
}

$checks = @()

try {
  $health = Invoke-Api -Method "GET" -Url "http://localhost:8000/health"
  $checks += [pscustomobject]@{ Check = "health"; Result = "PASS"; Detail = ($health | ConvertTo-Json -Compress) }
} catch {
  $checks += [pscustomobject]@{ Check = "health"; Result = "FAIL"; Detail = $_.Exception.Message }
}

$adminToken = $null
try {
  $adminLogin = Invoke-Api -Method "POST" -Url "$BaseUrl/auth/login" -Body @{
    email = $AdminEmail
    password = $AdminPassword
  }
  $adminToken = $adminLogin.access_token
  $checks += [pscustomobject]@{ Check = "admin_login"; Result = "PASS"; Detail = "token received" }
} catch {
  $checks += [pscustomobject]@{ Check = "admin_login"; Result = "FAIL"; Detail = $_.Exception.Message }
}

if ($adminToken) {
  try {
    $me = Invoke-Api -Method "GET" -Url "$BaseUrl/auth/me" -Headers @{ Authorization = "Bearer $adminToken" }
    $checks += [pscustomobject]@{ Check = "auth_me"; Result = "PASS"; Detail = "$($me.email) ($($me.role))" }
  } catch {
    $checks += [pscustomobject]@{ Check = "auth_me"; Result = "FAIL"; Detail = $_.Exception.Message }
  }

  try {
    $shifts = Invoke-Api -Method "GET" -Url "$BaseUrl/timetables/shifts" -Headers @{ Authorization = "Bearer $adminToken" }
    $count = @($shifts.shifts).Count
    $checks += [pscustomobject]@{ Check = "timetable_shifts"; Result = "PASS"; Detail = "count=$count" }
  } catch {
    $checks += [pscustomobject]@{ Check = "timetable_shifts"; Result = "FAIL"; Detail = $_.Exception.Message }
  }

  try {
    $lookups = Invoke-Api -Method "GET" -Url "$BaseUrl/timetables/lookups" -Headers @{ Authorization = "Bearer $adminToken" }
    $checks += [pscustomobject]@{
      Check = "timetable_lookups"
      Result = "PASS"
      Detail = "classes=$(@($lookups.classes).Count), subjects=$(@($lookups.subjects).Count), teachers=$(@($lookups.teachers).Count)"
    }
  } catch {
    $checks += [pscustomobject]@{ Check = "timetable_lookups"; Result = "FAIL"; Detail = $_.Exception.Message }
  }
}

try {
  $studentLogin = Invoke-Api -Method "POST" -Url "$BaseUrl/auth/login" -Body @{
    email = $StudentEmail
    password = $StudentPassword
  }
  $studentToken = $studentLogin.access_token
  $myTimetable = Invoke-Api -Method "GET" -Url "$BaseUrl/timetables/my?semester=8" -Headers @{ Authorization = "Bearer $studentToken" }
  $checks += [pscustomobject]@{
    Check = "student_timetable_my"
    Result = "PASS"
    Detail = "class_id=$($myTimetable.class_id), status=$($myTimetable.status), version=$($myTimetable.version)"
  }
} catch {
  $checks += [pscustomobject]@{ Check = "student_timetable_my"; Result = "FAIL"; Detail = $_.Exception.Message }
}

Write-Host "==> Smoke check results"
$checks | Format-Table -AutoSize

$failed = @($checks | Where-Object { $_.Result -eq "FAIL" })
if ($failed.Count -gt 0) {
  exit 1
}
exit 0
~~~

## scripts/README.md
~~~markdown
Utility scripts for local development and setup.

Available scripts:

- `python scripts/seed_medicaps_courses.py`
  - Upserts Medi-Caps course catalog and deactivates non-catalog courses.
- `python scripts/seed_medicaps_years.py`
  - Creates year records for active courses based on duration rules.
- `python scripts/seed_medicaps_departments_branches.py`
  - Upserts Medi-Caps departments/faculties and their branches/specializations.
- `powershell -ExecutionPolicy Bypass -File scripts/seed_minimum_stack.ps1`
  - Creates/updates a minimum runnable stack dataset:
    - admin, class coordinator teacher, student
    - course/year/section, subject
    - enrollment and published timetable baseline
- `powershell -ExecutionPolicy Bypass -File scripts/smoke_check_stack.ps1`
  - Validates backend smoke flow:
    - health check
    - login + `/auth/me`
    - timetable shifts/lookups
    - student `/timetables/my`
- `powershell -ExecutionPolicy Bypass -File scripts/migrate_to_azure_aks.ps1 ...`
  - End-to-end AKS migration automation:
    - optional Azure infrastructure bootstrap (RG + ACR + AKS + attach ACR)
    - optional node-pool hardening (dedicated non-B `System` pool + dedicated `User` pool)
    - Docker build and push to ACR
    - render Azure manifests with real image/domain/secret values
    - deploy and run rollout checks in `caps-ai` namespace
~~~

## backend/tests/test_health.py
~~~python
from fastapi.testclient import TestClient
from app.main import app
def test_health_check() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("x-request-id")
~~~

