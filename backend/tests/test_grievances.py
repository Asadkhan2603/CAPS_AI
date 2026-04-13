import asyncio

from bson import ObjectId

from app.models.grievances import grievance_public
from app.services import grievances as grievance_service


def test_first_available_stage_skips_missing_recipients(monkeypatch) -> None:
    async def _fake_stage_recipients(_grievance, stage: str, *, database=None):
        if stage == "dean":
            return [{"_id": ObjectId(), "full_name": "Dean Reviewer"}]
        return []

    monkeypatch.setattr(grievance_service, "stage_recipients", _fake_stage_recipients)

    stage, recipients, skipped = asyncio.run(grievance_service.first_available_stage({}))

    assert stage == "dean"
    assert len(recipients) == 1
    assert skipped == ["coordinator", "hod"]


def test_grievance_public_hides_internal_entries_for_students() -> None:
    grievance_id = ObjectId()
    document = {
        "_id": grievance_id,
        "title": "Library issue",
        "category": "facility",
        "description": "Need a quieter reading room.",
        "student_user_id": "student-1",
        "current_stage": "coordinator",
        "status": "open",
        "timeline": [
            {
                "entry_id": "public-1",
                "kind": "public_comment",
                "visibility": "public",
                "message": "Student submitted the grievance.",
            },
            {
                "entry_id": "internal-1",
                "kind": "internal_note",
                "visibility": "internal",
                "message": "Need to check facilities budget.",
            },
        ],
    }

    student_payload = grievance_public(document, include_internal=False)
    staff_payload = grievance_public(document, include_internal=True)

    assert [entry["entry_id"] for entry in student_payload["timeline"]] == ["public-1"]
    assert [entry["entry_id"] for entry in staff_payload["timeline"]] == ["public-1", "internal-1"]


def test_grievance_inbox_query_limits_coordinator_view_to_active_stage(monkeypatch) -> None:
    async def _fake_teacher_scope_section_ids(_current_user, *, database=None):
        return {"section-1", "section-2"}

    monkeypatch.setattr(grievance_service, "teacher_scope_section_ids", _fake_teacher_scope_section_ids)

    query = asyncio.run(
        grievance_service.grievance_inbox_query(
            {"_id": "teacher-1", "role": "teacher", "extended_roles": ["class_coordinator"]},
            view="coordinator",
        )
    )

    assert query == {
        "section_id": {"$in": ["section-1", "section-2"]},
        "current_stage": "coordinator",
        "status": {"$in": sorted(grievance_service.UNRESOLVED_GRIEVANCE_STATUSES)},
    }
