# 🚀 CAPS AI  
# Enterprise Academic Governance & AI-Assisted Evaluation Platform  
### Authoritative Master Architecture Document  

---

# 1. Executive Vision

CAPS AI is a university-aligned academic governance platform designed to standardize evaluation workflows while preserving strict institutional authority boundaries.

**Core Philosophy:**

> AI Assists — Humans Decide — Governance Controls

This system is not a grading tool.  
It is an **Academic Governance Operating System**.

---

# 2. Strategic Objectives

- Standardize 40 Internal + 60 Final evaluation model  
- Preserve teacher authority in grading decisions  
- Enforce multi-layer RBAC with scoped supervision  
- Detect cross-class and cross-year similarity  
- Maintain immutable academic audit trails  
- Provide role-based institutional analytics  
- Enable structured communication workflows  
- Support extracurricular club and event ecosystem  
- Identify academically at-risk students  

---

# 3. Governance Architecture

## Academic Hierarchy

Course  
→ Year  
→ Class  
→ Students  
→ Subjects  

## Governance Hierarchy

Admin  
→ Year Head  
→ Class Coordinator  
→ Subject Teacher  
→ Student  

Extension roles expand visibility — not grading power.

---

# 4. Enterprise RBAC Model

## Base Roles

- `admin`
- `teacher`
- `student`

## Teacher Extension Roles

- `year_head`
- `class_coordinator`
- `club_coordinator`

### Governance Rules

- Extension roles valid only if `role = teacher`
- Multiple extensions allowed
- Extensions never expand grading authority
- All role changes logged in `AuditLogs`
- Admin cannot enter or modify marks

---

# 5. Role Responsibility Matrix

## Admin

**Can:**
- Manage academic structure
- Assign teacher extensions
- Configure similarity threshold
- Publish institution-wide notices
- View analytics, logs, risk indicators

**Cannot:**
- Enter or modify marks
- Delete audit logs

If correction required → Review Ticket → Teacher performs change.

---

## Year Head

**Can:**
- View year-level analytics
- View similarity alerts
- View risk students
- Publish year-level notices

**Cannot:**
- Edit marks
- Modify structure

---

## Class Coordinator

**Can:**
- Manage enrollment mapping
- View class analytics
- View similarity trends
- Publish class-level notices

**Cannot:**
- Modify marks outside assigned scope
- Move students across years

---

## Subject Teacher

**Can:**
- Create assignments
- Toggle plagiarism per assignment
- Review submissions
- View AI suggestions
- Enter marks
- Finalize evaluations
- Review similarity alerts

---

## Student

**Can:**
- Upload submissions
- View own marks & feedback
- Register for events
- View notices

**Cannot:**
- Access other students' data
- Edit marks
- Access supervisory analytics

---

# 6. Evaluation Model

## Internal = 40

- Attendance: 5
- Skill: 2.5
- Behavior: 2.5
- Report/File: 10
- Viva: 20

## Final Exam = 60

Total = 100

---

## Attendance Mapping

| Percentage | Marks |
|------------|--------|
| 95–100     | 5      |
| 90–94      | 4      |
| 85–89      | 3      |
| 80–84      | 2      |
| 70–79      | 1      |
| Below 70   | 0      |

---

## Grade Mapping

| Score Range | Grade |
|-------------|--------|
| 90–100      | A+     |
| 80–89       | A      |
| 70–79       | B      |
| 60–69       | C      |
| Below 60    | Needs Improvement |

---

# 7. Evaluation Governance Flow

1. Teacher enters marks  
2. System validates constraints  
3. Total and grade computed  
4. Teacher clicks **Finalize**  
5. Status → `LOCKED`  

After Lock:
- Reopen request required  
- Mandatory reason  
- Audit log generated  

No silent edits allowed.

---

# 8. AI Evaluation Layer

### Workflow

1. Student uploads report  
2. Text extraction engine parses content  
3. AI rubric evaluation executed  
4. System stores:
   - Suggested score  
   - Rubric breakdown  
   - Qualitative feedback  

### Governance Rules

- AI never auto-applies marks  
- Teacher must confirm manually  
- AI suggestions + final score differences logged  
- AI failures handled gracefully  

---

# 9. Similarity Detection Engine

### Pipeline

Preprocessing  
→ TF-IDF Vectorization  
→ Cosine Similarity  

### Capabilities

- Cross-class comparison  
- Cross-year detection  

### Rules

- Default threshold: 0.75 (configurable)  
- No automatic punishment  
- Teacher manually decides action  
- Similarity logs immutable  

---

# 10. Academic Risk Intelligence

Student flagged if:

- Internal < 40%  
- Final < 35%  
- Attendance < 70%  
- Multiple similarity violations  

**Visibility:**
- Subject Teacher  
- Class Coordinator  
- Year Head  

---

# 11. Notice & Communication System

### Scopes

- College-wide  
- Year-level  
- Class-level  
- Subject-level  

### Urgent Notice Features

- Priority highlight  
- Expiry date  
- Dashboard alert  
- Optional email notification  

---

# 12. Clubs & Events Ecosystem

## Admin
- Create clubs  
- Assign coordinators  

## Coordinator
- Create events  
- Manage registrations  
- Publish results  

## Student
- Register for events  
- View outcomes  

---

# 13. Enterprise System Architecture

## Frontend
- React (Vite)  
- Tailwind CSS  
- Role-based routing  

## Backend
- FastAPI  
- Uvicorn  
- MongoDB  
- JWT authentication  
- Extension-role guards  

## AI Layer
- OpenAI SDK  

## Similarity Engine
- scikit-learn (TF-IDF + cosine similarity)  

## Security
- PBKDF2-SHA256 password hashing  
- File validation  
- Input sanitization  
- Immutable audit logging  
- Structured observability logs  

---

# 14. Canonical Database Collections

- Users  
- Courses  
- Years  
- Classes  
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
- ReviewTickets  

---

# 15. Delivery Roadmap

## Phase 1 – Foundation
- Project setup  
- JWT authentication  
- RBAC guards  
- Health endpoints  

## Phase 2 – Academic Core
- CRUD for academic structure  
- Role extensions  
- Enrollment mapping  
- Audit logging  

## Active API Domains (Frozen)
- Auth and identity: `/api/v1/auth`, `/api/v1/users`
- Academic hierarchy: `/api/v1/courses`, `/api/v1/years`, `/api/v1/classes`, `/api/v1/students`, `/api/v1/subjects`
- Academic operations: `/api/v1/assignments`, `/api/v1/submissions`, `/api/v1/evaluations`, `/api/v1/enrollments`
- Intelligence: `/api/v1/similarity`, `/api/v1/analytics`
- Institutional modules: `/api/v1/notices`, `/api/v1/notifications`, `/api/v1/clubs`, `/api/v1/club-events`, `/api/v1/event-registrations`
- Governance/ops: `/api/v1/audit-logs`, `/api/v1/review-tickets`, `/api/v1/branding`

## Phase 3 – Academic Operations
- Assignment lifecycle  
- Submission upload  
- Marks entry  
- Finalization lock  

## Phase 4 – Intelligence Layer
- AI suggestion pipeline  
- Similarity engine  
- Threshold configuration  

## Phase 5 – Institutional Modules
- Dashboards  
- Notices  
- Clubs & events  
- Risk indicators  

## Phase 6 – Hardening & Release
- Security validation  
- Regression testing  
- Deployment documentation  
- Production readiness checklist  

---

# 16. Compliance & Audit Layer

`AuditLogs` capture:

- Mark entries  
- Finalization actions  
- Role assignments  
- Enrollment changes  
- AI suggestion differences  
- Similarity actions  
- Notice publishing  
- Reopen requests  

Audit logs are immutable.

---

# 17. Final Outcome

CAPS AI becomes:

- University-aligned governance system  
- AI-assisted but teacher-controlled evaluation platform  
- Multi-layer RBAC academic SaaS  
- Transparent and auditable institutional solution  
- Enterprise-grade capstone architecture
