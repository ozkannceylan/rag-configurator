"""LLM module for unified language model access."""

from app.llm.base import (
    BaseLLM,
    Message,
    LLMConfig,
    LLMResponse,
    LLMUsage,
    LLMError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMContextLengthError,
)
from app.llm.openai import OpenAILLM
from app.llm.anthropic import AnthropicLLM
from app.llm.ollama import OllamaLLM
from app.llm.vllm import VLLMLlm
from app.llm.factory import (
    get_llm,
    get_llm_from_config,
    LLMProvider,
    create_llm_config,
)

__all__ = [
    # Base
    "BaseLLM",
    "Message",
    "LLMConfig",
    "LLMResponse",
    "LLMUsage",
    # Errors
    "LLMError",
    "LLMRateLimitError",
    "LLMAuthenticationError",
    "LLMContextLengthError",
    # Providers
    "OpenAILLM",
    "AnthropicLLM",
    "OllamaLLM",
    "VLLMLlm",
    # Factory
    "get_llm",
    "get_llm_from_config",
    "LLMProvider",
    "create_llm_config",
]
