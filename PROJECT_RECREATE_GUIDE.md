# PROJECT_RECREATE_GUIDE (Master)

Status: authoritative recreate + validation guide for CAPS_AI.
Last updated: 2026-03-05 (Asia/Calcutta).

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

## 6. Docker-only deployment policy
- Primary runtime for this project is Docker Compose.
- Cloud-variant manifests and automation are removed from active usage.
- Kubernetes YAMLs remain optional and cloud-neutral.

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

### 2026-03-05 (Docker-only migration)
- Changed:
  - `README.md`
  - `PROJECT_RECREATE_GUIDE.md`
  - `docs/DEPLOYMENT_CHECKLIST.md`
  - `scripts/README.md`
  - cloud variant manifests and migration docs/scripts (removed)
- Reason:
  - Shifted project operations to Docker-first deployment and retired cloud-specific artifacts.
- Validation:
  - Project cloud resource groups deletion initiated:
    - `caps-ai-rg` deleted.
    - `caps-ai-rg-sea` state `Deleting`.
    - `MC_caps-ai-rg-sea_caps-ai-aks-sea_southeastasia` state `Deleting`.

## 12. Code snapshot file
All critical recreate code/config snapshots are stored in:
- `code_recreate.md`
