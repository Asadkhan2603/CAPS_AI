# Deployment Guide

## Overview

This guide describes how CAPS AI is deployed from the current repository state.

The repo currently supports two practical deployment modes:
- local Docker Compose for full-stack local runtime
- Kubernetes manifests at the repo root for cluster deployment

This guide is based on the current deployable assets in the repo:
- [docker-compose.yml](docker-compose.yml)
- [backend/Dockerfile](/backend/Dockerfile)
- [frontend/Dockerfile](/frontend/Dockerfile)
- [frontend/nginx.conf](/frontend/nginx.conf)
- [k8s-namespace.yaml](k8s-namespace.yaml)
- [k8s-configmap.yaml](k8s-configmap.yaml)
- [k8s-secrets.yaml](k8s-secrets.yaml)
- [k8s-mongodb.yaml](k8s-mongodb.yaml)
- [k8s-redis.yaml](k8s-redis.yaml)
- [k8s-backend.yaml](k8s-backend.yaml)
- [k8s-backend-canary.yaml](k8s-backend-canary.yaml)
- [k8s-backend-canary-ingress.yaml](k8s-backend-canary-ingress.yaml)
- [k8s-frontend.yaml](k8s-frontend.yaml)
- [k8s-frontend-canary.yaml](k8s-frontend-canary.yaml)
- [k8s-frontend-canary-ingress.yaml](k8s-frontend-canary-ingress.yaml)
- [k8s-ingress.yaml](k8s-ingress.yaml)
- [k8s-uploads-pvc.yaml](k8s-uploads-pvc.yaml)

## Deployment Topology

### Local Topology

```text
Browser
|-- Frontend container (nginx, port 5173 on host)
`-- Backend container (FastAPI, port 8000 on host)
    |-- MongoDB container
    `-- Redis container
```

### Kubernetes Topology

```text
Ingress
|-- /           -> frontend service -> frontend deployment
`-- /api/v1     -> backend service  -> backend deployment

backend deployment
|-- uses MongoDB service/statefulset
|-- uses Redis service/deployment
`-- mounts uploads PVC

frontend deployment
`-- serves built static app via nginx
```

## Container Build Architecture

### Backend Image

Source:
- [backend/Dockerfile](/backend/Dockerfile)

Build characteristics:
- base image: `python:3.13.12-slim`
- installs runtime dependencies from `requirements.txt`
- copies only `app/`
- serves FastAPI with uvicorn on port `8000`

Entrypoint:
```text
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Implications:
- image is small and direct
- startup assumes dependencies and config are available at runtime
- no separate migration/init image exists

### Frontend Image

Source:
- [frontend/Dockerfile](/frontend/Dockerfile)

Build characteristics:
- multi-stage build
- build stage uses `node:20-alpine`
- runtime stage uses `nginx:1.27-alpine-slim`
- copies built `dist/` into nginx html root
- uses custom nginx config

Runtime nginx config:
- [frontend/nginx.conf](/frontend/nginx.conf)

Current behavior:
- serves SPA static assets
- proxies `/api/v1` to backend service name `backend:8000`
- falls back to `index.html` for client-side routes

## Local Docker Compose Deployment

Primary file:
- [docker-compose.yml](docker-compose.yml)

### Services

Compose defines four services:
- `mongodb`
- `redis`
- `backend`
- `frontend`

### Runtime Ports

- MongoDB -> `27017:27017`
- Redis -> `6379:6379`
- Backend -> `8000:8000`
- Frontend -> `5173:80`

### Volume Usage

Persistent/local volumes:
- named volume `mongo_data` for MongoDB
- bind mount `./uploads:/app/uploads` for backend uploads

### Environment Wiring

Backend runtime env file:
- `./backend/.env.production`

Current consequence:
- Compose local runtime behaves closer to production config than a pure dev-only setup
- local mistakes in production env values can break local runs

### Compose Startup

```powershell
docker compose up -d --build
```

### Compose Verification

Backend:
```powershell
Invoke-WebRequest http://localhost:8000/health
```

Frontend:
- open `http://localhost:5173`

Suggested local verification order:
1. confirm all containers are up
2. hit `/health`
3. verify login page loads
4. verify one authenticated flow
5. verify frontend can reach `/api/v1`

Suggested release-governance verification:
1. run `python scripts/perf_smoke.py`
2. run `python scripts/release_gate.py`
3. after deployment, run `python scripts/release_gate.py --base-url <api-root> --bearer-token <token>`

### Staged Canary Rollout

The repo now includes explicit canary deployment support for both backend and frontend:

- [k8s-backend-canary.yaml](k8s-backend-canary.yaml)
- [k8s-backend-canary-ingress.yaml](k8s-backend-canary-ingress.yaml)
- [k8s-frontend-canary.yaml](k8s-frontend-canary.yaml)
- [k8s-frontend-canary-ingress.yaml](k8s-frontend-canary-ingress.yaml)

Primary controller:

```powershell
python scripts/canary_rollout.py backend prepare --image <image> --base-url <api-root> --bearer-token <token>
python scripts/canary_rollout.py backend promote --image <image> --base-url <api-root> --bearer-token <token>
python scripts/canary_rollout.py backend rollback --base-url <api-root> --bearer-token <token>
```

Behavior:

1. `prepare`
2. apply canary deployment and ingress
3. set canary image
4. wait for rollout readiness
5. set canary traffic weight
6. run the remote release gate for backend canaries

`promote`

1. update the stable deployment image
2. wait for rollout readiness
3. run the remote release gate
4. set canary traffic back to `0`
5. scale the canary deployment down

`rollback`

1. set canary traffic to `0`
2. scale the canary deployment down
3. rerun the release gate to confirm recovery

Use `--print-only` first if you want to inspect the exact `kubectl` commands before execution.

### Compose Strengths

- fastest full-stack local reproduction path
- backend and frontend images are the same artifact shape used for container deployment
- nginx proxy path is already wired for `/api/v1`

### Compose Risks

- uploads still depend on local filesystem path
- production env file reuse can hide local configuration mistakes until runtime
- no readiness orchestration beyond Compose dependency order

## Standalone Local Developer Run

### Backend

```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Frontend

```powershell
cd frontend
npm install
npm run dev
```

Use this mode when:
- changing frontend UI rapidly
- debugging backend route behavior with autoreload
- avoiding image rebuild loops

## Kubernetes Deployment Architecture

### Namespace

Namespace manifest:
- [k8s-namespace.yaml](k8s-namespace.yaml)

Namespace:
- `caps-ai`

### Config And Secret Layer

Config map file:
- [k8s-configmap.yaml](k8s-configmap.yaml)

Defined configmaps:
- `backend-config`
- `frontend-config`
- `nginx-config`

Secret file:
- [k8s-secrets.yaml](k8s-secrets.yaml)

Defined secret:
- `backend-secrets`

Current important backend config values in Kubernetes:
- `ENVIRONMENT=production`
- `API_PREFIX=/api/v1`
- `MONGODB_URL=mongodb://mongodb:27017`
- `MONGODB_DB=caps_ai`
- `REDIS_ENABLED=true`
- `REDIS_URL=redis://redis:6379/0`
- `RESPONSE_ENVELOPE_ENABLED=true`
- `SCHEDULER_ENABLED=true`
- CORS origins include example domain and localhost

Current secrets expected:
- `JWT_SECRET`
- `OPENAI_API_KEY`
- `CLOUDINARY_CLOUD_NAME`
- `CLOUDINARY_API_KEY`
- `CLOUDINARY_API_SECRET`

Important deployment rule:
- the placeholder JWT secret in the manifest must be replaced before real deployment

### MongoDB Runtime

Manifest:
- [k8s-mongodb.yaml](k8s-mongodb.yaml)

Current topology:
- headless service `mongodb`
- statefulset with `1` replica
- per-pod PVC via `volumeClaimTemplates`
- `10Gi` requested storage
- TCP liveness and readiness probes on `27017`

### Redis Runtime

Manifest:
- [k8s-redis.yaml](k8s-redis.yaml)

Current topology:
- ClusterIP service `redis`
- deployment with `1` replica
- TCP liveness and readiness probes on `6379`

### Backend Runtime

Manifest:
- [k8s-backend.yaml](k8s-backend.yaml)

Current backend topology:
- ClusterIP service on port `8000`
- deployment with `2` replicas
- image `caps_ai-backend:latest`
- `IfNotPresent` pull policy
- config from `backend-config` and `backend-secrets`
- PVC mount at `/app/uploads`
- init containers waiting for MongoDB and Redis
- liveness/readiness probes on `/health`

Current resource settings:
- requests: `250m CPU`, `512Mi memory`
- limits: `500m CPU`, `1Gi memory`

Important operational consequence:
- scheduler is enabled in config while backend is multi-replica
- correctness therefore depends on scheduler leader-election lock behavior

### Frontend Runtime

Manifest:
- [k8s-frontend.yaml](k8s-frontend.yaml)

Current frontend topology:
- ClusterIP service on port `80`
- deployment with `2` replicas
- image `caps_ai-frontend:latest`
- liveness/readiness probes on `/`

Current resource settings:
- requests: `100m CPU`, `256Mi memory`
- limits: `250m CPU`, `512Mi memory`

### Ingress Runtime

Manifest:
- [k8s-ingress.yaml](k8s-ingress.yaml)

Current ingress behavior:
- host-based routing for `caps-ai.example.com`
- `/api/v1` -> backend service port `8000`
- `/` -> frontend service port `80`
- TLS configured via `caps-ai-tls`
- nginx ingress class annotation present
- cert-manager issuer annotation present

## Kubernetes Apply Order

Recommended order:
1. namespace
2. configmaps and secrets
3. MongoDB and Redis
4. uploads PVC
5. backend and frontend
6. ingress

Example:
```powershell
kubectl apply -f k8s-namespace.yaml
kubectl apply -f k8s-configmap.yaml
kubectl apply -f k8s-secrets.yaml
kubectl apply -f k8s-mongodb.yaml
kubectl apply -f k8s-redis.yaml
kubectl apply -f k8s-uploads-pvc.yaml
kubectl apply -f k8s-backend.yaml
kubectl apply -f k8s-frontend.yaml
kubectl apply -f k8s-ingress.yaml
```

## Kubernetes Validation Workflow

### Basic Resource Checks

```powershell
kubectl get ns
kubectl get pods -n caps-ai
kubectl get svc -n caps-ai
kubectl get ingress -n caps-ai
kubectl get pvc -n caps-ai
```

### Rollout Checks

```powershell
kubectl rollout status deployment/backend -n caps-ai
kubectl rollout status deployment/frontend -n caps-ai
kubectl rollout status deployment/redis -n caps-ai
kubectl rollout status statefulset/mongodb -n caps-ai
```

### Probe And Event Checks

```powershell
kubectl describe pod -n caps-ai <pod-name>
kubectl logs -n caps-ai deployment/backend
kubectl logs -n caps-ai deployment/frontend
```

### Traffic Validation

Validate:
1. ingress host resolves
2. `/` serves frontend
3. `/api/v1/...` reaches backend
4. backend `/health` succeeds
5. login and one authenticated route work end-to-end

## Current Manifest Gaps And Risks

These are not theoretical. They are visible in the current repo state.

### 1. Frontend ConfigMap Is Defined But Not Consumed

`k8s-configmap.yaml` defines:
- `frontend-config`
- `nginx-config`

But [k8s-frontend.yaml](k8s-frontend.yaml) currently does not mount or consume those configmaps.

Practical effect:
- runtime nginx config in the frontend pod comes from the baked image, not the cluster configmap
- `frontend-config` values are not injected into the static app at runtime

### 2. Static Frontend Env Is Build-Time, Not Runtime

Because the frontend is built to static files and served by nginx:
- Vite env values are baked at build time
- a Kubernetes ConfigMap alone does not mutate the built bundle unless an explicit runtime injection strategy exists

Practical effect:
- changing `frontend-config` after build does not automatically reconfigure the SPA

### 3. Upload Durability Still Depends On Filesystem Strategy

Backend mounts `/app/uploads` to a PVC in Kubernetes and to a host bind mount in Compose.

Practical effect:
- file durability is better than container-local ephemeral storage
- but the broader file architecture is still mixed with local filesystem assumptions

### 4. Scheduler Runs Inside Backend App Pods

Current configuration enables scheduler while backend has 2 replicas.

Practical effect:
- if leader election fails or is misconfigured, background jobs may duplicate
- deployment verification must include scheduler behavior, not only pod health

### 5. Example Ingress Host Is Placeholder

Current ingress host:
- `caps-ai.example.com`

Practical effect:
- real deployments must replace this host and TLS secret alignment must be verified

### 6. Secret Defaults Are Not Safe For Real Deployment

Current secret manifest contains placeholder JWT secret and empty optional secrets.

Practical effect:
- cluster deployment should not proceed with default placeholder secret material

## Environment Contract For Deployment

### Backend Critical Variables

Must be correct for any serious deployment:
- `ENVIRONMENT`
- `APP_NAME`
- `APP_VERSION`
- `API_PREFIX`
- `MONGODB_URL`
- `MONGODB_DB`
- `JWT_SECRET`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `REFRESH_TOKEN_EXPIRE_DAYS`
- `AUTH_REGISTRATION_POLICY`
- `REDIS_ENABLED`
- `REDIS_URL`
- `SCHEDULER_ENABLED`
- `CORS_ORIGINS`

Feature-dependent values:
- OpenAI settings for AI features
- Cloudinary settings if remote media upload is required

### Frontend Critical Variables

At build time or runtime strategy layer:
- `VITE_API_BASE_URL`
- Google auth client values if Google sign-in is enabled

## Deployment Verification Checklist

### Minimum Local Checklist

1. `docker compose up -d --build`
2. backend health responds
3. frontend login page loads
4. login works
5. one protected route loads
6. backend file write path exists for uploads

### Minimum Kubernetes Checklist

1. namespace exists
2. MongoDB ready
3. Redis ready
4. backend rollout healthy
5. frontend rollout healthy
6. ingress has address/host mapping
7. `/health` succeeds through expected path
8. browser login flow works
9. scheduler jobs behave once, not per replica
10. upload PVC is bound and mounted

## Recommended Deployment Modes By Use Case

### Use Docker Compose When

- developing locally
- validating frontend/backend integration quickly
- reproducing auth or API routing issues locally
- testing without cluster overhead

### Use Kubernetes When

- validating ingress behavior
- testing replica behavior
- testing PVC-backed uploads
- validating scheduler leadership under multi-pod conditions
- exercising environment separation closer to production

## Deployment Summary

The current deployment architecture is a pragmatic containerized monolith setup:
- one backend service
- one frontend static app
- MongoDB and Redis as supporting services
- optional cluster ingress for browser traffic

The deployment model is workable today. The main risks are not missing manifests. The main risks are:
- runtime/frontend config injection mismatch
- mixed file storage assumptions
- scheduler correctness under replica scaling
- placeholder secret and host values in cluster manifests

That means the next deployment improvements should focus on operational correctness and configuration discipline, not on adding more deployment targets.

For release decision rules, risk budgets, and rollback criteria, use [Release Governance](./release-governance.md) alongside this deployment guide.


