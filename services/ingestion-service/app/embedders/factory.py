"""Factory for creating embedding providers."""

import logging
from enum import StrEnum

from app.embedders.base import BaseEmbedder, EmbeddingConfig

logger = logging.getLogger(__name__)


class EmbeddingProvider(StrEnum):
    """Available embedding providers."""

    OPENAI = "openai"
    OLLAMA = "ollama"
    HUGGINGFACE = "huggingface"
    HUGGINGFACE_API = "huggingface_api"


def get_embedder(
    provider: EmbeddingProvider | str = EmbeddingProvider.OPENAI,
    config: EmbeddingConfig | None = None,
) -> BaseEmbedder:
    """
    Get an embedder instance for the specified provider.

    Args:
        provider: Embedding provider to use
        config: Optional embedding configuration

    Returns:
        BaseEmbedder instance

    Raises:
        ValueError: If provider is not recognized
    """
    # Convert string to enum if needed
    if isinstance(provider, str):
        try:
            provider = EmbeddingProvider(provider.lower())
        except ValueError:
            valid_providers = [p.value for p in EmbeddingProvider]
            raise ValueError(
                f"Unknown embedding provider: '{provider}'. "
                f"Valid providers: {valid_providers}"
            ) from None

    # Import and instantiate the appropriate embedder
    if provider == EmbeddingProvider.OPENAI:
        from app.embedders.openai import OpenAIEmbedder

        return OpenAIEmbedder(config)

    elif provider == EmbeddingProvider.OLLAMA:
        from app.embedders.ollama import OllamaEmbedder

        return OllamaEmbedder(config)

    elif provider == EmbeddingProvider.HUGGINGFACE:
        from app.embedders.huggingface import HuggingFaceEmbedder

        return HuggingFaceEmbedder(config)

    elif provider == EmbeddingProvider.HUGGINGFACE_API:
        from app.embedders.huggingface import HuggingFaceAPIEmbedder

        return HuggingFaceAPIEmbedder(config)

    else:
        raise ValueError(f"No embedder registered for provider: {provider}")


def get_available_providers() -> list[str]:
    """Get list of available embedding providers."""
    return [p.value for p in EmbeddingProvider]


def get_provider_info() -> dict[str, dict]:
    """
    Get information about all available providers.

    Returns:
        Dictionary with provider information
    """
    return {
        EmbeddingProvider.OPENAI.value: {
            "name": "OpenAI",
            "description": "OpenAI text-embedding models (requires API key)",
            "default_model": "text-embedding-3-small",
            "requires_api_key": True,
            "local": False,
        },
        EmbeddingProvider.OLLAMA.value: {
            "name": "Ollama",
            "description": "Local embeddings via Ollama (requires Ollama running)",
            "default_model": "nomic-embed-text",
            "requires_api_key": False,
            "local": True,
        },
        EmbeddingProvider.HUGGINGFACE.value: {
            "name": "HuggingFace (Local)",
            "description": "Local sentence-transformers models",
            "default_model": "sentence-transformers/all-MiniLM-L6-v2",
            "requires_api_key": False,
            "local": True,
        },
        EmbeddingProvider.HUGGINGFACE_API.value: {
            "name": "HuggingFace API",
            "description": "HuggingFace Inference API (requires API key)",
            "default_model": "sentence-transformers/all-MiniLM-L6-v2",
            "requires_api_key": True,
            "local": False,
        },
    }


def get_default_config(provider: EmbeddingProvider | str) -> EmbeddingConfig:
    """
    Get recommended default configuration for a provider.

    Args:
        provider: Embedding provider

    Returns:
        EmbeddingConfig with recommended settings
    """
    if isinstance(provider, str):
        provider = EmbeddingProvider(provider.lower())

    if provider == EmbeddingProvider.OPENAI:
        return EmbeddingConfig(
            model="text-embedding-3-small",
            dimensions=1536,
            batch_size=100,
        )

    elif provider == EmbeddingProvider.OLLAMA:
        return EmbeddingConfig(
            model="nomic-embed-text",
            dimensions=768,
            batch_size=1,  # Ollama processes one at a time
            base_url="http://localhost:11434",
        )

    elif provider == EmbeddingProvider.HUGGINGFACE:
        return EmbeddingConfig(
            model="sentence-transformers/all-MiniLM-L6-v2",
            dimensions=384,
            batch_size=32,
            normalize=True,
        )

    elif provider == EmbeddingProvider.HUGGINGFACE_API:
        return EmbeddingConfig(
            model="sentence-transformers/all-MiniLM-L6-v2",
            dimensions=384,
            batch_size=10,
        )

    return EmbeddingConfig()


def create_embedder_from_settings() -> BaseEmbedder:
    """
    Create an embedder using application settings.

    Returns:
        BaseEmbedder configured from settings
    """
    from app.core.settings import settings

    provider = EmbeddingProvider(settings.embedding_provider.lower())

    config = EmbeddingConfig(
        model=settings.embedding_model,
        dimensions=settings.embedding_dimensions,
        api_key=(
            settings.openai_api_key if provider == EmbeddingProvider.OPENAI else None
        ),
    )

    return get_embedder(provider, config)
