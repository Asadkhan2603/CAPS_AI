from typing import Any, Dict

from app.core.schema_versions import SUBMISSION_SCHEMA_VERSION, normalize_schema_version
from app.services.public_ids import apply_public_identity


def _normalize_score(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return max(0.0, min(float(value), 1.0))
    if isinstance(value, str):
        normalized = value.strip().lower()
        quality_map = {
            "excellent": 1.0,
            "high": 0.9,
            "good": 0.75,
            "medium": 0.5,
            "moderate": 0.5,
            "low": 0.2,
            "poor": 0.1,
        }
        if normalized in quality_map:
            return quality_map[normalized]
        try:
            return max(0.0, min(float(normalized), 1.0))
        except ValueError:
            return None
    return None


def submission_public(document: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
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
        'schema_version': normalize_schema_version(document.get('schema_version'), default=SUBMISSION_SCHEMA_VERSION),
        'similarity_score': document.get('similarity_score'),
        'extracted_text': document.get('extracted_text'),
        'extraction_quality': _normalize_score(document.get('extraction_quality')),
        'ocr_attempted': document.get('ocr_attempted'),
        'ocr_provider': document.get('ocr_provider'),
        'ocr_chars_added': document.get('ocr_chars_added'),
        'page_count': document.get('page_count'),
        'extraction_confidence': _normalize_score(document.get('extraction_confidence')),
        'low_text_reason': document.get('low_text_reason'),
        'ocr_result_state': document.get('ocr_result_state'),
        'ocr_retry_count': document.get('ocr_retry_count'),
        'ocr_timeout_seconds': document.get('ocr_timeout_seconds'),
        'ocr_error': document.get('ocr_error'),
        'ocr_retry_guidance': document.get('ocr_retry_guidance'),
        'created_at': document.get('created_at'),
    }
    return apply_public_identity(payload, kind="submission", document=document, display_name=document.get("original_filename"))
