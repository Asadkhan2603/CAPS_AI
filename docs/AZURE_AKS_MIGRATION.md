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
