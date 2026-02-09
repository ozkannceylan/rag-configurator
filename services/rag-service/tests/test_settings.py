"""Tests for RAG service settings."""

import pytest
from unittest.mock import patch


class TestSettings:
    """Tests for Settings configuration."""

    def test_default_settings(self):
        """Test default settings values."""
        with patch.dict("os.environ", {}, clear=True):
            from importlib import reload
            from app.core import settings as settings_module

            reload(settings_module)
            settings = settings_module.Settings()

            assert settings.service_name == "rag-service"
            assert settings.port == 8003
            assert settings.default_llm_provider == "openai"
            assert settings.default_llm_model == "gpt-4o-mini"
            assert settings.default_top_k == 5
            assert settings.enable_streaming is True

    def test_mongodb_settings(self):
        """Test MongoDB settings."""
        with patch.dict("os.environ", {}, clear=True):
            from importlib import reload
            from app.core import settings as settings_module

            reload(settings_module)
            settings = settings_module.Settings()

            assert settings.mongodb_uri == "mongodb://localhost:27017"
            assert settings.mongodb_database == "rag_configurator"

    def test_llm_provider_settings(self):
        """Test LLM provider settings."""
        with patch.dict("os.environ", {}, clear=True):
            from importlib import reload
            from app.core import settings as settings_module

            reload(settings_module)
            settings = settings_module.Settings()

            assert settings.ollama_base_url == "http://localhost:11434"
            assert settings.ollama_default_model == "llama3.2"

    def test_rag_settings(self):
        """Test RAG-specific settings."""
        with patch.dict("os.environ", {}, clear=True):
            from importlib import reload
            from app.core import settings as settings_module

            reload(settings_module)
            settings = settings_module.Settings()

            assert settings.default_min_score == 0.7
            assert settings.max_context_tokens == 4000
            assert settings.max_response_tokens == 2000

    def test_is_development(self):
        """Test is_development property."""
        with patch.dict("os.environ", {"ENVIRONMENT": "development"}, clear=True):
            from importlib import reload
            from app.core import settings as settings_module

            reload(settings_module)
            settings = settings_module.Settings()

            assert settings.is_development is True

    def test_is_not_development(self):
        """Test is_development returns False for production."""
        with patch.dict("os.environ", {"ENVIRONMENT": "production"}, clear=True):
            from importlib import reload
            from app.core import settings as settings_module

            reload(settings_module)
            settings = settings_module.Settings()

            assert settings.is_development is False

    def test_mlflow_enabled(self):
        """Test mlflow_enabled property."""
        with patch.dict("os.environ", {}, clear=True):
            from importlib import reload
            from app.core import settings as settings_module

            reload(settings_module)
            settings = settings_module.Settings()

            # Default: not enabled
            assert settings.mlflow_enabled is False

        with patch.dict(
            "os.environ",
            {"MLFLOW_TRACKING_URI": "http://mlflow:5000"},
            clear=True,
        ):
            reload(settings_module)
            settings = settings_module.Settings()

            assert settings.mlflow_enabled is True

    def test_cors_origins_from_string(self):
        """Test parsing CORS origins from comma-separated string."""
        with patch.dict(
            "os.environ",
            {"CORS_ORIGINS": "http://localhost:3000,http://localhost:5173"},
            clear=True,
        ):
            from importlib import reload
            from app.core import settings as settings_module

            reload(settings_module)
            settings = settings_module.Settings()

            assert "http://localhost:3000" in settings.cors_origins
            assert "http://localhost:5173" in settings.cors_origins

    def test_timeout_settings(self):
        """Test timeout configuration."""
        with patch.dict("os.environ", {}, clear=True):
            from importlib import reload
            from app.core import settings as settings_module

            reload(settings_module)
            settings = settings_module.Settings()

            assert settings.llm_timeout_seconds == 60.0
            assert settings.retrieval_timeout_seconds == 10.0
