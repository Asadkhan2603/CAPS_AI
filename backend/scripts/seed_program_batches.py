from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.v1.endpoints.programs import _seed_all_program_batches
from app.core.database import db


async def main() -> None:
    summary = await _seed_all_program_batches()
    counts = {
        "universities": await db.universities.count_documents({}),
        "faculties": await db.faculties.count_documents({}),
        "departments": await db.departments.count_documents({}),
        "programs": await db.programs.count_documents({}),
        "specializations": await db.specializations.count_documents({}),
        "batches": await db.batches.count_documents({}),
        "semesters": await db.semesters.count_documents({}),
        "classes": await db.classes.count_documents({}),
        "groups": await db.groups.count_documents({}),
        "subjects": await db.subjects.count_documents({}),
        "course_offerings": await db.course_offerings.count_documents({}),
        "class_slots": await db.class_slots.count_documents({}),
    }
    print(json.dumps({"seed_summary": summary, "counts": counts}, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
