from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.mongo import parse_object_id
from app.core.schema_versions import SEMESTER_RESULT_SCHEMA_VERSION
from app.services.grading_policy import DEFAULT_GRADE_POINTS, get_grading_policy


def grade_point_for(grade: str | None, grade_points: dict[str, float] | None = None) -> float:
    source = grade_points or DEFAULT_GRADE_POINTS
    return float(source.get(str(grade or "").strip(), 0.0))


async def _load_students_by_user_ids(student_user_ids: set[str], database: Any) -> dict[str, dict[str, Any]]:
    if not student_user_ids:
        return {}
    rows = await database.students.find(
        {"user_id": {"$in": sorted(student_user_ids)}, "is_active": True}
    ).to_list(length=len(student_user_ids))
    return {str(item.get("user_id")): item for item in rows if item.get("user_id")}


async def _load_assignments_for_evaluations(evaluations: list[dict[str, Any]], database: Any) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    submission_ids = sorted({row.get("submission_id") for row in evaluations if row.get("submission_id")})
    submission_rows = []
    if submission_ids:
        submission_rows = await database.submissions.find(
            {"_id": {"$in": [parse_object_id(value) for value in submission_ids]}},
            {"assignment_id": 1, "original_filename": 1},
        ).to_list(length=len(submission_ids))
    submission_map = {str(item["_id"]): item for item in submission_rows if item.get("_id")}

    assignment_ids = sorted({row.get("assignment_id") for row in submission_rows if row.get("assignment_id")})
    assignment_rows = []
    if assignment_ids:
        assignment_rows = await database.assignments.find(
            {"_id": {"$in": [parse_object_id(value) for value in assignment_ids]}},
            {"title": 1, "subject_id": 1, "class_id": 1},
        ).to_list(length=len(assignment_ids))
    assignment_map = {str(item["_id"]): item for item in assignment_rows if item.get("_id")}

    subject_ids = sorted({row.get("subject_id") for row in assignment_rows if row.get("subject_id")})
    subject_rows = []
    if subject_ids:
        subject_rows = await database.subjects.find(
            {"_id": {"$in": [parse_object_id(value) for value in subject_ids]}},
            {"name": 1, "code": 1},
        ).to_list(length=len(subject_ids))
    subject_map = {str(item["_id"]): item for item in subject_rows if item.get("_id")}

    class_ids = sorted({row.get("class_id") for row in assignment_rows if row.get("class_id")})
    class_rows = []
    if class_ids:
        class_rows = await database.classes.find(
            {"_id": {"$in": [parse_object_id(value) for value in class_ids]}},
            {"name": 1, "semester_id": 1, "batch_id": 1},
        ).to_list(length=len(class_ids))
    class_map = {str(item["_id"]): item for item in class_rows if item.get("_id")}

    semester_ids = sorted({row.get("semester_id") for row in class_rows if row.get("semester_id")})
    semester_rows = []
    if semester_ids:
        semester_rows = await database.semesters.find(
            {"_id": {"$in": [parse_object_id(value) for value in semester_ids]}},
            {"label": 1, "semester_number": 1},
        ).to_list(length=len(semester_ids))
    semester_map = {str(item["_id"]): item for item in semester_rows if item.get("_id")}
    return submission_map, assignment_map, subject_map, class_map, semester_map


async def build_semester_result_groups(
    *,
    student_user_id: str | None = None,
    semester_id: str | None = None,
    database: Any,
) -> list[dict[str, Any]]:
    grading_policy = await get_grading_policy(database=database)
    grade_points = grading_policy.get("grade_points") or DEFAULT_GRADE_POINTS
    precision = int(grading_policy.get("transcript_precision") or 2)
    query: dict[str, Any] = {"result_status": "released"}
    if student_user_id:
        query["student_user_id"] = student_user_id

    evaluations = await database.evaluations.find(query).sort("released_at", -1).to_list(length=1000)
    if not evaluations:
        return []

    submission_map, assignment_map, subject_map, class_map, semester_map = await _load_assignments_for_evaluations(evaluations, database)
    student_map = await _load_students_by_user_ids(
        {str(item.get("student_user_id")) for item in evaluations if item.get("student_user_id")},
        database,
    )
    exam_map: dict[str, dict[str, Any]] = {}
    assignment_ids = sorted(set(assignment_map))
    if assignment_ids and getattr(database, "exams", None) is not None:
        exam_rows = await database.exams.find(
            {"assignment_id": {"$in": assignment_ids}, "is_active": True},
            {"assignment_id": 1, "title": 1, "code": 1},
        ).to_list(length=500)
        exam_map = {str(item.get("assignment_id")): item for item in exam_rows if item.get("assignment_id")}

    grouped: dict[tuple[str, str], dict[str, Any]] = {}
    for evaluation in evaluations:
        student_key = str(evaluation.get("student_user_id") or "")
        submission = submission_map.get(str(evaluation.get("submission_id") or ""))
        assignment = assignment_map.get(str((submission or {}).get("assignment_id") or ""))
        class_doc = class_map.get(str((assignment or {}).get("class_id") or ""))
        resolved_semester_id = str((class_doc or {}).get("semester_id") or "")
        if not resolved_semester_id:
            continue
        if semester_id and resolved_semester_id != str(semester_id):
            continue

        resolved_class_id = str((assignment or {}).get("class_id") or "")
        subject_doc = subject_map.get(str((assignment or {}).get("subject_id") or ""))
        semester_doc = semester_map.get(resolved_semester_id) or {}
        student_doc = student_map.get(student_key) or {}
        grouping_key = (student_key, resolved_semester_id)
        bucket = grouped.setdefault(
            grouping_key,
            {
                "student_user_id": student_key,
                "student_name": student_doc.get("full_name"),
                "roll_number": student_doc.get("roll_number"),
                "semester_id": resolved_semester_id,
                "semester_label": semester_doc.get("label"),
                "semester_number": semester_doc.get("semester_number"),
                "class_id": resolved_class_id,
                "class_name": (class_doc or {}).get("name"),
                "batch_id": (class_doc or {}).get("batch_id"),
                "items": [],
            },
        )
        assignment_id = str((submission or {}).get("assignment_id") or "")
        exam = exam_map.get(assignment_id) or {}
        bucket["items"].append(
            {
                "evaluation_id": str(evaluation.get("_id") or ""),
                "submission_id": str(evaluation.get("submission_id") or ""),
                "assignment_id": assignment_id or None,
                "assignment_title": (assignment or {}).get("title") or (submission or {}).get("original_filename"),
                "subject_id": (assignment or {}).get("subject_id"),
                "subject_name": (subject_doc or {}).get("name"),
                "subject_code": (subject_doc or {}).get("code"),
                "exam_id": str(exam.get("_id")) if exam.get("_id") else None,
                "exam_title": exam.get("title"),
                "grand_total": float(evaluation.get("grand_total") or 0),
                "grade": evaluation.get("grade") or "Needs Improvement",
                "grade_point": grade_point_for(evaluation.get("grade"), grade_points),
                "released_at": evaluation.get("released_at"),
                "result_version": int(evaluation.get("result_version") or 1),
            }
        )

    groups = []
    for group in grouped.values():
        items = sorted(group["items"], key=lambda item: ((item.get("subject_name") or ""), (item.get("assignment_title") or "")))
        item_count = len(items)
        average_score = round(sum(item["grand_total"] for item in items) / item_count, 2) if items else 0.0
        gpa = round(sum(item["grade_point"] for item in items) / item_count, precision) if items else 0.0
        groups.append(
            {
                **group,
                "items": items,
                "result_count": item_count,
                "average_score": average_score,
                "gpa": gpa,
            }
        )

    groups.sort(key=lambda item: (item.get("semester_number") or 0, item.get("semester_label") or ""))
    return groups


async def _resolve_evaluation_result_context(
    *,
    evaluation: dict[str, Any],
    database: Any,
) -> dict[str, Any] | None:
    submission_id = str(evaluation.get("submission_id") or "")
    student_user_id = str(evaluation.get("student_user_id") or "")
    if not submission_id or not student_user_id:
        return None

    submission = await database.submissions.find_one(
        {"_id": parse_object_id(submission_id)},
        {"assignment_id": 1},
    )
    if not submission or not submission.get("assignment_id"):
        return None

    assignment = await database.assignments.find_one(
        {"_id": parse_object_id(str(submission.get("assignment_id")))},
        {"class_id": 1},
    )
    if not assignment or not assignment.get("class_id"):
        return None

    class_doc = await database.classes.find_one(
        {"_id": parse_object_id(str(assignment.get("class_id")))},
        {"semester_id": 1, "name": 1},
    )
    if not class_doc or not class_doc.get("semester_id"):
        return None

    return {
        "student_user_id": student_user_id,
        "semester_id": str(class_doc.get("semester_id") or ""),
        "class_id": str(assignment.get("class_id") or ""),
        "class_name": class_doc.get("name"),
    }


async def request_semester_result_correction(
    *,
    trigger_evaluation: dict[str, Any],
    actor_user_id: str,
    reason: str,
    database: Any,
) -> dict[str, Any] | None:
    context = await _resolve_evaluation_result_context(evaluation=trigger_evaluation, database=database)
    if not context:
        return None

    existing = await database.semester_results.find_one(
        {
            "student_user_id": context["student_user_id"],
            "semester_id": context["semester_id"],
            "is_active": True,
        }
    )
    if not existing:
        return None

    now = datetime.now(timezone.utc)
    await database.semester_results.update_one(
        {"_id": existing["_id"]},
        {
            "$set": {
                "status": "correction_requested",
                "correction_requested_at": now,
                "correction_requested_by_user_id": actor_user_id,
                "correction_reason": reason.strip(),
                "updated_at": now,
            }
        },
    )
    return await database.semester_results.find_one({"_id": existing["_id"]})


async def publish_semester_result(
    *,
    trigger_evaluation: dict[str, Any],
    actor_user_id: str,
    database: Any,
) -> dict[str, Any]:
    student_user_id = str(trigger_evaluation.get("student_user_id") or "")
    groups = await build_semester_result_groups(student_user_id=student_user_id, database=database)
    target_group = next(
        (
            group
            for group in groups
            if any(item["evaluation_id"] == str(trigger_evaluation.get("_id") or "") for item in group["items"])
        ),
        None,
    )
    if target_group is None:
        raise ValueError("No released semester result could be derived from this evaluation")

    existing = await database.semester_results.find_one(
        {
            "student_user_id": target_group["student_user_id"],
            "semester_id": target_group["semester_id"],
            "is_active": True,
        }
    )
    next_version = int((existing or {}).get("result_version") or 0) + 1
    now = datetime.now(timezone.utc)
    document = {
        "student_user_id": target_group["student_user_id"],
        "student_name": target_group.get("student_name"),
        "roll_number": target_group.get("roll_number"),
        "semester_id": target_group["semester_id"],
        "semester_label": target_group.get("semester_label"),
        "semester_number": target_group.get("semester_number"),
        "class_id": target_group.get("class_id"),
        "class_name": target_group.get("class_name"),
        "batch_id": target_group.get("batch_id"),
        "status": "released",
        "result_version": next_version,
        "released_at": now,
        "released_by_user_id": actor_user_id,
        "correction_requested_at": None,
        "correction_requested_by_user_id": None,
        "correction_reason": None,
        "reopened_at": None,
        "reopened_by_user_id": None,
        "reopen_reason": None,
        "result_count": target_group["result_count"],
        "average_score": target_group["average_score"],
        "gpa": target_group["gpa"],
        "items": target_group["items"],
        "is_active": True,
        "schema_version": SEMESTER_RESULT_SCHEMA_VERSION,
        "updated_at": now,
    }
    if existing:
        await database.semester_results.update_one({"_id": existing["_id"]}, {"$set": document})
        return await database.semester_results.find_one({"_id": existing["_id"]})

    document["created_at"] = now
    result = await database.semester_results.insert_one(document)
    return await database.semester_results.find_one({"_id": result.inserted_id})


async def build_transcript(
    *,
    student_user_id: str,
    database: Any,
) -> dict[str, Any]:
    grading_policy = await get_grading_policy(database=database)
    precision = int(grading_policy.get("transcript_precision") or 2)
    rows = await database.semester_results.find(
        {"student_user_id": student_user_id, "status": "released", "is_active": True}
    ).sort("semester_number", 1).to_list(length=100)
    student = await database.students.find_one({"user_id": student_user_id, "is_active": True})
    user_doc = await database.users.find_one({"_id": parse_object_id(student_user_id), "is_active": True})
    semesters = []
    cumulative_points = 0.0
    cumulative_count = 0
    for row in rows:
        result_count = int(row.get("result_count") or len(row.get("items") or []))
        gpa = float(row.get("gpa") or 0)
        cumulative_points += gpa * result_count
        cumulative_count += result_count
        semesters.append(
            {
                "result_id": str(row["_id"]),
                "semester_id": row.get("semester_id"),
                "semester_label": row.get("semester_label"),
                "semester_number": row.get("semester_number"),
                "status": row.get("status", "released"),
                "result_version": int(row.get("result_version") or 1),
                "released_at": row.get("released_at"),
                "result_count": result_count,
                "average_score": float(row.get("average_score") or 0),
                "gpa": gpa,
                "cgpa": round(cumulative_points / cumulative_count, precision) if cumulative_count else 0.0,
            }
        )
    return {
        "student_user_id": student_user_id,
        "student_name": (student or {}).get("full_name") or (user_doc or {}).get("full_name"),
        "roll_number": (student or {}).get("roll_number"),
        "email": (student or {}).get("email") or (user_doc or {}).get("email"),
        "generated_at": datetime.now(timezone.utc),
        "semester_count": len(semesters),
        "cgpa": round(cumulative_points / cumulative_count, precision) if cumulative_count else 0.0,
        "semesters": semesters,
    }
