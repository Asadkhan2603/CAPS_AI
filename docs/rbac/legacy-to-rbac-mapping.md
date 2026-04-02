# Legacy To RBAC Permission Mapping

This document defines the explicit legacy-to-RBAC mapping table for the next migration phase.

Status:
- specification only
- not applied to API decorators yet
- not applied to middleware yet
- not used as runtime alias logic

## Mapping Table

| Legacy Permission | RBAC Permission Mapping |
| --- | --- |
| `users.read` | `users.view` |
| `users.update` | `users.edit` |
| `analytics.read` | `analytics.view` |
| `audit.read` | `audit.view` |
| `system.read` | `system.view` |
| `announcements.publish` | `communication.create` |
| `communication:publish` | `communication.create` |
| `club:create` | `clubs.create` |
| `club:update` | `clubs.edit` |
| `clubs.manage` | `clubs.create`, `clubs.edit`, `clubs.delete`, `clubs.approve` |
| `academic:manage` | `subjects.create`, `subjects.edit`, `subjects.delete` |
| `admin:analytics` | `analytics.view`, `analytics.export`, `analytics.generate` |
| `universities.manage` | `faculty_management.create`, `faculty_management.edit`, `faculty_management.delete` |
| `faculties.manage` | `faculty_management.create`, `faculty_management.edit`, `faculty_management.delete` |
| `departments.manage` | `faculty_management.create`, `faculty_management.edit`, `faculty_management.delete` |
| `programs.manage` | `subjects.create`, `subjects.edit`, `subjects.delete` |
| `specializations.manage` | `subjects.create`, `subjects.edit`, `subjects.delete` |
| `batches.manage` | `student_management.create`, `student_management.edit`, `student_management.delete` |
| `semesters.manage` | `student_management.create`, `student_management.edit`, `student_management.delete` |
| `sections.manage` | `student_management.create`, `student_management.edit`, `student_management.delete` |
| `students.manage` | `student_management.create`, `student_management.edit`, `student_management.delete` |
| `students.bulk_import` | `student_management.create`, `users.create`, `users.activate` |
| `students.bulk_map` | `student_management.edit` |
| `sections.lock_mapping` | `student_management.approve` |

## Notes

- The mappings above are explicit replacements for the current vague alias behavior.
- The following legacy permissions now have direct first-class RBAC equivalents and should no longer be routed through report permissions:
  - `analytics.read -> analytics.view`
  - `audit.read -> audit.view`
  - `system.read -> system.view`
- Some legacy academic-structure permissions still map into broader current RBAC domains because the catalog does not yet have dedicated modules for:
  - universities
  - faculties
  - departments
  - programs
  - specializations
  - batches
  - semesters
  - sections
- If the next migration phase wants perfect domain fidelity, those academic-structure resources should be split into their own RBAC modules before runtime enforcement is switched.
