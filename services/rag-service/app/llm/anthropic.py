"""Anthropic LLM implementation."""

import logging
from typing import Any, AsyncIterator, List, Optional

from app.llm.base import (
    BaseLLM,
    LLMConfig,
    LLMResponse,
    LLMUsage,
    LLMError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMContextLengthError,
    Message,
)

logger = logging.getLogger(__name__)


class AnthropicLLM(BaseLLM):
    """Anthropic Claude LLM client."""

    # Supported models
    SUPPORTED_MODELS = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]

    # Default max tokens for Claude models
    DEFAULT_MAX_TOKENS = 4096

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize Anthropic LLM.

        Args:
            config: LLM configuration
        """
        super().__init__(config)
        self._provider_name = "anthropic"
        self._client = None

        # Set default model if not specified
        if self.config.model == "gpt-4o-mini":
            self.config.model = "claude-3-5-sonnet-20241022"

    def _get_client(self):
        """Get or create Anthropic async client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
            except ImportError:
                raise LLMError(
                    "anthropic package not installed. Install with: pip install anthropic",
                    provider=self.provider,
                )

            kwargs = {}
            if self.config.api_key:
                kwargs["api_key"] = self.config.api_key
            if self.config.base_url:
                kwargs["base_url"] = self.config.base_url
            if self.config.timeout_seconds:
                kwargs["timeout"] = self.config.timeout_seconds

            self._client = AsyncAnthropic(**kwargs)

        return self._client

    async def generate(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a response using Anthropic Claude.

        Args:
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments (e.g., stop_sequences)

        Returns:
            LLMResponse with generated content
        """
        client = self._get_client()
        temp = self._get_temperature(temperature)
        max_tok = max_tokens if max_tokens is not None else self.DEFAULT_MAX_TOKENS

        try:
            # Separate system message from conversation
            system_content, conversation = self._prepare_messages(messages)

            # Build request parameters
            params = {
                "model": self.config.model,
                "messages": conversation,
                "max_tokens": max_tok,
                "temperature": temp,
                "top_p": self.config.top_p,
            }

            # Add system prompt if present
            if system_content:
                params["system"] = system_content

            # Add optional parameters
            if "stop_sequences" in kwargs:
                params["stop_sequences"] = kwargs["stop_sequences"]
            if "tools" in kwargs:
                params["tools"] = kwargs["tools"]
            if "tool_choice" in kwargs:
                params["tool_choice"] = kwargs["tool_choice"]

            response = await client.messages.create(**params)

            # Extract usage
            usage = None
            if response.usage:
                usage = LLMUsage(
                    prompt_tokens=response.usage.input_tokens,
                    completion_tokens=response.usage.output_tokens,
                    total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                )

            # Get content from response
            content = ""
            if response.content:
                for block in response.content:
                    if hasattr(block, "text"):
                        content += block.text

            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                finish_reason=response.stop_reason,
                metadata={"id": response.id},
            )

        except Exception as e:
            self._handle_error(e)

    async def stream(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream a response from Anthropic Claude.

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
        max_tok = max_tokens if max_tokens is not None else self.DEFAULT_MAX_TOKENS

        try:
            # Separate system message from conversation
            system_content, conversation = self._prepare_messages(messages)

            params = {
                "model": self.config.model,
                "messages": conversation,
                "max_tokens": max_tok,
                "temperature": temp,
                "top_p": self.config.top_p,
            }

            if system_content:
                params["system"] = system_content

            if "stop_sequences" in kwargs:
                params["stop_sequences"] = kwargs["stop_sequences"]

            async with client.messages.stream(**params) as stream:
                async for text in stream.text_stream:
                    yield text

        except Exception as e:
            self._handle_error(e)

    def _prepare_messages(
        self, messages: List[Message]
    ) -> tuple[Optional[str], List[dict]]:
        """
        Prepare messages for Anthropic API.

        Anthropic expects system messages separately.

        Args:
            messages: List of messages

        Returns:
            Tuple of (system_content, conversation_messages)
        """
        system_content = None
        conversation = []

        for msg in messages:
            if msg.role == "system":
                # Anthropic uses separate system parameter
                system_content = msg.content
            else:
                conversation.append({
                    "role": msg.role,
                    "content": msg.content,
                })

        return system_content, conversation

    def _handle_error(self, error: Exception) -> None:
        """Handle Anthropic API errors."""
        try:
            from anthropic import (
                APIError,
                AuthenticationError,
                RateLimitError,
                BadRequestError,
            )

            if isinstance(error, AuthenticationError):
                raise LLMAuthenticationError(
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
                if "context" in error_msg or "tokens" in error_msg:
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
        """Clean up Anthropic client."""
        if self._client:
            await self._client.close()
            self._client = None
