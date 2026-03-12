from typing import Any, Dict


def class_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': str(document['_id']),
        'faculty_id': document.get('faculty_id'),
        'department_id': document.get('department_id'),
        'program_id': document.get('program_id'),
        'specialization_id': document.get('specialization_id'),
        'batch_id': document.get('batch_id'),
        'semester_id': document.get('semester_id'),
        'name': document.get('name', ''),
        'faculty_name': document.get('faculty_name'),
        'branch_name': document.get('branch_name'),
        'class_coordinator_user_id': document.get('class_coordinator_user_id'),
        'is_active': document.get('is_active', True),
        'deleted_at': document.get('deleted_at'),
        'deleted_by': document.get('deleted_by'),
        'created_at': document.get('created_at'),
    }
