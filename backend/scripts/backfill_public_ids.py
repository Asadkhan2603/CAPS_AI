from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path
import sys
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.database import db
from app.services.public_ids import build_public_id


COLLECTION_KIND_MAP: dict[str, str] = {
    "universities": "university",
    "faculties": "faculty",
    "departments": "department",
    "programs": "program",
    "specializations": "specialization",
    "batches": "batch",
    "semesters": "semester",
    "classes": "section",
    "groups": "group",
    "subjects": "subject",
    "students": "student",
    "assignments": "assignment",
    "submissions": "submission",
    "evaluations": "evaluation",
    "course_offerings": "course_offering",
    "class_slots": "class_slot",
    "clubs": "club",
    "club_members": "club_member",
    "club_applications": "club_application",
    "club_events": "club_event",
    "notifications": "notification",
    "review_tickets": "review_ticket",
    "audit_logs": "audit_log",
    "admin_action_reviews": "admin_action_review",
    "user_sessions": "user_session",
    "attendance_records": "attendance_record",
    "event_registrations": "event_registration",
}


async def _backfill_collection(
    collection_name: str,
    kind: str,
    *,
    dry_run: bool,
) -> dict[str, Any]:
    collection = getattr(db, collection_name, None)
    if collection is None:
        return {
            "collection": collection_name,
            "kind": kind,
            "status": "missing",
            "scanned": 0,
            "updated": 0,
            "skipped": 0,
            "examples": [],
        }

    scanned = 0
    updated = 0
    skipped = 0
    examples: list[dict[str, Any]] = []

    async for document in collection.find({}):
        scanned += 1
        expected_public_id = build_public_id(kind, document, prefer_existing=False)
        current_public_id = document.get("public_id")

        if not expected_public_id or current_public_id == expected_public_id:
            skipped += 1
            continue

        if len(examples) < 5:
            examples.append(
                {
                    "id": str(document.get("_id")),
                    "from": current_public_id,
                    "to": expected_public_id,
                }
            )

        if not dry_run:
            await collection.update_one(
                {"_id": document["_id"]},
                {"$set": {"public_id": expected_public_id}},
            )
        updated += 1

    return {
        "collection": collection_name,
        "kind": kind,
        "status": "ok",
        "scanned": scanned,
        "updated": updated,
        "skipped": skipped,
        "examples": examples,
    }


async def run_backfill(*, collections: list[str] | None = None, dry_run: bool = False) -> dict[str, Any]:
    selected_collections = collections or list(COLLECTION_KIND_MAP.keys())
    invalid = [name for name in selected_collections if name not in COLLECTION_KIND_MAP]
    if invalid:
        raise ValueError(f"Unsupported collections: {', '.join(sorted(invalid))}")

    results: list[dict[str, Any]] = []
    for collection_name in selected_collections:
        result = await _backfill_collection(
            collection_name,
            COLLECTION_KIND_MAP[collection_name],
            dry_run=dry_run,
        )
        results.append(result)

    return {
        "dry_run": dry_run,
        "collections": results,
        "summary": {
            "scanned": sum(item["scanned"] for item in results if item["status"] == "ok"),
            "updated": sum(item["updated"] for item in results if item["status"] == "ok"),
            "skipped": sum(item["skipped"] for item in results if item["status"] == "ok"),
            "missing_collections": [item["collection"] for item in results if item["status"] == "missing"],
        },
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill short human-readable public_id values across Mongo collections.")
    parser.add_argument(
        "--collections",
        nargs="*",
        default=None,
        help="Optional collection names to backfill. Defaults to all supported collections.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without updating Mongo records.")
    args = parser.parse_args()

    result = await run_backfill(collections=args.collections, dry_run=bool(args.dry_run))
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
