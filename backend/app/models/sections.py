from typing import Any, Dict

from app.core.schema_versions import CLASS_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity


def section_public(document: Dict[str, Any]) -> Dict[str, Any]:
    class_representatives = document.get("class_representatives", {}) or {}
    payload = {
        'id': str(document['_id']),
        'faculty_id': document.get('faculty_id'),
        'department_id': document.get('department_id'),
        'department_name': document.get('department_name'),
        'program_id': document.get('program_id'),
        'program_name': document.get('program_name'),
        'specialization_id': document.get('specialization_id'),
        'specialization_name': document.get('specialization_name'),
        'batch_id': document.get('batch_id'),
        'batch_name': document.get('batch_name'),
        'semester_id': document.get('semester_id'),
        'semester_label': document.get('semester_label'),
        'name': document.get('name', ''),
        'faculty_name': document.get('faculty_name'),
        'branch_name': document.get('branch_name'),
        'class_coordinator_user_id': document.get('class_coordinator_user_id'),
        'class_coordinator_name': document.get('class_coordinator_name'),
        'class_representatives': {
            'cr_1': {
                'user_id': (class_representatives.get('cr_1') or {}).get('user_id'),
                'full_name': (class_representatives.get('cr_1') or {}).get('full_name'),
            },
            'cr_2': {
                'user_id': (class_representatives.get('cr_2') or {}).get('user_id'),
                'full_name': (class_representatives.get('cr_2') or {}).get('full_name'),
            },
        },
        'mapping_locked': bool(document.get('mapping_locked')),
        'mapping_locked_by_user_id': document.get('mapping_locked_by_user_id'),
        'mapping_locked_by_name': document.get('mapping_locked_by_name'),
        'mapping_locked_by_email': document.get('mapping_locked_by_email'),
        'mapping_locked_at': document.get('mapping_locked_at'),
        'mapping_lock_reason': document.get('mapping_lock_reason'),
        'is_active': document.get('is_active', True),
        'deleted_at': document.get('deleted_at'),
        'deleted_by': document.get('deleted_by'),
        'created_at': document.get('created_at'),
        'schema_version': normalize_schema_version(
            document.get('schema_version'),
            default=CLASS_SCHEMA_VERSION,
        ),
    }
    return apply_public_identity(payload, kind="section", document=document, display_name=document.get("name"))


# Compatibility alias kept while internal callers finish moving from legacy
# class-named helpers to section terminology.
class_public = section_public
