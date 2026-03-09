from typing import Any, Dict


def course_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': str(document['_id']),
        'name': document.get('name', ''),
        'code': document.get('code', ''),
        'description': document.get('description'),
        'is_active': document.get('is_active', True),
        'deleted_at': document.get('deleted_at'),
        'deleted_by': document.get('deleted_by'),
        'created_at': document.get('created_at'),
    }
