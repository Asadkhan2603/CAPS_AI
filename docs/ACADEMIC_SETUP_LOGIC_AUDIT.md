# Academic Setup And Logic Audit

## Purpose

This document is a current-state audit of the Academic Setup and Academic Structure modules in CAPS AI.

It is based on a direct repository scan of the backend, frontend, models, schemas, routes, and supporting scripts. The goal is to document:

- what is already implemented
- what business logic exists in code
- what is exposed in the UI
- what exists in code but is not fully wired or not actively used
- what architectural inconsistencies currently exist

This is not a target-state design document. It describes what the codebase actually does today.

## Decision Status

The platform now explicitly adopts:

`Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`

as the canonical academic model.

`Course`, `Year`, and `Branch` remain in the codebase as legacy compatibility modules and are no longer treated as co-equal academic hierarchy roots.

## Canonical Academic Model In Code

The primary hierarchy implemented in the current codebase is:

`Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`

The repository also still contains a secondary legacy chain:

`Course -> Year -> Section`

There is also a legacy side structure:

`Department -> Branch`

This means the codebase still contains two overlapping academic models in implementation, but only one is canonical:

- the newer hierarchy built around `programs`, `batches`, and `semesters`
- the older or parallel hierarchy built around `courses`, `years`, and `branches`

This overlap is one of the main sources of logic drift in the system.

## Scan Coverage

The following code areas were reviewed for this audit.

### Backend

- `backend/app/api/v1/router.py`
- `backend/app/api/v1/endpoints/faculties.py`
- `backend/app/api/v1/endpoints/departments.py`
- `backend/app/api/v1/endpoints/programs.py`
- `backend/app/api/v1/endpoints/specializations.py`
- `backend/app/api/v1/endpoints/batches.py`
- `backend/app/api/v1/endpoints/semesters.py`
- `backend/app/api/v1/endpoints/classes.py`
- `backend/app/api/v1/endpoints/courses.py`
- `backend/app/api/v1/endpoints/years.py`
- `backend/app/api/v1/endpoints/branches.py`
- `backend/app/api/v1/endpoints/course_offerings.py`
- `backend/app/api/v1/endpoints/class_slots.py`
- `backend/app/api/v1/endpoints/groups.py`
- `backend/app/api/v1/endpoints/students.py`
- `backend/app/api/v1/endpoints/subjects.py`
- `backend/app/api/v1/endpoints/enrollments.py`
- `backend/app/core/security.py`
- `backend/app/core/permission_registry.py`
- `backend/app/services/governance.py`
- `backend/app/domains/academic/service.py`
- `backend/app/domains/academic/repository.py`
- related models and schemas under `backend/app/models` and `backend/app/schemas`

### Frontend

- `frontend/src/routes/AppRoutes.jsx`
- `frontend/src/config/featureAccess.js`
- `frontend/src/components/layout/Sidebar.jsx`
- `frontend/src/components/ui/EntityManager.jsx`
- `frontend/src/pages/FacultiesPage.jsx`
- `frontend/src/pages/DepartmentsPage.jsx`
- `frontend/src/pages/ProgramsPage.jsx`
- `frontend/src/pages/SpecializationsPage.jsx`
- `frontend/src/pages/BatchesPage.jsx`
- `frontend/src/pages/SemestersPage.jsx`
- `frontend/src/pages/ClassesPage.jsx`
- `frontend/src/pages/CoursesPage.jsx`
- `frontend/src/pages/YearsPage.jsx`
- `frontend/src/pages/BranchesPage.jsx`
- `frontend/src/pages/AcademicStructurePage.jsx`
- `frontend/src/pages/Admin/AdminAcademicStructurePage.jsx`
- related setup and academic pages using the same data chain

### Data Feed / Seeding

- `scripts/README.md`
- `scripts/seed_minimum_stack.ps1`
- `scripts/seed_medicaps_departments_branches.py`
- `out/feed-hierarchy.ps1`

## Architecture Summary

### Backend Architecture

The academic setup backend is mostly implemented as direct FastAPI endpoint handlers that talk straight to MongoDB collections through `db.<collection>`.

Only `courses` currently use a distinct domain layer:

- `backend/app/domains/academic/service.py`
- `backend/app/domains/academic/repository.py`

Everything else is endpoint-centric CRUD with validation embedded in the route functions.

Common implementation characteristics:

- pagination via `skip` and `limit`
- soft delete through `is_active = false`
- canonical archival metadata in the academic setup module through `deleted_at` and `deleted_by`
- foreign key validation using Mongo lookups
- permissions enforced through `require_roles(...)` or `require_permission(...)`

### Frontend Architecture

The setup UI is split into two patterns:

- generic CRUD pages built on `frontend/src/components/ui/EntityManager.jsx`
- custom academic hierarchy pages such as `AcademicStructurePage.jsx` and `ClassesPage.jsx`

The generic `EntityManager` provides:

- filters
- create form
- list table
- optional edit support
- optional delete support
- optional searchable selects

This means whether a module is editable in the UI is mostly decided page-by-page, not backend-by-backend.

## Route Inventory

Academic routes are mounted in `backend/app/api/v1/router.py`.

Canonical setup routes:

- `/faculties`
- `/departments`
- `/programs`
- `/specializations`
- `/batches`
- `/semesters`
- `/sections`

Legacy compatibility routes:

- `/classes`
- `/courses`
- `/years`
- `/branches`

Important note:

- `/sections` is the canonical route for sections
- `/classes` is still mounted as a legacy compatibility alias and is deprecated for new clients
- `/courses`, `/years`, and `/branches` are now marked as deprecated in API metadata

The router now distinguishes canonical routes from legacy compatibility routes directly in API metadata.

## Frontend Route And Navigation Inventory

The academic setup UI is exposed through:

- `/admin/academic-structure`
- `/academic-structure`
- `/faculties`
- `/departments`
- `/programs`
- `/specializations`
- `/batches`
- `/semesters`
- `/sections`
- `/courses`
- `/years`
- `/branches`

There are two distinct academic structure views:

- `AdminAcademicStructurePage.jsx`
  - acts as a navigation launcher for setup pages
  - now separates canonical setup modules from legacy compatibility modules
- `AcademicStructurePage.jsx`
  - renders the lazy-loaded drill-down tree from faculty to section
  - explicitly labels the faculty-to-section path as canonical
  - surfaces courses, years, and branches only as legacy compatibility links

## Entity-By-Entity Module Audit

### 1. Faculties

Backend:

- collection: `faculties`
- endpoint: `backend/app/api/v1/endpoints/faculties.py`
- supports list, get, create, update, archive
- enforces unique faculty code
- stores `university_name` and `university_code`

Frontend:

- page: `frontend/src/pages/FacultiesPage.jsx`
- create enabled
- edit enabled
- delete enabled
- university fields exposed in create form

Implemented logic:

- code normalized to uppercase
- name trimmed
- university metadata optional
- active/inactive state shown in UI

Status:

- this is one of the most complete setup modules end-to-end

### 2. Departments

Backend:

- collection: `departments`
- endpoint: `backend/app/api/v1/endpoints/departments.py`
- supports list, get, create, update, archive
- validates `faculty_id` on create and update when supplied
- enforces unique department code
- stores `university_name` and `university_code`
- on update, propagates department changes into `branches`
- on delete, archives related branches by department code
- delete can require governance review via `review_id`

Frontend:

- page: `frontend/src/pages/DepartmentsPage.jsx`
- create enabled
- edit enabled
- delete enabled
- faculty relation shown in table
- university metadata is now surfaced intentionally in both form and table

Implemented logic:

- department belongs to faculty when faculty is provided
- branch records denormalize department name and code
- university metadata is treated as operator-managed setup data, not backend-only metadata

Not fully used:

- governance-gated delete support is now wired through the shared `EntityManager` review id input for setup pages using that component

### 3. Programs

Backend:

- collection: `programs`
- endpoint: `backend/app/api/v1/endpoints/programs.py`
- supports list, get, create, update, archive
- validates `department_id`
- enforces unique program code
- stores `duration_years`
- stores `total_semesters`

Frontend:

- page: `frontend/src/pages/ProgramsPage.jsx`
- create enabled only for selected admin types
- edit enabled only for selected admin types
- delete enabled only for selected admin types
- duration shown in UI
- read-only banner explains that total semesters is auto-generated

Implemented logic:

- course duration must be between 3 and 5 years
- total semesters always equals `duration_years * 2`
- duration change is blocked if students are already enrolled in existing program semesters
- changing duration triggers semester synchronization across batches

Actual duration editor access in code:

- `super_admin`
- `admin`
- `academic_admin`
- `department_admin`

Status:

- this is the strongest business-rule module in the academic setup stack

### 4. Specializations

Backend:

- collection: `specializations`
- endpoint: `backend/app/api/v1/endpoints/specializations.py`
- supports list, get, create, update, archive
- validates `program_id`
- enforces unique specialization code

Frontend:

- page: `frontend/src/pages/SpecializationsPage.jsx`
- create enabled
- delete enabled
- edit not enabled in UI
- program relation shown in table

Implemented logic:

- specialization must belong to an existing program

Not fully used:

- backend update exists but UI edit is not exposed

### 5. Batches

Backend:

- collection: `batches`
- endpoint: `backend/app/api/v1/endpoints/batches.py`
- supports list, get, create, update, archive
- validates `program_id`
- validates `specialization_id`
- checks that specialization belongs to the selected program
- auto-derives academic years from program duration
- auto-creates semesters for the new batch

Frontend:

- page: `frontend/src/pages/BatchesPage.jsx`
- create enabled
- delete enabled
- edit not enabled in UI
- searchable program and specialization selection
- specialization selection is filtered by chosen program

Implemented logic:

- if only `start_year` is supplied, `end_year` is derived
- if only `end_year` is supplied, `start_year` is derived
- if both are supplied, they must match expected duration
- batch semester rows are created automatically based on program duration

Not fully used:

- backend update exists but UI edit is not exposed

### 6. Semesters

Backend:

- collection: `semesters`
- endpoint: `backend/app/api/v1/endpoints/semesters.py`
- supports list, get, create, update, archive
- validates `batch_id`
- enforces uniqueness of `(batch_id, semester_number)`

Frontend:

- page: `frontend/src/pages/SemestersPage.jsx`
- create enabled
- delete enabled
- edit not enabled in UI

Implemented logic:

- semester number must be unique inside a batch
- batch must exist

Not fully used:

- backend update exists but UI edit is not exposed

### 7. Sections

Backend:

- collection: `classes`
- endpoint: `backend/app/api/v1/endpoints/classes.py`
- mounted under both `/classes` and `/sections`
- supports list, get, create, update, archive
- delete can require governance review via `review_id`

Frontend:

- page: `frontend/src/pages/ClassesPage.jsx`
- custom cascading form
- supports faculty -> department -> program -> specialization -> batch -> semester filtering
- supports create and list
- does not expose all backend-supported fields equally

Implemented logic:

- validates faculty existence
- validates department existence and faculty ownership
- validates program existence and department ownership
- validates specialization existence and program ownership
- validates course existence
- validates year existence and course ownership
- validates batch existence
- validates semester existence and batch ownership
- teacher reads are scoped to `class_coordinator_user_id`

Important data model detail:

Sections can store both modern and legacy relationships:

- `faculty_id`
- `department_id`
- `program_id`
- `specialization_id`
- `batch_id`
- `semester_id`
- `course_id`
- `year_id`

Not fully used:

- frontend does not fully expose `course_id` and `year_id` even though backend supports them
- frontend uses `branch_name` as a displayed section code in some views, which is semantically confusing

### 8. Courses

Backend:

- collection: `courses`
- endpoint: `backend/app/api/v1/endpoints/courses.py`
- supports list, get, create, update, archive
- implemented through a dedicated service and repository layer

Frontend:

- page: `frontend/src/pages/CoursesPage.jsx`
- list only
- create hidden
- delete disabled
- edit disabled

Implemented logic:

- unique course code
- name and code normalization
- soft archive
- governance review for delete

Not fully used:

- backend CRUD exists
- UI is effectively read-only

### 9. Years

Backend:

- collection: `years`
- endpoint: `backend/app/api/v1/endpoints/years.py`
- supports list, get, create, update, archive
- validates `course_id`
- uniqueness is `(course_id, year_number)`
- delete can require governance review

Frontend:

- page: `frontend/src/pages/YearsPage.jsx`
- create enabled
- delete enabled
- edit not enabled

Implemented logic:

- year belongs to course
- year number uniqueness inside course

Not fully used:

- backend update exists but UI edit is not exposed

### 10. Branches

Backend:

- collection: `branches`
- endpoint: `backend/app/api/v1/endpoints/branches.py`
- supports list, get, create, update, archive
- validates `department_code`, not `department_id`
- denormalizes `department_name`, `university_name`, and `university_code`
- delete can require governance review

Frontend:

- page: `frontend/src/pages/BranchesPage.jsx`
- create enabled
- delete enabled
- edit not enabled
- department relation uses department code

Implemented logic:

- branches are attached to departments by code, not by object id
- department updates propagate branch name and code metadata

Architectural note:

- this is a denormalized legacy-style relation compared to the main id-based hierarchy

Not fully used:

- backend update exists but UI edit is not exposed

## Core Academic Business Logic

### Program Duration Logic

This is the strongest rule engine in the module and should be treated as the canonical academic duration configuration.

Rules currently enforced:

- minimum duration = 3 years
- maximum duration = 5 years
- `total_semesters = duration_years * 2`
- duration changes are blocked when enrolled students already exist in current program semesters
- duration changes trigger semester synchronization for all batches under that program

This means the program entity already acts as the source of truth for:

- academic duration
- semester count
- downstream batch semester structure

### Batch Creation Logic

When a batch is created:

- the selected program must exist
- optional specialization must belong to that program
- academic years are validated or auto-derived
- semesters are generated automatically based on the program's duration and total semesters

This makes `batch` a derived operational entity, not a free-form record.

### Semester Synchronization Logic

When program duration changes:

- expected semesters are ensured for every batch in that program
- missing semesters are created
- inactive required semesters are reactivated
- semesters beyond the new configured total are archived

This is an important automation feature already present in the backend.

### Section Integrity Logic

Sections are the most heavily validated node because they sit at the bottom of the hierarchy.

The backend checks:

- department belongs to faculty
- program belongs to department
- specialization belongs to program
- year belongs to course
- semester belongs to batch

This prevents invalid cross-tree assignments during section creation or update.

### Teacher Scope Logic

Teacher access to sections is not general-purpose.

In `classes.py`:

- teacher list results are restricted to records where `class_coordinator_user_id` matches the logged-in teacher
- teacher single-record access is blocked if the section is not assigned to them

This is real operational scoping logic, not just UI hiding.

### Governance Review Logic

Some delete routes support workflow gating via `enforce_review_approval(...)`.

This exists for:

- departments
- branches
- years
- courses
- classes or sections

Meaning:

- the backend is already capable of requiring an approved review ticket before destructive actions
- `EntityManager` can now pass an optional `review_id`, optional review metadata, and surfaces governance rejection errors inline and in toast notifications
- when the backend indicates that delete approval is required, the shared CRUD UI now opens a governance review prompt and lets the operator retry the delete with the approved `review_id`
- academic setup delete endpoints now emit destructive-action telemetry on request and completion
- governance enforcement now emits structured audit telemetry when a destructive action is blocked for missing or invalid review approval and when an approved review is executed
- destructive-action telemetry records actor id, entity, action, stage, `review_id` presence, and governance completion state

The remaining gap is that custom delete UIs outside `EntityManager` still need explicit review flow wiring.

### Static Analysis And Safety Gates

The academic setup safety-critical backend paths now have CI-backed static analysis coverage.

Current automated checks:

- `flake8` on governance and academic delete safety-critical modules
- `mypy` on governance and academic delete safety-critical modules with unreachable-code warnings enabled
- `bandit` on governance and academic delete safety-critical modules
- a custom AST safety check in `scripts/check_backend_safety.py`

The custom safety check currently enforces:

- detection of obvious unreachable statements after `return`, `raise`, `break`, or `continue`
- governance contract validation for review-gated delete handlers
- required `review_id` parameter on the protected delete endpoints
- required `enforce_review_approval(...)` call on the protected delete endpoints

Scope of the current CI safety gate:

- `backend/app/services/governance.py`
- `backend/app/api/v1/endpoints/departments.py`
- `backend/app/api/v1/endpoints/branches.py`
- `backend/app/api/v1/endpoints/years.py`
- `backend/app/api/v1/endpoints/courses.py`
- `backend/app/api/v1/endpoints/classes.py`
- `scripts/check_backend_safety.py`

This scope is intentionally narrow for now. It covers the governance-sensitive academic setup paths without failing the pipeline on unrelated legacy lint debt elsewhere in the backend.

### Automated Test Coverage

The academic setup module now has targeted automated coverage for its highest-risk business rules.

Current backend rule tests cover:

- program duration change safety, including rejection when enrolled students already exist
- semester synchronization when program duration changes, including creating missing semesters, reactivating required semesters, and archiving extra semesters
- batch creation semester generation from program duration
- section cross-entity ownership validation across faculty, department, program, specialization, batch, and semester relationships
- governance-gated delete behavior when `review_id` is required

Current permission-alignment coverage includes:

- backend integration tests that verify route-level academic permission enforcement
- frontend permission tests that verify `FEATURE_ACCESS` matches the intended backend policy split between:
  - central academic setup modules
  - lower-hierarchy canonical setup modules
  - teacher read access for sections

Relevant test files:

- `backend/tests/test_academic_setup_rules.py`
- `backend/tests/test_departments.py`
- `backend/tests/test_academic_permissions.py`
- `frontend/src/utils/permissions.test.js`

## Academic Structure UI Logic

### Admin Academic Structure Page

`frontend/src/pages/Admin/AdminAcademicStructurePage.jsx` is a navigation hub, not a working data tree.

It provides quick entry links to:

- faculties
- departments
- programs
- specializations
- batches
- semesters
- sections
- courses
- years
- branches

### Main Academic Structure Page

`frontend/src/pages/AcademicStructurePage.jsx` is the actual lazy drill-down hierarchy UI.

Implemented behavior:

- starts at faculties
- lazy-loads each next level only after expansion
- supports expand and collapse
- uses animated transitions
- supports in-tree search across already loaded nodes
- supports super-admin edit modal

Levels included in the tree:

- faculties
- departments
- programs
- specializations
- batches
- semesters
- sections

Levels not included in the tree:

- courses
- years
- branches

This confirms that the tree is built around the new canonical hierarchy, not the legacy one.

## Permission Model

### What The Backend Actually Enforces

Read operations for most academic entities allow:

- `admin`
- `teacher`

Write operations in academic setup now use entity-level permissions:

- `faculties.manage`
- `departments.manage`
- `programs.manage`
- `specializations.manage`
- `batches.manage`
- `semesters.manage`
- `sections.manage`
- `courses.manage`
- `years.manage`
- `branches.manage`

The older blanket `academic:manage` permission still exists for non-setup academic modules such as `students.py` and `subjects.py`.

Central academic setup permissions:

- `faculties.manage`
- `departments.manage`
- `courses.manage`
- `years.manage`
- `branches.manage`

Allowed admin types:

- `super_admin`
- `admin`
- `academic_admin`

Canonical lower-hierarchy permissions:

- `programs.manage`
- `specializations.manage`
- `batches.manage`
- `semesters.manage`
- `sections.manage`

Allowed admin types:

- `super_admin`
- `admin`
- `academic_admin`
- `department_admin`

### What The Frontend Shows

The frontend feature matrix in `frontend/src/config/featureAccess.js` exposes setup pages mainly to `admin`.

Important differences between UI and backend:

- UI may allow page access without exposing edit buttons
- backend may support update even when the page only exposes create and delete
- program duration editing is more granular than other setup entities

### Permission Inconsistencies

The permission key mismatch inside academic setup has now been normalized.

Remaining risk:

- the system still lacks row-level scope enforcement for `department_admin`
- entity-level permission grants are global unless a route also performs entity ownership checks

This means permission naming is now coherent, but administrative scope is still broad.

## Features Present In Code But Not Fully Used

### Backend Exists, UI Does Not Expose It

- course create, update, and archive exist in backend, but `CoursesPage.jsx` is read-only
- department update exists, but `DepartmentsPage.jsx` does not enable edit
- specialization update exists, but `SpecializationsPage.jsx` does not enable edit
- batch update exists, but `BatchesPage.jsx` does not enable edit
- semester update exists, but `SemestersPage.jsx` does not enable edit
- year update exists, but `YearsPage.jsx` does not enable edit
- branch update exists, but `BranchesPage.jsx` does not enable edit

### Backend Fields Exist, UI Uses Only Part Of Them

- departments support `university_name` and `university_code`, but the departments page does not expose them
- sections support `course_id` and `year_id`, but the section page primarily operates on the newer faculty-to-semester chain
- sections support `faculty_name` and `branch_name`, but naming and display are inconsistent across views

### Permission Policy Now Lives In Two Places

The route-level policy is now encoded in:

- `backend/app/core/permission_registry.py`
- `docs/ACADEMIC_PERMISSION_POLICY.md`

This is an improvement over the earlier state where the registry suggested granular permissions that the routes did not actually enforce.

### Governance Review Is Only Partially Operationalized In UI

Delete APIs for several entities support a `review_id`.

The shared `EntityManager` delete action can now send:

- `DELETE <endpoint>/<id>?review_id=<approved id>`
- `DELETE <endpoint>/<id>?review_id=<approved id>&review_metadata=<json>`

This now covers the academic setup pages that use `EntityManager`, such as departments, branches, and years.

The delete-governance experience is now partially centralized in `frontend/src/config/featureAccess.js`, which defines review prompt copy and optional metadata fields for governance-gated entities.

Remaining gaps:

- `CoursesPage.jsx` still has delete disabled
- `ClassesPage.jsx` is custom and does not yet expose a governance review id driven delete flow

### Legacy Academic Model Still Exists But Is Not Part Of The Main Tree

The following modules still exist and are functional:

- courses
- years
- branches

But they are not part of the canonical `AcademicStructurePage.jsx` drill-down tree.

This means they are alive in the system without being part of the main hierarchy narrative presented to users.

## Features Present But Only Partially Used

### Intentional UI Field Exposure Policy

The academic setup module now distinguishes between:

- operator-managed setup fields that should be visible and editable in CRUD forms
- system-managed fields that should remain hidden from standard setup forms
- legacy compatibility fields that remain in API contracts but are not part of the canonical setup UI

Operator-managed fields intentionally exposed in the setup UI:

- faculties: `name`, `code`, `university_name`, `university_code`
- departments: `name`, `code`, `faculty_id`, `university_name`, `university_code`
- programs: `name`, `code`, `department_id`, `duration_years`, `description`
- specializations: `name`, `code`, `program_id`, `description`
- batches: `name`, `code`, `program_id`, `specialization_id`, `start_year`, `end_year`
- semesters: `batch_id`, `semester_number`, `label`

System-managed fields intentionally hidden from normal CRUD forms:

- `is_active` when used as an archive state rather than a normal editable business field
- `deleted_at`
- `deleted_by`
- timestamps such as `created_at`

Legacy compatibility fields intentionally hidden from canonical setup forms:

- section `course_id`
- section `year_id`

Reason:

- the adopted canonical academic model is `Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`
- `course_id` and `year_id` still exist for compatibility with older academic and analytics flows, but they are not part of the canonical academic setup experience
- exposing them in the standard section setup form would reintroduce parallel hierarchy drift directly into the UI

### In-Tree Editing

The hierarchy page supports in-tree editing only for super admin.

This is implemented for:

- faculties
- departments
- programs
- specializations
- batches
- semesters
- sections

But:

- courses
- years
- branches

are not part of that tree, so they do not benefit from the same editing pattern.

### Search

The tree page search is intentionally scoped to already loaded nodes.

This is useful and clearly labeled in UI, but it is not a global academic structure search.

### Delete Semantics

The academic setup module now uses one canonical soft-delete contract:

- `is_active = false`
- `deleted_at`
- `deleted_by`

`is_deleted` is now treated as a legacy compatibility marker only.

Current academic behavior:

- academic setup delete routes write canonical metadata through a shared helper
- academic setup update routes clear delete markers when an entity is reactivated through `is_active = true`
- academic setup response models expose `deleted_at` and `deleted_by`
- admin recovery derives deletion state from `deleted_at` and unsets legacy `is_deleted` on restore
- migration tooling exists to normalize legacy academic setup records that still carry `is_deleted`

Important nuance:

- inactive records are not automatically equivalent to deleted records
- example: program duration synchronization can still set `is_active = false` on extra semesters without marking them deleted
- recovery semantics therefore use `deleted_at` as the authoritative delete marker

## Known Inconsistencies And Risks

### 1. Dual Academic Model

The repository currently maintains both:

- faculty -> department -> program -> specialization -> batch -> semester -> section
- course -> year -> section

This creates ambiguity around which model is authoritative for:

- student grouping
- section generation
- subject allocation
- enrollment
- timetable integration

### 2. Missing Row-Level Scope

Permission names are now aligned, but `department_admin` still passes permission checks globally for lower-hierarchy entities.

This means the next authorization improvement is not renaming permissions again. It is adding row-level department or faculty scope enforcement.

### 3. UI/Backend Capability Mismatch

Several entities are update-capable in backend but not editable in UI.

This creates a false appearance that those modules are simpler than they actually are.

### 4. Governance Flow Not Fully Wired

Review-gated delete APIs are in place, and the shared CRUD UI now integrates review ticket prompting and retry.

Remaining issue:

- custom delete UIs still need the same governance review prompt flow if they do not use `EntityManager`

### 5. Denormalized Branch Model

Branches depend on `department_code`, while most of the newer academic model uses object ids.

That is a persistent architectural inconsistency.

## What Is Already Strong

The following parts are already solid and should be preserved as the foundation:

- program duration rule engine
- auto-derived total semester count
- batch semester auto-generation
- section cross-entity validation
- lazy academic structure drill-down
- feature-gated admin access
- governance hooks for delete workflows

## Adopted Canonical Operating Model

The platform decision is now:

- `Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section` is the canonical academic structure
- `Course`, `Year`, and `Branch` are treated as legacy compatibility modules

The current implementation now marks that distinction in both UI and API metadata.

## Recommended Next Refactor Order

### Phase 1

Normalize the academic authority model.

- decide whether `course/year/branch` remain first-class
- if not, mark them legacy in UI and documentation
- if yes, define exact relationships to program/batch/semester/section

### Phase 2

Add row-level administrative scope.

- constrain `department_admin` writes to entities inside the admin's allowed department scope
- keep the entity-level permission keys, but pair them with ownership validation

### Phase 3

Close the UI/backend gap.

- enable edit where backend already supports update
- expose missing fields intentionally, not accidentally
- wire governance review into delete flows

### Phase 4

Unify academic structure experience.

- either extend the tree to include legacy nodes
- or remove those nodes from primary setup navigation

### Phase 5

Extend the same canonical soft-delete contract from academic setup into the remaining non-academic modules that still persist `is_deleted`.

## Practical Feature Map

### Fully Operational End-To-End

- faculties
- programs
- academic structure drill-down
- batch creation with downstream semester generation
- program duration validation and semester derivation

### Operational But Incompletely Surfaced

- departments
- specializations
- semesters
- years
- branches
- courses
- sections with legacy course and year support

### Present As Infrastructure More Than Product

- governance delete review hooks
- granular academic permission keys
- data feed and seeding scripts

## Final Assessment

The academic module is not empty or loosely defined. It already contains real business logic and a meaningful operational hierarchy.

The strongest current design line in the codebase is:

- program duration drives semester count
- batch creation inherits academic duration
- sections sit at the validated bottom of the hierarchy

The main architectural problem is not missing logic. The main problem is that the codebase contains:

- a newer canonical model
- older legacy structures
- UI exposure that does not fully match backend capability
- permission and governance features that are only partially wired

If this module is treated as a product area rather than a set of CRUD pages, the next step is not inventing new logic first. The next step is consolidating and operationalizing the logic that already exists.
