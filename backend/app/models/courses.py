from typing import Any, Dict


def course_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': str(document['_id']),
        'name': document.get('name', ''),
        'code': document.get('code', ''),
        'description': document.get('description'),
        'is_active': document.get('is_active', True),
        'created_at': document.get('created_at'),
    }
