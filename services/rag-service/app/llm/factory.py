"""Factory functions for creating LLM instances."""

import logging
from enum import StrEnum
from typing import Any

from app.llm.base import BaseLLM, LLMConfig, LLMError

logger = logging.getLogger(__name__)


class LLMProvider(StrEnum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    VLLM = "vllm"


# Default models for each provider
DEFAULT_MODELS = {
    LLMProvider.OPENAI: "gpt-4o-mini",
    LLMProvider.ANTHROPIC: "claude-3-5-sonnet-20241022",
    LLMProvider.OLLAMA: "llama3.2",
    LLMProvider.VLLM: "default",
}


def get_llm(
    provider: LLMProvider,
    config: LLMConfig | None = None,
    **kwargs: Any,
) -> BaseLLM:
    """
    Factory function to create LLM instance.

    Args:
        provider: LLM provider to use
        config: LLM configuration
        **kwargs: Additional configuration passed to LLMConfig

    Returns:
        Configured LLM instance

    Example:
        ```python
        llm = get_llm(LLMProvider.OPENAI, api_key="sk-...")
        response = await llm.generate([Message.user("Hello")])
        ```
    """
    # Build config from kwargs if not provided
    if config is None:
        config_kwargs = {
            "model": kwargs.pop("model", DEFAULT_MODELS.get(provider)),
        }
        # Copy relevant kwargs to config
        for key in [
            "api_key",
            "base_url",
            "organization",
            "temperature",
            "max_tokens",
            "top_p",
            "frequency_penalty",
            "presence_penalty",
            "timeout_seconds",
            "max_retries",
            "stream",
        ]:
            if key in kwargs:
                config_kwargs[key] = kwargs.pop(key)

        config = LLMConfig(**config_kwargs)

    if provider == LLMProvider.OPENAI:
        from app.llm.openai import OpenAILLM

        return OpenAILLM(config=config)

    elif provider == LLMProvider.ANTHROPIC:
        from app.llm.anthropic import AnthropicLLM

        return AnthropicLLM(config=config)

    elif provider == LLMProvider.OLLAMA:
        from app.llm.ollama import OllamaLLM

        return OllamaLLM(config=config)

    elif provider == LLMProvider.VLLM:
        from app.llm.vllm import VLLMLlm

        return VLLMLlm(config=config)

    else:
        raise LLMError(
            message=f"Unknown LLM provider: {provider}",
            provider="factory",
        )


def get_llm_from_config(
    pipeline_config: dict[str, Any],
    config_override: LLMConfig | None = None,
) -> BaseLLM:
    """
    Create LLM from pipeline configuration.

    Args:
        pipeline_config: RAG pipeline configuration dict
        config_override: Optional config to override settings

    Returns:
        Configured LLM instance

    Example config:
        ```python
        config = {
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 2048
            }
        }
        llm = get_llm_from_config(config)
        ```
    """
    llm_config = pipeline_config.get("llm", {})

    # Determine provider
    provider_str = llm_config.get("provider", "openai")
    try:
        provider = LLMProvider(provider_str.lower())
    except ValueError:
        logger.warning(f"Unknown LLM provider: {provider_str}, defaulting to openai")
        provider = LLMProvider.OPENAI

    # Build LLM config
    if config_override:
        config = config_override
    else:
        config = LLMConfig(
            model=llm_config.get("model", DEFAULT_MODELS.get(provider)),
            temperature=llm_config.get("temperature", 0.7),
            max_tokens=llm_config.get("max_tokens", 2048),
            top_p=llm_config.get("top_p", 1.0),
            frequency_penalty=llm_config.get("frequency_penalty", 0.0),
            presence_penalty=llm_config.get("presence_penalty", 0.0),
            api_key=llm_config.get("api_key"),
            base_url=llm_config.get("base_url"),
            organization=llm_config.get("organization"),
            timeout_seconds=llm_config.get("timeout_seconds", 60.0),
            max_retries=llm_config.get("max_retries", 3),
            stream=llm_config.get("stream", False),
        )

    return get_llm(provider=provider, config=config)


def create_llm_config(
    model: str = "gpt-4o-mini",
    temperature: float = 0.7,
    max_tokens: int = 2048,
    api_key: str | None = None,
    base_url: str | None = None,
    **kwargs: Any,
) -> LLMConfig:
    """
    Helper to create LLMConfig with sensible defaults.

    Args:
        model: Model identifier
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        api_key: API key for provider
        base_url: Base URL for API
        **kwargs: Additional config options

    Returns:
        LLMConfig instance
    """
    return LLMConfig(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
        base_url=base_url,
        top_p=kwargs.get("top_p", 1.0),
        frequency_penalty=kwargs.get("frequency_penalty", 0.0),
        presence_penalty=kwargs.get("presence_penalty", 0.0),
        organization=kwargs.get("organization"),
        timeout_seconds=kwargs.get("timeout_seconds", 60.0),
        max_retries=kwargs.get("max_retries", 3),
        stream=kwargs.get("stream", False),
    )


async def check_provider_availability(provider: LLMProvider) -> bool:
    """
    Check if a provider is available and properly configured.

    Args:
        provider: LLM provider to check

    Returns:
        True if provider is available
    """
    try:
        if provider == LLMProvider.OLLAMA:
            from app.llm.ollama import OllamaLLM

            llm = OllamaLLM()
            return await llm.is_available()

        elif provider == LLMProvider.VLLM:
            from app.llm.vllm import VLLMLlm

            llm = VLLMLlm()
            return await llm.is_available()

        elif provider == LLMProvider.OPENAI:
            # OpenAI is available if we can import and API key exists
            try:
                import os

                # Availability probe only; ImportError below is the signal.
                from openai import AsyncOpenAI  # noqa: F401

                return bool(os.environ.get("OPENAI_API_KEY"))
            except ImportError:
                return False

        elif provider == LLMProvider.ANTHROPIC:
            try:
                import os

                # Availability probe only; ImportError below is the signal.
                from anthropic import AsyncAnthropic  # noqa: F401

                return bool(os.environ.get("ANTHROPIC_API_KEY"))
            except ImportError:
                return False

        return False

    except Exception as e:
        logger.error(f"Error checking provider {provider}: {e}")
        return False


def list_providers() -> dict[str, dict[str, Any]]:
    """
    List all available providers with their default models.

    Returns:
        Dictionary of provider information
    """
    return {
        provider.value: {
            "name": provider.value,
            "default_model": DEFAULT_MODELS.get(provider),
            "description": _get_provider_description(provider),
        }
        for provider in LLMProvider
    }


def _get_provider_description(provider: LLMProvider) -> str:
    """Get description for a provider."""
    descriptions = {
        LLMProvider.OPENAI: "OpenAI GPT models (GPT-4, GPT-3.5-turbo)",
        LLMProvider.ANTHROPIC: "Anthropic Claude models (Claude 3.5, Claude 3)",
        LLMProvider.OLLAMA: "Local models via Ollama (Llama, Mistral, etc.)",
        LLMProvider.VLLM: "Self-hosted models via vLLM inference server",
    }
    return descriptions.get(provider, "Unknown provider")
