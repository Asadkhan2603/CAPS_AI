from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.database import db
from app.core.mongo import parse_object_id
from app.models.student_interventions import student_intervention_public
from app.schemas.academic_predictive import (
    PredictiveEvidenceOut,
    PredictiveOverviewOut,
    SectionRiskSummaryItemOut,
    SectionRiskSummaryResponseOut,
    StaffingForecastItemOut,
    StaffingForecastResponseOut,
    StudentRiskForecastItemOut,
    StudentRiskForecastResponseOut,
)
from app.schemas.student_intervention import StudentInterventionOut
from app.services.attendance_summary import build_attendance_section_summary
from app.services.rbac import build_batch_scope_filter, merge_query_with_scope_filter
from app.services.section_mapping import coordinator_scope_class_id
from app.api.v1.endpoints.timetables import _compute_sync_snapshot


def _safe_object_ids(values: set[str]) -> list[Any]:
    object_ids: list[Any] = []
    for value in values:
        try:
            object_ids.append(parse_object_id(value))
        except Exception:
            continue
    return object_ids


def _risk_level(score: int) -> str:
    if score >= 80:
        return "critical"
    if score >= 55:
        return "high"
    if score >= 30:
        return "moderate"
    return "low"


def _score_summary(items: list[Any], *, attr: str = "risk_level") -> dict[str, int]:
    summary = {"critical": 0, "high": 0, "moderate": 0, "low": 0, "total": len(items)}
    for item in items:
        level = getattr(item, attr, None) if hasattr(item, attr) else item.get(attr)
        if level in summary:
            summary[level] += 1
    return summary


def _teacher_extensions(current_user: dict[str, Any]) -> set[str]:
    return {str(item) for item in (current_user.get("extended_roles") or [])}


async def _scoped_sections(
    *,
    current_user: dict[str, Any],
    batch_id: str | None = None,
    semester_id: str | None = None,
    department_id: str | None = None,
    database: Any = db,
) -> list[dict[str, Any]]:
    query: dict[str, Any] = {"is_active": True}
    if batch_id:
        query["batch_id"] = batch_id
    if semester_id:
        query["semester_id"] = semester_id
    if department_id:
        query["department_id"] = department_id

    if current_user.get("role") == "teacher":
        extensions = _teacher_extensions(current_user)
        if "year_head" in extensions:
            pass
        elif "class_coordinator" in extensions:
            scoped_section_id = coordinator_scope_class_id(current_user)
            if scoped_section_id:
                query["_id"] = parse_object_id(scoped_section_id)
            else:
                query["class_coordinator_user_id"] = str(current_user.get("_id"))
        else:
            return []
    else:
        scope_filter = await build_batch_scope_filter(
            current_user,
            department_field="department_id",
            batch_field="batch_id",
            database=database,
        )
        query = merge_query_with_scope_filter(query, scope_filter)

    return await database.classes.find(
        query,
        {
            "name": 1,
            "batch_id": 1,
            "semester_id": 1,
            "department_id": 1,
            "class_coordinator_user_id": 1,
        },
    ).to_list(length=500)


async def _name_map(collection: Any, ids: set[str], field_name: str) -> dict[str, str]:
    if not ids:
        return {}
    rows = await collection.find(
        {"_id": {"$in": [parse_object_id(value) for value in ids]}},
        {field_name: 1},
    ).to_list(length=len(ids))
    return {str(item.get("_id")): str(item.get(field_name) or "") for item in rows if item.get("_id")}


async def _build_section_bundles(
    *,
    current_user: dict[str, Any],
    batch_id: str | None = None,
    semester_id: str | None = None,
    department_id: str | None = None,
    database: Any = db,
) -> tuple[list[dict[str, Any]], dict[str, str], dict[str, str], dict[str, str]]:
    sections = await _scoped_sections(
        current_user=current_user,
        batch_id=batch_id,
        semester_id=semester_id,
        department_id=department_id,
        database=database,
    )
    batch_names = await _name_map(database.batches, {str(item.get("batch_id")) for item in sections if item.get("batch_id")}, "name")
    semester_names = await _name_map(database.semesters, {str(item.get("semester_id")) for item in sections if item.get("semester_id")}, "label")
    teacher_ids = {str(item.get("class_coordinator_user_id")) for item in sections if item.get("class_coordinator_user_id")}
    teacher_names = await _name_map(database.users, teacher_ids, "full_name")
    return sections, batch_names, semester_names, teacher_names


async def _build_section_signal_bundle(
    section: dict[str, Any],
    *,
    batch_names: dict[str, str],
    semester_names: dict[str, str],
    teacher_names: dict[str, str],
    database: Any = db,
) -> dict[str, Any]:
    section_id = str(section.get("_id") or "")
    enrollments = await database.enrollments.find({"class_id": section_id}).to_list(length=5000)
    enrolled_student_ids = {
        str(item.get("student_id"))
        for item in enrollments
        if item.get("student_id")
    }

    student_object_ids = _safe_object_ids(enrolled_student_ids)
    if student_object_ids:
        student_query: dict[str, Any] = {
            "$or": [
                {"_id": {"$in": student_object_ids}, "is_active": True},
                {"class_id": section_id, "is_active": True},
            ]
        }
    else:
        student_query = {"class_id": section_id, "is_active": True}

    students = await database.students.find(student_query).to_list(length=5000)
    student_map = {str(item.get("_id")): item for item in students if item.get("_id")}
    active_students = [item for item in student_map.values() if item.get("is_active", True)]
    student_ids = sorted(student_map)
    student_user_ids = [str(item.get("user_id")) for item in active_students if item.get("user_id")]

    legacy_profile_only_count = sum(1 for item in active_students if str(item.get("_id")) not in enrolled_student_ids)

    offerings = await database.course_offerings.find(
        {"section_id": section_id, "is_active": True},
        {"_id": 1, "teacher_user_id": 1, "subject_id": 1, "group_id": 1},
    ).to_list(length=5000)
    offering_ids = [str(item.get("_id")) for item in offerings if item.get("_id")]
    teacher_load: dict[str, int] = defaultdict(int)
    for offering in offerings:
        teacher_user_id = str(offering.get("teacher_user_id") or "")
        if teacher_user_id:
            teacher_load[teacher_user_id] += 1

    slots = []
    if offering_ids:
        slots = await database.class_slots.find(
            {"course_offering_id": {"$in": offering_ids}, "is_active": True},
            {"_id": 1},
        ).to_list(length=5000)

    evaluation_rows = []
    if student_user_ids:
        evaluation_rows = await database.evaluations.find(
            {"student_user_id": {"$in": student_user_ids}},
            {"student_user_id": 1, "is_finalized": 1, "result_status": 1, "grand_total": 1, "released_at": 1},
        ).to_list(length=10000)

    latest_timetable = await database.timetables.find_one(
        {"class_id": section_id, "status": "published", "is_active": True},
        sort=[("version", -1)],
    )
    sync_snapshot = {"sync_status": None, "drift_count": 0}
    if latest_timetable:
        sync_snapshot = await _compute_sync_snapshot(latest_timetable)

    attendance_summary = None
    if slots:
        attendance_summary = await build_attendance_section_summary(section_id=section_id, database=database)

    recent_interventions = []
    interventions_collection = getattr(database, "student_interventions", None)
    if interventions_collection is not None:
        recent_interventions = await interventions_collection.find(
            {"section_id": section_id},
        ).sort("created_at", -1).to_list(length=500)
    intervention_by_student: dict[str, dict[str, Any]] = {}
    for row in recent_interventions:
        student_id = str(row.get("student_id") or "")
        if student_id and student_id not in intervention_by_student:
            intervention_by_student[student_id] = row

    semester_results = []
    semester_results_collection = getattr(database, "semester_results", None)
    if student_user_ids and semester_results_collection is not None:
        semester_results = await semester_results_collection.find(
            {
                "student_user_id": {"$in": student_user_ids},
                "is_active": True,
                "status": {"$in": ["released", "correction_requested"]},
            },
            {"student_user_id": 1, "gpa": 1, "average_score": 1, "status": 1},
        ).to_list(length=5000)

    return {
        "section_id": section_id,
        "section_name": str(section.get("name") or ""),
        "batch_id": str(section.get("batch_id") or "") or None,
        "batch_name": batch_names.get(str(section.get("batch_id") or ""), ""),
        "semester_id": str(section.get("semester_id") or "") or None,
        "semester_label": semester_names.get(str(section.get("semester_id") or ""), ""),
        "coordinator_user_id": str(section.get("class_coordinator_user_id") or "") or None,
        "coordinator_name": teacher_names.get(str(section.get("class_coordinator_user_id") or ""), "") or None,
        "students": active_students,
        "student_ids": student_ids,
        "student_user_ids": student_user_ids,
        "legacy_profile_only_count": legacy_profile_only_count,
        "offerings": offerings,
        "teacher_load": teacher_load,
        "evaluations": evaluation_rows,
        "attendance_summary": attendance_summary,
        "sync_snapshot": sync_snapshot,
        "latest_timetable": latest_timetable,
        "latest_interventions": intervention_by_student,
        "semester_results": semester_results,
    }


async def build_staffing_forecast(
    *,
    current_user: dict[str, Any],
    batch_id: str | None = None,
    semester_id: str | None = None,
    department_id: str | None = None,
    section_id: str | None = None,
    teacher_user_id: str | None = None,
    risk_level: str | None = None,
    database: Any = db,
) -> StaffingForecastResponseOut:
    generated_at = datetime.now(timezone.utc)
    sections, batch_names, semester_names, teacher_names = await _build_section_bundles(
        current_user=current_user,
        batch_id=batch_id,
        semester_id=semester_id,
        department_id=department_id,
        database=database,
    )
    bundles = []
    for section in sections:
        if section_id and str(section.get("_id")) != str(section_id):
            continue
        bundles.append(
            await _build_section_signal_bundle(
                section,
                batch_names=batch_names,
                semester_names=semester_names,
                teacher_names=teacher_names,
                database=database,
            )
        )

    global_teacher_offering_load: dict[str, int] = defaultdict(int)
    global_teacher_section_load: dict[str, set[str]] = defaultdict(set)
    for bundle in bundles:
        for offering in bundle["offerings"]:
            owner = str(offering.get("teacher_user_id") or "")
            if not owner:
                continue
            global_teacher_offering_load[owner] += 1
            global_teacher_section_load[owner].add(bundle["section_id"])

    items: list[StaffingForecastItemOut] = []
    for bundle in bundles:
        score = 0
        reason_codes: list[str] = []
        reasons: list[str] = []
        evidence: list[PredictiveEvidenceOut] = []
        total_students = len(bundle["students"])
        offering_count = len(bundle["offerings"])
        coordinator_id = bundle["coordinator_user_id"]
        primary_teacher_id = coordinator_id
        primary_teacher_name = bundle["coordinator_name"]

        if not primary_teacher_id and bundle["teacher_load"]:
            primary_teacher_id = max(bundle["teacher_load"], key=bundle["teacher_load"].get)
            primary_teacher_name = teacher_names.get(primary_teacher_id) or primary_teacher_id

        if teacher_user_id and str(primary_teacher_id or "") != str(teacher_user_id):
            continue

        if offering_count == 0:
            score += 55
            reason_codes.append("no_active_offerings")
            reasons.append("Section has no active course delivery mapped.")
        elif total_students >= 45 and offering_count <= 1:
            score += 35
            reason_codes.append("undercovered_large_section")
            reasons.append("Large section is running with thin course delivery coverage.")
        elif total_students >= 30 and offering_count <= 2:
            score += 20
            reason_codes.append("coverage_pressure")
            reasons.append("Student count is rising faster than the active offering footprint.")

        drift_count = int(bundle["sync_snapshot"].get("drift_count") or 0)
        if drift_count >= 3:
            score += 20
            reason_codes.append("timetable_drift")
            reasons.append("Published timetable is drifting away from active class slots.")
        elif drift_count > 0:
            score += 10
            reason_codes.append("minor_timetable_drift")
            reasons.append("Timetable drift needs cleanup before delivery pressure grows.")

        sync_status = str(bundle["sync_snapshot"].get("sync_status") or "")
        if sync_status and sync_status != "synced":
            score += 10
            reason_codes.append("unsynced_timetable")
            reasons.append("Student schedule trust is reduced because the timetable is not fully synced.")

        pending_evaluation_count = sum(1 for item in bundle["evaluations"] if not item.get("is_finalized"))
        unreleased_evaluation_count = sum(
            1 for item in bundle["evaluations"] if item.get("is_finalized") and item.get("result_status") != "released"
        )
        shortage_risk_count = int(getattr(bundle["attendance_summary"], "shortage_risk_count", 0) or 0)
        average_attendance_percent = getattr(bundle["attendance_summary"], "average_attendance_percent", None)
        if unreleased_evaluation_count >= 5:
            score += 10
            reason_codes.append("result_release_backlog")
            reasons.append("Result release backlog is building around this section.")
        if pending_evaluation_count >= 5:
            score += 8
            reason_codes.append("evaluation_backlog")
            reasons.append("Evaluation backlog suggests coordination pressure on the teaching team.")
        if shortage_risk_count >= 5:
            score += 15
            reason_codes.append("attendance_pressure")
            reasons.append("Multiple students are already in shortage-risk territory for this section.")

        if bundle["legacy_profile_only_count"] > 0:
            score += 8
            reason_codes.append("legacy_profiles_only")
            reasons.append("Legacy-only student profiles still need placement cleanup for reliable operations.")

        if primary_teacher_id:
            if global_teacher_offering_load.get(primary_teacher_id, 0) >= 6:
                score += 18
                reason_codes.append("teacher_overload")
                reasons.append("Lead teacher is already carrying a heavy delivery load across the scope.")
            elif len(global_teacher_section_load.get(primary_teacher_id, set())) >= 4:
                score += 12
                reason_codes.append("teacher_spread")
                reasons.append("Lead teacher is stretched across many sections.")

        suggested_action = "Review section capacity and load balancing."
        if "no_active_offerings" in reason_codes:
            suggested_action = "Add course delivery for this section before the next academic cycle."
        elif "undercovered_large_section" in reason_codes or "coverage_pressure" in reason_codes:
            suggested_action = "Add or rebalance offerings before student load outruns delivery coverage."
        elif "timetable_drift" in reason_codes or "unsynced_timetable" in reason_codes:
            suggested_action = "Publish and sync the timetable so staffing changes land in student-visible schedules."
        elif "teacher_overload" in reason_codes:
            suggested_action = "Rebalance teacher assignments across sections to reduce overload."
        elif "legacy_profiles_only" in reason_codes:
            suggested_action = "Resolve unmapped or legacy-only students before planning the next delivery window."

        evidence.extend(
            [
                PredictiveEvidenceOut(label="Students", value=total_students),
                PredictiveEvidenceOut(label="Active offerings", value=offering_count),
                PredictiveEvidenceOut(label="Timetable drift", value=drift_count),
                PredictiveEvidenceOut(label="Pending evaluations", value=pending_evaluation_count),
                PredictiveEvidenceOut(label="Unreleased results", value=unreleased_evaluation_count),
                PredictiveEvidenceOut(label="Shortage-risk students", value=shortage_risk_count),
                PredictiveEvidenceOut(label="Average attendance", value=average_attendance_percent),
            ]
        )

        level = _risk_level(score)
        if risk_level and level != risk_level:
            continue

        items.append(
            StaffingForecastItemOut(
                section_id=bundle["section_id"],
                section_name=bundle["section_name"],
                batch_id=bundle["batch_id"],
                batch_name=bundle["batch_name"],
                semester_id=bundle["semester_id"],
                semester_label=bundle["semester_label"],
                teacher_user_id=primary_teacher_id,
                teacher_name=primary_teacher_name,
                risk_level=level,
                risk_score=score,
                reason_codes=reason_codes,
                reasons=reasons,
                suggested_action=suggested_action,
                evidence=evidence,
            )
        )

    items.sort(key=lambda item: (-item.risk_score, item.section_name.lower()))
    return StaffingForecastResponseOut(generated_at=generated_at, summary=_score_summary(items), items=items)


def _student_attendance_stats(attendance_summary: Any | None) -> dict[str, dict[str, Any]]:
    if attendance_summary is None:
        return {}
    stats: dict[str, dict[str, Any]] = {}
    for item in attendance_summary.students:
        payload = item.model_dump() if hasattr(item, "model_dump") else dict(item)
        stats[str(payload.get("student_id") or "")] = payload
    return stats


async def _student_trend_deltas(
    *,
    student_ids: list[str],
    section_bundle: dict[str, Any],
    database: Any,
) -> dict[str, float]:
    if not student_ids or not section_bundle["offerings"]:
        return {}
    offering_ids = [str(item.get("_id")) for item in section_bundle["offerings"] if item.get("_id")]
    if not offering_ids:
        return {}
    slot_rows = await database.class_slots.find(
        {"course_offering_id": {"$in": offering_ids}, "is_active": True},
        {"_id": 1},
    ).to_list(length=5000)
    slot_ids = [str(item.get("_id")) for item in slot_rows if item.get("_id")]
    if not slot_ids:
        return {}

    since = datetime.now(timezone.utc) - timedelta(days=60)
    records = await database.attendance_records.find(
        {
            "class_slot_id": {"$in": slot_ids},
            "student_id": {"$in": student_ids},
            "marked_at": {"$gte": since},
        },
        {"student_id": 1, "status": 1, "marked_at": 1},
    ).sort("marked_at", 1).to_list(length=50000)

    midpoint = datetime.now(timezone.utc) - timedelta(days=30)
    buckets: dict[str, dict[str, list[int]]] = defaultdict(lambda: {"older": [0, 0], "recent": [0, 0]})
    for record in records:
        student_id = str(record.get("student_id") or "")
        bucket = "recent" if record.get("marked_at") and record["marked_at"] >= midpoint else "older"
        buckets[student_id][bucket][1] += 1
        if record.get("status") in {"present", "late", "excused"}:
            buckets[student_id][bucket][0] += 1

    deltas: dict[str, float] = {}
    for student_id, periods in buckets.items():
        older_present, older_total = periods["older"]
        recent_present, recent_total = periods["recent"]
        older_pct = (older_present / older_total) * 100 if older_total else None
        recent_pct = (recent_present / recent_total) * 100 if recent_total else None
        if older_pct is None or recent_pct is None:
            continue
        deltas[student_id] = round(recent_pct - older_pct, 2)
    return deltas


async def build_student_risk_forecast(
    *,
    current_user: dict[str, Any],
    batch_id: str | None = None,
    semester_id: str | None = None,
    department_id: str | None = None,
    section_id: str | None = None,
    risk_level: str | None = None,
    database: Any = db,
) -> StudentRiskForecastResponseOut:
    generated_at = datetime.now(timezone.utc)
    sections, batch_names, semester_names, teacher_names = await _build_section_bundles(
        current_user=current_user,
        batch_id=batch_id,
        semester_id=semester_id,
        department_id=department_id,
        database=database,
    )

    items: list[StudentRiskForecastItemOut] = []
    for section in sections:
        if section_id and str(section.get("_id")) != str(section_id):
            continue
        bundle = await _build_section_signal_bundle(
            section,
            batch_names=batch_names,
            semester_names=semester_names,
            teacher_names=teacher_names,
            database=database,
        )
        attendance_stats = _student_attendance_stats(bundle["attendance_summary"])
        trend_deltas = await _student_trend_deltas(
            student_ids=bundle["student_ids"],
            section_bundle=bundle,
            database=database,
        )
        evaluations_by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in bundle["evaluations"]:
            student_user_id = str(row.get("student_user_id") or "")
            if student_user_id:
                evaluations_by_user[student_user_id].append(row)
        semester_results_by_user: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in bundle["semester_results"]:
            student_user_id = str(row.get("student_user_id") or "")
            if student_user_id:
                semester_results_by_user[student_user_id].append(row)

        for student in bundle["students"]:
            student_id = str(student.get("_id") or "")
            student_user_id = str(student.get("user_id") or "") or None
            score = 0
            reason_codes: list[str] = []
            reasons: list[str] = []
            evidence: list[PredictiveEvidenceOut] = []

            attendance = attendance_stats.get(student_id) or {}
            attendance_percent = float(attendance.get("attendance_percent") or 0)
            if attendance:
                evidence.append(PredictiveEvidenceOut(label="Attendance", value=attendance_percent))
            if attendance and attendance.get("shortage_risk"):
                score += 35
                reason_codes.append("attendance_shortage")
                reasons.append("Attendance is already below the shortage threshold.")
            elif attendance and attendance_percent < 75:
                score += 20
                reason_codes.append("low_attendance")
                reasons.append("Attendance is slipping into an unsafe range.")

            trend_delta = trend_deltas.get(student_id)
            if trend_delta is not None:
                evidence.append(PredictiveEvidenceOut(label="Attendance trend delta", value=trend_delta))
                if trend_delta <= -15:
                    score += 20
                    reason_codes.append("attendance_downtrend")
                    reasons.append("Attendance trend is dropping sharply compared with the previous period.")
                elif trend_delta <= -8:
                    score += 10
                    reason_codes.append("attendance_soft_decline")
                    reasons.append("Attendance trend is falling and needs follow-up.")

            student_evaluations = evaluations_by_user.get(student_user_id or "", [])
            latest_released = max(
                (row for row in student_evaluations if row.get("result_status") == "released"),
                key=lambda row: row.get("released_at") or datetime.min.replace(tzinfo=timezone.utc),
                default=None,
            )
            if latest_released:
                grand_total = float(latest_released.get("grand_total") or 0)
                evidence.append(PredictiveEvidenceOut(label="Latest released score", value=grand_total))
                if grand_total < 40:
                    score += 28
                    reason_codes.append("weak_released_result")
                    reasons.append("Latest released evaluation is in a high-risk scoring band.")
                elif grand_total < 55:
                    score += 16
                    reason_codes.append("soft_score_risk")
                    reasons.append("Recent released performance suggests academic follow-up is needed.")

            unfinished_count = sum(1 for row in student_evaluations if not row.get("is_finalized"))
            unreleased_count = sum(1 for row in student_evaluations if row.get("is_finalized") and row.get("result_status") != "released")
            if unfinished_count >= 2:
                score += 8
                reason_codes.append("evaluation_backlog")
                reasons.append("Evaluation backlog may be masking the student’s current academic state.")
            if unreleased_count >= 2:
                score += 8
                reason_codes.append("result_pending")
                reasons.append("Released result visibility is lagging for this student.")

            semester_rows = semester_results_by_user.get(student_user_id or "", [])
            released_semester = next((row for row in semester_rows if row.get("status") == "released"), None)
            if released_semester:
                average_score = float(released_semester.get("average_score") or 0)
                gpa = float(released_semester.get("gpa") or 0)
                evidence.append(PredictiveEvidenceOut(label="Semester average", value=average_score))
                evidence.append(PredictiveEvidenceOut(label="Semester GPA", value=gpa))
                if average_score < 45 or gpa < 2:
                    score += 18
                    reason_codes.append("semester_result_risk")
                    reasons.append("Semester result trend places the student in an elevated academic risk band.")
            elif student_user_id and not semester_rows and latest_released:
                score += 6
                reason_codes.append("result_release_gap")
                reasons.append("Released evaluations exist, but semester-level official result flow is still incomplete.")

            if not student_user_id:
                score += 12
                reason_codes.append("identity_link_gap")
                reasons.append("Student profile is missing a stable user link, which can disrupt academic workflows.")

            latest_intervention_raw = bundle["latest_interventions"].get(student_id)
            latest_intervention = (
                StudentInterventionOut(**student_intervention_public(latest_intervention_raw))
                if latest_intervention_raw
                else None
            )
            if latest_intervention and latest_intervention.status in {"open", "in_progress"}:
                score += 10
                reason_codes.append("active_intervention")
                reasons.append("An intervention is already open, which confirms ongoing academic concern.")

            suggested_action = "Review this student in the academic risk queue."
            if "attendance_shortage" in reason_codes or "attendance_downtrend" in reason_codes:
                suggested_action = "Contact the student and review attendance exceptions before the shortage widens."
            elif "weak_released_result" in reason_codes or "semester_result_risk" in reason_codes:
                suggested_action = "Escalate for academic counseling and result review."
            elif "identity_link_gap" in reason_codes:
                suggested_action = "Verify placement and identity linkage so academic records stay trustworthy."
            elif "result_pending" in reason_codes or "evaluation_backlog" in reason_codes:
                suggested_action = "Clear result and evaluation backlog before finalizing intervention decisions."

            level = _risk_level(score)
            if risk_level and level != risk_level:
                continue
            if score <= 0:
                continue

            items.append(
                StudentRiskForecastItemOut(
                    student_id=student_id,
                    student_name=str(student.get("full_name") or ""),
                    roll_number=student.get("roll_number"),
                    student_user_id=student_user_id,
                    section_id=bundle["section_id"],
                    section_name=bundle["section_name"],
                    batch_id=bundle["batch_id"],
                    batch_name=bundle["batch_name"],
                    semester_id=bundle["semester_id"],
                    semester_label=bundle["semester_label"],
                    risk_level=level,
                    risk_score=score,
                    reason_codes=reason_codes,
                    reasons=reasons,
                    suggested_action=suggested_action,
                    evidence=evidence,
                    latest_intervention=latest_intervention,
                )
            )

    items.sort(key=lambda item: (-item.risk_score, item.student_name.lower()))
    summary = _score_summary(items)
    summary["open_interventions"] = sum(
        1 for item in items if item.latest_intervention and item.latest_intervention.status in {"open", "in_progress"}
    )
    summary["sections_impacted"] = len({item.section_id for item in items})
    return StudentRiskForecastResponseOut(generated_at=generated_at, summary=summary, items=items)


async def build_section_risk_summary(
    *,
    current_user: dict[str, Any],
    batch_id: str | None = None,
    semester_id: str | None = None,
    department_id: str | None = None,
    section_id: str | None = None,
    risk_level: str | None = None,
    database: Any = db,
) -> SectionRiskSummaryResponseOut:
    generated_at = datetime.now(timezone.utc)
    staffing = await build_staffing_forecast(
        current_user=current_user,
        batch_id=batch_id,
        semester_id=semester_id,
        department_id=department_id,
        section_id=section_id,
        risk_level=None,
        database=database,
    )
    student_risk = await build_student_risk_forecast(
        current_user=current_user,
        batch_id=batch_id,
        semester_id=semester_id,
        department_id=department_id,
        section_id=section_id,
        risk_level=None,
        database=database,
    )

    student_counts_by_section: dict[str, int] = defaultdict(int)
    student_level_counts_by_section: dict[str, dict[str, int]] = defaultdict(
        lambda: {"critical": 0, "high": 0, "moderate": 0, "low": 0}
    )
    for item in student_risk.items:
        student_counts_by_section[item.section_id] += 1
        if item.risk_level in student_level_counts_by_section[item.section_id]:
            student_level_counts_by_section[item.section_id][item.risk_level] += 1

    items: list[SectionRiskSummaryItemOut] = []
    for staffing_item in staffing.items:
        score = staffing_item.risk_score
        reasons = list(staffing_item.reasons)
        reason_codes = list(staffing_item.reason_codes)
        at_risk_students = student_counts_by_section.get(staffing_item.section_id, 0)
        student_levels = student_level_counts_by_section.get(staffing_item.section_id, {})
        critical_students = int(student_levels.get("critical", 0) or 0)
        high_students = int(student_levels.get("high", 0) or 0)
        if critical_students >= 1:
            score += 25
            reason_codes.append("critical_student_risk")
            reasons.append("A critical-risk student is already active in this section and needs coordinator follow-up.")
        elif high_students >= 2:
            score += 18
            reason_codes.append("multiple_high_risk_students")
            reasons.append("Multiple high-risk students are concentrated in this section.")
        elif at_risk_students >= 3:
            score += 18
            reason_codes.append("multiple_at_risk_students")
            reasons.append("Multiple students in this section already need intervention.")
        elif at_risk_students >= 1:
            score += 10
            reason_codes.append("at_risk_students_present")
            reasons.append("Student-level academic risk is already visible in this section.")

        timetable_drift = 0
        unreleased_evaluation_count = 0
        total_students = 0
        shortage_risk_count = 0
        for evidence in staffing_item.evidence:
            if evidence.label == "Timetable drift":
                timetable_drift = int(evidence.value or 0)
            if evidence.label == "Unreleased results":
                unreleased_evaluation_count = int(evidence.value or 0)
            if evidence.label == "Students":
                total_students = int(evidence.value or 0)
            if evidence.label == "Shortage-risk students":
                shortage_risk_count = int(evidence.value or 0)

        base_level = _risk_level(score)
        if risk_level and base_level != risk_level:
            continue

        suggested_action = staffing_item.suggested_action
        if critical_students >= 1:
            suggested_action = "Review this section immediately for student intervention, staffing readiness, and result follow-through."
        elif at_risk_students >= 3:
            suggested_action = "Review this section jointly for staffing and student intervention pressure."

        items.append(
            SectionRiskSummaryItemOut(
                section_id=staffing_item.section_id,
                section_name=staffing_item.section_name,
                batch_id=staffing_item.batch_id,
                batch_name=staffing_item.batch_name,
                semester_id=staffing_item.semester_id,
                semester_label=staffing_item.semester_label,
                risk_level=base_level,
                risk_score=score,
                total_students=total_students,
                at_risk_students=at_risk_students,
                staffing_pressure=staffing_item.risk_level in {"high", "critical"},
                timetable_drift=timetable_drift,
                shortage_risk_count=shortage_risk_count,
                unreleased_evaluation_count=unreleased_evaluation_count,
                reason_codes=reason_codes,
                reasons=reasons,
                suggested_action=suggested_action,
            )
        )

    items.sort(key=lambda item: (-item.risk_score, item.section_name.lower()))
    summary = _score_summary(items)
    summary["sections_requiring_attention"] = sum(
        1
        for item in items
        if item.risk_level in {"moderate", "high", "critical"}
    )
    return SectionRiskSummaryResponseOut(generated_at=generated_at, summary=summary, items=items)


async def build_predictive_overview(
    *,
    current_user: dict[str, Any],
    batch_id: str | None = None,
    semester_id: str | None = None,
    department_id: str | None = None,
    database: Any = db,
) -> PredictiveOverviewOut:
    staffing = await build_staffing_forecast(
        current_user=current_user,
        batch_id=batch_id,
        semester_id=semester_id,
        department_id=department_id,
        database=database,
    )
    student_risk = await build_student_risk_forecast(
        current_user=current_user,
        batch_id=batch_id,
        semester_id=semester_id,
        department_id=department_id,
        database=database,
    )
    section_risk = await build_section_risk_summary(
        current_user=current_user,
        batch_id=batch_id,
        semester_id=semester_id,
        department_id=department_id,
        database=database,
    )
    summary = {
        "critical_staffing_items": staffing.summary.get("critical", 0),
        "high_staffing_items": staffing.summary.get("high", 0),
        "critical_students": student_risk.summary.get("critical", 0),
        "high_students": student_risk.summary.get("high", 0),
        "open_interventions": student_risk.summary.get("open_interventions", 0),
        "sections_requiring_attention": section_risk.summary.get("sections_requiring_attention", 0),
        "total_staffing_items": staffing.summary.get("total", 0),
        "total_student_risk_items": student_risk.summary.get("total", 0),
        "total_section_risk_items": section_risk.summary.get("total", 0),
    }
    intervention_queue = [
        item
        for item in student_risk.items
        if item.latest_intervention and item.latest_intervention.status in {"open", "in_progress"}
    ]
    return PredictiveOverviewOut(
        generated_at=max(staffing.generated_at, student_risk.generated_at, section_risk.generated_at),
        summary=summary,
        staffing_forecast=staffing.items,
        student_risk=student_risk.items,
        section_risk=section_risk.items,
        intervention_queue=intervention_queue,
    )
