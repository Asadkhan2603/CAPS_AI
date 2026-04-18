import asyncio

from bson import ObjectId

from app.api.v1.endpoints import attendance_records as attendance_endpoint
from backend.tests.test_auth import FakeDB


def test_attendance_percent_map_for_students_batches_section_and_group_slots(monkeypatch) -> None:
    fake_db = FakeDB()
    monkeypatch.setattr(attendance_endpoint, "db", fake_db)

    student_group_a_id = ObjectId()
    student_group_b_id = ObjectId()
    default_offering_id = ObjectId()
    group_a_offering_id = ObjectId()
    group_b_offering_id = ObjectId()
    default_slot_id = ObjectId()
    group_a_slot_id = ObjectId()
    group_b_slot_id = ObjectId()

    fake_db.course_offerings.items.extend(
        [
            {"_id": default_offering_id, "section_id": "section-1", "group_id": None, "is_active": True},
            {"_id": group_a_offering_id, "section_id": "section-1", "group_id": "group-a", "is_active": True},
            {"_id": group_b_offering_id, "section_id": "section-1", "group_id": "group-b", "is_active": True},
        ]
    )
    fake_db.class_slots.items.extend(
        [
            {"_id": default_slot_id, "course_offering_id": str(default_offering_id), "is_active": True},
            {"_id": group_a_slot_id, "course_offering_id": str(group_a_offering_id), "is_active": True},
            {"_id": group_b_slot_id, "course_offering_id": str(group_b_offering_id), "is_active": True},
        ]
    )

    students = [
        {"_id": student_group_a_id, "full_name": "Group A Student", "group_id": "group-a"},
        {"_id": student_group_b_id, "full_name": "Group B Student", "group_id": "group-b"},
    ]
    fake_db.attendance_records.items.extend(
        [
            {"_id": ObjectId(), "class_slot_id": str(default_slot_id), "student_id": str(student_group_a_id), "status": "present"},
            {"_id": ObjectId(), "class_slot_id": str(group_a_slot_id), "student_id": str(student_group_a_id), "status": "absent"},
            {"_id": ObjectId(), "class_slot_id": str(group_b_slot_id), "student_id": str(student_group_a_id), "status": "present"},
            {"_id": ObjectId(), "class_slot_id": str(default_slot_id), "student_id": str(student_group_b_id), "status": "late"},
            {"_id": ObjectId(), "class_slot_id": str(group_a_slot_id), "student_id": str(student_group_b_id), "status": "absent"},
            {"_id": ObjectId(), "class_slot_id": str(group_b_slot_id), "student_id": str(student_group_b_id), "status": "present"},
        ]
    )

    percent_map = asyncio.run(
        attendance_endpoint._attendance_percent_map_for_students(
            students=students,
            section_id="section-1",
        )
    )

    assert percent_map[str(student_group_a_id)] == 50.0
    assert percent_map[str(student_group_b_id)] == 100.0
