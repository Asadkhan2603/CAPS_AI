import os
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


ROOT = Path(__file__).resolve().parents[1]
load_env(ROOT / 'backend' / '.env')

MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
MONGODB_DB = os.getenv('MONGODB_DB', 'caps_ai')

# Catalog aligned to user-provided Medi-Caps offering list screenshots.
COURSES = [
    # Faculty of Engineering
    ('BTECH', 'B.Tech', 'Faculty: Engineering | Tracks: Computer Science Engineering (AI, Data Science, CCBS), Information Technology, Robotics & Automation, Automobile Engineering, Civil Engineering, Electrical Engineering, Mechanical Engineering, Electronics & Communication Engineering'),
    ('BTECH-LE', 'B.Tech - Lateral Entry', 'Faculty: Engineering | Lateral-entry B.Tech for diploma graduates.'),
    ('BTECH-INT-CSE', 'B.Tech + M.Tech (Integrated) - Computer Science Engineering', 'Faculty: Engineering | Integrated dual-degree CSE program.'),
    ('MTECH', 'M.Tech', 'Faculty: Engineering | Tracks: Computer Science Engineering, Civil Engineering, Electronics & Communication, Electrical Engineering, Information Technology, Mechanical Engineering, Nanotechnology'),
    ('BCA', 'BCA', 'Faculty: Engineering | Bachelor of Computer Applications'),
    ('MCA', 'MCA', 'Faculty: Engineering | Master of Computer Applications'),

    # Faculty of Arts, Humanities & Social Sciences
    ('BJMC', 'BJMC', 'Faculty: Arts, Humanities & Social Sciences | Journalism & Mass Communication'),
    ('MA-ENGLISH', 'M.A. - English', 'Faculty: Arts, Humanities & Social Sciences | Master of Arts in English'),

    # Faculty of Pharmacy
    ('BPHARM', 'B.Pharm', 'Faculty: Pharmacy | Bachelor of Pharmacy'),
    ('MPHARM', 'M.Pharm', 'Faculty: Pharmacy | Pharmaceutics'),

    # Faculty of Management
    ('BBA', 'BBA', 'Faculty: Management | Tracks: Finance, Foreign Trade, Human Resource, Marketing Management, Digital Marketing'),
    ('BBA-BA', 'BBA (Business Analytics)', 'Faculty: Management | Business Analytics program'),
    ('MBA-GLOBAL', 'MBA (Global)', 'Faculty: Management | Tracks: Finance, Foreign Trade, Human Resource, Marketing, Logistics & Supply Chain Management'),
    ('MBA-BA', 'MBA (Business Analytics)', 'Faculty: Management | Business Analytics specialization'),
    ('MBA', 'MBA', 'Faculty: Management | Master of Business Administration'),

    # Faculty of Law
    ('BA-LLB-H', 'B.A. LL.B. (Hons)', 'Faculty: Law | Bachelor of Arts and Legislative Law'),
    ('BBA-LLB-H', 'B.B.A. LL.B. (Hons)', 'Faculty: Law | Bachelor of Business Administration and Legislative Law'),
    ('LLB-H', 'LL.B. (Hons)', 'Faculty: Law | Bachelor of Legislative Law'),
    ('LLM', 'LL.M.', 'Faculty: Law | Master of Legislative Law'),

    # Faculty of Commerce
    ('BCOM', 'B.Com.', 'Faculty: Commerce | Tracks: Accounting & Taxation, Banking & Finance, Computer Applications'),
    ('BCOM-GF', 'B.Com. - Global Finance', 'Faculty: Commerce | Global finance-focused commerce program'),

    # Faculty of Science
    ('BSC-H', 'B.Sc. (Hons)', 'Faculty: Science | Tracks: Agriculture, Forensic Science, Biotechnology, Computer Science'),
    ('MSC', 'M.Sc.', 'Faculty: Science | Tracks: Physics, Physics (Research), Chemistry, Chemistry (Research), Mathematics, Forensic Science, Agriculture (Agronomy)'),

    # Faculty of Allied Health Sciences
    ('BSC-H-AHS', 'B.Sc. (Hons) - Allied Health Sciences', 'Faculty: Allied Health Sciences | Tracks: Anaesthesia & Operation Theatre Technology, Medical Laboratory Technology, Cardiovascular Technology, Respiratory Technology'),
]


def main() -> None:
    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_DB]
    collection = db['courses']

    inserted = 0
    updated = 0
    deactivated = 0
    now = datetime.now(timezone.utc)

    desired_codes = {code for code, _, _ in COURSES}

    for code, name, description in COURSES:
        existing = collection.find_one({'code': code})
        if existing:
            collection.update_one(
                {'_id': existing['_id']},
                {
                    '$set': {
                        'name': name,
                        'description': description,
                        'is_active': True,
                    }
                },
            )
            updated += 1
        else:
            collection.insert_one(
                {
                    'name': name,
                    'code': code,
                    'description': description,
                    'is_active': True,
                    'created_at': now,
                }
            )
            inserted += 1

    deactivate_result = collection.update_many(
        {'code': {'$nin': list(desired_codes)}},
        {'$set': {'is_active': False}}
    )
    deactivated = deactivate_result.modified_count

    total = collection.count_documents({})
    active_total = collection.count_documents({'is_active': True})
    print(
        'Courses synced successfully. '
        f'inserted={inserted}, updated={updated}, deactivated={deactivated}, '
        f'active_total={active_total}, total={total}'
    )


if __name__ == '__main__':
    main()
