from app.models.admin_action_reviews import admin_action_review_public
from app.models.audit_logs import audit_log_public
from app.models.departments import department_public
from app.models.faculties import faculty_public
from app.models.programs import program_public
from app.models.review_tickets import review_ticket_public
from app.models.students import student_public
from app.services.academic_batching import build_batch_document, build_semester_document
from app.services.public_ids import build_public_id, persist_public_id_update


def test_build_public_id_for_master_entities_prefers_short_codes() -> None:
    assert build_public_id("faculty", {"faculty_code": "ENG"}) == "FAC-ENG"
    assert build_public_id("department", {"department_code": "CSE"}) == "DPT-CSE"
    assert build_public_id("program", {"program_code": "BTECH-CSE"}) == "PRG-BTECH-CSE"
    assert build_public_id("specialization", {"specialization_code": "AI"}) == "SPC-AI"


def test_master_serializers_include_public_id_and_display_label() -> None:
    faculty = faculty_public(
        {
            "_id": "fac1",
            "faculty_id": "FAC-ENG",
            "faculty_code": "ENG",
            "faculty_name": "Faculty of Engineering",
        }
    )
    department = department_public(
        {
            "_id": "dep1",
            "department_id": "DEP-ENG-CSE",
            "department_code": "CSE",
            "department_name": "Department of Computer Science Engineering",
        }
    )
    program = program_public(
        {
            "_id": "prg1",
            "program_id": "PRG-ENG-CSE-BTECH-CSE",
            "program_code": "BTECH-CSE",
            "program_name": "Bachelor of Technology in Computer Science Engineering",
            "duration_years": 4,
            "total_semesters": 8,
            "department_id": "dep1",
        }
    )

    assert faculty["public_id"] == "FAC-ENG"
    assert faculty["display_label"] == "Faculty of Engineering (FAC-ENG)"
    assert department["public_id"] == "DPT-CSE"
    assert department["display_label"].endswith("(DPT-CSE)")
    assert program["public_id"] == "PRG-BTECH-CSE"
    assert program["display_label"].endswith("(PRG-BTECH-CSE)")


def test_student_serializer_uses_roll_number_for_human_readable_id() -> None:
    payload = student_public(
        {
            "_id": "507f1f77bcf86cd799439011",
            "full_name": "Anita Sharma",
            "roll_number": "2024CSE0041",
            "email": "anita@example.com",
        }
    )

    assert payload["public_id"] == "STU-2024CSE0041"
    assert payload["display_label"] == "Anita Sharma (STU-2024CSE0041)"


def test_persist_public_id_update_recomputes_when_identity_fields_change() -> None:
    current = {
        "program_code": "MBA",
        "public_id": "PRG-MBA",
    }
    update_data = {"program_code": "BBA"}

    persist_public_id_update(current, update_data, kind="program")

    assert update_data["public_id"] == "PRG-BBA"


def test_batch_and_semester_builders_stamp_public_ids() -> None:
    batch = build_batch_document(
        program_context={
            "faculty_id": "fac1",
            "department_id": "dep1",
            "program_id": "prg1",
            "university_name": "Example University",
            "university_code": "EXU",
        },
        specialization_id=None,
        name="Batch 2024-2028",
        code="B24-28",
        start_year=2024,
        end_year=2028,
        now=None,
        auto_generated=False,
    )
    semester = build_semester_document(
        batch={
            **batch,
            "id": "batch1",
        },
        semester_number=1,
        now=None,
    )

    assert batch["public_id"] == "BAT-2024"
    assert semester["public_id"] == "SEM-01"


def test_audit_and_review_serializers_emit_readable_labels() -> None:
    audit_payload = audit_log_public(
        {
            "_id": "507f1f77bcf86cd799439012",
            "actor_user_id": "507f1f77bcf86cd799439013",
            "action": "programs.delete",
            "entity_type": "program",
            "entity_id": "507f1f77bcf86cd799439014",
        }
    )
    review_payload = admin_action_review_public(
        {
            "_id": "507f1f77bcf86cd799439015",
            "review_type": "destructive",
            "action": "programs.delete",
            "entity_type": "program",
            "entity_id": "507f1f77bcf86cd799439014",
            "status": "pending",
            "requested_by": "507f1f77bcf86cd799439013",
        }
    )
    ticket_payload = review_ticket_public(
        {
            "_id": "507f1f77bcf86cd799439016",
            "evaluation_id": "507f1f77bcf86cd799439017",
            "requested_by_user_id": "507f1f77bcf86cd799439013",
            "reason": "Re-evaluate",
            "status": "pending",
        }
    )

    assert audit_payload["public_id"] == "ADT-9012"
    assert audit_payload["actor_label"] == "User 9013"
    assert audit_payload["entity_label"] == "Program 9014"
    assert review_payload["public_id"] == "APR-9015"
    assert review_payload["requested_by_label"] == "User 9013"
    assert review_payload["entity_label"] == "Program 9014"
    assert ticket_payload["public_id"] == "RVT-9016"
    assert ticket_payload["requested_by_label"] == "User 9013"
    assert ticket_payload["evaluation_label"] == "Evaluation 9017"
