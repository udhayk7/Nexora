from typing import Literal, Optional, Union

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized application settings with environment validation."""

    PROJECT_NAME: str = "Nexora API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: Literal["development", "test", "production"] = "development"
    DEBUG: bool = True

    # Security & Tokens
    SECRET_KEY: str = "development_secret_key_change_in_production"
    JWT_SECRET_KEY: str = "development_jwt_secret_key_change_in_production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AUTH_RATE_LIMIT_PER_MINUTE: int = 5
    ALLOWED_ORIGINS: Union[str, list[str]] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database Configuration
    DATABASE_URL: str = (
        "postgresql+psycopg://nexora_user:change_me_in_local_env@localhost:5432/nexora_db"
    )
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800
    DB_ECHO: bool = False

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Storage & Uploads
    STORAGE_LOCAL_PATH: str = "storage/resumes"
    MAX_UPLOAD_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

    # AI Intelligence & Providers
    AI_PROVIDER: Literal["gemini", "openai", "none"] = "gemini"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.5-flash"
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    AI_MAX_INPUT_CHARS: int = 25000
    AI_REQUEST_TIMEOUT_SECONDS: int = 45
    AI_MAX_RETRIES: int = 2

    # Job Freshness & Verification
    JOB_FRESHNESS_RECENT_DAYS: int = 7
    JOB_FRESHNESS_DUE_DAYS: int = 14

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: Literal["json", "text"] = "text"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, list[str]]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @model_validator(mode="after")
    def validate_production_settings(self) -> "Settings":
        """Enforce strict security validation for production environments."""
        if self.ENVIRONMENT == "production":
            if self.DEBUG:
                raise ValueError("DEBUG must be False in production environment")
            if (
                self.SECRET_KEY == "development_secret_key_change_in_production"
                or len(self.SECRET_KEY) < 32
            ):
                raise ValueError(
                    "SECRET_KEY must be a cryptographically secure string "
                    "of at least 32 characters in production"
                )
            if (
                self.JWT_SECRET_KEY == "development_jwt_secret_key_change_in_production"
                or len(self.JWT_SECRET_KEY) < 32
            ):
                raise ValueError(
                    "JWT_SECRET_KEY must be a cryptographically secure string "
                    "of at least 32 characters in production"
                )
            if "change_me_in_local_env" in self.DATABASE_URL:
                raise ValueError("DATABASE_URL contains default placeholder password in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_test(self) -> bool:
        return self.ENVIRONMENT == "test"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
