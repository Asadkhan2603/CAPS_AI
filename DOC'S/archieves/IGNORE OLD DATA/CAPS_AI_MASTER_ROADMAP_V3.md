# 🚀 CAPS AI

# Master Institutional Development & Governance Roadmap (Combined Edition)

**Tech Stack:** React (Vite) + FastAPI + MongoDB + OpenAI + scikit-learn

------------------------------------------------------------------------

# 1. Project Vision

CAPS AI is a university‑aligned academic governance and AI‑assisted
evaluation platform designed to:

-   Standardize 40 Internal + 60 Final evaluation model
-   Maintain strict multi‑layer RBAC with supervisory extensions
-   Provide AI‑assisted (non‑decision) evaluation
-   Detect cross‑class plagiarism using TF‑IDF + cosine similarity
-   Maintain immutable audit trails
-   Provide analytics across academic hierarchy
-   Manage notices, clubs, and institutional workflows

Core Principle: **AI Assists --- Humans Decide**

------------------------------------------------------------------------

# 2. Governance Principles

1.  No Silent Overrides
2.  Immutable Audit Logs
3.  Scoped Authority
4.  Teacher Final Authority
5.  Separation of Structure & Evaluation
6.  Transparent Analytics Without Data Leakage

------------------------------------------------------------------------

# 3. Institutional Structure

## Academic Hierarchy

Course → Year → Class → Section → SectionSubject → Student

## Governance Hierarchy

Admin → Year Head → Class Coordinator → Subject Teacher → Student

Extension roles expand visibility --- NOT grading power.

------------------------------------------------------------------------

# 4. Role Architecture

## Base Roles

-   admin
-   teacher
-   student

## Teacher Extension Roles

-   year_head
-   class_coordinator
-   club_coordinator

Rules: - Extensions valid only if role = teacher - Multiple extensions
allowed - Extensions never expand grading authority

------------------------------------------------------------------------

# 5. Role Responsibilities

## Admin

Can: - Manage academic structure - Assign roles - Configure similarity
threshold - Publish college notices - View analytics and audit logs

Cannot: - Enter or modify marks - Delete audit history

If correction required → Review Ticket → Teacher performs change.

## Year Head

Can: - View year analytics - View similarity alerts - Publish year
notices

Cannot: - Edit marks - Modify structure

## Class Coordinator

Can: - Manage enrollment mapping - View class analytics - Publish class
notices

Cannot: - Move students across years - Modify other teacher marks

## Subject Teacher

Can: - Create assignments - Review submissions - View AI suggestions -
Enter & finalize marks - Review similarity alerts

## Student

Can: - Upload assignments - View own marks & feedback - Download
reports - Register for events

------------------------------------------------------------------------

# 6. Evaluation Model

## Internal = 40

-   Attendance: 5
-   Skill: 2.5
-   Behavior: 2.5
-   Report/File: 10
-   Viva: 20

## Final Exam = 60

Total = 100

### Attendance Mapping

95--100 → 5\
90--94 → 4\
85--89 → 3\
80--84 → 2\
70--79 → 1\
Below 70 → 0

### Grade Mapping

90--100 → A+\
80--89 → A\
70--79 → B\
60--69 → C\
Below 60 → Needs Improvement

------------------------------------------------------------------------

# 7. Evaluation Governance Flow

1.  Teacher enters marks
2.  System validates constraints
3.  Total & grade computed
4.  Teacher clicks Finalize
5.  Status becomes LOCKED

After Lock: - Editable only via Reopen Request - Mandatory reason -
Audit log created

------------------------------------------------------------------------

# 8. AI Evaluation Module

## Workflow

1.  Student uploads report
2.  Text extracted
3.  AI evaluates with rubric
4.  Returns:
    -   Suggested score
    -   Rubric breakdown
    -   Feedback

Rules: - AI score NEVER auto‑applied - Teacher must confirm manually -
AI output + final decision logged

------------------------------------------------------------------------

# 9. Similarity Engine

Technical Flow: 1. Preprocess text 2. TF‑IDF vectorization 3. Cosine
similarity scoring

Governance Rules: - Threshold configurable (default 0.75) - Creates
SimilarityLog - Teacher decides Ignore / Warn / Penalize - No automatic
punishment

------------------------------------------------------------------------

# 10. Academic Risk Indicator

Flag if: - Internal \< 40% - Final \< 35% - Attendance \< 70% - Multiple
similarity violations

Visible only to authorized supervisors.

------------------------------------------------------------------------

# 11. Notice System

Scopes: - College-wide - Year-level - Class-level - Subject-level

Urgent notices: - Priority flag - Expiry date - Dashboard highlight -
Optional email alerts

------------------------------------------------------------------------

# 12. Clubs & Events Module

Admin: - Create clubs - Assign coordinators

Coordinator: - Create events - Publish results

Student: - Register & view outcomes

------------------------------------------------------------------------

# 13. System Architecture

React Frontend\
→ FastAPI Backend\
→ MongoDB\
→ OpenAI API\
→ scikit‑learn Similarity Engine

Security: - JWT Authentication - Role Guards - Extension-role Guards -
PBKDF2-SHA256 Password Hashing - File validation & input sanitization

------------------------------------------------------------------------

# 14. Canonical Database Collections

Users\
Courses\
Years\
Classes\
Sections\
SectionSubjects\
Students\
Subjects\
Assignments\
Submissions\
Evaluations\
SimilarityLogs\
Notices\
Clubs\
ClubEvents\
EventRegistrations\
Notifications\
AuditLogs\
ReviewTickets

------------------------------------------------------------------------

# 15. 10‑Week Delivery Plan (Combined Best Version)

## Phase 1 -- Foundation (Weeks 1--2)

-   Setup frontend & backend
-   JWT authentication
-   RBAC base
-   Health endpoints

## Phase 2 -- Academic Core (Weeks 3--4)

-   Academic structure CRUD
-   Role extensions
-   Enrollment mapping
-   Audit logging

## Phase 3 -- Academic Operations (Weeks 5--6)

-   Assignment lifecycle
-   Submission system
-   Marks entry & Finalization lock
-   Grade computation

## Phase 4 -- Intelligence Layer (Weeks 7--8)

-   AI suggestion pipeline
-   Similarity engine
-   Threshold configuration

## Phase 5 -- Institutional Modules (Week 9)

-   Dashboards
-   Notices
-   Clubs & Events
-   Risk indicators

## Phase 6 -- Hardening & Release (Week 10)

-   Security review
-   Validation testing
-   Deployment documentation

------------------------------------------------------------------------

# 16. Final Outcome

CAPS AI becomes:

-   University‑aligned governance system
-   AI‑assisted but teacher‑controlled evaluation
-   Multi‑layer RBAC academic platform
-   Transparent & auditable institutional solution
-   Enterprise‑level capstone project
