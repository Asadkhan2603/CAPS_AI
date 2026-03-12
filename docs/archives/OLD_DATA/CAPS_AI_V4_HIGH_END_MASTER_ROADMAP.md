# CAPS AI

# Enterprise Institutional Academic Governance and AI-Assisted Evaluation Platform

## Version 4.0 - High-End Unified Architecture Document

Core Philosophy: AI Assists - Humans Decide - Governance Controls

------------------------------------------------------------------------

# 1. Executive Vision

CAPS AI is a university-aligned academic governance and AI-assisted evaluation platform designed to deliver:

- Standardized 40 Internal + 60 Final evaluation model
- Multi-layer RBAC with scoped supervision
- AI-assisted (non-autonomous) grading support
- Cross-section and cross-year similarity detection
- Teacher-controlled plagiarism enforcement
- Immutable audit trails
- Institutional analytics and risk intelligence
- Structured communication and club ecosystem
- Enterprise-grade academic compliance

This is not a grading tool. This is an Academic Governance Operating System.

------------------------------------------------------------------------

# 2. Governance Architecture

## Academic Hierarchy

Course -> Year -> Class -> Section -> SectionSubject -> Student

## Governance Hierarchy

Admin -> Year Head -> Class Coordinator -> Subject Teacher -> Student

Extension roles expand visibility - not grading power.

------------------------------------------------------------------------

# 3. Enterprise RBAC Model

## Base Roles

- admin
- teacher
- student

## Teacher Extension Roles

- year_head
- class_coordinator
- club_coordinator

Rules:
- Extensions valid only if role = teacher
- Multiple extensions allowed
- Extensions never expand grading authority
- All assignments logged in AuditLogs

------------------------------------------------------------------------

# 4. Evaluation Model

## Internal = 40

- Attendance: 5
- Skill: 2.5
- Behavior: 2.5
- Report/File: 10
- Viva: 20

## Final = 60

Total = 100

### Attendance Mapping

- 95-100 -> 5
- 90-94 -> 4
- 85-89 -> 3
- 80-84 -> 2
- 70-79 -> 1
- Below 70 -> 0

### Grade Mapping

- 90-100 -> A+
- 80-89 -> A
- 70-79 -> B
- 60-69 -> C
- Below 60 -> Needs Improvement

------------------------------------------------------------------------

# 5. Evaluation Governance Flow

1. Teacher enters marks
2. System validates constraints
3. Total and grade computed
4. Teacher clicks Finalize
5. STATUS -> LOCKED

After Lock:
- Reopen request required
- Mandatory reason
- Audit log created

No silent edits.

------------------------------------------------------------------------

# 6. Teacher-Controlled Plagiarism Detection

Each assignment includes:

`plagiarism_enabled: true | false`

If TRUE:
- Similarity engine executes
- TF-IDF + cosine similarity applied
- Logs generated if threshold crossed

If FALSE:
- No similarity computation
- Submission processed normally

Only subject teacher can toggle. Toggle action logged. Admin cannot override per assignment.

------------------------------------------------------------------------

# 7. AI Evaluation Layer

1. Student uploads report
2. Text extracted
3. AI rubric evaluation executed
4. System stores suggested score and feedback

Rules:
- AI never auto-applies marks
- Teacher manually confirms
- Differences logged in audit

------------------------------------------------------------------------

# 8. System Architecture

Frontend: React (Vite) + Tailwind  
Backend: FastAPI + Uvicorn  
Database: MongoDB  
AI: OpenAI SDK  
ML: scikit-learn

Security:
- JWT Authentication
- Role Guards
- Extension Guards
- PBKDF2-SHA256 password hashing
- Immutable AuditLogs

------------------------------------------------------------------------

# 9. Canonical Collections

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

# 10. Enterprise Outcome

CAPS AI becomes:

- University-grade governance system
- AI-assisted but teacher-controlled platform
- Multi-layer supervised academic SaaS
- Transparent, auditable institutional solution
- Enterprise-ready capstone architecture
