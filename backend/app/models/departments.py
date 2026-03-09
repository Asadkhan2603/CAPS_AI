from typing import Any, Dict


def department_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': str(document['_id']),
        'name': document.get('name', ''),
        'code': document.get('code', ''),
        'faculty_id': document.get('faculty_id'),
        'university_name': document.get('university_name'),
        'university_code': document.get('university_code'),
        'is_active': document.get('is_active', True),
        'deleted_at': document.get('deleted_at'),
        'deleted_by': document.get('deleted_by'),
        'created_at': document.get('created_at'),
    }
