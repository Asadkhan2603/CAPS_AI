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
    redis_enabled: bool = field(
        default_factory=lambda: _as_bool(os.getenv("REDIS_ENABLED"), False)
    )
    redis_url: str = field(default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0"))
    analytics_cache_ttl_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("ANALYTICS_CACHE_TTL_SECONDS", "120"), 120)
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


settings = Settings()
