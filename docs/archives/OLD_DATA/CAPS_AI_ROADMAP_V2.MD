# CAPS AI
## Complete Institutional Project Development Roadmap
**Tech Stack:** React + FastAPI + MongoDB + OpenAI + scikit-learn

---

## 1. Project Overview

CAPS AI is a university-aligned academic governance and evaluation platform designed to:

- Standardize a fixed 40 internal + 60 final marking model
- Support multi-level academic supervision
- Assist teachers with AI-supported report evaluation
- Detect plagiarism across classes and sections using TF-IDF + cosine similarity
- Provide analytics at subject, class, year, and institutional levels
- Maintain audit logs for transparency and governance
- Support structured notices and urgent communications
- Support extracurricular operations (clubs and events)
- Flag academically at-risk students

---

## 2. Objectives

- Ensure fair and transparent evaluation
- Align data and workflows with university hierarchy
- Keep teacher authority in final grading decisions
- Enforce scalable RBAC with supervisory extensions
- Protect academic integrity with similarity checks
- Provide actionable analytics for admin and academic supervisors

---

## 3. Institutional Structure

### Academic Hierarchy
Course -> Year -> Class -> Section -> SectionSubjects -> Students

### Governance Hierarchy
Admin -> Year Head (Teacher Extension) -> Class Coordinator (Teacher Extension) -> Subject Teacher -> Student

---

## 4. Role Model

### Base Roles
- admin
- teacher
- student

### Teacher Extension Roles
- year_head
- class_coordinator
- club_coordinator

Notes:
- Extension roles are valid only when `role=teacher`.
- A teacher can hold multiple extension roles.

---

## 5. Role Responsibilities

### Admin
Can:
- Manage academic structure (courses, years, classes, sections, section-subject mappings)
- Assign teachers and supervisory extensions
- Manage users and activation status
- Publish college-wide and urgent notices
- View full analytics, similarity logs, and audit logs

Cannot:
- Enter or silently override marks
- Delete audit history

### Year Head (Teacher + year_head)
Can:
- View year-level classes, analytics, similarity cases, and risk indicators
- Publish urgent year-level notices

Cannot:
- Change academic structure
- Modify marks outside authorized scope
- Delete logs

### Class Coordinator (Teacher + class_coordinator)
Can:
- Manage class-level enrollment mapping
- View class analytics and class-level similarity trends
- Publish class-level notices

Cannot:
- Change global structure
- Modify unrelated teacher marks

### Subject Teacher
Can:
- Create assignments and deadlines
- Review submissions and AI suggestions
- Enter and finalize marks for assigned scope
- Review similarity alerts
- Publish subject-level notices

### Student
Can:
- Upload assignments and reports
- View own marks and AI feedback summary
- Download own PDF report
- View notices and club events

Cannot:
- View other students' private data
- Edit marks
- Access admin or supervisory analytics

---

## 6. System Architecture

React Frontend
-> FastAPI Backend
-> MongoDB
-> OpenAI API
-> scikit-learn Similarity Engine

---

## 7. Technology Stack

### Frontend
- React (Vite)
- Tailwind CSS
- React Router
- Axios
- Recharts

### Backend
- FastAPI
- Uvicorn
- Motor (MongoDB async driver)
- Pydantic
- python-jose (JWT)
- python-multipart

### Security and Auth
- JWT-based authentication
- Role and extension-role authorization
- Password hashing: PBKDF2-SHA256 (current implementation)

### NLP and AI
- OpenAI Python SDK
- scikit-learn
- NLTK (optional)

### File Handling
- pdfplumber
- python-docx

### PDF
- ReportLab

---

## 8. Canonical Collections

- Users
- Courses
- Years
- Classes
- Sections
- SectionSubjects
- Students
- Subjects
- Assignments
- Submissions
- Evaluations
- SimilarityLogs
- Notices
- Clubs
- ClubEvents
- EventRegistrations
- Notifications
- AuditLogs

---

## 9. Evaluation Model

### Internal = 40
- Attendance: 5
- Skill: 2.5
- Behavior: 2.5
- Report/File: 10
- Viva: 20

### Final Exam = 60

### Attendance Mapping
- 95-100 -> 5
- 90-94 -> 4
- 85-89 -> 3
- 80-84 -> 2
- 70-79 -> 1
- below 70 -> 0

### Grade Mapping
- 90-100 -> A+
- 80-89 -> A
- 70-79 -> B
- 60-69 -> C
- below 60 -> Needs Improvement

---

## 10. AI Evaluation Flow

1. Student uploads report
2. System extracts text
3. System requests AI evaluation
4. System returns suggestions (score + qualitative feedback)
5. Teacher reviews and confirms final marks

---

## 11. Similarity Flow

1. Preprocess text
2. Vectorize with TF-IDF
3. Compute cosine similarity
4. If score exceeds threshold:
   - Create SimilarityLog
   - Notify relevant teacher(s)
   - Expose to class coordinator and year head by scope

---

## 12. Notice System

Notice scopes:
- College-wide (admin)
- Year-level (year_head)
- Class-level (class_coordinator)
- Subject-level (teacher)

Urgent notices include priority flags and expiry controls.

---

## 13. Club and Event Module

- Admin: create and manage clubs, assign coordinators
- Coordinator: create events, publish results
- Student: register for events, view outcomes

---

## 14. 10-Week Delivery Plan with Acceptance Criteria

### Week 1: Setup and Foundations
Deliverables:
- Backend and frontend bootstrapped
- Environment templates available (`.env.example`)
- Health endpoint and base routing live
Acceptance Criteria:
- `GET /health` returns 200 with status payload
- Frontend runs and resolves configured API base URL
- Lint and build pass in CI or local pipeline

### Week 2: Authentication and RBAC Base
Deliverables:
- Register, login, and profile (`/me`) endpoints
- JWT issuance and validation middleware
- Base role guards for admin, teacher, student
Acceptance Criteria:
- Unauthorized requests return 401
- Wrong-role requests return 403
- Token expiry and invalid token paths are tested

### Week 3: Academic Structure Core
Deliverables:
- CRUD for Courses, Years, Classes, Sections, Subjects, SectionSubjects, Students
- Pagination and filtering for list endpoints
Acceptance Criteria:
- Role-appropriate CRUD works for each entity
- List endpoints support `skip`, `limit`, and filters
- Validation errors return structured 422 responses

### Week 4: Role Assignments and Enrollment
Deliverables:
- Teacher extension-role assignment flows
- Student enrollment and class/section mapping workflows
Acceptance Criteria:
- `year_head` and `class_coordinator` permissions enforced by policy tests
- Enrollment mappings prevent invalid cross-year assignments
- Audit logs generated for assignment and mapping changes

### Week 5: Assignment and Submission Operations
Deliverables:
- Assignment lifecycle (create, update, close)
- Submission upload, parse, and ownership checks
Acceptance Criteria:
- Supported file types upload successfully within size limits
- Students can submit only in allowed assignment scope
- Teachers can only access submissions in assigned scope

### Week 6: Evaluation Module
Deliverables:
- Marks entry workflow
- Internal + final total and grade computation
- Teacher finalization workflow
Acceptance Criteria:
- Computed totals match model constraints (40 + 60)
- Grade output matches configured mapping for boundary values
- Finalized evaluations become read-only except authorized override flow

### Week 7: AI Integration
Deliverables:
- AI suggestion pipeline and stored feedback artifacts
- UI for teacher review of AI suggestions
Acceptance Criteria:
- AI timeout and failure handled with fallback response
- Teacher can edit and override all AI suggestions
- AI responses are traceable by submission ID in logs

### Week 8: Similarity Engine
Deliverables:
- TF-IDF vectorization and cosine scoring pipeline
- Similarity threshold alert generation and logs
Acceptance Criteria:
- Similarity score persisted with compared submission references
- Threshold crossing creates SimilarityLog and notification
- Coordinator and year-head visibility respects scope rules

### Week 9: Analytics, Notices, and Clubs
Deliverables:
- Role-specific dashboards
- Notice center with urgency and expiry
- Club/event registration and result publishing
Acceptance Criteria:
- Dashboard metrics load by role without unauthorized leakage
- Urgent notices render as high-priority and expire correctly
- Event registration validates duplicates and capacity rules

### Week 10: Hardening and Release Readiness
Deliverables:
- Test stabilization and bug triage closure
- Security and validation review
- Deployment and operational documentation
Acceptance Criteria:
- Critical flows pass regression suite
- High-severity security findings resolved or documented with mitigation
- Deployment checklist completed for backend and frontend

---

## 15. Security and Compliance

- JWT authentication and expiry control
- Role and extension-role authorization checks
- File type and size validation
- Input validation and sanitization
- Immutable audit logging for sensitive actions

---

## 16. Final Deliverables

- Institutional academic governance web application
- AI-assisted grading support
- Cross-class and section similarity monitoring
- Multi-layer RBAC with supervisory extensions
- Notice system with urgency support
- Enrollment and mapping workflows
- Analytics dashboards
- PDF reporting
- Complete technical and operational documentation

---

## 17. Project Outcome

- University-aligned academic system
- Multi-level supervision with clear authority boundaries
- AI-assisted but teacher-controlled evaluation
- Transparent and auditable integrity workflow
- Portfolio-ready capstone with real governance depth

---

## Execution Sequence

Setup -> Auth/RBAC -> Academic Structure -> Role Assignment -> Evaluation -> AI -> Similarity -> Notices/Analytics -> Hardening
