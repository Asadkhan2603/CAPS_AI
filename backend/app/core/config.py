import os
from dataclasses import dataclass, field
from typing import List

from dotenv import load_dotenv

load_dotenv(override=True)


def _as_float(value: str, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _as_int(value: str, fallback: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _as_bool(value: str | None, fallback: bool) -> bool:
    if value is None:
        return fallback
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    return fallback


def _merge_cors_origins(raw_origins: str) -> List[str]:
    configured = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
    # Always keep common local frontend origins enabled to avoid dev CORS lockouts.
    defaults = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    ordered = []
    for origin in [*configured, *defaults]:
        if origin not in ordered:
            ordered.append(origin)
    return ordered


def _as_csv_list(raw_value: str | None) -> List[str]:
    if not raw_value:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


@dataclass
class Settings:
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development").lower())
    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "CAPS AI API"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "0.1.0"))
    api_prefix: str = field(default_factory=lambda: os.getenv("API_PREFIX", "/api/v1"))
    mongodb_url: str = field(default_factory=lambda: os.getenv("MONGODB_URL", "mongodb://localhost:27017"))
    mongodb_db: str = field(default_factory=lambda: os.getenv("MONGODB_DB", "caps_ai"))
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", "change_me"))
    jwt_algorithm: str = field(default_factory=lambda: os.getenv("JWT_ALGORITHM", "HS256"))
    access_token_expire_minutes: int = field(
        default_factory=lambda: _as_int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"), 60)
    )
    refresh_token_expire_days: int = field(
        default_factory=lambda: _as_int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"), 7)
    )
    account_lockout_max_attempts: int = field(
        default_factory=lambda: _as_int(os.getenv("ACCOUNT_LOCKOUT_MAX_ATTEMPTS", "5"), 5)
    )
    account_lockout_window_minutes: int = field(
        default_factory=lambda: _as_int(os.getenv("ACCOUNT_LOCKOUT_WINDOW_MINUTES", "15"), 15)
    )
    account_lockout_duration_minutes: int = field(
        default_factory=lambda: _as_int(os.getenv("ACCOUNT_LOCKOUT_DURATION_MINUTES", "30"), 30)
    )
    auth_registration_policy: str = field(
        default_factory=lambda: os.getenv("AUTH_REGISTRATION_POLICY", "single_admin_open").strip().lower()
    )
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    openai_timeout_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("OPENAI_TIMEOUT_SECONDS", "20"), 20)
    )
    openai_max_output_tokens: int = field(
        default_factory=lambda: _as_int(os.getenv("OPENAI_MAX_OUTPUT_TOKENS", "400"), 400)
    )
    similarity_threshold: float = field(
        default_factory=lambda: _as_float(os.getenv("SIMILARITY_THRESHOLD", "0.8"), 0.8)
    )
    similarity_prefilter_enabled: bool = field(
        default_factory=lambda: _as_bool(os.getenv("SIMILARITY_PREFILTER_ENABLED"), True)
    )
    similarity_retrieval_cache_enabled: bool = field(
        default_factory=lambda: _as_bool(os.getenv("SIMILARITY_RETRIEVAL_CACHE_ENABLED"), True)
    )
    similarity_retrieval_terms_limit: int = field(
        default_factory=lambda: _as_int(os.getenv("SIMILARITY_RETRIEVAL_TERMS_LIMIT", "96"), 96)
    )
    similarity_prefilter_top_k: int = field(
        default_factory=lambda: _as_int(os.getenv("SIMILARITY_PREFILTER_TOP_K", "250"), 250)
    )
    similarity_prefilter_min_shared_tokens: int = field(
        default_factory=lambda: _as_int(os.getenv("SIMILARITY_PREFILTER_MIN_SHARED_TOKENS", "1"), 1)
    )
    similarity_min_non_prompt_shared_tokens: int = field(
        default_factory=lambda: _as_int(os.getenv("SIMILARITY_MIN_NON_PROMPT_SHARED_TOKENS", "2"), 2)
    )
    similarity_min_effective_excerpt_overlap: float = field(
        default_factory=lambda: _as_float(os.getenv("SIMILARITY_MIN_EFFECTIVE_EXCERPT_OVERLAP", "0.18"), 0.18)
    )
    similarity_min_token_count: int = field(
        default_factory=lambda: _as_int(os.getenv("SIMILARITY_MIN_TOKEN_COUNT", "10"), 10)
    )
    similarity_min_extraction_confidence: float = field(
        default_factory=lambda: _as_float(os.getenv("SIMILARITY_MIN_EXTRACTION_CONFIDENCE", "0.5"), 0.5)
    )
    similarity_borderline_extraction_confidence: float = field(
        default_factory=lambda: _as_float(os.getenv("SIMILARITY_BORDERLINE_EXTRACTION_CONFIDENCE", "0.25"), 0.25)
    )
    similarity_prompt_overlap_assist_threshold: float = field(
        default_factory=lambda: _as_float(os.getenv("SIMILARITY_PROMPT_OVERLAP_ASSIST_THRESHOLD", "0.6"), 0.6)
    )
    similarity_generic_overlap_assist_threshold: float = field(
        default_factory=lambda: _as_float(os.getenv("SIMILARITY_GENERIC_OVERLAP_ASSIST_THRESHOLD", "0.55"), 0.55)
    )
    similarity_boilerplate_token_ceiling: int = field(
        default_factory=lambda: _as_int(os.getenv("SIMILARITY_BOILERPLATE_TOKEN_CEILING", "24"), 24)
    )
    similarity_sync_inline_candidate_limit: int = field(
        default_factory=lambda: _as_int(os.getenv("SIMILARITY_SYNC_INLINE_CANDIDATE_LIMIT", "250"), 250)
    )
    semantic_shadow_enabled: bool = field(
        default_factory=lambda: _as_bool(os.getenv("SEMANTIC_SHADOW_ENABLED"), True)
    )
    semantic_shadow_capture_top_n: int = field(
        default_factory=lambda: _as_int(os.getenv("SEMANTIC_SHADOW_CAPTURE_TOP_N", "10"), 10)
    )
    semantic_shadow_min_lexical_score: float = field(
        default_factory=lambda: _as_float(os.getenv("SEMANTIC_SHADOW_MIN_LEXICAL_SCORE", "0.35"), 0.35)
    )
    semantic_shadow_calibration_exact_min: float = field(
        default_factory=lambda: _as_float(os.getenv("SEMANTIC_SHADOW_CALIBRATION_EXACT_MIN", "0.95"), 0.95)
    )
    semantic_shadow_calibration_paraphrase_advantage_min: float = field(
        default_factory=lambda: _as_float(
            os.getenv("SEMANTIC_SHADOW_CALIBRATION_PARAPHRASE_ADVANTAGE_MIN", "0.15"),
            0.15,
        )
    )
    semantic_shadow_calibration_mixed_language_advantage_min: float = field(
        default_factory=lambda: _as_float(
            os.getenv("SEMANTIC_SHADOW_CALIBRATION_MIXED_LANGUAGE_ADVANTAGE_MIN", "0.15"),
            0.15,
        )
    )
    semantic_shadow_calibration_unrelated_max: float = field(
        default_factory=lambda: _as_float(os.getenv("SEMANTIC_SHADOW_CALIBRATION_UNRELATED_MAX", "0.1"), 0.1)
    )
    semantic_same_assignment_drift_threshold: float = field(
        default_factory=lambda: _as_float(os.getenv("SEMANTIC_SAME_ASSIGNMENT_DRIFT_THRESHOLD", "0.15"), 0.15)
    )
    semantic_cross_assignment_drift_threshold: float = field(
        default_factory=lambda: _as_float(os.getenv("SEMANTIC_CROSS_ASSIGNMENT_DRIFT_THRESHOLD", "0.22"), 0.22)
    )
    semantic_same_assignment_min_score: float = field(
        default_factory=lambda: _as_float(os.getenv("SEMANTIC_SAME_ASSIGNMENT_MIN_SCORE", "0.7"), 0.7)
    )
    semantic_cross_assignment_min_score: float = field(
        default_factory=lambda: _as_float(os.getenv("SEMANTIC_CROSS_ASSIGNMENT_MIN_SCORE", "0.8"), 0.8)
    )
    semantic_same_assignment_min_sample_size: int = field(
        default_factory=lambda: _as_int(os.getenv("SEMANTIC_SAME_ASSIGNMENT_MIN_SAMPLE_SIZE", "5"), 5)
    )
    semantic_cross_assignment_min_sample_size: int = field(
        default_factory=lambda: _as_int(os.getenv("SEMANTIC_CROSS_ASSIGNMENT_MIN_SAMPLE_SIZE", "8"), 8)
    )
    semantic_multilingual_min_sample_size: int = field(
        default_factory=lambda: _as_int(os.getenv("SEMANTIC_MULTILINGUAL_MIN_SAMPLE_SIZE", "4"), 4)
    )
    fairness_gate_max_concise_delta: float = field(
        default_factory=lambda: _as_float(os.getenv("FAIRNESS_GATE_MAX_CONCISE_DELTA", "1.5"), 1.5)
    )
    fairness_gate_max_formula_delta: float = field(
        default_factory=lambda: _as_float(os.getenv("FAIRNESS_GATE_MAX_FORMULA_DELTA", "1.25"), 1.25)
    )
    fairness_gate_max_mixed_language_eval_delta: float = field(
        default_factory=lambda: _as_float(os.getenv("FAIRNESS_GATE_MAX_MIXED_LANGUAGE_EVAL_DELTA", "1.0"), 1.0)
    )
    fairness_gate_max_unicode_eval_delta: float = field(
        default_factory=lambda: _as_float(os.getenv("FAIRNESS_GATE_MAX_UNICODE_EVAL_DELTA", "1.25"), 1.25)
    )
    fairness_gate_max_short_answer_delta: float = field(
        default_factory=lambda: _as_float(os.getenv("FAIRNESS_GATE_MAX_SHORT_ANSWER_DELTA", "1.1"), 1.1)
    )
    fairness_gate_max_rubric_shape_delta: float = field(
        default_factory=lambda: _as_float(os.getenv("FAIRNESS_GATE_MAX_RUBRIC_SHAPE_DELTA", "1.25"), 1.25)
    )
    fairness_gate_max_risk_context_leak_delta: float = field(
        default_factory=lambda: _as_float(os.getenv("FAIRNESS_GATE_MAX_RISK_CONTEXT_LEAK_DELTA", "0.0"), 0.0)
    )
    fairness_regression_dataset_path: str = field(
        default_factory=lambda: os.getenv("FAIRNESS_REGRESSION_DATASET_PATH", "").strip()
    )
    fairness_regression_min_check_count: int = field(
        default_factory=lambda: _as_int(os.getenv("FAIRNESS_REGRESSION_MIN_CHECK_COUNT", "10"), 10)
    )
    fairness_regression_min_external_check_count: int = field(
        default_factory=lambda: _as_int(os.getenv("FAIRNESS_REGRESSION_MIN_EXTERNAL_CHECK_COUNT", "0"), 0)
    )
    false_positive_negative_dataset_path: str = field(
        default_factory=lambda: os.getenv("FALSE_POSITIVE_NEGATIVE_DATASET_PATH", "").strip()
    )
    false_positive_negative_min_case_count: int = field(
        default_factory=lambda: _as_int(os.getenv("FALSE_POSITIVE_NEGATIVE_MIN_CASE_COUNT", "10"), 10)
    )
    false_positive_negative_min_external_case_count: int = field(
        default_factory=lambda: _as_int(os.getenv("FALSE_POSITIVE_NEGATIVE_MIN_EXTERNAL_CASE_COUNT", "0"), 0)
    )
    similarity_language_detection_enabled: bool = field(
        default_factory=lambda: _as_bool(os.getenv("SIMILARITY_LANGUAGE_DETECTION_ENABLED"), False)
    )
    similarity_language_detector: str = field(
        default_factory=lambda: os.getenv("SIMILARITY_LANGUAGE_DETECTOR", "unicode_script_heuristic").strip().lower()
    )
    similarity_tokenizer_mode: str = field(
        default_factory=lambda: os.getenv("SIMILARITY_TOKENIZER_MODE", "ascii_legacy").strip().lower()
    )
    similarity_stopword_strategy: str = field(
        default_factory=lambda: os.getenv("SIMILARITY_STOPWORD_STRATEGY", "english_only").strip().lower()
    )
    similarity_mixed_language_mode: str = field(
        default_factory=lambda: os.getenv("SIMILARITY_MIXED_LANGUAGE_MODE", "keep_all_tokens").strip().lower()
    )
    similarity_cross_assignment_enabled: bool = field(
        default_factory=lambda: _as_bool(os.getenv("SIMILARITY_CROSS_ASSIGNMENT_ENABLED"), False)
    )
    ocr_enabled: bool = field(
        default_factory=lambda: _as_bool(os.getenv("OCR_ENABLED"), False)
    )
    ocr_provider: str = field(
        default_factory=lambda: os.getenv("OCR_PROVIDER", "disabled").strip().lower()
    )
    ocr_openai_model: str = field(
        default_factory=lambda: os.getenv("OCR_OPENAI_MODEL", os.getenv("OPENAI_MODEL", "gpt-4o-mini")).strip()
    )
    ocr_languages: List[str] = field(
        default_factory=lambda: _as_csv_list(os.getenv("OCR_LANGUAGES", "eng"))
    )
    ocr_min_chars: int = field(
        default_factory=lambda: _as_int(os.getenv("OCR_MIN_CHARS", "120"), 120)
    )
    ocr_timeout_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("OCR_TIMEOUT_SECONDS", "25"), 25)
    )
    ocr_max_output_tokens: int = field(
        default_factory=lambda: _as_int(os.getenv("OCR_MAX_OUTPUT_TOKENS", "1800"), 1800)
    )
    ocr_max_retries: int = field(
        default_factory=lambda: _as_int(os.getenv("OCR_MAX_RETRIES", "1"), 1)
    )
    ocr_retry_backoff_seconds: float = field(
        default_factory=lambda: _as_float(os.getenv("OCR_RETRY_BACKOFF_SECONDS", "0.5"), 0.5)
    )
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    observability_slow_request_ms: int = field(
        default_factory=lambda: _as_int(os.getenv("OBSERVABILITY_SLOW_REQUEST_MS", "1500"), 1500)
    )
    observability_slow_request_count_alert_threshold: int = field(
        default_factory=lambda: _as_int(
            os.getenv("OBSERVABILITY_SLOW_REQUEST_COUNT_ALERT_THRESHOLD", "3"),
            3,
        )
    )
    observability_error_rate_threshold_pct: float = field(
        default_factory=lambda: _as_float(
            os.getenv("OBSERVABILITY_ERROR_RATE_THRESHOLD_PCT", "5"),
            5.0,
        )
    )
    operational_alert_notifications_enabled: bool = field(
        default_factory=lambda: _as_bool(os.getenv("OPERATIONAL_ALERT_NOTIFICATIONS_ENABLED"), True)
    )
    operational_alert_notification_cooldown_minutes: int = field(
        default_factory=lambda: _as_int(
            os.getenv("OPERATIONAL_ALERT_NOTIFICATION_COOLDOWN_MINUTES", "30"),
            30,
        )
    )
    rate_limit_max_requests: int = field(
        default_factory=lambda: _as_int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"), 120)
    )
    rate_limit_window_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"), 60)
    )
    response_envelope_enabled: bool = field(
        default_factory=lambda: _as_bool(os.getenv("RESPONSE_ENVELOPE_ENABLED"), False)
    )
    response_envelope_skip_paths: List[str] = field(
        default_factory=lambda: _as_csv_list(
            os.getenv(
                "RESPONSE_ENVELOPE_SKIP_PATHS",
                "/api/v1/auth/me,/api/v1/session/bootstrap,/api/v1/analytics/dashboard,/api/v1/analytics/summary,/api/v1/notices/unread-count,/api/v1/notifications/unread-count",
            )
        )
    )
    redis_enabled: bool = field(
        default_factory=lambda: _as_bool(os.getenv("REDIS_ENABLED"), False)
    )
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    analytics_cache_ttl_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("ANALYTICS_CACHE_TTL_SECONDS", "120"), 120)
    )
    analytics_snapshot_freshness_hours: int = field(
        default_factory=lambda: _as_int(os.getenv("ANALYTICS_SNAPSHOT_FRESHNESS_HOURS", "36"), 36)
    )
    system_health_snapshot_freshness_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("SYSTEM_HEALTH_SNAPSHOT_FRESHNESS_SECONDS", "60"), 60)
    )
    scheduler_enabled: bool = field(
        default_factory=lambda: _as_bool(os.getenv("SCHEDULER_ENABLED"), False)
    )
    scheduler_lock_id: str = field(
        default_factory=lambda: os.getenv("SCHEDULER_LOCK_ID", "caps_ai_scheduler_primary").strip()
    )
    scheduler_lock_ttl_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("SCHEDULER_LOCK_TTL_SECONDS", "90"), 90)
    )
    scheduler_lock_renew_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("SCHEDULER_LOCK_RENEW_SECONDS", "20"), 20)
    )
    scheduled_notice_poll_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("SCHEDULED_NOTICE_POLL_SECONDS", "60"), 60)
    )
    scheduled_notice_retry_limit: int = field(
        default_factory=lambda: _as_int(os.getenv("SCHEDULED_NOTICE_RETRY_LIMIT", "3"), 3)
    )
    scheduled_notice_retry_backoff_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("SCHEDULED_NOTICE_RETRY_BACKOFF_SECONDS", "120"), 120)
    )
    scheduled_notice_dispatch_lease_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("SCHEDULED_NOTICE_DISPATCH_LEASE_SECONDS", "300"), 300)
    )
    notification_digest_poll_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("NOTIFICATION_DIGEST_POLL_SECONDS", "300"), 300)
    )
    ai_job_poll_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("AI_JOB_POLL_SECONDS", "10"), 10)
    )
    analytics_snapshot_hour_utc: int = field(
        default_factory=lambda: _as_int(os.getenv("ANALYTICS_SNAPSHOT_HOUR_UTC", "0"), 0)
    )
    analytics_snapshot_minute_utc: int = field(
        default_factory=lambda: _as_int(os.getenv("ANALYTICS_SNAPSHOT_MINUTE_UTC", "15"), 15)
    )
    internship_auto_logout_hours: int = field(
        default_factory=lambda: _as_int(os.getenv("INTERNSHIP_AUTO_LOGOUT_HOURS", "9"), 9)
    )
    cloudinary_cloud_name: str = field(default_factory=lambda: os.getenv("CLOUDINARY_CLOUD_NAME", "").strip())
    cloudinary_api_key: str = field(default_factory=lambda: os.getenv("CLOUDINARY_API_KEY", "").strip())
    cloudinary_api_secret: str = field(default_factory=lambda: os.getenv("CLOUDINARY_API_SECRET", "").strip())
    outbound_email_enabled: bool = field(
        default_factory=lambda: _as_bool(os.getenv("OUTBOUND_EMAIL_ENABLED"), False)
    )
    smtp_host: str = field(default_factory=lambda: os.getenv("SMTP_HOST", "").strip())
    smtp_port: int = field(default_factory=lambda: _as_int(os.getenv("SMTP_PORT", "587"), 587))
    smtp_username: str = field(default_factory=lambda: os.getenv("SMTP_USERNAME", "").strip())
    smtp_password: str = field(default_factory=lambda: os.getenv("SMTP_PASSWORD", "").strip())
    smtp_use_tls: bool = field(default_factory=lambda: _as_bool(os.getenv("SMTP_USE_TLS"), True))
    smtp_use_ssl: bool = field(default_factory=lambda: _as_bool(os.getenv("SMTP_USE_SSL"), False))
    outbound_email_from: str = field(default_factory=lambda: os.getenv("OUTBOUND_EMAIL_FROM", "").strip())
    outbound_email_from_name: str = field(default_factory=lambda: os.getenv("OUTBOUND_EMAIL_FROM_NAME", "").strip())
    outbound_email_reply_to: str = field(default_factory=lambda: os.getenv("OUTBOUND_EMAIL_REPLY_TO", "").strip())
    cors_origins: List[str] = field(
        default_factory=lambda: _merge_cors_origins(
            os.getenv("CORS_ORIGINS", "http://localhost:5173")
        )
    )

    def __post_init__(self) -> None:
        if self.environment != "development" and self.jwt_secret == "change_me":
            raise ValueError("JWT_SECRET must be set for non-development environments")
        if self.auth_registration_policy not in {"single_admin_open", "bootstrap_strict", "open"}:
            self.auth_registration_policy = "single_admin_open"
        if not self.outbound_email_from_name:
            self.outbound_email_from_name = self.app_name


settings = Settings()
