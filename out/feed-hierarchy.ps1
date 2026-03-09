$ErrorActionPreference = 'Stop'

$base = 'https://20.197.115.29/api/v1'
$email = 'asad_super_admin@caps.ai'
$password = 'Asad@12345'
$excelPath = 'd:\ASAD\Book1.xlsx'

function Invoke-CapsApi {
  param(
    [Parameter(Mandatory = $true)][string]$Method,
    [Parameter(Mandatory = $true)][string]$Url,
    [string]$Token = '',
    $BodyObj = $null
  )

  $outFile = [System.IO.Path]::GetTempFileName()
  $args = @('-k', '-s', '-o', $outFile, '-w', '%{http_code}', '-X', $Method, '-H', 'Content-Type: application/json')
  $bodyFile = $null

  if ($Token) {
    $args += @('-H', "Authorization: Bearer $Token")
  }

  if ($null -ne $BodyObj) {
    $json = $BodyObj | ConvertTo-Json -Depth 20 -Compress
    $bodyFile = [System.IO.Path]::GetTempFileName()
    [System.IO.File]::WriteAllText($bodyFile, $json)
    $args += @('--data-binary', "@$bodyFile")
  }

  $args += $Url
  $statusCode = [int](& curl.exe @args)
  $raw = Get-Content $outFile -Raw

  Remove-Item $outFile -Force -ErrorAction SilentlyContinue
  if ($bodyFile) { Remove-Item $bodyFile -Force -ErrorAction SilentlyContinue }

  $jsonObj = $null
  if ($raw) {
    try { $jsonObj = $raw | ConvertFrom-Json } catch { $jsonObj = $null }
  }

  return [pscustomobject]@{
    Status = $statusCode
    Raw = $raw
    Json = $jsonObj
  }
}

function Get-ApiData {
  param($Response)
  if ($null -eq $Response.Json) { return $null }
  if ($Response.Json.PSObject.Properties.Name -contains 'data') {
    return $Response.Json.data
  }
  return $Response.Json
}

function To-Array {
  param($Value)
  if ($null -eq $Value) { return @() }
  if ($Value -is [System.Array]) { return $Value }
  if ($Value -is [string]) { return @($Value) }
  if ($Value.GetType().Name -eq 'PSCustomObject') { return @($Value) }
  if ($Value -is [System.Collections.IEnumerable]) { return @($Value) }
  return @($Value)
}

function Ensure-Success {
  param([string]$Action, $Response, [int[]]$Allowed = @(200, 201))
  if ($Allowed -notcontains $Response.Status) {
    throw "$Action failed. HTTP $($Response.Status). Body: $($Response.Raw)"
  }
}

function Get-All {
  param([string]$Path, [string]$Token)
  $items = @()
  $skip = 0
  $limit = 100
  while ($true) {
    $joiner = if ($Path.Contains('?')) { '&' } else { '?' }
    $url = "$base$Path${joiner}skip=$skip&limit=$limit"
    $resp = Invoke-CapsApi -Method 'GET' -Url $url -Token $Token
    Ensure-Success -Action "GET $Path" -Response $resp -Allowed @(200)
    $page = To-Array (Get-ApiData $resp)
    if ($page.Count -eq 0) { break }
    $items += $page
    if ($page.Count -lt $limit) { break }
    $skip += $limit
  }
  return $items
}

function Make-SpecCode {
  param([string]$ProgramCode, [string]$SpecName)
  $slug = ($SpecName.ToUpper() -replace '[^A-Z0-9]+', '-')
  $slug = $slug.Trim('-')
  if (-not $slug) { $slug = 'SPEC' }

  $md5 = [System.Security.Cryptography.MD5]::Create()
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($SpecName)
  $hashBytes = $md5.ComputeHash($bytes)
  $hash = ([System.BitConverter]::ToString($hashBytes)).Replace('-', '').Substring(0, 6)

  $prefix = "$ProgramCode-SP-"
  $maxSlugLen = 120 - $prefix.Length - 1 - $hash.Length
  if ($maxSlugLen -lt 2) { $maxSlugLen = 2 }
  if ($slug.Length -gt $maxSlugLen) {
    $slug = $slug.Substring(0, $maxSlugLen)
  }

  return "$prefix$slug-$hash"
}

# Login
$loginResp = Invoke-CapsApi -Method 'POST' -Url "$base/auth/login" -BodyObj @{ email = $email; password = $password }
Ensure-Success -Action 'Admin login' -Response $loginResp -Allowed @(200)
$loginData = Get-ApiData $loginResp
$token = [string]$loginData.access_token
if (-not $token) { throw 'Login succeeded but access token missing.' }

# Load existing data
$existingFaculties = Get-All -Path '/faculties/' -Token $token
$existingDepartments = Get-All -Path '/departments/' -Token $token
$existingPrograms = Get-All -Path '/programs/' -Token $token
$existingSpecializations = Get-All -Path '/specializations/' -Token $token

$facultyByCode = @{}
foreach ($x in $existingFaculties) { if ($x.code) { $facultyByCode[[string]$x.code] = $x } }
$departmentByCode = @{}
foreach ($x in $existingDepartments) { if ($x.code) { $departmentByCode[[string]$x.code] = $x } }
$programByCode = @{}
foreach ($x in $existingPrograms) { if ($x.code) { $programByCode[[string]$x.code] = $x } }
$specializationByPair = @{}
$specializationByCode = @{}
foreach ($x in $existingSpecializations) {
  $specializationByCode[[string]$x.code] = $x
  $pairKey = ("{0}|{1}" -f [string]$x.program_id, ([string]$x.name).Trim().ToLowerInvariant())
  $specializationByPair[$pairKey] = $x
}

# Parse workbook
$excel = $null
$wb = $null
$facultyDefs = @{}
$departmentDefs = @{}
$programDefs = @{}
$specializationDefs = @{}

try {
  $excel = New-Object -ComObject Excel.Application
  $excel.Visible = $false
  $excel.DisplayAlerts = $false
  $wb = $excel.Workbooks.Open($excelPath)

  foreach ($ws in $wb.Worksheets) {
    $used = $ws.UsedRange
    $rows = [int]$used.Rows.Count
    if ($rows -lt 2) { continue }

    $headerRow = 0
    for ($r = 1; $r -le [Math]::Min(12, $rows); $r++) {
      $c1 = ([string]$ws.Cells.Item($r, 1).Text).Trim()
      $c3 = ([string]$ws.Cells.Item($r, 3).Text).Trim()
      if ($c1 -match 'Faculty Code' -or $c3 -match 'Dept Code') {
        $headerRow = $r
        break
      }
    }
    if ($headerRow -eq 0) { continue }

    $cfCode = ''; $cfName = ''
    $cdCode = ''; $cdName = ''
    $cpCode = ''; $cpName = ''

    for ($r = $headerRow + 1; $r -le $rows; $r++) {
      $fCode = ([string]$ws.Cells.Item($r, 1).Text).Trim().ToUpper()
      $fName = ([string]$ws.Cells.Item($r, 2).Text).Trim()
      $dCode = ([string]$ws.Cells.Item($r, 3).Text).Trim().ToUpper()
      $dName = ([string]$ws.Cells.Item($r, 4).Text).Trim()
      $pCode = ([string]$ws.Cells.Item($r, 5).Text).Trim().ToUpper()
      $pName = ([string]$ws.Cells.Item($r, 6).Text).Trim()
      $spec = ([string]$ws.Cells.Item($r, 7).Text).Trim()

      if ($fCode) { $cfCode = $fCode }
      if ($fName) { $cfName = $fName }
      if ($dCode) { $cdCode = $dCode }
      if ($dName) { $cdName = $dName }
      if ($pCode) { $cpCode = $pCode }
      if ($pName) { $cpName = $pName }

      if (-not $cfCode -or -not $cfName -or -not $cdCode -or -not $cdName -or -not $cpCode -or -not $cpName) {
        continue
      }

      $facultyDefs[$cfCode] = [pscustomobject]@{ code = $cfCode; name = $cfName }
      $departmentDefs[$cdCode] = [pscustomobject]@{ code = $cdCode; name = $cdName; faculty_code = $cfCode }
      $programDefs[$cpCode] = [pscustomobject]@{ code = $cpCode; name = $cpName; department_code = $cdCode }

      if ($spec -and $spec -ne '—' -and $spec -ne '-') {
        $specKey = ("{0}|{1}" -f $cpCode, $spec.ToLowerInvariant())
        $specializationDefs[$specKey] = [pscustomobject]@{
          program_code = $cpCode
          name = $spec
        }
      }
    }
  }
}
finally {
  if ($wb) { $wb.Close($false) | Out-Null }
  if ($excel) { $excel.Quit() | Out-Null }
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
  [GC]::Collect()
  [GC]::WaitForPendingFinalizers()
}

$stats = [ordered]@{
  faculties_created = 0
  faculties_updated = 0
  faculties_skipped = 0
  departments_created = 0
  departments_updated = 0
  departments_skipped = 0
  programs_created = 0
  programs_updated = 0
  programs_skipped = 0
  specializations_created = 0
  specializations_updated = 0
  specializations_skipped = 0
}

# Faculties
foreach ($code in ($facultyDefs.Keys | Sort-Object)) {
  $def = $facultyDefs[$code]
  if ($facultyByCode.ContainsKey($code)) {
    $current = $facultyByCode[$code]
    $needsUpdate = ($current.name -ne $def.name)
    if ($needsUpdate) {
      $resp = Invoke-CapsApi -Method 'PUT' -Url "$base/faculties/$($current.id)" -Token $token -BodyObj @{ name = $def.name }
      Ensure-Success -Action "Update faculty $code" -Response $resp
      $updated = Get-ApiData $resp
      $facultyByCode[$code] = $updated
      $stats.faculties_updated++
    } else {
      $stats.faculties_skipped++
    }
  } else {
    $resp = Invoke-CapsApi -Method 'POST' -Url "$base/faculties/" -Token $token -BodyObj @{ name = $def.name; code = $def.code }
    Ensure-Success -Action "Create faculty $code" -Response $resp
    $created = Get-ApiData $resp
    $facultyByCode[$code] = $created
    $stats.faculties_created++
  }
}

# Departments
foreach ($code in ($departmentDefs.Keys | Sort-Object)) {
  $def = $departmentDefs[$code]
  if (-not $facultyByCode.ContainsKey($def.faculty_code)) {
    throw "Missing faculty for department $code -> $($def.faculty_code)"
  }
  $facultyId = [string]$facultyByCode[$def.faculty_code].id

  if ($departmentByCode.ContainsKey($code)) {
    $current = $departmentByCode[$code]
    $body = @{}
    if ($current.name -ne $def.name) { $body.name = $def.name }
    if ([string]$current.faculty_id -ne $facultyId) { $body.faculty_id = $facultyId }

    if ($body.Count -gt 0) {
      $resp = Invoke-CapsApi -Method 'PUT' -Url "$base/departments/$($current.id)" -Token $token -BodyObj $body
      Ensure-Success -Action "Update department $code" -Response $resp
      $updated = Get-ApiData $resp
      $departmentByCode[$code] = $updated
      $stats.departments_updated++
    } else {
      $stats.departments_skipped++
    }
  } else {
    $resp = Invoke-CapsApi -Method 'POST' -Url "$base/departments/" -Token $token -BodyObj @{ name = $def.name; code = $def.code; faculty_id = $facultyId }
    Ensure-Success -Action "Create department $code" -Response $resp
    $created = Get-ApiData $resp
    $departmentByCode[$code] = $created
    $stats.departments_created++
  }
}

# Programs
foreach ($code in ($programDefs.Keys | Sort-Object)) {
  $def = $programDefs[$code]
  if (-not $departmentByCode.ContainsKey($def.department_code)) {
    throw "Missing department for program $code -> $($def.department_code)"
  }
  $departmentId = [string]$departmentByCode[$def.department_code].id

  if ($programByCode.ContainsKey($code)) {
    $current = $programByCode[$code]
    $body = @{}
    if ($current.name -ne $def.name) { $body.name = $def.name }
    if ([string]$current.department_id -ne $departmentId) { $body.department_id = $departmentId }

    if ($body.Count -gt 0) {
      $resp = Invoke-CapsApi -Method 'PUT' -Url "$base/programs/$($current.id)" -Token $token -BodyObj $body
      Ensure-Success -Action "Update program $code" -Response $resp
      $updated = Get-ApiData $resp
      $programByCode[$code] = $updated
      $stats.programs_updated++
    } else {
      $stats.programs_skipped++
    }
  } else {
    $resp = Invoke-CapsApi -Method 'POST' -Url "$base/programs/" -Token $token -BodyObj @{ name = $def.name; code = $def.code; department_id = $departmentId }
    Ensure-Success -Action "Create program $code" -Response $resp
    $created = Get-ApiData $resp
    $programByCode[$code] = $created
    $stats.programs_created++
  }
}

# Specializations
foreach ($specKey in ($specializationDefs.Keys | Sort-Object)) {
  $def = $specializationDefs[$specKey]
  if (-not $programByCode.ContainsKey($def.program_code)) {
    throw "Missing program for specialization $($def.name) -> $($def.program_code)"
  }
  $program = $programByCode[$def.program_code]
  $programId = [string]$program.id
  $pairKey = ("{0}|{1}" -f $programId, $def.name.ToLowerInvariant())

  if ($specializationByPair.ContainsKey($pairKey)) {
    $stats.specializations_skipped++
    continue
  }

  $code = Make-SpecCode -ProgramCode $def.program_code -SpecName $def.name
  $candidate = $code
  $suffix = 1
  while ($specializationByCode.ContainsKey($candidate)) {
    $candidate = "$code-$suffix"
    $suffix++
  }

  $resp = Invoke-CapsApi -Method 'POST' -Url "$base/specializations/" -Token $token -BodyObj @{ name = $def.name; code = $candidate; program_id = $programId }
  Ensure-Success -Action "Create specialization $($def.name)" -Response $resp
  $created = Get-ApiData $resp
  $specializationByCode[[string]$created.code] = $created
  $specializationByPair[$pairKey] = $created
  $stats.specializations_created++
}

# Final counts
$facCount = (Get-All -Path '/faculties/' -Token $token).Count
$deptCount = (Get-All -Path '/departments/' -Token $token).Count
$progCount = (Get-All -Path '/programs/' -Token $token).Count
$specCount = (Get-All -Path '/specializations/' -Token $token).Count

$result = [ordered]@{
  message = 'Hierarchy import completed'
  source = $excelPath
  stats = $stats
  totals_after = [ordered]@{
    faculties = $facCount
    departments = $deptCount
    programs = $progCount
    specializations = $specCount
  }
}

$result | ConvertTo-Json -Depth 8
