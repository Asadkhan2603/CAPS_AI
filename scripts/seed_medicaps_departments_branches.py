import os
import re
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


def slug(value: str) -> str:
    cleaned = re.sub(r'[^a-zA-Z0-9]+', '-', value.strip().lower()).strip('-')
    return re.sub(r'-{2,}', '-', cleaned)


ROOT = Path(__file__).resolve().parents[1]
load_env(ROOT / 'backend' / '.env')

MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
MONGODB_DB = os.getenv('MONGODB_DB', 'caps_ai')
UNIVERSITY_NAME = 'Medi-Caps University'
UNIVERSITY_CODE = 'MEDICAPS'


DEPARTMENT_BRANCHES = [
    (
        'Faculty of Engineering',
        [
            'Computer Science Engineering',
            'Artificial Intelligence',
            'Data Science',
            'Computer Science & Business Systems',
            'Information Technology',
            'Robotics & Automation',
            'Automobile Engineering',
            'Civil Engineering',
            'Electrical Engineering',
            'Mechanical Engineering',
            'Electronics & Communication Engineering',
            'Power Electronics',
            'Power Systems',
            'Construction Technology & Management',
            'VLSI',
            'Mechatronics',
            'CAD/CAM/CAE',
            'Industrial & Production Engineering',
            'Nanotechnology',
        ],
    ),
    (
        'Faculty of Arts, Humanities & Social Sciences',
        [
            'Journalism & Mass Communication',
            'English',
        ],
    ),
    (
        'Faculty of Pharmacy',
        [
            'Pharmaceutics',
        ],
    ),
    (
        'Faculty of Management',
        [
            'Finance',
            'Foreign Trade',
            'Human Resource',
            'Marketing Management',
            'Digital Marketing',
            'Logistics & Supply Chain Management',
            'Business Analytics',
        ],
    ),
    (
        'Faculty of Law',
        [
            'Bachelor of Arts and Legislative Law',
            'Bachelor of Business Administration and Legislative Law',
            'Bachelor of Legislative Law',
            'Master of Legislative Law',
        ],
    ),
    (
        'Faculty of Commerce',
        [
            'Accounting & Taxation',
            'Banking & Finance',
            'Computer Applications',
            'Global Finance',
        ],
    ),
    (
        'Faculty of Science',
        [
            'Agriculture',
            'Forensic Science',
            'Biotechnology',
            'Computer Science',
            'Physics',
            'Physics (Research)',
            'Chemistry',
            'Chemistry (Research)',
            'Mathematics',
            'Agriculture (Agronomy)',
        ],
    ),
    (
        'Faculty of Allied Health Sciences',
        [
            'Anaesthesia & Operation Theatre Technology',
            'Medical Laboratory Technology',
            'Cardiovascular Technology',
            'Respiratory Technology',
        ],
    ),
]


def main() -> None:
    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_DB]
    departments_collection = db['departments']
    branches_collection = db['branches']

    now = datetime.now(timezone.utc)
    department_inserted = 0
    department_updated = 0
    branch_inserted = 0
    branch_updated = 0

    desired_department_codes: set[str] = set()
    desired_branch_codes: set[str] = set()

    for department_name, branches in DEPARTMENT_BRANCHES:
        department_code = f'DEPT-{slug(department_name).upper()}'
        desired_department_codes.add(department_code)

        department_doc = {
            'name': department_name,
            'code': department_code,
            'university_name': UNIVERSITY_NAME,
            'university_code': UNIVERSITY_CODE,
            'is_active': True,
            'updated_at': now,
        }
        existing_department = departments_collection.find_one({'code': department_code})
        if existing_department:
            departments_collection.update_one({'_id': existing_department['_id']}, {'$set': department_doc})
            department_updated += 1
        else:
            department_doc['created_at'] = now
            departments_collection.insert_one(department_doc)
            department_inserted += 1

        for branch_name in branches:
            branch_code = f'BR-{slug(department_name)}-{slug(branch_name)}'.upper()
            desired_branch_codes.add(branch_code)
            branch_doc = {
                'name': branch_name,
                'code': branch_code,
                'department_name': department_name,
                'department_code': department_code,
                'university_name': UNIVERSITY_NAME,
                'university_code': UNIVERSITY_CODE,
                'is_active': True,
                'updated_at': now,
            }
            existing_branch = branches_collection.find_one({'code': branch_code})
            if existing_branch:
                branches_collection.update_one({'_id': existing_branch['_id']}, {'$set': branch_doc})
                branch_updated += 1
            else:
                branch_doc['created_at'] = now
                branches_collection.insert_one(branch_doc)
                branch_inserted += 1

    department_deactivated = departments_collection.update_many(
        {'code': {'$nin': list(desired_department_codes)}},
        {'$set': {'is_active': False, 'updated_at': now}},
    ).modified_count

    branch_deactivated = branches_collection.update_many(
        {'code': {'$nin': list(desired_branch_codes)}},
        {'$set': {'is_active': False, 'updated_at': now}},
    ).modified_count

    print(
        'Departments/Branches synced successfully. '
        f'department_inserted={department_inserted}, department_updated={department_updated}, '
        f'department_deactivated={department_deactivated}, '
        f'branch_inserted={branch_inserted}, branch_updated={branch_updated}, '
        f'branch_deactivated={branch_deactivated}, '
        f'department_total={departments_collection.count_documents({})}, '
        f'branch_total={branches_collection.count_documents({})}'
    )


if __name__ == '__main__':
    main()
