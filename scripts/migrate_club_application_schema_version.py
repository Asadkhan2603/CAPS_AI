import argparse
import os
from pathlib import Path

from pymongo import MongoClient

CLUB_APPLICATION_SCHEMA_VERSION = 1


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def normalize_schema_version(raw_value) -> int | None:
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 1 else None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Backfill schema_version on club_applications documents."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Persist changes. Without this flag the script runs in dry-run mode.",
    )
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    load_env(root / "backend" / ".env")

    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db = os.getenv("MONGODB_DB", "caps_ai")

    client = MongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
    database = client[mongodb_db]
    club_applications = database["club_applications"]

    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Database: {mongodb_db}")

    scanned = 0
    candidates = 0
    modified = 0

    for document in club_applications.find({}):
        scanned += 1
        current = normalize_schema_version(document.get("schema_version"))
        if current == CLUB_APPLICATION_SCHEMA_VERSION:
            continue

        candidates += 1
        print(
            f"[club_applications] {document['_id']}: "
            f"club_id={document.get('club_id')} "
            f"student_user_id={document.get('student_user_id')} "
            f"schema_version={document.get('schema_version')} -> {CLUB_APPLICATION_SCHEMA_VERSION}"
        )

        if args.apply:
            result = club_applications.update_one(
                {"_id": document["_id"]},
                {"$set": {"schema_version": CLUB_APPLICATION_SCHEMA_VERSION}},
            )
            modified += int(result.modified_count)

    print(
        f"Summary: scanned={scanned} candidates={candidates} modified={modified} "
        f"target_version={CLUB_APPLICATION_SCHEMA_VERSION}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
