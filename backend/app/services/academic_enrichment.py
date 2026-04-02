from typing import Any

from app.core.mongo import parse_object_id


def _document_name(document: dict[str, Any] | None, *keys: str) -> str | None:
    if not document:
        return None
    for key in keys:
        value = document.get(key)
        if value:
            return str(value)
    return None


async def _related_lookup_map(database: Any, collection_name: str, ids: list[str]) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}
    collection = getattr(database, collection_name, None)
    if collection is None:
        return {}
    object_ids = [parse_object_id(item_id) for item_id in ids if item_id]
    if not object_ids:
        return {}
    rows = await collection.find({"_id": {"$in": object_ids}}).to_list(length=len(object_ids))
    return {str(row.get("_id")): row for row in rows if row.get("_id")}


async def enrich_section_documents(database: Any, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return items

    faculty_map = await _related_lookup_map(database, "faculties", list({str(item.get("faculty_id")) for item in items if item.get("faculty_id")}))
    department_map = await _related_lookup_map(database, "departments", list({str(item.get("department_id")) for item in items if item.get("department_id")}))
    program_map = await _related_lookup_map(database, "programs", list({str(item.get("program_id")) for item in items if item.get("program_id")}))
    specialization_map = await _related_lookup_map(
        database,
        "specializations",
        list({str(item.get("specialization_id")) for item in items if item.get("specialization_id")}),
    )
    batch_map = await _related_lookup_map(database, "batches", list({str(item.get("batch_id")) for item in items if item.get("batch_id")}))
    semester_map = await _related_lookup_map(database, "semesters", list({str(item.get("semester_id")) for item in items if item.get("semester_id")}))
    teacher_map = await _related_lookup_map(
        database,
        "users",
        list({str(item.get("class_coordinator_user_id")) for item in items if item.get("class_coordinator_user_id")}),
    )

    enriched: list[dict[str, Any]] = []
    for item in items:
        faculty = faculty_map.get(str(item.get("faculty_id") or ""))
        department = department_map.get(str(item.get("department_id") or ""))
        program = program_map.get(str(item.get("program_id") or ""))
        specialization = specialization_map.get(str(item.get("specialization_id") or ""))
        batch = batch_map.get(str(item.get("batch_id") or ""))
        semester = semester_map.get(str(item.get("semester_id") or ""))
        teacher = teacher_map.get(str(item.get("class_coordinator_user_id") or ""))
        enriched.append(
            {
                **item,
                "faculty_name": item.get("faculty_name") or _document_name(faculty, "faculty_name", "name"),
                "department_name": item.get("department_name") or _document_name(department, "department_name", "name"),
                "program_name": item.get("program_name") or _document_name(program, "program_name", "name"),
                "specialization_name": item.get("specialization_name")
                or _document_name(specialization, "specialization_name", "name"),
                "batch_name": item.get("batch_name") or _document_name(batch, "name", "academic_span_label", "code"),
                "semester_label": item.get("semester_label") or _document_name(semester, "label"),
                "class_coordinator_name": item.get("class_coordinator_name")
                or _document_name(teacher, "full_name", "email"),
            }
        )
    return enriched


async def enrich_batch_documents(database: Any, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return items

    program_map = await _related_lookup_map(
        database,
        "programs",
        list({str(item.get("program_id")) for item in items if item.get("program_id")}),
    )
    specialization_map = await _related_lookup_map(
        database,
        "specializations",
        list({str(item.get("specialization_id")) for item in items if item.get("specialization_id")}),
    )

    enriched: list[dict[str, Any]] = []
    for item in items:
        program = program_map.get(str(item.get("program_id") or ""))
        specialization = specialization_map.get(str(item.get("specialization_id") or ""))
        enriched.append(
            {
                **item,
                "program_name": item.get("program_name") or _document_name(program, "program_name", "name"),
                "program_code": item.get("program_code") or _document_name(program, "program_code", "code"),
                "program_duration_years": item.get("program_duration_years")
                or (int(program.get("duration_years")) if program and program.get("duration_years") is not None else None),
                "specialization_name": item.get("specialization_name")
                or _document_name(specialization, "specialization_name", "name"),
                "specialization_code": item.get("specialization_code")
                or _document_name(specialization, "specialization_code", "code"),
            }
        )
    return enriched


async def enrich_semester_documents(database: Any, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return items

    batch_map = await _related_lookup_map(
        database,
        "batches",
        list({str(item.get("batch_id")) for item in items if item.get("batch_id")}),
    )
    program_map = await _related_lookup_map(
        database,
        "programs",
        list({str(item.get("program_id")) for item in items if item.get("program_id")}),
    )
    specialization_map = await _related_lookup_map(
        database,
        "specializations",
        list({str(item.get("specialization_id")) for item in items if item.get("specialization_id")}),
    )

    enriched: list[dict[str, Any]] = []
    for item in items:
        batch = batch_map.get(str(item.get("batch_id") or ""))
        program = program_map.get(str(item.get("program_id") or ""))
        specialization = specialization_map.get(str(item.get("specialization_id") or ""))
        enriched.append(
            {
                **item,
                "batch_name": item.get("batch_name") or _document_name(batch, "name"),
                "batch_code": item.get("batch_code") or _document_name(batch, "code"),
                "program_name": item.get("program_name") or _document_name(program, "program_name", "name"),
                "program_code": item.get("program_code") or _document_name(program, "program_code", "code"),
                "specialization_name": item.get("specialization_name")
                or _document_name(specialization, "specialization_name", "name"),
                "specialization_code": item.get("specialization_code")
                or _document_name(specialization, "specialization_code", "code"),
            }
        )
    return enriched


async def enrich_group_documents(database: Any, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return items

    section_map = await _related_lookup_map(
        database,
        "classes",
        list({str(item.get("section_id")) for item in items if item.get("section_id")}),
    )
    batch_map = await _related_lookup_map(
        database,
        "batches",
        list({str(section.get("batch_id")) for section in section_map.values() if section.get("batch_id")}),
    )
    semester_map = await _related_lookup_map(
        database,
        "semesters",
        list({str(section.get("semester_id")) for section in section_map.values() if section.get("semester_id")}),
    )
    program_ids = {str(section.get("program_id")) for section in section_map.values() if section.get("program_id")}
    program_ids.update(str(batch.get("program_id")) for batch in batch_map.values() if batch.get("program_id"))
    specialization_ids = {str(section.get("specialization_id")) for section in section_map.values() if section.get("specialization_id")}
    specialization_ids.update(str(batch.get("specialization_id")) for batch in batch_map.values() if batch.get("specialization_id"))
    program_map = await _related_lookup_map(database, "programs", list(program_ids))
    specialization_map = await _related_lookup_map(database, "specializations", list(specialization_ids))

    enriched: list[dict[str, Any]] = []
    for item in items:
        section = section_map.get(str(item.get("section_id") or ""))
        batch = batch_map.get(str(section.get("batch_id") or "")) if section else None
        semester = semester_map.get(str(section.get("semester_id") or "")) if section else None
        program = (
            program_map.get(str(section.get("program_id") or batch.get("program_id") or ""))
            if (section or batch)
            else None
        )
        specialization = (
            specialization_map.get(str(section.get("specialization_id") or batch.get("specialization_id") or ""))
            if (section or batch)
            else None
        )

        enriched.append(
            {
                **item,
                "section_name": item.get("section_name") or _document_name(section, "name"),
                "batch_id": item.get("batch_id") or (str(section.get("batch_id")) if section and section.get("batch_id") else None),
                "batch_name": item.get("batch_name") or _document_name(batch, "name"),
                "batch_code": item.get("batch_code") or _document_name(batch, "code"),
                "semester_id": item.get("semester_id") or (str(section.get("semester_id")) if section and section.get("semester_id") else None),
                "semester_label": item.get("semester_label") or _document_name(semester, "label"),
                "program_id": item.get("program_id")
                or (str(section.get("program_id")) if section and section.get("program_id") else None)
                or (str(batch.get("program_id")) if batch and batch.get("program_id") else None),
                "program_name": item.get("program_name") or _document_name(program, "program_name", "name"),
                "program_code": item.get("program_code") or _document_name(program, "program_code", "code"),
                "specialization_id": item.get("specialization_id")
                or (str(section.get("specialization_id")) if section and section.get("specialization_id") else None)
                or (str(batch.get("specialization_id")) if batch and batch.get("specialization_id") else None),
                "specialization_name": item.get("specialization_name")
                or _document_name(specialization, "specialization_name", "name"),
                "specialization_code": item.get("specialization_code")
                or _document_name(specialization, "specialization_code", "code"),
            }
        )
    return enriched
