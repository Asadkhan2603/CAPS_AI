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
