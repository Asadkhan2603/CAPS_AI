# Module Index

This file is the entry point for the project documentation tree under `docs/`.

## Core Audits

- [Documentation Audit Report](../DOCUMENTATION_AUDIT_REPORT.md)
- [Academic Setup Logic Audit](../ACADEMIC_SETUP_LOGIC_AUDIT.md)

## Module Masters

### Platform And Governance

- [Auth Module Master](../modules/AUTH_MODULE_MASTER.md)
- [User Module Master](../modules/USER_MODULE_MASTER.md)
- [RBAC Module Master](../modules/RBAC_MODULE_MASTER.md)
- [Governance Module Master](../modules/GOVERNANCE_MODULE_MASTER.md)
- [Review Ticket Module Master](../modules/REVIEW_TICKET_MODULE_MASTER.md)
- [Audit Module Master](../modules/AUDIT_MODULE_MASTER.md)
- [Recovery Module Master](../modules/RECOVERY_MODULE_MASTER.md)
- [System Module Master](../modules/SYSTEM_MODULE_MASTER.md)
- [Branding Module Master](../modules/BRANDING_MODULE_MASTER.md)

### Academic Core

- [Academic Module Master](../modules/ACADEMIC_MODULE_MASTER.md)
- [Subject Module Master](../modules/SUBJECT_MODULE_MASTER.md)
- [Teacher Module Master](../modules/TEACHER_MODULE_MASTER.md)
- [Student Module Master](../modules/STUDENT_MODULE_MASTER.md)
- [Enrollment Module Master](../modules/ENROLLMENT_MODULE_MASTER.md)
- [Course Offering Module Master](../modules/COURSE_OFFERING_MODULE_MASTER.md)
- [Class Section Module Master](../modules/CLASS_SECTION_MODULE_MASTER.md)
- [Class Slot Module Master](../modules/CLASS_SLOT_MODULE_MASTER.md)
- [Timetable Module Master](../modules/TIMETABLE_MODULE_MASTER.md)
- [Attendance Module Master](../modules/ATTENDANCE_MODULE_MASTER.md)
- [Exam Module Master](../modules/EXAM_MODULE_MASTER.md)
- [Evaluation Module Master](../modules/EVALUATION_MODULE_MASTER.md)
- [Assignment Module Master](../modules/ASSIGNMENT_MODULE_MASTER.md)
- [Submission Module Master](../modules/SUBMISSION_MODULE_MASTER.md)

### Communication And Campus Operations

- [Communication Module Master](../modules/COMMUNICATION_MODULE_MASTER.md)
- [Notification Module Master](../modules/NOTIFICATION_MODULE_MASTER.md)
- [Club Module Master](../modules/CLUB_MODULE_MASTER.md)
- [Event Module Master](../modules/EVENT_MODULE_MASTER.md)
- [Group Module Master](../modules/GROUP_MODULE_MASTER.md)

### Intelligence And Reporting

- [AI Module Master](../modules/AI_MODULE_MASTER.md)
- [Analytics Module Master](../modules/ANALYTICS_MODULE_MASTER.md)

## Complete Module Tree

This tree shows the current module order and structural relationships in the codebase.

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

1. Platform Foundation
   - [Auth Module Master](../modules/AUTH_MODULE_MASTER.md)
   - [User Module Master](../modules/USER_MODULE_MASTER.md)
   - [RBAC Module Master](../modules/RBAC_MODULE_MASTER.md)
   - [Governance Module Master](../modules/GOVERNANCE_MODULE_MASTER.md)
   - [Audit Module Master](../modules/AUDIT_MODULE_MASTER.md)
   - [Review Ticket Module Master](../modules/REVIEW_TICKET_MODULE_MASTER.md)
   - [Recovery Module Master](../modules/RECOVERY_MODULE_MASTER.md)
   - [System Module Master](../modules/SYSTEM_MODULE_MASTER.md)
   - [Branding Module Master](../modules/BRANDING_MODULE_MASTER.md)

2. Academic Core
   - [Academic Module Master](../modules/ACADEMIC_MODULE_MASTER.md)
   - [Subject Module Master](../modules/SUBJECT_MODULE_MASTER.md)
   - [Teacher Module Master](../modules/TEACHER_MODULE_MASTER.md)
   - [Student Module Master](../modules/STUDENT_MODULE_MASTER.md)
   - [Enrollment Module Master](../modules/ENROLLMENT_MODULE_MASTER.md)
   - [Group Module Master](../modules/GROUP_MODULE_MASTER.md)
   - [Course Offering Module Master](../modules/COURSE_OFFERING_MODULE_MASTER.md)
   - [Class Section Module Master](../modules/CLASS_SECTION_MODULE_MASTER.md)
   - [Class Slot Module Master](../modules/CLASS_SLOT_MODULE_MASTER.md)
   - [Timetable Module Master](../modules/TIMETABLE_MODULE_MASTER.md)
   - [Attendance Module Master](../modules/ATTENDANCE_MODULE_MASTER.md)
   - [Assignment Module Master](../modules/ASSIGNMENT_MODULE_MASTER.md)
   - [Submission Module Master](../modules/SUBMISSION_MODULE_MASTER.md)
   - [Evaluation Module Master](../modules/EVALUATION_MODULE_MASTER.md)
   - [Exam Module Master](../modules/EXAM_MODULE_MASTER.md)

3. Communication And Campus Operations
   - [Communication Module Master](../modules/COMMUNICATION_MODULE_MASTER.md)
   - [Notification Module Master](../modules/NOTIFICATION_MODULE_MASTER.md)
   - [Club Module Master](../modules/CLUB_MODULE_MASTER.md)
   - [Event Module Master](../modules/EVENT_MODULE_MASTER.md)

4. Intelligence And Reporting
   - [AI Module Master](../modules/AI_MODULE_MASTER.md)
   - [Analytics Module Master](../modules/ANALYTICS_MODULE_MASTER.md)

## Academic Hierarchy Tree

Canonical academic hierarchy:

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

## Guides

- [API Contracts](./api-contracts.md)
- [Backend Architecture](./backend-architecture.md)
- [Data Model](./data-model.md)
- [Deployment](./deployment.md)
- [Frontend Architecture](./frontend-architecture.md)
- [Governance Workflows](./governance-workflows.md)
- [Testing](./testing.md)

## Archives

- `../archives/OLD_DATA`

## Recommended Reading Order

1. [Module Index](./module-index.md)
2. [Backend Architecture](./backend-architecture.md)
3. [Frontend Architecture](./frontend-architecture.md)
4. [Data Model](./data-model.md)
5. [Academic Setup Logic Audit](../ACADEMIC_SETUP_LOGIC_AUDIT.md)
6. Relevant module master under `docs/modules`

## Notes

- `ACADEMIC_MODULE_MASTER.md` should remain the umbrella for the canonical hierarchy:
  `Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`
- Legacy compatibility areas such as courses, years, branches, and classes should be documented inside the relevant module masters with explicit deprecation or compatibility notes.
