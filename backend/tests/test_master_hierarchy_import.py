from backend.scripts import import_master_hierarchy as import_script
from backend.scripts import audit_academic_integrity as audit_script
import json


def test_validate_workbook_payload_reconciles_program_id_mismatch() -> None:
    payload = import_script.WorkbookPayload(
        universities=[{"university_id": "UM", "university_name": "UM UNIVERSITY"}],
        faculties=[{"university_id": "UM", "faculty_id": "FAC-SCI", "faculty_code": "SCI", "faculty_name": "Faculty of Science"}],
        departments=[
            {
                "faculty_id": "FAC-SCI",
                "faculty_code": "SCI",
                "department_id": "DEP-SCI-CSE",
                "department_code": "CSE",
                "department_name": "Department of Computer Science",
            }
        ],
        programs=[
            {
                "department_id": "DEP-SCI-CSE",
                "department_name": "Department of Computer Science",
                "program_id": "PRG-ENG-CSE-BSC-CS",
                "program_code": "BSC-CS",
                "program_name": "Bachelor of Science in Computer Science",
                "duration_years": 3,
                "total_semesters": 6,
                "degree_type": "Degree",
            }
        ],
        specializations=[],
        rough_cross_check=[
            {
                "faculty_id": "FAC-SCI",
                "faculty_code": "SCI",
                "department_id": "DEP-SCI-CSE",
                "department_code": "CSE",
                "program_id": "PRG-ENG-CSE-BSC-CS",
                "program_code": "BSC-CS",
                "program_name": "Bachelor of Science in Computer Science",
            }
        ],
        generic_patterns={
            "FAC-[FAC_CODE]",
            "DEP-[FAC_CODE]-[DEPT_CODE]",
            "PRG-[FAC_CODE]-[DEPT_CODE]-[PROGRAM_CODE]",
            "SPC-[FAC_CODE]-[DEPT_CODE]-[PROGRAM_CODE]-[SPEC_CODE]",
        },
    )

    report = import_script.validate_workbook_payload(payload)

    assert report["sheet_counts"]["programs"] == 1
    assert payload.programs[0]["program_id"] == "PRG-SCI-CSE-BSC-CS"
    assert report["reconciliations"] == [
        {
            "entity": "program",
            "name": "Bachelor of Science in Computer Science",
            "from": "PRG-ENG-CSE-BSC-CS",
            "to": "PRG-SCI-CSE-BSC-CS",
        }
    ]


def test_validate_workbook_payload_allows_scoped_code_reuse() -> None:
    payload = import_script.WorkbookPayload(
        universities=[{"university_id": "UM", "university_name": "UM UNIVERSITY"}],
        faculties=[
            {"university_id": "UM", "faculty_id": "FAC-ENG", "faculty_code": "ENG", "faculty_name": "Faculty of Engineering"},
            {"university_id": "UM", "faculty_id": "FAC-SCI", "faculty_code": "SCI", "faculty_name": "Faculty of Science"},
        ],
        departments=[
            {
                "faculty_id": "FAC-ENG",
                "faculty_code": "ENG",
                "department_id": "DEP-ENG-CSE",
                "department_code": "CSE",
                "department_name": "Department of Computer Science Engineering",
            },
            {
                "faculty_id": "FAC-SCI",
                "faculty_code": "SCI",
                "department_id": "DEP-SCI-CSE",
                "department_code": "CSE",
                "department_name": "Department of Computer Science",
            },
        ],
        programs=[
            {
                "department_id": "DEP-ENG-CSE",
                "department_name": "Department of Computer Science Engineering",
                "program_id": "PRG-ENG-CSE-BTECH-CSE",
                "program_code": "BTECH-CSE",
                "program_name": "Bachelor of Technology in Computer Science Engineering",
                "duration_years": 4,
                "total_semesters": 8,
                "degree_type": "Degree",
            },
            {
                "department_id": "DEP-SCI-CSE",
                "department_name": "Department of Computer Science",
                "program_id": "PRG-SCI-CSE-BSC-CS",
                "program_code": "BSC-CS",
                "program_name": "Bachelor of Science in Computer Science",
                "duration_years": 3,
                "total_semesters": 6,
                "degree_type": "Degree",
            },
        ],
        specializations=[
            {
                "faculty_id": "FAC-ENG",
                "faculty_code": "ENG",
                "department_id": "DEP-ENG-CSE",
                "department_code": "CSE",
                "department_name": "Department of Computer Science Engineering",
                "program_code": "BTECH-CSE",
                "program_name": "Bachelor of Technology in Computer Science Engineering",
                "specialization_id": "SPC-ENG-CSE-BTECH-CSE-AI",
                "specialization_code": "AI",
                "specialization_name": "Artificial Intelligence",
            },
            {
                "faculty_id": "FAC-SCI",
                "faculty_code": "SCI",
                "department_id": "DEP-SCI-CSE",
                "department_code": "CSE",
                "department_name": "Department of Computer Science",
                "program_code": "BSC-CS",
                "program_name": "Bachelor of Science in Computer Science",
                "specialization_id": "SPC-SCI-CSE-BSC-CS-AI",
                "specialization_code": "AI",
                "specialization_name": "Artificial Intelligence",
            },
        ],
        rough_cross_check=[
            {
                "faculty_id": "FAC-ENG",
                "faculty_code": "ENG",
                "department_id": "DEP-ENG-CSE",
                "department_code": "CSE",
                "program_id": "PRG-ENG-CSE-BTECH-CSE",
                "program_code": "BTECH-CSE",
                "program_name": "Bachelor of Technology in Computer Science Engineering",
            },
            {
                "faculty_id": "FAC-SCI",
                "faculty_code": "SCI",
                "department_id": "DEP-SCI-CSE",
                "department_code": "CSE",
                "program_id": "PRG-SCI-CSE-BSC-CS",
                "program_code": "BSC-CS",
                "program_name": "Bachelor of Science in Computer Science",
            },
        ],
        generic_patterns={
            "FAC-[FAC_CODE]",
            "DEP-[FAC_CODE]-[DEPT_CODE]",
            "PRG-[FAC_CODE]-[DEPT_CODE]-[PROGRAM_CODE]",
            "SPC-[FAC_CODE]-[DEPT_CODE]-[PROGRAM_CODE]-[SPEC_CODE]",
        },
    )

    report = import_script.validate_workbook_payload(payload)

    assert report["reconciliations"] == []


def test_build_master_change_plan_detects_add_update_and_remove() -> None:
    payload = import_script.WorkbookPayload(
        universities=[{"university_id": "UM", "university_name": "UM University"}],
        faculties=[{"university_id": "UM", "faculty_id": "FAC-ENG", "faculty_code": "ENG", "faculty_name": "Faculty of Engineering"}],
        departments=[],
        programs=[],
        specializations=[],
        rough_cross_check=[],
        generic_patterns=set(),
    )
    current_state = {
        "universities": [
            {"_id": "1", "university_id": "OLD", "university_name": "Old University"},
            {"_id": "2", "university_id": "UM", "university_name": "Legacy Name"},
        ],
        "faculties": [],
        "departments": [],
        "programs": [],
        "specializations": [],
    }

    change_plan = import_script.build_master_change_plan(current_state=current_state, payload=payload)

    assert change_plan["universities"]["added"]["count"] == 0
    assert change_plan["universities"]["updated"]["count"] == 1
    assert change_plan["universities"]["removed"]["count"] == 1
    assert change_plan["universities"]["updated"]["sample_ids"] == ["UM"]
    assert change_plan["universities"]["removed"]["sample_ids"] == ["OLD"]
    assert change_plan["faculties"]["added"]["sample_ids"] == ["FAC-ENG"]


def test_write_master_backup_exports_json(tmp_path) -> None:
    backup_dir = import_script.write_master_backup(
        current_state={
            "universities": [{"_id": "1", "university_id": "UM", "university_name": "UM University"}],
            "faculties": [],
            "departments": [],
            "programs": [],
            "specializations": [],
        },
        backup_root=tmp_path,
    )

    exported = json.loads((backup_dir / "universities.json").read_text(encoding="utf-8"))
    assert exported == [{"_id": "1", "university_id": "UM", "university_name": "UM University"}]


def test_format_downstream_blockers_is_human_readable() -> None:
    message = import_script.format_downstream_blockers(
        [
            {
                "master_collection": "programs",
                "referenced_by_collection": "batches",
                "field": "program_id",
                "count": 3,
                "sample": [{"_id": "a1", "program_id": "p1"}],
            }
        ]
    )

    assert "Downstream blockers detected" in message
    assert "programs is still referenced by 3 records in batches.program_id" in message
    assert "sample: _id=a1, program_id=p1" in message


def test_change_plan_has_mutations_detects_clean_and_dirty_states() -> None:
    clean_plan = {
        "universities": {
            "added": {"count": 0},
            "updated": {"count": 0},
            "removed": {"count": 0},
        }
    }
    dirty_plan = {
        "universities": {
            "added": {"count": 0},
            "updated": {"count": 1},
            "removed": {"count": 0},
        }
    }

    assert import_script.change_plan_has_mutations(clean_plan) is False
    assert import_script.change_plan_has_mutations(dirty_plan) is True


def test_audit_summary_helpers_count_findings() -> None:
    findings = {
        "program_duration_findings": [{"program_id": "p1"}],
        "semester_bound_findings": [],
        "orphaned_section_findings": [{"section_id": "s1"}, {"section_id": "s2"}],
    }

    summary = audit_script.summarize_findings(findings)

    assert summary["program_duration_findings"] == 1
    assert summary["orphaned_section_findings"] == 2
    assert audit_script.total_findings(summary) == 3
