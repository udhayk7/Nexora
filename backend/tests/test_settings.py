import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_default_settings() -> None:
    settings = Settings()
    assert settings.ENVIRONMENT == "development"
    assert settings.DEBUG is True
    assert settings.is_development is True
    assert settings.is_production is False
    assert settings.is_test is False
    assert "http://localhost:3000" in settings.ALLOWED_ORIGINS


def test_cors_origins_parsing() -> None:
    settings = Settings(ALLOWED_ORIGINS="http://example.com, https://app.example.com")
    assert settings.ALLOWED_ORIGINS == ["http://example.com", "https://app.example.com"]


def test_production_settings_validation_debug_failure() -> None:
    with pytest.raises(ValidationError, match="DEBUG must be False in production"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=True,
            SECRET_KEY="a_very_long_secure_secret_key_exceeding_32_characters",
            DATABASE_URL="postgresql+psycopg://user:prod_pass@prod-db.internal:5432/prod_db",
        )


def test_production_settings_validation_secret_key_failure() -> None:
    with pytest.raises(
        ValidationError, match="SECRET_KEY must be a cryptographically secure string"
    ):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="short",
            DATABASE_URL="postgresql+psycopg://user:prod_pass@prod-db.internal:5432/prod_db",
        )


def test_production_settings_validation_database_url_failure() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL contains default placeholder password"):
        Settings(
            ENVIRONMENT="production",
            DEBUG=False,
            SECRET_KEY="a_very_long_secure_secret_key_exceeding_32_characters",
            JWT_SECRET_KEY="a_very_long_secure_jwt_secret_key_exceeding_32_characters",
            DATABASE_URL="postgresql+psycopg://user:change_me_in_local_env@prod-db.internal:5432/prod_db",
        )


def test_valid_production_settings() -> None:
    settings = Settings(
        ENVIRONMENT="production",
        DEBUG=False,
        SECRET_KEY="a_very_long_secure_secret_key_exceeding_32_characters",
        JWT_SECRET_KEY="a_very_long_secure_jwt_secret_key_exceeding_32_characters",
        DATABASE_URL="postgresql+psycopg://user:secure_prod_password@prod-db.internal:5432/prod_db",
    )
    assert settings.is_production is True
    assert settings.DEBUG is False
