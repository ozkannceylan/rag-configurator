"""Base LLM interface and common types."""

import logging
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class MessageRole(StrEnum):
    """Message role types."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """A chat message."""

    role: str  # "system", "user", "assistant"
    content: str
    name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        result = {"role": self.role, "content": self.content}
        if self.name:
            result["name"] = self.name
        return result

    @classmethod
    def system(cls, content: str) -> "Message":
        """Create a system message."""
        return cls(role=MessageRole.SYSTEM.value, content=content)

    @classmethod
    def user(cls, content: str) -> "Message":
        """Create a user message."""
        return cls(role=MessageRole.USER.value, content=content)

    @classmethod
    def assistant(cls, content: str) -> "Message":
        """Create an assistant message."""
        return cls(role=MessageRole.ASSISTANT.value, content=content)


@dataclass
class LLMUsage:
    """Token usage statistics."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        """Convert to dictionary."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class LLMResponse:
    """Response from LLM generation."""

    content: str
    model: str
    usage: LLMUsage | None = None
    finish_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "content": self.content,
            "model": self.model,
            "usage": self.usage.to_dict() if self.usage else None,
            "finish_reason": self.finish_reason,
        }


@dataclass
class LLMConfig:
    """Configuration for LLM providers."""

    # Model settings
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2048
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    # Provider settings
    api_key: str | None = None
    base_url: str | None = None
    organization: str | None = None

    # Timeout and retry
    timeout_seconds: float = 60.0
    max_retries: int = 3

    # Streaming
    stream: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LLMConfig":
        """Create from dictionary."""
        return cls(
            model=data.get("model", "gpt-4o-mini"),
            temperature=data.get("temperature", 0.7),
            max_tokens=data.get("max_tokens", 2048),
            top_p=data.get("top_p", 1.0),
            frequency_penalty=data.get("frequency_penalty", 0.0),
            presence_penalty=data.get("presence_penalty", 0.0),
            api_key=data.get("api_key"),
            base_url=data.get("base_url"),
            organization=data.get("organization"),
            timeout_seconds=data.get("timeout_seconds", 60.0),
            max_retries=data.get("max_retries", 3),
            stream=data.get("stream", False),
        )


class LLMError(Exception):
    """Base exception for LLM errors."""

    def __init__(self, message: str, provider: str = "unknown", **kwargs):
        self.message = message
        self.provider = provider
        self.details = kwargs
        super().__init__(f"[{provider}] {message}")


class LLMRateLimitError(LLMError):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        provider: str = "unknown",
        retry_after: float | None = None,
        **kwargs,
    ):
        self.retry_after = retry_after
        super().__init__(message, provider, **kwargs)


class LLMAuthenticationError(LLMError):
    """Authentication failed."""

    def __init__(
        self,
        message: str = "Authentication failed",
        provider: str = "unknown",
        **kwargs,
    ):
        super().__init__(message, provider, **kwargs)


class LLMContextLengthError(LLMError):
    """Context length exceeded."""

    def __init__(
        self,
        message: str = "Context length exceeded",
        provider: str = "unknown",
        max_tokens: int | None = None,
        **kwargs,
    ):
        self.max_tokens = max_tokens
        super().__init__(message, provider, **kwargs)


class BaseLLM(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig | None = None):
        """
        Initialize LLM.

        Args:
            config: LLM configuration
        """
        self.config = config or LLMConfig()
        self._provider_name = "base"

    @property
    def provider(self) -> str:
        """Get provider name."""
        return self._provider_name

    @property
    def model(self) -> str:
        """Get model name."""
        return self.config.model

    @abstractmethod
    async def generate(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a response from the LLM.

        Args:
            messages: List of messages in the conversation
            temperature: Sampling temperature (overrides config)
            max_tokens: Maximum tokens to generate (overrides config)
            **kwargs: Additional provider-specific arguments

        Returns:
            LLMResponse with generated content
        """
        pass

    @abstractmethod
    async def stream(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream a response from the LLM.

        Args:
            messages: List of messages in the conversation
            temperature: Sampling temperature (overrides config)
            max_tokens: Maximum tokens to generate (overrides config)
            **kwargs: Additional provider-specific arguments

        Yields:
            String chunks of the response
        """
        pass

    async def generate_text(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> str:
        """
        Convenience method for simple text generation.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments

        Returns:
            Generated text content
        """
        messages = []
        if system_prompt:
            messages.append(Message.system(system_prompt))
        messages.append(Message.user(prompt))

        response = await self.generate(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs,
        )
        return response.content

    async def close(self) -> None:
        """Clean up resources."""
        pass

    def _get_temperature(self, temperature: float | None) -> float:
        """Get temperature, using override or config default."""
        return temperature if temperature is not None else self.config.temperature

    def _get_max_tokens(self, max_tokens: int | None) -> int:
        """Get max tokens, using override or config default."""
        return max_tokens if max_tokens is not None else self.config.max_tokens

    def _format_messages(self, messages: list[Message]) -> list[dict[str, str]]:
        """Format messages for API call."""
        return [msg.to_dict() for msg in messages]
