from typing import Any, Dict


def class_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': str(document['_id']),
        'course_id': document.get('course_id'),
        'year_id': document.get('year_id'),
        'name': document.get('name', ''),
        'faculty_name': document.get('faculty_name'),
        'branch_name': document.get('branch_name'),
        'section': document.get('section'),
        'class_coordinator_user_id': document.get('class_coordinator_user_id'),
        'is_active': document.get('is_active', True),
        'created_at': document.get('created_at'),
    }
