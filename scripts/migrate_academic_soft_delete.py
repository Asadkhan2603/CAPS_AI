import argparse
import os
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient


ACADEMIC_COLLECTIONS = (
    "faculties",
    "departments",
    "programs",
    "specializations",
    "batches",
    "semesters",
    "courses",
    "branches",
    "years",
    "classes",
)


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def canonical_update(document: dict) -> tuple[dict, dict, list[str]]:
    set_fields: dict = {}
    unset_fields: dict = {}
    notes: list[str] = []

    legacy_deleted = bool(document.get("is_deleted"))
    current_is_active = document.get("is_active")

    if current_is_active is None:
        set_fields["is_active"] = not legacy_deleted
        notes.append("set missing is_active")

    if legacy_deleted:
        if document.get("is_active") is not False:
            set_fields["is_active"] = False
            notes.append("forced is_active=false for deleted record")
        if document.get("deleted_at") is None:
            set_fields["deleted_at"] = (
                document.get("updated_at")
                or document.get("created_at")
                or datetime.now(timezone.utc)
            )
            notes.append("backfilled deleted_at")

    if "is_deleted" in document:
        unset_fields["is_deleted"] = ""
        notes.append("removed legacy is_deleted")

    if document.get("is_active") is True and document.get("deleted_at") is not None:
        notes.append("anomaly: active record has deleted_at")

    return set_fields, unset_fields, notes


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Normalize academic setup soft-delete metadata to is_active + deleted_at + deleted_by."
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

    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Database: {mongodb_db}")

    total_examined = 0
    total_candidates = 0
    total_modified = 0

    for collection_name in ACADEMIC_COLLECTIONS:
        collection = database[collection_name]
        examined = 0
        candidates = 0
        modified = 0
        anomalies = 0

        for document in collection.find({}):
            examined += 1
            set_fields, unset_fields, notes = canonical_update(document)
            actionable_notes = [note for note in notes if not note.startswith("anomaly:")]
            anomaly_notes = [note for note in notes if note.startswith("anomaly:")]
            if anomaly_notes:
                anomalies += 1

            if not set_fields and not unset_fields:
                continue

            candidates += 1
            if args.apply:
                update = {}
                if set_fields:
                    update["$set"] = set_fields
                if unset_fields:
                    update["$unset"] = unset_fields
                result = collection.update_one({"_id": document["_id"]}, update)
                modified += int(result.modified_count)

            if actionable_notes or anomaly_notes:
                print(
                    f"[{collection_name}] {document['_id']}: "
                    + ", ".join([*actionable_notes, *anomaly_notes])
                )

        total_examined += examined
        total_candidates += candidates
        total_modified += modified

        print(
            f"{collection_name}: examined={examined} candidates={candidates} "
            f"modified={modified} anomalies={anomalies}"
        )

    print(
        f"Summary: examined={total_examined} candidates={total_candidates} modified={total_modified}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
