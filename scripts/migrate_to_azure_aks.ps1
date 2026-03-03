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
