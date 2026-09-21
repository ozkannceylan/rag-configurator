"""Tests for settings configuration."""


def test_settings_defaults():
    """Test default settings values."""
    from app.core.settings import Settings

    settings = Settings()

    assert settings.service_name == "ingestion-service"
    assert settings.port == 8002
    assert settings.environment == "development"
    assert settings.mongodb_database == "rag_configurator"
    assert settings.celery_task_default_queue == "ingestion"


def test_settings_cors_parsing(monkeypatch):
    """Test CORS origins parsing from string."""
    from app.core.settings import Settings

    # Test comma-separated string
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
    settings = Settings()
    assert "http://localhost:3000" in settings.cors_origins
    assert "http://localhost:5173" in settings.cors_origins


def test_settings_celery_broker_fallback():
    """Test Celery broker falls back to Redis URL."""
    from app.core.settings import Settings

    settings = Settings()

    # When CELERY_BROKER_URL is not set, should use REDIS_URL
    assert settings.celery_broker == settings.redis_url
    assert settings.celery_backend == settings.redis_url


def test_settings_is_development():
    """Test is_development property."""
    from app.core.settings import Settings

    settings = Settings(environment="development")
    assert settings.is_development is True

    settings = Settings(environment="production")
    assert settings.is_development is False
