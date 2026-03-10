from typing import Any, Dict


def submission_public(document: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'id': str(document['_id']),
        'assignment_id': document.get('assignment_id'),
        'student_user_id': document.get('student_user_id'),
        'original_filename': document.get('original_filename', ''),
        'stored_filename': document.get('stored_filename', ''),
        'file_mime_type': document.get('file_mime_type'),
        'file_size_bytes': document.get('file_size_bytes', 0),
        'notes': document.get('notes'),
        'status': document.get('status', 'submitted'),
        'ai_status': document.get('ai_status', 'pending'),
        'ai_score': document.get('ai_score'),
        'ai_feedback': document.get('ai_feedback'),
        'ai_provider': document.get('ai_provider'),
        'ai_error': document.get('ai_error'),
        'ai_prompt_version': document.get('ai_prompt_version'),
        'ai_runtime_snapshot': document.get('ai_runtime_snapshot'),
        'similarity_score': document.get('similarity_score'),
        'extracted_text': document.get('extracted_text'),
        'created_at': document.get('created_at'),
    }
