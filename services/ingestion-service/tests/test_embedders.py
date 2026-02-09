"""Tests for embedding providers."""

import os

import pytest

from app.embedders.base import BaseEmbedder, EmbeddingConfig, EmbeddingResult
from app.embedders.factory import (
    EmbeddingProvider,
    get_available_providers,
    get_default_config,
    get_embedder,
    get_provider_info,
)


class TestEmbeddingConfig:
    """Tests for EmbeddingConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = EmbeddingConfig()

        assert config.model == "text-embedding-3-small"
        assert config.batch_size == 100
        assert config.max_retries == 3
        assert config.normalize is True

    def test_custom_values(self):
        """Test custom configuration values."""
        config = EmbeddingConfig(
            model="custom-model",
            dimensions=768,
            batch_size=50,
            api_key="test-key",
        )

        assert config.model == "custom-model"
        assert config.dimensions == 768
        assert config.batch_size == 50
        assert config.api_key == "test-key"


class TestEmbeddingResult:
    """Tests for EmbeddingResult."""

    def test_result_creation(self):
        """Test result creation."""
        embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
        result = EmbeddingResult(
            embeddings=embeddings,
            model="test-model",
            dimensions=3,
        )

        assert result.count == 2
        assert result.dimensions == 3
        assert result.model == "test-model"

    def test_result_to_dict(self):
        """Test conversion to dictionary."""
        result = EmbeddingResult(
            embeddings=[[0.1, 0.2]],
            model="test-model",
            dimensions=2,
            total_tokens=10,
        )

        data = result.to_dict()
        assert data["count"] == 1
        assert data["dimensions"] == 2
        assert data["total_tokens"] == 10


class TestEmbedderFactory:
    """Tests for embedder factory."""

    def test_get_openai_embedder(self):
        """Test getting OpenAI embedder."""
        embedder = get_embedder(EmbeddingProvider.OPENAI)
        assert embedder is not None
        assert embedder.model_name == "text-embedding-3-small"

    def test_get_ollama_embedder(self):
        """Test getting Ollama embedder."""
        embedder = get_embedder(EmbeddingProvider.OLLAMA)
        assert embedder is not None
        assert "nomic" in embedder.model_name or embedder.model_name

    def test_get_huggingface_embedder(self):
        """Test getting HuggingFace embedder."""
        embedder = get_embedder(EmbeddingProvider.HUGGINGFACE)
        assert embedder is not None

    def test_get_embedder_by_string(self):
        """Test getting embedder by string name."""
        embedder = get_embedder("openai")
        assert embedder is not None

    def test_get_embedder_with_config(self):
        """Test getting embedder with custom config."""
        config = EmbeddingConfig(model="custom-model", dimensions=512)
        embedder = get_embedder(EmbeddingProvider.OPENAI, config)

        assert embedder.config.model == "custom-model"
        assert embedder.config.dimensions == 512

    def test_invalid_provider(self):
        """Test getting embedder with invalid provider."""
        with pytest.raises(ValueError):
            get_embedder("invalid_provider")

    def test_get_available_providers(self):
        """Test getting available providers."""
        providers = get_available_providers()

        assert "openai" in providers
        assert "ollama" in providers
        assert "huggingface" in providers

    def test_get_provider_info(self):
        """Test getting provider information."""
        info = get_provider_info()

        assert "openai" in info
        assert info["openai"]["requires_api_key"] is True
        assert info["ollama"]["local"] is True

    def test_get_default_config_openai(self):
        """Test default config for OpenAI."""
        config = get_default_config(EmbeddingProvider.OPENAI)

        assert config.model == "text-embedding-3-small"
        assert config.dimensions == 1536

    def test_get_default_config_ollama(self):
        """Test default config for Ollama."""
        config = get_default_config(EmbeddingProvider.OLLAMA)

        assert config.model == "nomic-embed-text"
        assert "localhost" in config.base_url

    def test_get_default_config_huggingface(self):
        """Test default config for HuggingFace."""
        config = get_default_config(EmbeddingProvider.HUGGINGFACE)

        assert "MiniLM" in config.model
        assert config.normalize is True


class TestOpenAIEmbedder:
    """Tests for OpenAI embedder (mocked)."""

    def test_embedder_creation(self):
        """Test embedder creation."""
        from app.embedders.openai import OpenAIEmbedder

        embedder = OpenAIEmbedder()
        assert embedder.model_name == "text-embedding-3-small"
        assert embedder.dimensions == 1536

    def test_dimensions_lookup(self):
        """Test dimensions lookup for different models."""
        from app.embedders.openai import OpenAIEmbedder

        config = EmbeddingConfig(model="text-embedding-3-large")
        embedder = OpenAIEmbedder(config)
        assert embedder.dimensions == 3072

    def test_batch_size_limit(self):
        """Test batch size is limited to API maximum."""
        from app.embedders.openai import OpenAIEmbedder, MAX_BATCH_SIZE

        config = EmbeddingConfig(batch_size=5000)
        embedder = OpenAIEmbedder(config)
        assert embedder.config.batch_size == MAX_BATCH_SIZE


class TestOllamaEmbedder:
    """Tests for Ollama embedder."""

    def test_embedder_creation(self):
        """Test embedder creation."""
        from app.embedders.ollama import OllamaEmbedder

        embedder = OllamaEmbedder()
        assert embedder.model_name == "nomic-embed-text"
        assert "localhost" in embedder.config.base_url

    def test_custom_base_url(self):
        """Test custom base URL."""
        from app.embedders.ollama import OllamaEmbedder

        config = EmbeddingConfig(base_url="http://custom:11434")
        embedder = OllamaEmbedder(config)
        assert embedder.config.base_url == "http://custom:11434"


class TestHuggingFaceEmbedder:
    """Tests for HuggingFace embedder."""

    def test_embedder_creation(self):
        """Test embedder creation."""
        from app.embedders.huggingface import HuggingFaceEmbedder

        embedder = HuggingFaceEmbedder()
        assert "MiniLM" in embedder.model_name or "sentence" in embedder.model_name

    def test_dimensions_lookup(self):
        """Test dimensions lookup for known models."""
        from app.embedders.huggingface import HuggingFaceEmbedder

        config = EmbeddingConfig(model="BAAI/bge-large-en-v1.5")
        embedder = HuggingFaceEmbedder(config)
        assert embedder.dimensions == 1024


class TestBaseEmbedder:
    """Tests for base embedder functionality."""

    def test_validate_texts_empty(self):
        """Test text validation with empty input."""
        from app.embedders.openai import OpenAIEmbedder

        embedder = OpenAIEmbedder()
        result = embedder._validate_texts([])
        assert result == []

    def test_validate_texts_with_none(self):
        """Test text validation skips None values."""
        from app.embedders.openai import OpenAIEmbedder

        embedder = OpenAIEmbedder()
        result = embedder._validate_texts(["hello", None, "world"])
        assert result == ["hello", "world"]

    def test_validate_texts_strips_whitespace(self):
        """Test text validation strips whitespace."""
        from app.embedders.openai import OpenAIEmbedder

        embedder = OpenAIEmbedder()
        result = embedder._validate_texts(["  hello  ", "world  "])
        assert result == ["hello", "world"]

    def test_batch_texts(self):
        """Test text batching."""
        from app.embedders.openai import OpenAIEmbedder

        embedder = OpenAIEmbedder()
        texts = ["a", "b", "c", "d", "e"]
        batches = embedder._batch_texts(texts, 2)

        assert len(batches) == 3
        assert batches[0] == ["a", "b"]
        assert batches[1] == ["c", "d"]
        assert batches[2] == ["e"]


class TestOllamaEmbedderIntegration:
    """Integration tests for Ollama embedder (requires Ollama running)."""

    @pytest.mark.skipif(
        os.environ.get("RUN_OLLAMA_TESTS", "").lower() != "true",
        reason="Ollama integration tests require RUN_OLLAMA_TESTS=true and running Ollama",
    )
    @pytest.mark.asyncio
    async def test_embed_single_text(self):
        """Test embedding a single text with Ollama."""
        from app.embedders.ollama import OllamaEmbedder

        embedder = OllamaEmbedder()
        result = await embedder.embed(["Hello world"])

        assert result.count == 1
        assert len(result.embeddings[0]) == 768
        assert result.model == "nomic-embed-text"

    @pytest.mark.skipif(
        os.environ.get("RUN_OLLAMA_TESTS", "").lower() != "true",
        reason="Ollama integration tests require RUN_OLLAMA_TESTS=true and running Ollama",
    )
    @pytest.mark.asyncio
    async def test_embed_multiple_texts(self):
        """Test embedding multiple texts with Ollama."""
        from app.embedders.ollama import OllamaEmbedder

        embedder = OllamaEmbedder()
        texts = [
            "The quick brown fox jumps over the lazy dog",
            "Machine learning is transforming industries",
            "RAG systems combine retrieval with generation",
        ]
        result = await embedder.embed(texts)

        assert result.count == 3
        for emb in result.embeddings:
            assert len(emb) == 768

    @pytest.mark.skipif(
        os.environ.get("RUN_OLLAMA_TESTS", "").lower() != "true",
        reason="Ollama integration tests require RUN_OLLAMA_TESTS=true and running Ollama",
    )
    @pytest.mark.asyncio
    async def test_embed_with_custom_model(self):
        """Test embedding with specific model configuration."""
        from app.embedders.ollama import OllamaEmbedder

        config = EmbeddingConfig(model="nomic-embed-text")
        embedder = OllamaEmbedder(config)

        result = await embedder.embed(["Test text"])

        assert result.model == "nomic-embed-text"
        assert result.count == 1