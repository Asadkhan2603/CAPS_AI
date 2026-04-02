# Academic Master Hierarchy

## Purpose

This module owns the canonical institutional hierarchy above the app-managed academic operations layer.

## Data Model

Entities:

- universities
- faculties
- departments
- programs
- specializations

Master identifiers:

- `university_id`
- `faculty_id`
- `department_id`
- `program_id`
- `specialization_id`

The business ID generation rules are implemented in `master_hierarchy.py`.

## APIs

Primary endpoints:

- `/universities`
- `/faculties`
- `/departments`
- `/programs`
- `/programs/seed-batches`
- `/specializations`
- `/specializations/seed-batches`

## Workflow

1. import or create top-level master records
2. validate business IDs and parent lineage
3. enforce program duration and specialization constraints
4. seed downstream batches when applicable
5. block destructive changes when active descendants exist

## Dependencies

- `backend/scripts/import_master_hierarchy.py`
- `backend/scripts/audit_academic_integrity.py`
- `backend/app/services/master_hierarchy.py`
- `backend/app/services/academic_hierarchy.py`
- endpoints for universities through specializations
