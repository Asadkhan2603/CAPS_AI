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

## Canonical Academic Model In Code

The primary hierarchy implemented in the current codebase is:

`Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section`

The repository also still contains a secondary legacy or parallel academic chain:

`Course -> Year -> Section`

There is also a side structure:

`Department -> Branch`

This means the codebase currently supports two partially overlapping academic models:

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
- archival metadata on some modules such as `is_deleted`, `deleted_at`, `deleted_by`
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

Relevant setup routes:

- `/faculties`
- `/departments`
- `/programs`
- `/specializations`
- `/batches`
- `/semesters`
- `/sections`
- `/classes`
- `/courses`
- `/years`
- `/branches`

Important note:

- `/sections` is the canonical route for sections
- `/classes` is still mounted as a legacy compatibility alias

The code comment in `backend/app/api/v1/router.py` explicitly marks `/classes` as deprecated for new clients.

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
- `AcademicStructurePage.jsx`
  - renders the lazy-loaded drill-down tree from faculty to section

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
- validates `faculty_id` if supplied
- enforces unique department code
- stores `university_name` and `university_code`
- on update, propagates department changes into `branches`
- on delete, archives related branches by department code
- delete can require governance review via `review_id`

Frontend:

- page: `frontend/src/pages/DepartmentsPage.jsx`
- create enabled
- delete enabled
- edit not enabled in UI
- faculty relation shown in table
- university fields are not surfaced in the create form

Implemented logic:

- department belongs to faculty when faculty is provided
- branch records denormalize department name and code

Not fully used:

- backend update exists but UI does not expose edit
- backend university fields exist but UI form does not expose them
- governance review support exists but normal delete flow does not supply `review_id`

Known issue:

- `backend/app/api/v1/endpoints/departments.py` contains unreachable validation code after the final `return` in `delete_department`

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
- `academic_admin`
- `department_admin`

Notable inconsistency:

- the error message says "Only super admin or department admin can configure course duration."
- actual allowed set also includes `academic_admin`

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
- the generic frontend delete buttons do not consistently pass `review_id`

So the capability exists, but the normal UI flow does not fully operationalize it.

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

Write operations are inconsistent across modules:

- most setup modules use `require_permission("academic:manage")`
- `academic:manage` only allows `super_admin`
- programs create and update do not use `academic:manage`
- programs instead use `require_roles(["admin"])` plus a custom admin type check allowing:
  - `super_admin`
  - `academic_admin`
  - `department_admin`

### What The Frontend Shows

The frontend feature matrix in `frontend/src/config/featureAccess.js` exposes setup pages mainly to `admin`.

Important differences between UI and backend:

- UI may allow page access without exposing edit buttons
- backend may support update even when the page only exposes create and delete
- program duration editing is more granular than other setup entities

### Permission Inconsistencies

The current permission model is not fully normalized.

Examples:

- `courses.manage`, `departments.manage`, and `sections.manage` exist in the permission registry
- most academic endpoints do not use those granular permission keys
- they use `academic:manage` instead
- `academic:manage` is stricter than some module-specific policy implied elsewhere

This means the permission registry is more detailed than the actual route-level implementation.

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

### Permission Keys Exist But Routes Do Not Use Them

- `courses.manage`
- `departments.manage`
- `sections.manage`

These keys are defined but not consistently wired into the academic route handlers.

### Governance Review Exists But UI Does Not Operationalize It

Delete APIs for several entities support a `review_id`.

The shared `EntityManager` delete action currently does:

- `DELETE <endpoint>/<id>`

It does not include:

- `review_id`

So if governance review becomes mandatory, standard delete buttons will not be sufficient.

### Legacy Academic Model Still Exists But Is Not Part Of The Main Tree

The following modules still exist and are functional:

- courses
- years
- branches

But they are not part of the canonical `AcademicStructurePage.jsx` drill-down tree.

This means they are alive in the system without being part of the main hierarchy narrative presented to users.

## Features Present But Only Partially Used

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

Many modules use soft delete, but archival metadata is not fully uniform across all entities.

Some routes set:

- `is_active`
- `is_deleted`
- `deleted_at`
- `deleted_by`

Others only set:

- `is_active`
- `deleted_at`

This is not a blocker, but it shows the academic setup stack was built incrementally rather than as one normalized framework.

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

### 2. Permission Drift

The permission registry suggests granular entity permissions, but most academic routes still collapse writes into `academic:manage`.

Programs are handled differently again.

This makes authorization harder to reason about and harder to audit.

### 3. UI/Backend Capability Mismatch

Several entities are update-capable in backend but not editable in UI.

This creates a false appearance that those modules are simpler than they actually are.

### 4. Governance Flow Not Fully Wired

Review-gated delete APIs are in place, but the default CRUD UI does not integrate review ticket selection or approval flow.

### 5. Denormalized Branch Model

Branches depend on `department_code`, while most of the newer academic model uses object ids.

That is a persistent architectural inconsistency.

### 6. Department Delete Handler Contains Dead Code

`backend/app/api/v1/endpoints/departments.py` contains code after the function has already returned.

This is a maintainability problem and may hide intended validation behavior.

## What Is Already Strong

The following parts are already solid and should be preserved as the foundation:

- program duration rule engine
- auto-derived total semester count
- batch semester auto-generation
- section cross-entity validation
- lazy academic structure drill-down
- feature-gated admin access
- governance hooks for delete workflows

## Recommended Canonical Operating Model

The cleanest interpretation of the existing codebase is:

- `Faculty -> Department -> Program -> Specialization -> Batch -> Semester -> Section` should be the canonical academic structure
- `Course`, `Year`, and `Branch` should either be:
  - explicitly marked as legacy compatibility modules, or
  - re-integrated into the canonical hierarchy with a clear business role

Right now they are in-between, which is why the overall structure feels inconsistent.

## Recommended Next Refactor Order

### Phase 1

Normalize the academic authority model.

- decide whether `course/year/branch` remain first-class
- if not, mark them legacy in UI and documentation
- if yes, define exact relationships to program/batch/semester/section

### Phase 2

Align permissions.

- replace blanket `academic:manage` usage with entity-level permissions where intended
- keep programs and other academic entities under one coherent policy

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

Standardize soft-delete metadata and auditing across all academic entities.

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
