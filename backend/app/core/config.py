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
    rate_limit_max_requests: int = field(
        default_factory=lambda: _as_int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "120"), 120)
    )
    rate_limit_window_seconds: int = field(
        default_factory=lambda: _as_int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"), 60)
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


settings = Settings()
