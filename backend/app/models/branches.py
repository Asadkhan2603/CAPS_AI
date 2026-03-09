from typing import Any, Dict


def branch_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': str(document['_id']),
        'name': document.get('name', ''),
        'code': document.get('code', ''),
        'department_name': document.get('department_name'),
        'department_code': document.get('department_code'),
        'university_name': document.get('university_name'),
        'university_code': document.get('university_code'),
        'is_active': document.get('is_active', True),
        'deleted_at': document.get('deleted_at'),
        'deleted_by': document.get('deleted_by'),
        'created_at': document.get('created_at'),
    }
