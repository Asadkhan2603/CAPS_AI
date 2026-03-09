# CAPS AI Documentation Index

This file is the root entry point for the documentation tree under `docs/`.

## Start Here

- [Module Index](d:\VS CODE\MY PROJECT\CAPS_AI\docs\guides\module-index.md)
- [Academic Setup Logic Audit](d:\VS CODE\MY PROJECT\CAPS_AI\docs\ACADEMIC_SETUP_LOGIC_AUDIT.md)

## Core Guides

- [API Contracts](d:\VS CODE\MY PROJECT\CAPS_AI\docs\guides\api-contracts.md)
- [Backend Architecture](d:\VS CODE\MY PROJECT\CAPS_AI\docs\guides\backend-architecture.md)
- [Data Model](d:\VS CODE\MY PROJECT\CAPS_AI\docs\guides\data-model.md)
- [Deployment](d:\VS CODE\MY PROJECT\CAPS_AI\docs\guides\deployment.md)
- [Frontend Architecture](d:\VS CODE\MY PROJECT\CAPS_AI\docs\guides\frontend-architecture.md)
- [Governance Workflows](d:\VS CODE\MY PROJECT\CAPS_AI\docs\guides\governance-workflows.md)
- [Testing](d:\VS CODE\MY PROJECT\CAPS_AI\docs\guides\testing.md)

## Module Masters

### Platform And Governance

- [Auth Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\AUTH_MODULE_MASTER.md)
- [User Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\USER_MODULE_MASTER.md)
- [RBAC Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\RBAC_MODULE_MASTER.md)
- [Governance Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\GOVERNANCE_MODULE_MASTER.md)
- [Review Ticket Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\REVIEW_TICKET_MODULE_MASTER.md)
- [Audit Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\AUDIT_MODULE_MASTER.md)
- [Recovery Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\RECOVERY_MODULE_MASTER.md)
- [System Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\SYSTEM_MODULE_MASTER.md)
- [Branding Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\BRANDING_MODULE_MASTER.md)

### Academic Core

- [Academic Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\ACADEMIC_MODULE_MASTER.md)
- [Subject Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\SUBJECT_MODULE_MASTER.md)
- [Teacher Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\TEACHER_MODULE_MASTER.md)
- [Student Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\STUDENT_MODULE_MASTER.md)
- [Enrollment Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\ENROLLMENT_MODULE_MASTER.md)
- [Course Offering Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\COURSE_OFFERING_MODULE_MASTER.md)
- [Class Section Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\CLASS_SECTION_MODULE_MASTER.md)
- [Class Slot Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\CLASS_SLOT_MODULE_MASTER.md)
- [Timetable Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\TIMETABLE_MODULE_MASTER.md)
- [Attendance Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\ATTENDANCE_MODULE_MASTER.md)
- [Exam Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\EXAM_MODULE_MASTER.md)
- [Evaluation Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\EVALUATION_MODULE_MASTER.md)
- [Assignment Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\ASSIGNMENT_MODULE_MASTER.md)
- [Submission Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\SUBMISSION_MODULE_MASTER.md)

### Communication And Campus Operations

- [Communication Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\COMMUNICATION_MODULE_MASTER.md)
- [Notification Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\NOTIFICATION_MODULE_MASTER.md)
- [Club Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\CLUB_MODULE_MASTER.md)
- [Event Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\EVENT_MODULE_MASTER.md)
- [Group Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\GROUP_MODULE_MASTER.md)

### Intelligence And Reporting

- [AI Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\AI_MODULE_MASTER.md)
- [Analytics Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\ANALYTICS_MODULE_MASTER.md)

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
   - [Auth Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\AUTH_MODULE_MASTER.md)
   - [User Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\USER_MODULE_MASTER.md)
   - [RBAC Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\RBAC_MODULE_MASTER.md)
   - [Governance Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\GOVERNANCE_MODULE_MASTER.md)
   - [Audit Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\AUDIT_MODULE_MASTER.md)
   - [Review Ticket Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\REVIEW_TICKET_MODULE_MASTER.md)
   - [Recovery Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\RECOVERY_MODULE_MASTER.md)
   - [System Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\SYSTEM_MODULE_MASTER.md)
   - [Branding Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\BRANDING_MODULE_MASTER.md)

2. Academic Core
   - [Academic Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\ACADEMIC_MODULE_MASTER.md)
   - [Subject Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\SUBJECT_MODULE_MASTER.md)
   - [Teacher Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\TEACHER_MODULE_MASTER.md)
   - [Student Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\STUDENT_MODULE_MASTER.md)
   - [Enrollment Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\ENROLLMENT_MODULE_MASTER.md)
   - [Group Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\GROUP_MODULE_MASTER.md)
   - [Course Offering Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\COURSE_OFFERING_MODULE_MASTER.md)
   - [Class Section Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\CLASS_SECTION_MODULE_MASTER.md)
   - [Class Slot Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\CLASS_SLOT_MODULE_MASTER.md)
   - [Timetable Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\TIMETABLE_MODULE_MASTER.md)
   - [Attendance Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\ATTENDANCE_MODULE_MASTER.md)
   - [Assignment Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\ASSIGNMENT_MODULE_MASTER.md)
   - [Submission Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\SUBMISSION_MODULE_MASTER.md)
   - [Evaluation Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\EVALUATION_MODULE_MASTER.md)
   - [Exam Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\EXAM_MODULE_MASTER.md)

3. Communication And Campus Operations
   - [Communication Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\COMMUNICATION_MODULE_MASTER.md)
   - [Notification Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\NOTIFICATION_MODULE_MASTER.md)
   - [Club Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\CLUB_MODULE_MASTER.md)
   - [Event Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\EVENT_MODULE_MASTER.md)

4. Intelligence And Reporting
   - [AI Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\AI_MODULE_MASTER.md)
   - [Analytics Module Master](d:\VS CODE\MY PROJECT\CAPS_AI\docs\modules\ANALYTICS_MODULE_MASTER.md)

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

Legacy compatibility hierarchy still exists in parts of the codebase and should not be extended:

```text
Department
`-- Branch
    `-- Course
        `-- Year
            `-- Section/Class
```

## Archives

- `docs/archives/OLD_DATA`

## Recommended Reading Order

1. [This Root Index](d:\VS CODE\MY PROJECT\CAPS_AI\docs\README.md)
2. [Module Index](d:\VS CODE\MY PROJECT\CAPS_AI\docs\guides\module-index.md)
3. [Backend Architecture](d:\VS CODE\MY PROJECT\CAPS_AI\docs\guides\backend-architecture.md)
4. [Frontend Architecture](d:\VS CODE\MY PROJECT\CAPS_AI\docs\guides\frontend-architecture.md)
5. [Data Model](d:\VS CODE\MY PROJECT\CAPS_AI\docs\guides\data-model.md)
6. [Academic Setup Logic Audit](d:\VS CODE\MY PROJECT\CAPS_AI\docs\ACADEMIC_SETUP_LOGIC_AUDIT.md)
7. Relevant module master in `docs/modules`

## Notes

- The canonical academic hierarchy remains:
  `Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`
- Legacy compatibility areas such as `courses`, `years`, `branches`, and class-named section storage should be treated as compatibility layers, not new design targets.

