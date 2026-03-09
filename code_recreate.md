# code_recreate.md

This file contains critical CAPS_AI recreate code snapshots from the current repository state.
Generated on: 2026-03-05 10:42:09 +05:30.

## Included Files
- PROJECT_RECREATE_GUIDE.md
- README.md
- docs/DEPLOYMENT_CHECKLIST.md
- docker-compose.yml
- k8s-namespace.yaml
- k8s-secrets.yaml
- k8s-configmap.yaml
- k8s-uploads-pvc.yaml
- k8s-redis.yaml
- k8s-mongodb.yaml
- k8s-backend.yaml
- k8s-frontend.yaml
- k8s-ingress.yaml
- backend/.env.example
- backend/.env.production
- frontend/.env.example
- frontend/.env.production
- frontend/nginx.conf
- frontend/src/services/apiClient.js
- frontend/src/pages/AcademicStructurePage.jsx
- frontend/src/pages/LoginPage.jsx
- scripts/seed_minimum_stack.ps1
- scripts/smoke_check_stack.ps1
- scripts/README.md

## PROJECT_RECREATE_GUIDE.md
~~~markdown
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
- Docker Desktop (recommended for full stack run)

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

## Docker Deployment (Primary)

Run the complete stack from repo root:

```bash
docker compose up -d --build
docker compose ps
```

Verify:

```bash
curl http://localhost:8000/health
curl http://localhost:5173
```

Stop stack:

```bash
docker compose down
```

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

## Kubernetes (Optional)

Base manifests are available in repo root as `k8s-*.yaml`.

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

## 7. Docker Release Checklist

- Confirm Docker Desktop is running.
- Rebuild and start stack:
  - `docker compose up -d --build`
- Verify containers:
  - `docker compose ps`
- Verify backend health:
  - `GET http://localhost:8000/health`
- Verify frontend:
  - `http://localhost:5173`

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
VITE_GOOGLE_AUTH_URL=
VITE_GOOGLE_OAUTH_CLIENT_ID=
VITE_GOOGLE_OAUTH_REDIRECT_URI=
VITE_GOOGLE_OAUTH_SCOPE=openid email profile
VITE_AUTH_IDLE_TIMEOUT_MINUTES=30
VITE_AUTH_MAX_SESSION_HOURS=8

~~~

## frontend/.env.production
~~~
VITE_API_BASE_URL=/api/v1
VITE_GOOGLE_AUTH_URL=
VITE_GOOGLE_OAUTH_CLIENT_ID=
VITE_GOOGLE_OAUTH_REDIRECT_URI=
VITE_GOOGLE_OAUTH_SCOPE=openid email profile
VITE_AUTH_IDLE_TIMEOUT_MINUTES=30
VITE_AUTH_MAX_SESSION_HOURS=8

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
export const USER_KEY = 'caps_ai_user';
const MAX_TRACE_ENTRIES = 100;
const traceEntries = [];

function getSessionStore() {
  try {
    return globalThis.sessionStorage || null;
  } catch {
    return null;
  }
}

function removeLegacyLocalValue(key) {
  try {
    globalThis.localStorage?.removeItem(key);
  } catch {
    // Ignore legacy storage cleanup failures.
  }
}

export function readAuthStorage(key) {
  const store = getSessionStore();
  return store?.getItem(key) || '';
}

export function writeAuthStorage(key, value) {
  const store = getSessionStore();
  if (store) {
    store.setItem(key, value);
  }
  removeLegacyLocalValue(key);
}

export function removeAuthStorage(key) {
  const store = getSessionStore();
  store?.removeItem(key);
  removeLegacyLocalValue(key);
}

export function clearAuthStorage() {
  removeAuthStorage(TOKEN_KEY);
  removeAuthStorage(REFRESH_TOKEN_KEY);
  removeAuthStorage(USER_KEY);
}

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
  const token = readAuthStorage(TOKEN_KEY);
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
      const refreshToken = readAuthStorage(REFRESH_TOKEN_KEY);
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
            writeAuthStorage(TOKEN_KEY, nextAccessToken);
            originalRequest.headers = originalRequest.headers || {};
            originalRequest.headers.Authorization = `Bearer ${nextAccessToken}`;
          }
          if (nextRefreshToken) {
            writeAuthStorage(REFRESH_TOKEN_KEY, nextRefreshToken);
          }
          return apiClient(originalRequest);
        } catch {
          clearAuthStorage();
        }
      }
    }
    return Promise.reject(error);
  }
);

~~~

## frontend/src/pages/AcademicStructurePage.jsx
~~~jsx
import { useEffect, useMemo, useState } from 'react';
import { BookOpen, Building2, CalendarDays, GraduationCap, Layers3, Plus, Search, School } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import Card from '../components/ui/Card';
import Table from '../components/ui/Table';
import { apiClient } from '../services/apiClient';
import { FEATURE_ACCESS } from '../config/featureAccess';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { formatApiError } from '../utils/apiError';
import { canAccessFeature } from '../utils/permissions';

const TABS = [
  { key: 'faculties', label: 'Faculties', icon: Building2, addRoute: '/faculties', addLabel: 'Add New Faculty', feature: 'faculties' },
  { key: 'departments', label: 'Departments', icon: Building2, addRoute: '/departments', addLabel: 'Add New Department', feature: 'departments' },
  { key: 'programs', label: 'Programs', icon: BookOpen, addRoute: '/programs', addLabel: 'Add New Program', feature: 'programs' },
  { key: 'specializations', label: 'Specializations', icon: Layers3, addRoute: '/specializations', addLabel: 'Add New Specialization', feature: 'specializations' },
  { key: 'batches', label: 'Batches', icon: GraduationCap, addRoute: '/batches', addLabel: 'Add New Batch', feature: 'batches' },
  { key: 'semesters', label: 'Semesters', icon: CalendarDays, addRoute: '/semesters', addLabel: 'Add New Semester', feature: 'semesters' },
  {
    key: 'sections',
    label: 'Sections',
    icon: School,
    addRoute: '/sections',
    addLabel: 'Add New Section',
    feature: 'sections'
  }
];

export default function AcademicStructurePage() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { pushToast } = useToast();
  const [faculties, setFaculties] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [programs, setPrograms] = useState([]);
  const [specializations, setSpecializations] = useState([]);
  const [batches, setBatches] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('sections');
  const [query, setQuery] = useState('');

  async function safeList(path) {
    const pageSize = 100;
    const maxPages = 20;
    const collected = [];
    try {
      for (let page = 0; page < maxPages; page += 1) {
        const response = await apiClient.get(path, { params: { skip: page * pageSize, limit: pageSize } });
        const items = Array.isArray(response.data) ? response.data : [];
        collected.push(...items);
        if (items.length < pageSize) break;
      }
      return collected;
    } catch {
      return [];
    }
  }

  async function loadStructure() {
    setLoading(true);
    setError('');
    try {
      const [facultiesRes, departmentsRes, programsRes, specializationsRes, batchesRes, semestersRes, sectionsRes] = await Promise.all([
        safeList('/faculties/'),
        safeList('/departments/'),
        safeList('/programs/'),
        safeList('/specializations/'),
        safeList('/batches/'),
        safeList('/semesters/'),
        safeList('/sections/')
      ]);
      setFaculties(facultiesRes);
      setDepartments(departmentsRes);
      setPrograms(programsRes);
      setSpecializations(specializationsRes);
      setBatches(batchesRes);
      setSemesters(semestersRes);
      setSections(sectionsRes);
    } catch (err) {
      const message = formatApiError(err, 'Failed to load academic hierarchy');
      setError(message);
      pushToast({ title: 'Load failed', description: message, variant: 'error' });
      setFaculties([]);
      setDepartments([]);
      setPrograms([]);
      setSpecializations([]);
      setBatches([]);
      setSemesters([]);
      setSections([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadStructure();
  }, []);

  const tabRows = useMemo(() => {
    if (activeTab === 'faculties') {
      return faculties.map((item) => ({
        id: item.id,
        name: item.name,
        code: item.code || '-',
        status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
      }));
    }
    if (activeTab === 'departments') {
      return departments.map((item) => ({
        id: item.id,
        name: item.name,
        code: item.code || '-',
        status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
      }));
    }
    if (activeTab === 'programs') {
      return programs.map((item) => ({
        id: item.id,
        name: item.name,
        code: item.code || '-',
        status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
      }));
    }
    if (activeTab === 'specializations') {
      return specializations.map((item) => ({
        id: item.id,
        name: item.name,
        code: item.code || '-',
        status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
      }));
    }
    if (activeTab === 'batches') {
      return batches.map((item) => ({
        id: item.id,
        name: item.name,
        code: item.code || '-',
        status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
      }));
    }
    if (activeTab === 'semesters') {
      return semesters.map((item) => ({
        id: item.id,
        name: item.label,
        code: `S${item.semester_number}`,
        status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
      }));
    }
    return sections.map((item) => ({
      id: item.id,
      name: item.name,
      code: item.branch_name || '-',
      status: item.is_active === false ? 'INACTIVE' : 'ACTIVE'
    }));
  }, [activeTab, faculties, departments, programs, specializations, batches, semesters, sections]);

  const filteredRows = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return tabRows;
    return tabRows.filter((row) =>
      [row.name, row.code, row.status].some((v) => String(v || '').toLowerCase().includes(q))
    );
  }, [query, tabRows]);

  const columns = useMemo(
    () => [
      { key: 'name', label: 'Name' },
      {
        key: 'code',
        label: 'Code',
        render: (row) => (
          <span className="rounded-lg bg-slate-100 px-2 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
            {row.code}
          </span>
        )
      },
      {
        key: 'status',
        label: 'Status',
        render: (row) => (
          <span
            className={`rounded-full px-3 py-1 text-xs font-semibold ${
              row.status === 'ACTIVE'
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/35 dark:text-emerald-300'
                : 'bg-rose-100 text-rose-700 dark:bg-rose-900/35 dark:text-rose-300'
            }`}
          >
            {row.status}
          </span>
        )
      }
    ],
    []
  );

  const activeTabMeta = TABS.find((tab) => tab.key === activeTab) || TABS[0];
  const canManageActiveTab = canAccessFeature(user, FEATURE_ACCESS[activeTabMeta.feature] || {});
  const searchPlaceholder = `Search ${activeTab}...`;

  function handleBlockedRoute() {
    pushToast({
      title: 'Access Restricted',
      description: 'You can view the structure here, but only admins can manage this tab.',
      variant: 'info'
    });
  }

  return (
    <div className="space-y-5 page-fade">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 dark:text-white">Academic Structure</h1>
          <p className="mt-1 text-lg text-slate-500 dark:text-slate-400">Manage your university's core academic hierarchy.</p>
        </div>
        <button
          className="btn-primary !rounded-2xl !px-5 !py-3 disabled:cursor-not-allowed disabled:opacity-50"
          onClick={() => (canManageActiveTab ? navigate(activeTabMeta.addRoute) : handleBlockedRoute())}
          disabled={!canManageActiveTab}
          title={!canManageActiveTab ? 'Only admin can manage this tab' : activeTabMeta.addLabel}
        >
          <Plus size={18} /> {activeTabMeta.addLabel}
        </button>
      </div>

      <Card className="!p-2">
        <div className="grid gap-2 md:grid-cols-2 xl:grid-cols-4">
          {TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`inline-flex items-center justify-center gap-2 rounded-2xl px-4 py-3 text-base font-semibold transition ${
                activeTab === tab.key
                  ? 'bg-white text-brand-700 shadow-soft ring-1 ring-slate-200 dark:bg-slate-800 dark:ring-slate-700'
                  : 'text-slate-500 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800'
              }`}
            >
              <tab.icon size={18} /> {tab.label}
            </button>
          ))}
        </div>
      </Card>

      <Card className="space-y-4">
        <label className="relative block max-w-xl">
          <Search size={18} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            className="input !h-12 !rounded-2xl !pl-11"
            placeholder={searchPlaceholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>

        {loading ? <p className="text-sm text-slate-500">Loading structure...</p> : null}
        {error ? <p className="text-sm text-rose-600">{error}</p> : null}

        <Table
          columns={columns}
          data={filteredRows}
          onEdit={canManageActiveTab ? () => navigate(activeTabMeta.addRoute) : undefined}
          onDelete={
            canManageActiveTab
              ? () =>
                  pushToast({
                    title: 'Use Dedicated Page',
                    description: `Delete ${activeTabMeta.label.toLowerCase()} from ${activeTabMeta.addRoute} page.`,
                    variant: 'info'
                  })
              : undefined
          }
        />
      </Card>
    </div>
  );
}

~~~

## frontend/src/pages/LoginPage.jsx
~~~jsx
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, GraduationCap, Lock, Mail, Sparkles } from 'lucide-react';
import { motion, useMotionValue, useSpring, useTransform } from 'framer-motion';
import Card from '../components/ui/Card';
import { useAuth } from '../hooks/useAuth';
import { useToast } from '../hooks/useToast';
import { pushApiErrorToast } from '../utils/errorToast';

function resolveGoogleAuthUrl() {
  const directUrl = import.meta.env.VITE_GOOGLE_AUTH_URL?.trim();
  if (directUrl) return directUrl;

  const clientId = import.meta.env.VITE_GOOGLE_OAUTH_CLIENT_ID?.trim();
  const redirectUri = import.meta.env.VITE_GOOGLE_OAUTH_REDIRECT_URI?.trim();
  if (!clientId || !redirectUri) return '';

  const scope = import.meta.env.VITE_GOOGLE_OAUTH_SCOPE?.trim() || 'openid email profile';
  const params = new URLSearchParams({
    client_id: clientId,
    redirect_uri: redirectUri,
    response_type: 'code',
    scope,
    access_type: 'offline',
    prompt: 'select_account'
  });
  return `https://accounts.google.com/o/oauth2/v2/auth?${params.toString()}`;
}

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const { pushToast } = useToast();
  const googleAuthUrl = resolveGoogleAuthUrl();
  const [form, setForm] = useState({ email: '', password: '' });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const mouseX = useMotionValue(0);
  const mouseY = useMotionValue(0);
  const springX = useSpring(mouseX, { stiffness: 50, damping: 20 });
  const springY = useSpring(mouseY, { stiffness: 50, damping: 20 });
  const x1 = useTransform(springX, (value) => value);
  const y1 = useTransform(springY, (value) => value);
  const x2 = useTransform(springX, (value) => value * -1.5);
  const y2 = useTransform(springY, (value) => value * -1.5);
  const x3 = useTransform(springX, (value) => value * 0.8);
  const y3 = useTransform(springY, (value) => value * 1.2);

  useEffect(() => {
    function handleMouseMove(event) {
      const { clientX, clientY } = event;
      const { innerWidth, innerHeight } = window;
      mouseX.set((clientX / innerWidth - 0.5) * 50);
      mouseY.set((clientY / innerHeight - 0.5) * 50);
    }

    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, [mouseX, mouseY]);

  function onChange(event) {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  }

  async function onSubmit(event) {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(form.email, form.password);
      pushToast({ title: 'Welcome back', description: 'Login successful.', variant: 'success' });
      navigate('/dashboard', { replace: true });
    } catch (err) {
      const detail = err?.response?.data?.detail || 'Login failed';
      setError(String(detail));
      pushApiErrorToast(pushToast, err, 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  function onGoogleClick() {
    if (googleAuthUrl) {
      globalThis.location.assign(googleAuthUrl);
      return;
    }
    pushToast({
      title: 'Google sign-in unavailable',
      description: 'Set VITE_GOOGLE_AUTH_URL or VITE_GOOGLE_OAUTH_CLIENT_ID + VITE_GOOGLE_OAUTH_REDIRECT_URI.',
      variant: 'info'
    });
  }

  return (
    <main className="auth-shell relative flex min-h-screen items-center justify-center overflow-hidden p-4">
      <div className="absolute inset-0 z-0">
        <div className="auth-wallpaper" />
        <motion.div
          style={{ x: x1, y: y1 }}
          animate={{ scale: [1, 1.1, 1], rotate: [0, 5, 0] }}
          transition={{ duration: 20, repeat: Infinity, ease: 'linear' }}
          className="auth-orb left-[-10%] top-[-10%] h-[600px] w-[600px] bg-cyan-500/10 blur-[120px]"
        />
        <motion.div
          style={{ x: x2, y: y2 }}
          animate={{ scale: [1, 1.2, 1], rotate: [0, -5, 0] }}
          transition={{ duration: 25, repeat: Infinity, ease: 'linear' }}
          className="auth-orb right-[-5%] top-[20%] h-[500px] w-[500px] bg-blue-600/10 blur-[100px]"
        />
        <motion.div
          style={{ x: x3, y: y3 }}
          animate={{ scale: [1, 1.15, 1] }}
          transition={{ duration: 18, repeat: Infinity, ease: 'linear' }}
          className="auth-orb bottom-[-10%] left-[20%] h-[550px] w-[550px] bg-indigo-500/10 blur-[110px]"
        />
      </div>

      <section className="relative z-10 mx-auto grid w-full max-w-6xl items-center gap-12 lg:grid-cols-[1.1fr_0.9fr]">
        <motion.aside
          initial={{ opacity: 0, x: -30 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut' }}
          className="auth-hero hidden space-y-8 lg:block"
        >
          <div className="space-y-4">
            <motion.p
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-semibold uppercase tracking-[0.2em] text-sky-300 backdrop-blur-md"
            >
              <Sparkles size={14} className="animate-pulse" />
              CAPS AI Portal
            </motion.p>
            <h1 className="text-5xl font-bold leading-[1.1] tracking-tight text-white">
              Welcome back.
              <br />
              <span className="bg-gradient-to-r from-sky-400 to-indigo-400 bg-clip-text text-transparent">
                Build smarter classrooms.
              </span>
            </h1>
            <p className="max-w-xl text-lg leading-relaxed text-slate-300/90">
              Access attendance, timetable, evaluations, and AI-assisted workflows from one secure dashboard.
            </p>
          </div>

          <div className="grid gap-4">
            {[
              'Role-aware access for admins, teachers, and students.',
              'Live API + analytics modules with secure token sessions.',
              'Designed for institution-scale operations on Docker and Kubernetes.'
            ].map((text, index) => (
              <motion.div
                key={text}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 + index * 0.1 }}
                className="group flex items-center gap-4 rounded-2xl border border-white/10 bg-white/[0.03] p-4 backdrop-blur-sm transition-colors hover:bg-white/[0.06]"
              >
                <div className="h-2 w-2 rounded-full bg-sky-500 transition-transform group-hover:scale-150" />
                <span className="text-sm text-slate-200">{text}</span>
              </motion.div>
            ))}
          </div>
        </motion.aside>

        <div className="w-full max-w-[460px] justify-self-center lg:justify-self-end">
          <motion.div
            initial={{ opacity: 0, y: 40, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.7, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="mb-8 text-center lg:hidden">
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 260, damping: 20, delay: 0.3 }}
                className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/20"
              >
                <GraduationCap size={32} />
              </motion.div>
              <h1 className="text-3xl font-bold text-white">Welcome Back</h1>
              <p className="mt-2 text-slate-400">Sign in to your CAPS AI account</p>
            </div>

            <Card className="auth-card overflow-hidden !rounded-[2.5rem] !border-white/20 !bg-white/10 !shadow-[0_8px_32px_0_rgba(0,0,0,0.37)] !backdrop-blur-2xl">
              <div className="space-y-7 p-8 sm:p-10">
                <div className="hidden space-y-2 text-center lg:block">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 260, damping: 20, delay: 0.3 }}
                    className="mx-auto mb-4 grid h-16 w-16 place-items-center rounded-2xl bg-gradient-to-br from-sky-500 to-indigo-600 text-white shadow-lg shadow-sky-500/20"
                  >
                    <GraduationCap size={32} />
                  </motion.div>
                  <h1 className="text-3xl font-bold text-white">Welcome Back</h1>
                  <p className="text-slate-400">Sign in to your CAPS AI account</p>
                </div>

                <motion.button
                  whileHover={{ scale: 1.02, backgroundColor: 'rgba(255,255,255,0.15)' }}
                  whileTap={{ scale: 0.98 }}
                  className="flex w-full items-center justify-center gap-3 rounded-2xl border border-white/10 bg-white/10 py-3.5 text-sm font-semibold text-white backdrop-blur-md transition-all"
                  type="button"
                  onClick={onGoogleClick}
                >
                  <div className="grid h-6 w-6 place-items-center rounded-full bg-white text-xs font-bold text-sky-600">G</div>
                  Continue with Google
                </motion.button>

                <div className="flex items-center gap-4 text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">
                  <span className="h-px flex-1 bg-white/10" />
                  or email
                  <span className="h-px flex-1 bg-white/10" />
                </div>

                <form className="space-y-5" onSubmit={onSubmit}>
                  <div className="space-y-2">
                    <label className="ml-1 text-xs font-bold uppercase tracking-wider text-slate-400">Email Address</label>
                    <div className="group relative">
                      <Mail
                        className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 transition-colors group-focus-within:text-sky-400"
                        size={18}
                      />
                      <input
                        className="w-full rounded-2xl border border-white/10 bg-white/5 py-4 pl-12 pr-4 text-sm text-white outline-none transition-all placeholder:text-slate-600 focus:border-sky-500/50 focus:bg-white/10 focus:ring-4 focus:ring-sky-500/10"
                        name="email"
                        type="email"
                        placeholder="name@university.edu"
                        required
                        value={form.email}
                        onChange={onChange}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <div className="ml-1 flex items-center justify-between">
                      <label className="text-xs font-bold uppercase tracking-wider text-slate-400">Password</label>
                      <button className="text-xs font-semibold text-sky-400 transition-colors hover:text-sky-300" type="button" onClick={onGoogleClick}>
                        Forgot?
                      </button>
                    </div>
                    <div className="group relative">
                      <Lock
                        className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-500 transition-colors group-focus-within:text-sky-400"
                        size={18}
                      />
                      <input
                        className="w-full rounded-2xl border border-white/10 bg-white/5 py-4 pl-12 pr-4 text-sm text-white outline-none transition-all placeholder:text-slate-600 focus:border-sky-500/50 focus:bg-white/10 focus:ring-4 focus:ring-sky-500/10"
                        name="password"
                        type="password"
                        placeholder="********"
                        required
                        value={form.password}
                        onChange={onChange}
                      />
                    </div>
                  </div>

                  <motion.button
                    whileHover={{ scale: 1.03, filter: 'brightness(1.1)', boxShadow: '0 0 25px rgba(14, 165, 233, 0.5)' }}
                    whileTap={{ scale: 0.97 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 15 }}
                    className="flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-sky-500 to-indigo-600 py-4 text-sm font-bold text-white shadow-lg transition-all disabled:cursor-not-allowed disabled:opacity-50"
                    type="submit"
                    disabled={loading}
                  >
                    <span>{loading ? 'Signing in...' : 'Sign In'}</span>
                    {!loading ? <ArrowRight size={18} /> : null}
                  </motion.button>
                </form>

                {error ? (
                  <motion.p
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    className="rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-center text-xs font-medium text-rose-400"
                  >
                    {error}
                  </motion.p>
                ) : null}

                <p className="text-center text-[11px] font-medium leading-relaxed text-slate-500">
                  User provisioning is managed by your administrator.
                  <br />
                  Secure access via CAPS AI Infrastructure.
                </p>
              </div>
            </Card>
          </motion.div>
        </div>
      </section>
    </main>
  );
}

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

~~~

