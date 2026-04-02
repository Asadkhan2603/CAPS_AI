import argparse
import os
from pathlib import Path

from pymongo import MongoClient

ROLE_CODES = {
    "super_admin": "SUPER_ADMIN",
    "compliance_admin": "COMPLIANCE_ADMIN",
    "academic_admin": "ACADEMIC_ADMIN",
    "year_admin": "YEAR_ADMIN",
    "hod": "HOD",
    "dean": "DEAN",
}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed RBAC collections and backfill admin role links.")
    parser.add_argument("--apply", action="store_true", help="Persist changes. Default is dry-run.")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    load_env(root / "backend" / ".env")

    mongodb_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    mongodb_db = os.getenv("MONGODB_DB", "caps_ai")
    client = MongoClient(mongodb_url, serverSelectionTimeoutMS=5000)
    database = client[mongodb_db]

    roles = database["roles"]
    users = database["users"]

    print(f"Mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print(f"Database: {mongodb_db}")
    print("Expectations: default RBAC roles and permissions should already exist before backfill.")

    scanned = 0
    candidates = 0
    modified = 0

    role_lookup = {role["code"]: str(role["_id"]) for role in roles.find({})}
    for user in users.find({"role": "admin"}):
        scanned += 1
        admin_type = str(user.get("admin_type") or "").strip().lower()
        role_code = ROLE_CODES.get(admin_type)
        if not role_code:
            continue
        role_id = role_lookup.get(role_code)
        if not role_id:
            print(f"Skipping {user.get('email')}: missing role document for {role_code}")
            continue
        if user.get("role_id") == role_id and user.get("rbac_role_code") == role_code:
            continue

        candidates += 1
        print(
            f"[users] {user['_id']} email={user.get('email')} "
            f"admin_type={admin_type} -> role_code={role_code}"
        )
        if args.apply:
            result = users.update_one(
                {"_id": user["_id"]},
                {
                    "$set": {
                        "role_id": role_id,
                        "rbac_role_code": role_code,
                        "status": "active" if user.get("is_active", True) else "inactive",
                    }
                },
            )
            modified += int(result.modified_count)

    print(f"Summary: scanned={scanned} candidates={candidates} modified={modified}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
