# 🚀 CAPS AI

# Enterprise Institutional Academic Governance & AI-Assisted Evaluation Platform

## Version 4.0 -- High-End Unified Architecture Document

Core Philosophy: AI Assists --- Humans Decide --- Governance Controls

------------------------------------------------------------------------

# 1. Executive Vision

CAPS AI is a university-aligned academic governance and AI-assisted
evaluation platform designed to deliver:

-   Standardized 40 Internal + 60 Final evaluation model
-   Multi-layer RBAC with scoped supervision
-   AI-assisted (non-autonomous) grading support
-   Cross-section & cross-year similarity detection
-   Teacher-controlled plagiarism enforcement
-   Immutable audit trails
-   Institutional analytics & risk intelligence
-   Structured communication and club ecosystem
-   Enterprise-grade academic compliance

This is not a grading tool. This is an Academic Governance Operating
System.

------------------------------------------------------------------------

# 2. Governance Architecture

## Academic Hierarchy

Course → Year → Class → Section → SectionSubject → Student

## Governance Hierarchy

Admin → Year Head → Class Coordinator → Subject Teacher → Student

Extension roles expand visibility --- NOT grading power.

------------------------------------------------------------------------

# 3. Enterprise RBAC Model

## Base Roles

-   admin
-   teacher
-   student

## Teacher Extension Roles

-   year_head
-   class_coordinator
-   club_coordinator

Rules: - Extensions valid only if role = teacher - Multiple extensions
allowed - Extensions never expand grading authority - All assignments
logged in AuditLogs

------------------------------------------------------------------------

# 4. Evaluation Model

## Internal = 40

-   Attendance: 5
-   Skill: 2.5
-   Behavior: 2.5
-   Report/File: 10
-   Viva: 20

## Final = 60

Total = 100

### Attendance Mapping

95--100 → 5 90--94 → 4 85--89 → 3 80--84 → 2 70--79 → 1 Below 70 → 0

### Grade Mapping

90--100 → A+ 80--89 → A 70--79 → B 60--69 → C Below 60 → Needs
Improvement

------------------------------------------------------------------------

# 5. Evaluation Governance Flow

1.  Teacher enters marks
2.  System validates constraints
3.  Total & grade computed
4.  Teacher clicks Finalize
5.  STATUS → LOCKED

After Lock: - Reopen request required - Mandatory reason - Audit log
created

No silent edits.

------------------------------------------------------------------------

# 6. Teacher-Controlled Plagiarism Detection

Each assignment includes:

    plagiarism_enabled: true | false

If TRUE: - Similarity engine executes - TF-IDF + cosine similarity
applied - Logs generated if threshold crossed

If FALSE: - No similarity computation - Submission processed normally

Only subject teacher can toggle. Toggle action logged. Admin cannot
override per assignment.

------------------------------------------------------------------------

# 7. AI Evaluation Layer

1.  Student uploads report
2.  Text extracted
3.  AI rubric evaluation executed
4.  System stores suggested score and feedback

Rules: - AI never auto-applies marks - Teacher manually confirms -
Differences logged in audit

------------------------------------------------------------------------

# 8. System Architecture

Frontend: React (Vite) + Tailwind Backend: FastAPI + Uvicorn Database:
MongoDB AI: OpenAI SDK ML: scikit-learn

Security: - JWT Authentication - Role Guards - Extension Guards -
PBKDF2-SHA256 password hashing - Immutable AuditLogs

------------------------------------------------------------------------

# 9. Canonical Collections

Users Courses Years Classes Sections SectionSubjects Students Subjects
Assignments Submissions Evaluations SimilarityLogs Notices Clubs
ClubEvents EventRegistrations Notifications AuditLogs ReviewTickets

------------------------------------------------------------------------

# 10. Enterprise Outcome

CAPS AI becomes:

-   University-grade governance system
-   AI-assisted but teacher-controlled platform
-   Multi-layer supervised academic SaaS
-   Transparent, auditable institutional solution
-   Enterprise-ready capstone architecture

------------------------------------------------------------------------

# 📦 Additional Component

# Teacher Section Tiles Module

Component Name: `TeacherSectionTiles`\
Module Category: Dashboard Enhancement v1.0

------------------------------------------------------------------------

## Purpose

Provide teachers with a clean, modern, tile-based overview of all
assigned sections, enhancing visibility and operational monitoring
without altering governance logic.

------------------------------------------------------------------------

## UI Structure (Tile View)

Each section appears as a clickable tile:

    ┌─────────────────────────────┐
    │ 📘 Subject Name             │
    │ Year 2 • CSE-A • A1         │
    │ 👥 62 Students              │
    │ 📝 3 Active Assignments     │
    │ ⚠ 2 Late Submissions        │
    │ 🔍 1 Similarity Alert       │
    │                             │
    │ Status: 🟢 Healthy          │
    └─────────────────────────────┘

------------------------------------------------------------------------

## Layout Standards

-   Desktop: 3 tiles per row
-   Tablet: 2 tiles per row
-   Mobile: 1 tile per row
-   Rounded corners (2xl)
-   Soft shadow
-   Hover elevation effect
-   Border color based on health status

------------------------------------------------------------------------

## Status Logic

🟢 Healthy\
- No late submissions\
- No similarity flags\
- No risk students

🟡 Attention\
- Minor late submissions\
- Single similarity alert

🔴 Risk\
- Multiple late submissions\
- Multiple similarity cases\
- Risk students flagged

------------------------------------------------------------------------

## Backend Endpoint

    GET /teacher/classes

Returns aggregated section-level metrics.

------------------------------------------------------------------------

## Data Contract

    {
      section_id,
      subject_name,
      year,
      class_name,
      section_name,
      total_students,
      active_assignments,
      late_submissions_count,
      similarity_alert_count,
      risk_student_count
    }

------------------------------------------------------------------------

## Governance Impact

-   No change to evaluation logic
-   No change to AI scoring
-   No change to similarity engine
-   Read-only for supervisors
-   Teacher-scoped visibility only

------------------------------------------------------------------------

This component enhances dashboard usability while preserving CAPS AI's
governance-first architecture.
