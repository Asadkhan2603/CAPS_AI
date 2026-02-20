# CAPS AI - ULTRA PRO MASTER ROADMAP

## Enterprise Institutional Academic Governance and AI-Assisted Evaluation Platform

Authoritative Combined Architecture Document  
Version: 3.0 (Ultra Professional Edition)

Tech Stack: React (Vite) | FastAPI | MongoDB | OpenAI | scikit-learn

------------------------------------------------------------------------

# 1. Executive Summary

CAPS AI is a university-aligned academic governance platform engineered to bring standardized evaluation, AI-assisted assessment, and institutional transparency into a single enterprise-grade system.

The platform enforces strict academic authority boundaries while introducing assistive intelligence to reduce human bias, administrative friction, and operational complexity.

Core Design Philosophy:

AI Assists - Humans Decide.

------------------------------------------------------------------------

# 2. Strategic Objectives

- Standardize internal (40) + final (60) evaluation model
- Preserve teacher authority in grading decisions
- Implement multi-layer RBAC governance
- Detect plagiarism across sections and years
- Maintain immutable academic audit trails
- Provide institution-wide analytics visibility
- Enable structured communication workflows

------------------------------------------------------------------------

# 3. Governance Architecture

## Academic Hierarchy

Course -> Year -> Class -> Section -> SectionSubject -> Student

## Governance Hierarchy

Admin -> Year Head -> Class Coordinator -> Subject Teacher -> Student

Extension roles expand visibility - not grading power.

------------------------------------------------------------------------

# 4. RBAC Model (2-Layer Enterprise Design)

Base Roles:
- admin
- teacher
- student

Teacher Extension Roles:
- year_head
- class_coordinator
- club_coordinator

Governance Rules:
- Extension roles require role=teacher
- Multiple extensions allowed
- Extension roles never expand grading authority

------------------------------------------------------------------------

# 5. Role Responsibility Matrix

ADMIN
Can:
- Manage academic structure
- Configure similarity thresholds
- Publish institution notices
- View analytics and logs

Cannot:
- Enter or modify marks
- Delete audit logs

YEAR HEAD
Can:
- View analytics
- View risk indicators
- Publish year notices

CLASS COORDINATOR
Can:
- Manage enrollment mapping
- View class analytics

SUBJECT TEACHER
Can:
- Create assignments
- Review AI suggestions
- Finalize marks

STUDENT
Can:
- Submit reports
- View feedback
- Register for events

------------------------------------------------------------------------

# 6. Evaluation Governance Model

Internal = 40
- Attendance: 5
- Skill: 2.5
- Behavior: 2.5
- Report: 10
- Viva: 20

Final Exam = 60
Total = 100

Evaluation Flow:

1. Teacher enters marks
2. System validates constraints
3. Grade calculated
4. Teacher finalizes -> STATUS = LOCKED

Post-Lock Editing:
- Reopen request required
- Mandatory reason
- Audit log generated

------------------------------------------------------------------------

# 7. AI Evaluation Intelligence Layer

Workflow:

1. Student uploads report
2. Text extraction engine parses content
3. AI rubric evaluation executed
4. System stores:
   - Suggested score
   - Rubric explanation
   - Qualitative feedback

Governance Rules:

- AI score never auto-applied
- Teacher decision always final
- Score differences tracked in audit logs

------------------------------------------------------------------------

# 8. Similarity Detection Engine

Pipeline:

Preprocessing -> TF-IDF Vectorization -> Cosine Similarity

Capabilities:

- Cross-section comparison
- Cross-class comparison
- Cross-year detection

Rules:

- Default threshold 0.75 (configurable)
- No automatic penalties
- Teacher manually decides action

------------------------------------------------------------------------

# 9. Academic Risk Intelligence

Student flagged when:

- Internal < 40%
- Final < 35%
- Attendance < 70%
- Multiple similarity violations

Visibility: Teacher | Class Coordinator | Year Head

------------------------------------------------------------------------

# 10. Notice and Institutional Communication System

Scopes:

- College-wide
- Year-level
- Class-level
- Subject-level

Urgent Notice Features:

- Priority highlighting
- Expiry logic
- Dashboard alert
- Optional email notification

------------------------------------------------------------------------

# 11. Clubs and Events Ecosystem

Admin:
- Create clubs
- Assign coordinators

Coordinator:
- Create events
- Publish results

Student:
- Register
- View outcomes

------------------------------------------------------------------------

# 12. Enterprise System Architecture

Frontend: React (Vite) + Tailwind  
Backend: FastAPI + Uvicorn  
Database: MongoDB  
AI Layer: OpenAI SDK  
ML Layer: scikit-learn

Security:

- JWT authentication
- Extension-role guards
- Input validation
- File validation
- PBKDF2-SHA256 password hashing

------------------------------------------------------------------------

# 13. Canonical Database Collections

Users  
Courses  
Years  
Classes  
Sections  
SectionSubjects  
Students  
Subjects  
Assignments  
Submissions  
Evaluations  
SimilarityLogs  
Notices  
Clubs  
ClubEvents  
EventRegistrations  
Notifications  
AuditLogs  
ReviewTickets

------------------------------------------------------------------------

# 14. Enterprise Delivery Roadmap

PHASE 1 - Foundation Setup  
- Auth
- RBAC
- Health APIs

PHASE 2 - Academic Core Structure  
- CRUD
- Role extensions
- Enrollment mapping

PHASE 3 - Academic Operations  
- Assignments
- Submissions
- Evaluation lock

PHASE 4 - Intelligence Layer  
- AI suggestions
- Similarity engine

PHASE 5 - Institutional Modules  
- Dashboards
- Notices
- Clubs
- Risk flags

PHASE 6 - Hardening and Release  
- Security audit
- Regression testing
- Deployment docs

------------------------------------------------------------------------

# 15. Compliance and Audit Layer

AuditLogs capture:

- Mark entries
- Role changes
- Enrollment edits
- AI suggestions
- Similarity actions
- Notice publishing

Immutable by design.

------------------------------------------------------------------------

# 16. Final Institutional Outcome

CAPS AI becomes:

- University-aligned governance platform
- AI-assisted but teacher-controlled evaluation system
- Multi-layer supervised academic SaaS
- Transparent, auditable, enterprise-ready solution
- Industry-grade capstone architecture
