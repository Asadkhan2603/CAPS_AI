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
