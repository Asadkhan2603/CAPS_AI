from typing import Any, Dict


def year_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': str(document['_id']),
        'course_id': document.get('course_id'),
        'year_number': document.get('year_number', 1),
        'label': document.get('label', ''),
        'is_active': document.get('is_active', True),
        'created_at': document.get('created_at'),
    }
