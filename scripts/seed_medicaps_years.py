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


def year_label(year_number: int) -> str:
    if year_number == 1:
        return '1st Year'
    if year_number == 2:
        return '2nd Year'
    if year_number == 3:
        return '3rd Year'
    return f'{year_number}th Year'


def duration_for_course(code: str, name: str) -> int:
    code_u = code.upper()
    name_u = name.upper()

    # 5-year integrated programs
    if code_u in {'BTECH-INT-CSE', 'BA-LLB-H', 'BBA-LLB-H'}:
        return 5

    # 4-year UG technical/professional programs
    if code_u.startswith('BTECH') or code_u in {'BPHARM', 'BSC-H', 'BSC-H-AHS'}:
        return 4

    # 3-year UG programs
    if code_u in {'BCA', 'BBA', 'BBA-BA', 'BCOM', 'BCOM-GF', 'BJMC', 'LLB-H'}:
        return 3

    # 2-year PG programs
    if code_u.startswith('MTECH') or code_u.startswith('MBA') or code_u in {'MCA', 'MPHARM', 'LLM', 'MSC', 'MA-ENGLISH'}:
        return 2

    # fallback by naming convention
    if name_u.startswith('B.') or name_u.startswith('B '):
        return 3
    if name_u.startswith('M.') or name_u.startswith('M '):
        return 2

    return 4


ROOT = Path(__file__).resolve().parents[1]
load_env(ROOT / 'backend' / '.env')

MONGODB_URL = os.getenv('MONGODB_URL', 'mongodb://localhost:27017')
MONGODB_DB = os.getenv('MONGODB_DB', 'caps_ai')


def main() -> None:
    client = MongoClient(MONGODB_URL)
    db = client[MONGODB_DB]
    courses_collection = db['courses']
    years_collection = db['years']

    active_courses = list(courses_collection.find({'is_active': True}))
    now = datetime.now(timezone.utc)

    inserted = 0
    updated = 0

    for course in active_courses:
        course_id = str(course['_id'])
        code = str(course.get('code') or '')
        name = str(course.get('name') or '')
        duration = duration_for_course(code, name)

        for year_number in range(1, duration + 1):
            label = year_label(year_number)
            existing = years_collection.find_one({'course_id': course_id, 'year_number': year_number})
            if existing:
                years_collection.update_one(
                    {'_id': existing['_id']},
                    {
                        '$set': {
                            'label': label,
                            'is_active': True,
                        }
                    },
                )
                updated += 1
            else:
                years_collection.insert_one(
                    {
                        'course_id': course_id,
                        'year_number': year_number,
                        'label': label,
                        'is_active': True,
                        'created_at': now,
                    }
                )
                inserted += 1

    total_years = years_collection.count_documents({})
    print(f'Years seeded successfully. inserted={inserted}, updated={updated}, total={total_years}, active_courses={len(active_courses)}')


if __name__ == '__main__':
    main()
