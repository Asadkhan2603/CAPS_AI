# University Academic Structure

## Source Of Truth

CAPS AI now treats `exports/Master_copy.xlsx` as the source of truth for the core academic master hierarchy only:

- University
- Faculty
- Department
- Program
- Specialization

Operational entities such as batches, semesters, sections, groups, course offerings, class slots, staff assignments, and student academic mappings continue to be created and managed inside CAPS AI.

## Authoritative Hierarchy

CAPS AI uses one hybrid academic model across backend validation, frontend setup flows, import scripts, and documentation.

```text
University
|-- Faculty
|   `-- Department
|       `-- Program
|           |-- Batch
|           |   `-- Semester
|           |       `-- Section
|           |           `-- Group
|           `-- Specialization
|               `-- Batch
|                   `-- Semester
|                       `-- Section
|                           `-- Group
```

## Rules

- Specialization is optional.
- A program may create direct batches when no specialization is used.
- A specialization-specific batch must belong to that specialization.
- If a batch is program-level, its semesters, sections, groups, and course delivery records must remain program-level.
- If a batch is specialization-bound, all descendants must stay inside the same specialization branch.
- Course delivery follows the same structural branch:
  `Batch -> Semester -> Section -> optional Group`

## Program Duration Rules

| Duration | Total Semesters | Example Programs |
| --- | --- | --- |
| 1 year | 2 semesters | LLM |
| 2 years | 4 semesters | MBA, MCA, M.Tech, M.Sc, MA, M.Pharm |
| 3 years | 6 semesters | BCA, BBA, B.Com, BJMC, B.Sc, LLB |
| 4 years | 8 semesters | B.Tech, B.Pharm, B.Sc Agriculture |
| 5 years | 10 semesters | BA LLB (Hons), BBA LLB (Hons), B.Tech + M.Tech Integrated |

## Batch Rules

- `start_year` is the admission year.
- `end_year` is the pass-out year.
- `end_year = start_year + duration_years`
- `total_semesters = duration_years * 2`
- Example:
  - August 2022 intake finishing in May 2026 is still a `2022-2026` batch.
  - A 4-year batch has 8 semesters.

## Real Academic Hierarchy

```text
University
|-- Faculty of Engineering
|   |-- Department of Computer Science Engineering
|   |   |-- B.Tech Computer Science Engineering (4 Years, 8 Semesters)
|   |   |   |-- Artificial Intelligence (Specialization)
|   |   |   |-- Data Science (Specialization)
|   |   |   `-- Computer Science & Business Systems (Specialization)
|   |   |-- B.Tech + M.Tech Integrated (CSE) (5 Years, 10 Semesters)
|   |   |-- M.Tech Computer Science Engineering (2 Years, 4 Semesters)
|   |   |-- BCA (3 Years, 6 Semesters)
|   |   `-- MCA (2 Years, 4 Semesters)
|   |
|   |-- Department of Information Technology
|   |   |-- B.Tech Information Technology (4 Years, 8 Semesters)
|   |   `-- M.Tech Information Technology (2 Years, 4 Semesters)
|   |
|   |-- Department of Robotics & Automation
|   |   `-- B.Tech Robotics & Automation (4 Years, 8 Semesters)
|   |
|   |-- Department of Automobile Engineering
|   |   `-- B.Tech Automobile Engineering (4 Years, 8 Semesters)
|   |       `-- Electric Vehicle (Specialization)
|   |
|   |-- Department of Civil Engineering
|   |   |-- B.Tech Civil Engineering (4 Years, 8 Semesters)
|   |   |   |-- Construction Technology & Management (Specialization)
|   |   |   |-- Structural Engineering (Specialization)
|   |   |   |-- Environmental Engineering (Specialization)
|   |   |   `-- Artificial Intelligence (Specialization)
|   |   `-- M.Tech Civil Engineering (2 Years, 4 Semesters)
|   |
|   |-- Department of Electronics & Communication Engineering
|   |   |-- B.Tech Electronics & Communication (4 Years, 8 Semesters)
|   |   |   |-- Communication Engineering (Specialization)
|   |   |   |-- Computer Technology (Specialization)
|   |   |   |-- Microwave Engineering (Specialization)
|   |   |   |-- VLSI (Specialization)
|   |   |   `-- Artificial Intelligence (Specialization)
|   |   `-- M.Tech Electronics & Communication (2 Years, 4 Semesters)
|   |
|   |-- Department of Electrical Engineering
|   |   |-- B.Tech Electrical Engineering (4 Years, 8 Semesters)
|   |   |   |-- Power Electronics (Specialization)
|   |   |   |-- Power Systems (Specialization)
|   |   |   `-- Information Technology (Specialization)
|   |   `-- M.Tech Electrical Engineering (2 Years, 4 Semesters)
|   |
|   |-- Department of Mechanical Engineering
|   |   |-- B.Tech Mechanical Engineering (4 Years, 8 Semesters)
|   |   |   |-- Mechatronics (Specialization)
|   |   |   |-- CAD/CAM/CAE (Specialization)
|   |   |   |-- Industrial & Production Engineering (Specialization)
|   |   |   |-- Energy Technology (Specialization)
|   |   |   `-- Artificial Intelligence (Specialization)
|   |   `-- M.Tech Mechanical Engineering (2 Years, 4 Semesters)
|   |
|   `-- Department of Nanotechnology
|       `-- M.Tech Nanotechnology (2 Years, 4 Semesters)
|
|-- Faculty of Arts, Humanities & Social Sciences
|   |-- Department of Journalism & Mass Communication
|   |   `-- BJMC (3 Years, 6 Semesters)
|   `-- Department of English
|       `-- MA English (2 Years, 4 Semesters)
|
|-- Faculty of Pharmacy
|   `-- Department of Pharmacy
|       |-- B.Pharm (4 Years, 8 Semesters)
|       `-- M.Pharm Pharmaceutics (2 Years, 4 Semesters)
|
|-- Faculty of Management
|   `-- Department of Business Administration
|       |-- BBA (3 Years, 6 Semesters)
|       |   |-- Finance (Specialization)
|       |   |-- Foreign Trade (Specialization)
|       |   |-- Human Resource (Specialization)
|       |   |-- Marketing Management (Specialization)
|       |   `-- Digital Marketing (Specialization)
|       |
|       |-- BBA Business Analytics (3 Years, 6 Semesters)
|       |
|       |-- MBA (2 Years, 4 Semesters)
|       |   |-- Finance (Specialization)
|       |   |-- Foreign Trade (Specialization)
|       |   |-- Human Resource (Specialization)
|       |   |-- Marketing Management (Specialization)
|       |   `-- Logistics & Supply Chain Management (Specialization)
|       |
|       |-- MBA Global (2 Years, 4 Semesters)
|       `-- MBA Business Analytics (2 Years, 4 Semesters)
|
|-- Faculty of Law
|   `-- Department of Legal Studies
|       |-- BA LLB (Hons) (5 Years, 10 Semesters)
|       |-- BBA LLB (Hons) (5 Years, 10 Semesters)
|       |-- LLB (Hons) (3 Years, 6 Semesters)
|       `-- LLM (1 Year, 2 Semesters)
|
|-- Faculty of Commerce
|   `-- Department of Commerce
|       |-- B.Com (3 Years, 6 Semesters)
|       |   |-- Accounting & Taxation (Specialization)
|       |   |-- Banking & Finance (Specialization)
|       |   `-- Computer Applications (Specialization)
|       `-- B.Com Global Finance (3 Years, 6 Semesters)
|
|-- Faculty of Science
|   |-- Department of Agriculture
|   |   |-- B.Sc Agriculture (4 Years, 8 Semesters)
|   |   `-- M.Sc Agriculture Agronomy (2 Years, 4 Semesters)
|   |
|   |-- Department of Forensic Science
|   |   |-- B.Sc Forensic Science (3 Years, 6 Semesters)
|   |   `-- M.Sc Forensic Science (2 Years, 4 Semesters)
|   |
|   |-- Department of Biotechnology
|   |   `-- B.Sc Biotechnology (3 Years, 6 Semesters)
|   |
|   |-- Department of Computer Science
|   |   `-- B.Sc Computer Science (3 Years, 6 Semesters)
|   |
|   |-- Department of Physics
|   |   `-- B.Sc Physics (3 Years, 6 Semesters)
|   |
|   |-- Department of Chemistry
|   |   |-- B.Sc Chemistry (3 Years, 6 Semesters)
|   |   `-- M.Sc Chemistry (Research) (2 Years, 4 Semesters)
|   |
|   `-- Department of Mathematics
|       `-- M.Sc Mathematics (2 Years, 4 Semesters)
|
`-- Faculty of Allied Health Sciences
    `-- Department of Health Sciences
        `-- B.Sc (3 Years, 6 Semesters)
            |-- Anaesthesia & Operation Theatre Technology (Specialization)
            |-- Medical Laboratory Technology (Specialization)
            |-- Cardiovascular Technology (Specialization)
            `-- Respiratory Technology (Specialization)
```
