from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from motor.motor_asyncio import AsyncIOMotorClient

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings


DEFAULT_UPDATED_AT_FIELDS = (
    "updated_at",
    "last_updated_at",
    "modified_at",
    "created_at",
)


async def build_inventory(limit_collections: int | None = None) -> dict:
    client = AsyncIOMotorClient(settings.mongodb_url)
    database = client[settings.mongodb_db]
    try:
        collection_names = await database.list_collection_names()
        collection_names.sort()
        if limit_collections is not None:
            collection_names = collection_names[:limit_collections]

        collections: list[dict] = []
        for name in collection_names:
            collection = database[name]
            count = await collection.count_documents({})
            indexes = await collection.index_information()

            last_updated = None
            for field_name in DEFAULT_UPDATED_AT_FIELDS:
                document = await collection.find_one(
                    {field_name: {"$exists": True}},
                    sort=[(field_name, -1)],
                    projection={field_name: 1},
                )
                if document and document.get(field_name) is not None:
                    value = document[field_name]
                    last_updated = value.isoformat() if hasattr(value, "isoformat") else str(value)
                    break

            collections.append(
                {
                    "collection": name,
                    "document_count": count,
                    "indexes": sorted(indexes.keys()),
                    "last_updated": last_updated,
                }
            )

        return {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "mongodb_url": settings.mongodb_url,
            "database": settings.mongodb_db,
            "collection_count": len(collections),
            "collections": collections,
        }
    finally:
        client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only MongoDB inventory report for cleanup audits.")
    parser.add_argument(
        "--output",
        default="new_docs/code/mongo_inventory_report.json",
        help="Path to the JSON output file.",
    )
    parser.add_argument(
        "--limit-collections",
        type=int,
        default=None,
        help="Optional cap on the number of collections to inspect.",
    )
    args = parser.parse_args()

    try:
        report = asyncio.run(build_inventory(limit_collections=args.limit_collections))
    except Exception as exc:
        report = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "mongodb_url": settings.mongodb_url,
            "database": settings.mongodb_db,
            "status": "connection_failed",
            "error": str(exc),
            "collections": [],
        }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Wrote Mongo inventory report to {output_path}")


if __name__ == "__main__":
    main()
