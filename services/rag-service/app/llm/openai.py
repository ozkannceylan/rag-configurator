"""OpenAI LLM implementation."""

import logging
from collections.abc import AsyncIterator
from typing import Any

from app.llm.base import BaseLLM, LLMConfig, LLMResponse, LLMUsage, Message
from app.llm.exceptions import (
    LLMAuthError,
    LLMConnectionError,
    LLMContextLengthError,
    LLMError,
    LLMRateLimitError,
)

logger = logging.getLogger(__name__)


class OpenAILLM(BaseLLM):
    """OpenAI LLM client."""

    # Supported models
    SUPPORTED_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4",
        "gpt-3.5-turbo",
        "o1-preview",
        "o1-mini",
    ]

    def __init__(self, config: LLMConfig | None = None):
        """
        Initialize OpenAI LLM.

        Args:
            config: LLM configuration
        """
        super().__init__(config)
        self._provider_name = "openai"
        self._client = None
        self._async_client = None

    def _get_client(self):
        """Get or create OpenAI async client."""
        if self._async_client is None:
            try:
                from openai import AsyncOpenAI
            except ImportError:
                raise LLMError(
                    "openai package not installed. Install with: pip install openai",
                    provider=self.provider,
                )

            kwargs = {}
            if self.config.api_key:
                kwargs["api_key"] = self.config.api_key
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            if self.config.organization:
                kwargs["organization"] = self.config.organization
            if self.config.timeout_seconds:
                kwargs["timeout"] = self.config.timeout_seconds

            self._async_client = AsyncOpenAI(**kwargs)

        return self._async_client

    async def generate(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a response using OpenAI.

        Args:
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments (e.g., stop, tools)

        Returns:
            LLMResponse with generated content
        """
        client = self._get_client()
        temp = self._get_temperature(temperature)
        max_tok = self._get_max_tokens(max_tokens)

        try:
            # Build request parameters
            params = {
                "model": self.config.model,
                "messages": self._format_messages(messages),
                "temperature": temp,
                "max_tokens": max_tok,
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "presence_penalty": self.config.presence_penalty,
            }

            # Add optional parameters
            if "stop" in kwargs:
                params["stop"] = kwargs["stop"]
            if "tools" in kwargs:
                params["tools"] = kwargs["tools"]
            if "tool_choice" in kwargs:
                params["tool_choice"] = kwargs["tool_choice"]
            if "response_format" in kwargs:
                params["response_format"] = kwargs["response_format"]

            response = await client.chat.completions.create(**params)

            # Extract usage
            usage = None
            if response.usage:
                usage = LLMUsage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    total_tokens=response.usage.total_tokens,
                )

            # Get content from response
            content = response.choices[0].message.content or ""
            finish_reason = response.choices[0].finish_reason

            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=finish_reason,
                metadata={"id": response.id},
            )

        except Exception as e:
            self._handle_error(e)

    async def stream(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream a response from OpenAI.

        Args:
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments

        Yields:
            String chunks of the response
        """
        client = self._get_client()
        temp = self._get_temperature(temperature)
        max_tok = self._get_max_tokens(max_tokens)

        try:
            params = {
                "model": self.config.model,
                "messages": self._format_messages(messages),
                "temperature": temp,
                "max_tokens": max_tok,
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "presence_penalty": self.config.presence_penalty,
                "stream": True,
            }

            if "stop" in kwargs:
                params["stop"] = kwargs["stop"]

            stream = await client.chat.completions.create(**params)

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            self._handle_error(e)

    def _handle_error(self, error: Exception) -> None:
        """Handle OpenAI API errors."""
        try:
            from openai import (
                APIConnectionError,
                APIError,
                APITimeoutError,
                AuthenticationError,
                BadRequestError,
                RateLimitError,
            )

            if isinstance(error, AuthenticationError):
                raise LLMAuthError(
                    message=str(error),
                    provider=self.provider,
                )
            elif isinstance(error, (APIConnectionError, APITimeoutError)):
                raise LLMConnectionError(
                    message=str(error),
                    provider=self.provider,
                )
            elif isinstance(error, RateLimitError):
                raise LLMRateLimitError(
                    message=str(error),
                    provider=self.provider,
                )
            elif isinstance(error, BadRequestError):
                error_msg = str(error).lower()
                if (
                    "context_length" in error_msg
                    or "maximum context length" in error_msg
                ):
                    raise LLMContextLengthError(
                        message=str(error),
                        provider=self.provider,
                    )
                raise LLMError(
                    message=str(error),
                    provider=self.provider,
                )
            elif isinstance(error, APIError):
                raise LLMError(
                    message=str(error),
                    provider=self.provider,
                )
            else:
                raise LLMError(
                    message=str(error),
                    provider=self.provider,
                )
        except ImportError:
            raise LLMError(
                message=str(error),
                provider=self.provider,
            )

    async def close(self) -> None:
        """Clean up OpenAI client."""
        if self._async_client:
            await self._async_client.close()
            self._async_client = None
