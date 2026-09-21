"""vLLM client for self-hosted inference servers."""

import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.llm.base import BaseLLM, LLMConfig, LLMResponse, LLMUsage, Message
from app.llm.exceptions import LLMAuthError, LLMConnectionError, LLMError

logger = logging.getLogger(__name__)


class VLLMLlm(BaseLLM):
    """vLLM client for OpenAI-compatible inference servers."""

    DEFAULT_BASE_URL = "http://localhost:8000"

    def __init__(self, config: LLMConfig | None = None):
        """
        Initialize vLLM client.

        Args:
            config: LLM configuration
        """
        super().__init__(config)
        self._provider_name = "vllm"
        self._client = None

        # Set default base URL
        if not self.config.base_url:
            self.config.base_url = self.DEFAULT_BASE_URL

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {}
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key}"

            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout_seconds,
                headers=headers,
            )
        return self._client

    async def generate(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a response using vLLM.

        vLLM provides an OpenAI-compatible API.

        Args:
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments

        Returns:
            LLMResponse with generated content
        """
        client = self._get_client()
        temp = self._get_temperature(temperature)
        max_tok = self._get_max_tokens(max_tokens)

        try:
            # Build request payload (OpenAI-compatible)
            payload = {
                "model": self.config.model,
                "messages": self._format_messages(messages),
                "temperature": temp,
                "max_tokens": max_tok,
                "top_p": self.config.top_p,
                "frequency_penalty": self.config.frequency_penalty,
                "presence_penalty": self.config.presence_penalty,
                "stream": False,
            }

            # Add optional parameters
            if "stop" in kwargs:
                payload["stop"] = kwargs["stop"]
            if "best_of" in kwargs:
                payload["best_of"] = kwargs["best_of"]
            if "use_beam_search" in kwargs:
                payload["use_beam_search"] = kwargs["use_beam_search"]
            if "skip_special_tokens" in kwargs:
                payload["skip_special_tokens"] = kwargs["skip_special_tokens"]

            response = await client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract usage
            usage = None
            if "usage" in data:
                usage = LLMUsage(
                    prompt_tokens=data["usage"].get("prompt_tokens", 0),
                    completion_tokens=data["usage"].get("completion_tokens", 0),
                    total_tokens=data["usage"].get("total_tokens", 0),
                )

            # Get content from response
            content = ""
            if data.get("choices"):
                content = data["choices"][0].get("message", {}).get("content", "")

            finish_reason = None
            if data.get("choices"):
                finish_reason = data["choices"][0].get("finish_reason")

            return LLMResponse(
                content=content,
                model=data.get("model", self.config.model),
                usage=usage,
                finish_reason=finish_reason,
                metadata={"id": data.get("id")},
            )

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
        except httpx.RequestError as e:
            raise LLMConnectionError(
                message=f"Connection error: {str(e)}",
                provider=self.provider,
            )
        except Exception as e:
            raise LLMError(
                message=str(e),
                provider=self.provider,
            )

    async def stream(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream a response from vLLM.

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
            payload = {
                "model": self.config.model,
                "messages": self._format_messages(messages),
                "temperature": temp,
                "max_tokens": max_tok,
                "top_p": self.config.top_p,
                "stream": True,
            }

            if "stop" in kwargs:
                payload["stop"] = kwargs["stop"]

            async with client.stream(
                "POST", "/v1/chat/completions", json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str.strip() == "[DONE]":
                            break

                        import json

                        try:
                            data = json.loads(data_str)
                            if data.get("choices"):
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
        except httpx.RequestError as e:
            raise LLMConnectionError(
                message=f"Connection error: {str(e)}",
                provider=self.provider,
            )
        except Exception as e:
            raise LLMError(
                message=str(e),
                provider=self.provider,
            )

    async def list_models(self) -> list[dict[str, Any]]:
        """
        List available models from vLLM server.

        Returns:
            List of model information dictionaries
        """
        client = self._get_client()

        try:
            response = await client.get("/v1/models")
            response.raise_for_status()
            data = response.json()
            return data.get("data", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def get_model_info(self) -> dict[str, Any] | None:
        """
        Get information about the current model.

        Returns:
            Model information dictionary or None
        """
        models = await self.list_models()
        for model in models:
            if model.get("id") == self.config.model:
                return model
        return None

    async def is_available(self) -> bool:
        """
        Check if vLLM server is available.

        Returns:
            True if server is reachable
        """
        client = self._get_client()

        try:
            response = await client.get("/health")
            # Some vLLM deployments use /v1/models for health check
            if response.status_code != 200:
                response = await client.get("/v1/models")
            return response.status_code == 200
        except Exception:
            return False

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle HTTP errors from vLLM."""
        status_code = error.response.status_code

        if status_code == 401:
            raise LLMAuthError(
                message="Invalid API key",
                provider=self.provider,
            )
        elif status_code == 404:
            raise LLMError(
                message=f"Model '{self.config.model}' not found on vLLM server",
                provider=self.provider,
            )
        elif status_code == 500:
            raise LLMError(
                message="vLLM server error. Check server logs.",
                provider=self.provider,
            )
        else:
            raise LLMError(
                message=f"HTTP error {status_code}: {error.response.text}",
                provider=self.provider,
            )

    async def close(self) -> None:
        """Clean up HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


# Completions API support for text completion (non-chat)
class VLLMCompletionsLLM(VLLMLlm):
    """vLLM client using completions API instead of chat API."""

    async def generate(
        self,
        messages: list[Message],
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate using completions API.

        Converts messages to a single prompt string.
        """
        client = self._get_client()
        temp = self._get_temperature(temperature)
        max_tok = self._get_max_tokens(max_tokens)

        # Convert messages to prompt
        prompt = self._messages_to_prompt(messages)

        try:
            payload = {
                "model": self.config.model,
                "prompt": prompt,
                "temperature": temp,
                "max_tokens": max_tok,
                "top_p": self.config.top_p,
                "stream": False,
            }

            if "stop" in kwargs:
                payload["stop"] = kwargs["stop"]

            response = await client.post("/v1/completions", json=payload)
            response.raise_for_status()
            data = response.json()

            usage = None
            if "usage" in data:
                usage = LLMUsage(
                    prompt_tokens=data["usage"].get("prompt_tokens", 0),
                    completion_tokens=data["usage"].get("completion_tokens", 0),
                    total_tokens=data["usage"].get("total_tokens", 0),
                )

            content = ""
            if data.get("choices"):
                content = data["choices"][0].get("text", "")

            return LLMResponse(
                content=content,
                model=data.get("model", self.config.model),
                usage=usage,
                finish_reason=(
                    data["choices"][0].get("finish_reason")
                    if data.get("choices")
                    else None
                ),
            )

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
        except Exception as e:
            raise LLMError(message=str(e), provider=self.provider)

    def _messages_to_prompt(self, messages: list[Message]) -> str:
        """Convert messages to a single prompt string."""
        parts = []
        for msg in messages:
            if msg.role == "system":
                parts.append(f"System: {msg.content}\n")
            elif msg.role == "user":
                parts.append(f"User: {msg.content}\n")
            elif msg.role == "assistant":
                parts.append(f"Assistant: {msg.content}\n")
        parts.append("Assistant:")
        return "".join(parts)
