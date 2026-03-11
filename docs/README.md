# CAPS AI Documentation Index

This file is the root entry point for the documentation tree under `docs/`.

## Start Here

- [Module Index](./guides/module-index.md)
- [Documentation Audit Report](./DOCUMENTATION_AUDIT_REPORT.md)
- [Academic Setup Logic Audit](./ACADEMIC_SETUP_LOGIC_AUDIT.md)

## Core Guides

- [API Contracts](./guides/api-contracts.md)
- [Backend Architecture](./guides/backend-architecture.md)
- [Data Model](./guides/data-model.md)
- [Deployment](./guides/deployment.md)
- [Frontend Architecture](./guides/frontend-architecture.md)
- [Governance Workflows](./guides/governance-workflows.md)
- [Testing](./guides/testing.md)

## Module Masters

### Platform And Governance

- [Auth Module Master](./modules/AUTH_MODULE_MASTER.md)
- [User Module Master](./modules/USER_MODULE_MASTER.md)
- [RBAC Module Master](./modules/RBAC_MODULE_MASTER.md)
- [Governance Module Master](./modules/GOVERNANCE_MODULE_MASTER.md)
- [Review Ticket Module Master](./modules/REVIEW_TICKET_MODULE_MASTER.md)
- [Audit Module Master](./modules/AUDIT_MODULE_MASTER.md)
- [Recovery Module Master](./modules/RECOVERY_MODULE_MASTER.md)
- [System Module Master](./modules/SYSTEM_MODULE_MASTER.md)
- [Branding Module Master](./modules/BRANDING_MODULE_MASTER.md)

### Academic Core

- [Academic Module Master](./modules/ACADEMIC_MODULE_MASTER.md)
- [Subject Module Master](./modules/SUBJECT_MODULE_MASTER.md)
- [Teacher Module Master](./modules/TEACHER_MODULE_MASTER.md)
- [Student Module Master](./modules/STUDENT_MODULE_MASTER.md)
- [Enrollment Module Master](./modules/ENROLLMENT_MODULE_MASTER.md)
- [Course Offering Module Master](./modules/COURSE_OFFERING_MODULE_MASTER.md)
- [Class Section Module Master](./modules/CLASS_SECTION_MODULE_MASTER.md)
- [Class Slot Module Master](./modules/CLASS_SLOT_MODULE_MASTER.md)
- [Timetable Module Master](./modules/TIMETABLE_MODULE_MASTER.md)
- [Attendance Module Master](./modules/ATTENDANCE_MODULE_MASTER.md)
- [Exam Module Master](./modules/EXAM_MODULE_MASTER.md)
- [Evaluation Module Master](./modules/EVALUATION_MODULE_MASTER.md)
- [Assignment Module Master](./modules/ASSIGNMENT_MODULE_MASTER.md)
- [Submission Module Master](./modules/SUBMISSION_MODULE_MASTER.md)

### Communication And Campus Operations

- [Communication Module Master](./modules/COMMUNICATION_MODULE_MASTER.md)
- [Notification Module Master](./modules/NOTIFICATION_MODULE_MASTER.md)
- [Club Module Master](./modules/CLUB_MODULE_MASTER.md)
- [Event Module Master](./modules/EVENT_MODULE_MASTER.md)
- [Group Module Master](./modules/GROUP_MODULE_MASTER.md)

### Intelligence And Reporting

- [AI Module Master](./modules/AI_MODULE_MASTER.md)
- [Analytics Module Master](./modules/ANALYTICS_MODULE_MASTER.md)

## Complete Module Tree

This tree shows the current module order and structural relationships in the codebase. It is an architectural reading map, not a strict package boundary map.

```text
CAPS AI
|-- Platform Foundation
|   |-- Auth
|   |-- User
|   |-- RBAC
|   |-- Governance
|   |   |-- Review Ticket
|   |   |-- Audit
|   |   `-- Recovery
|   |-- System
|   `-- Branding
|
|-- Academic Core
|   |-- Academic Setup
|   |   |-- Faculty
|   |   |-- Department
|   |   |-- Program
|   |   |-- Specialization
|   |   |-- Batch
|   |   |-- Semester
|   |   `-- Section
|   |-- Subject
|   |-- Teacher
|   |-- Student
|   |-- Enrollment
|   |-- Group
|   |-- Course Offering
|   |-- Class Section
|   |-- Class Slot
|   |-- Timetable
|   |-- Attendance
|   `-- Assessment
|       |-- Assignment
|       |-- Submission
|       |-- Evaluation
|       `-- Exam
|
|-- Communication And Campus Operations
|   |-- Communication
|   |   `-- Notification
|   |-- Club
|   `-- Event
|
`-- Intelligence And Reporting
    |-- AI
    `-- Analytics
```

## Functional Dependency Order

Read the modules in this order if you want the system from foundation to business workflows:

1. Platform Foundation
   - [Auth Module Master](./modules/AUTH_MODULE_MASTER.md)
   - [User Module Master](./modules/USER_MODULE_MASTER.md)
   - [RBAC Module Master](./modules/RBAC_MODULE_MASTER.md)
   - [Governance Module Master](./modules/GOVERNANCE_MODULE_MASTER.md)
   - [Audit Module Master](./modules/AUDIT_MODULE_MASTER.md)
   - [Review Ticket Module Master](./modules/REVIEW_TICKET_MODULE_MASTER.md)
   - [Recovery Module Master](./modules/RECOVERY_MODULE_MASTER.md)
   - [System Module Master](./modules/SYSTEM_MODULE_MASTER.md)
   - [Branding Module Master](./modules/BRANDING_MODULE_MASTER.md)

2. Academic Core
   - [Academic Module Master](./modules/ACADEMIC_MODULE_MASTER.md)
   - [Subject Module Master](./modules/SUBJECT_MODULE_MASTER.md)
   - [Teacher Module Master](./modules/TEACHER_MODULE_MASTER.md)
   - [Student Module Master](./modules/STUDENT_MODULE_MASTER.md)
   - [Enrollment Module Master](./modules/ENROLLMENT_MODULE_MASTER.md)
   - [Group Module Master](./modules/GROUP_MODULE_MASTER.md)
   - [Course Offering Module Master](./modules/COURSE_OFFERING_MODULE_MASTER.md)
   - [Class Section Module Master](./modules/CLASS_SECTION_MODULE_MASTER.md)
   - [Class Slot Module Master](./modules/CLASS_SLOT_MODULE_MASTER.md)
   - [Timetable Module Master](./modules/TIMETABLE_MODULE_MASTER.md)
   - [Attendance Module Master](./modules/ATTENDANCE_MODULE_MASTER.md)
   - [Assignment Module Master](./modules/ASSIGNMENT_MODULE_MASTER.md)
   - [Submission Module Master](./modules/SUBMISSION_MODULE_MASTER.md)
   - [Evaluation Module Master](./modules/EVALUATION_MODULE_MASTER.md)
   - [Exam Module Master](./modules/EXAM_MODULE_MASTER.md)

3. Communication And Campus Operations
   - [Communication Module Master](./modules/COMMUNICATION_MODULE_MASTER.md)
   - [Notification Module Master](./modules/NOTIFICATION_MODULE_MASTER.md)
   - [Club Module Master](./modules/CLUB_MODULE_MASTER.md)
   - [Event Module Master](./modules/EVENT_MODULE_MASTER.md)

4. Intelligence And Reporting
   - [AI Module Master](./modules/AI_MODULE_MASTER.md)
   - [Analytics Module Master](./modules/ANALYTICS_MODULE_MASTER.md)

## Academic Hierarchy Tree

The canonical academic hierarchy remains the central business tree for the product:

```text
University
`-- Faculty
    `-- Department
        `-- Program
            `-- Specialization
                `-- Batch
                    `-- Semester
                        `-- Section
```

Legacy compatibility hierarchy is retained only for historical data translation:

```text
Department
`-- Branch
    `-- Course
        `-- Year
            `-- Section
```

## Archives

- `./archives/OLD_DATA`

## Recommended Reading Order

1. [This Root Index](./README.md)
2. [Module Index](./guides/module-index.md)
3. [Backend Architecture](./guides/backend-architecture.md)
4. [Frontend Architecture](./guides/frontend-architecture.md)
5. [Data Model](./guides/data-model.md)
6. [Academic Setup Logic Audit](./ACADEMIC_SETUP_LOGIC_AUDIT.md)
7. Relevant module master in `docs/modules`

## Notes

- The canonical academic hierarchy remains:
  `Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`
- Legacy compatibility areas such as `courses`, `years`, `branches`, and class-named section storage should be treated as compatibility layers, not new design targets.
