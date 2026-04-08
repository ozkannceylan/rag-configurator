"""Shared LLM provider exception types."""

from app.llm.base import (
    LLMAuthenticationError,
    LLMContextLengthError,
    LLMError,
    LLMRateLimitError as BaseLLMRateLimitError,
)


class LLMRateLimitError(BaseLLMRateLimitError):
    """Provider rate limit failure."""


class LLMAuthError(LLMAuthenticationError):
    """Provider authentication failure."""


class LLMConnectionError(LLMError):
    """Provider connectivity failure."""


__all__ = [
    "LLMError",
    "LLMRateLimitError",
    "LLMAuthError",
    "LLMConnectionError",
    "LLMContextLengthError",
]
