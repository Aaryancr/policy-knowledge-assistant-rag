"""Unit tests for configuration loading and validation."""

from app.config import Settings


def test_default_settings():
    settings = Settings()
    assert settings.PROJECT_NAME == "Policy & Knowledge Assistant"
    assert settings.ALGORITHM == "HS256"
    assert settings.ACCESS_TOKEN_EXPIRE_MINUTES > 0
    assert settings.EMBEDDING_DIMENSION == 1536
    assert "postgresql" in settings.get_database_url()
    assert "postgresql" in settings.get_sync_database_url()


def test_settings_custom_override():
    custom = Settings(
        PROJECT_NAME="Custom Assistant",
        ENVIRONMENT="test",
        ACCESS_TOKEN_EXPIRE_MINUTES=120,
    )
    assert custom.PROJECT_NAME == "Custom Assistant"
    assert custom.ENVIRONMENT == "test"
    assert custom.ACCESS_TOKEN_EXPIRE_MINUTES == 120
