# Course Delivery And Timetable

## Purpose

This module owns section-level teaching delivery, scheduling, and teaching assignments.

## Data Model

Entities:

- subjects
- course_offerings
- class_slots
- timetables
- timetable subject-teacher maps

Key links:

- course offering belongs to a section
- timetable belongs to a section through `class_id`
- class slot reflects active delivery windows

## APIs

Primary endpoints:

- `/subjects`
- `/course-offerings`
- `/class-slots`
- `/class-slots/my`
- `/timetables/shifts`
- `/timetables/generate-grid`
- `/timetables/lookups`
- `/timetables`
- `/timetables/class/{class_id}`
- `/timetables/my`
- `/timetables/{timetable_id}/publish`
- `/timetables/{timetable_id}/lock`

## Workflow

1. create subjects
2. attach course offerings to sections
3. create class slots and timetables
4. map subject-teacher responsibility
5. publish and lock finalized timetable versions

## Dependencies

- subjects, offerings, class slots, and timetable endpoints
- `backend/app/services/section_mapping.py`
- `frontend/src/pages/SubjectsPage.jsx`
- `frontend/src/pages/CourseOfferingsPage.jsx`
- `frontend/src/pages/ClassSlotsPage.jsx`
- `frontend/src/pages/TimetablePage.jsx`
