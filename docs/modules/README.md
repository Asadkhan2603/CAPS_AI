# Module Docs Review Index

Reviewed on `2026-03-11`.

This index covers the module master documents under `docs/modules` and records a structural review status for each file.

Review method:

- checked the full module-doc set for coverage, consistency, and maintainability
- compared the docs set against the common module-reference shape used in the stronger masters:
  - overview
  - data or collections
  - backend logic
  - business rules
  - API surface
  - frontend implementation
  - testing
  - final summary
- marked the next refresh priority where a module master is useful but still uneven
- for duplicate surface and module overlap review, use [DUPLICATE_FEATURES_AND_MODULES_AUDIT.md](/docs/modules/DUPLICATE_FEATURES_AND_MODULES_AUDIT.md)
- for keep/merge/retire decisions on each duplicate, use [DUPLICATE_FEATURES_TREATMENT_PLAN.md](/docs/modules/DUPLICATE_FEATURES_TREATMENT_PLAN.md)

Status legend:

- `Reference-ready`: broad operational coverage and usable as a current module reference
- `Targeted reference`: useful and substantial, but the structure is narrower than the preferred master format
- `Needs structured refresh`: valid starting point, but should be normalized to the full module master format in the next pass

## Review Matrix

| Module | Doc | Status | Review Note |
|---|---|---|---|
| Academic | `ACADEMIC_MODULE_MASTER.md` | `Reference-ready` | Strong canonical hierarchy, collection, API, governance, and testing coverage |
| AI | `AI_MODULE_MASTER.md` | `Reference-ready` | Strong implementation and workflow coverage; already links companion planning docs |
| Analytics | `ANALYTICS_MODULE_MASTER.md` | `Reference-ready` | Good operational reference with enough implementation detail for current use |
| Assignment | `ASSIGNMENT_MODULE_MASTER.md` | `Needs structured refresh` | Useful content exists, but it needs stronger API, frontend, and business-rule normalization |
| Attendance | `ATTENDANCE_MODULE_MASTER.md` | `Reference-ready` | Good balance of rules, APIs, frontend usage, and operational behavior |
| Audit | `AUDIT_MODULE_MASTER.md` | `Reference-ready` | Broad enough for current governance and telemetry review workflows |
| Auth | `AUTH_MODULE_MASTER.md` | `Targeted reference` | Deep content, but the section structure should be normalized to the common master format |
| Branding | `BRANDING_MODULE_MASTER.md` | `Targeted reference` | Useful focused doc; should expand API, frontend, and testing sections in a later pass |
| Class / Section | `CLASS_SECTION_MODULE_MASTER.md` | `Targeted reference` | Operationally helpful, but needs stronger API and testing structure |
| Class Slot | `CLASS_SLOT_MODULE_MASTER.md` | `Targeted reference` | Good implementation notes, but should be normalized to the shared master outline |
| Club | `CLUB_MODULE_MASTER.md` | `Reference-ready` | Good data, backend, and testing coverage for current module shape |
| Communication | `COMMUNICATION_MODULE_MASTER.md` | `Targeted reference` | Useful current-state doc; should expand API and testing coverage |
| Course Offering | `COURSE_OFFERING_MODULE_MASTER.md` | `Targeted reference` | Good implementation detail; needs fuller business-rule and frontend normalization |
| Enrollment | `ENROLLMENT_MODULE_MASTER.md` | `Needs structured refresh` | Present but too light relative to module importance and access-rule complexity |
| Evaluation | `EVALUATION_MODULE_MASTER.md` | `Needs structured refresh` | Important module that needs a more explicit API, frontend, and testing breakdown |
| Event | `EVENT_MODULE_MASTER.md` | `Reference-ready` | Strong current-state coverage across data, rules, APIs, frontend, and tests |
| Exam | `EXAM_MODULE_MASTER.md` | `Targeted reference` | Substantial and useful, but still uneven against the preferred master structure |
| Governance | `GOVERNANCE_MODULE_MASTER.md` | `Reference-ready` | Good governance flow reference with strong frontend and operational value |
| Group | `GROUP_MODULE_MASTER.md` | `Needs structured refresh` | Valid doc, but the module master needs fuller API, frontend, and testing structure |
| Notification | `NOTIFICATION_MODULE_MASTER.md` | `Needs structured refresh` | Helpful surface coverage, but the master needs more backend, rules, and testing detail |
| RBAC | `RBAC_MODULE_MASTER.md` | `Targeted reference` | Strong policy context, but the master structure should be normalized for consistency |
| Recovery | `RECOVERY_MODULE_MASTER.md` | `Needs structured refresh` | Good targeted doc, but it should be expanded into the full module format |
| Review Ticket | `REVIEW_TICKET_MODULE_MASTER.md` | `Reference-ready` | Strong workflow and testing orientation for a governance-sensitive module |
| Student | `STUDENT_MODULE_MASTER.md` | `Reference-ready` | Broad enough to serve as a real operational reference |
| Subject | `SUBJECT_MODULE_MASTER.md` | `Needs structured refresh` | Existing master should be expanded to cover API, frontend, and testing in more detail |
| Submission | `SUBMISSION_MODULE_MASTER.md` | `Targeted reference` | Good implementation notes, but still narrower than the stronger module masters |
| System | `SYSTEM_MODULE_MASTER.md` | `Reference-ready` | Strong operational and platform-level value |
| Teacher | `TEACHER_MODULE_MASTER.md` | `Reference-ready` | Broad enough to guide workflow and permission review |
| Timetable | `TIMETABLE_MODULE_MASTER.md` | `Reference-ready` | Good current-state module reference with strong downstream impact |
| User | `USER_MODULE_MASTER.md` | `Reference-ready` | Good base module reference with implementation depth and testing guidance |

## Next Refresh Priority

Highest-priority masters to normalize next:

1. `ENROLLMENT_MODULE_MASTER.md`
2. `EVALUATION_MODULE_MASTER.md`
3. `NOTIFICATION_MODULE_MASTER.md`
4. `SUBJECT_MODULE_MASTER.md`
5. `GROUP_MODULE_MASTER.md`
6. `ASSIGNMENT_MODULE_MASTER.md`

Second-priority normalization set:

1. `AUTH_MODULE_MASTER.md`
2. `BRANDING_MODULE_MASTER.md`
3. `CLASS_SECTION_MODULE_MASTER.md`
4. `CLASS_SLOT_MODULE_MASTER.md`
5. `COMMUNICATION_MODULE_MASTER.md`
6. `COURSE_OFFERING_MODULE_MASTER.md`
7. `EXAM_MODULE_MASTER.md`
8. `RBAC_MODULE_MASTER.md`
9. `RECOVERY_MODULE_MASTER.md`
10. `SUBMISSION_MODULE_MASTER.md`

## Notes

- The module-doc set is already strong in breadth; the main issue is consistency, not absence.
- The best current master documents are the ones that connect backend behavior, frontend surfaces, business rules, and tests in one place.
- Use this index as the review checkpoint for future doc updates rather than re-auditing the folder from scratch each time.
- For legacy academic cleanup sequencing, use [LEGACY_ACADEMIC_MIGRATION_CHECKLIST.md](./LEGACY_ACADEMIC_MIGRATION_CHECKLIST.md) as the dependency and retirement tracker for `courses`, `years`, and `branches`.


