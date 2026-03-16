# Master Hierarchy Mutation Safety

## Principle

Master hierarchy changes must not strand active descendants or dependent operational records.

CAPS AI now rejects unsafe mutations instead of silently rewriting branches.

## Protected Mutations

### Universities

University archive is blocked while active faculties still exist below that university.

### Faculties

Faculty archive or move-to-another-university is blocked while active:
- departments
- class records
- user scope records

### Departments

Department archive or move-to-another-faculty is blocked while active:
- programs
- class records
- user scope records

### Programs

Program archive or move-to-another-department is blocked while active:
- specializations
- batches
- semesters
- sections/classes
- user scope records

### Specializations

Specialization archive or move-to-another-program is blocked while active:
- batches
- semesters
- sections/classes
- user scope records

## Why We Reject Instead Of Cascading

Automatic cross-branch rewrites are risky because they can:
- invalidate operational history
- change academic meaning of existing batches/sections
- break downstream lineage assumptions

For production safety, CAPS AI prefers explicit cleanup and review before mutation.

## Admin Guidance

If a master mutation is blocked:

1. find active descendants
2. archive or move descendants intentionally
3. rerun the master change

If the change comes from workbook import, use the dry run first and review blocker output before applying.
