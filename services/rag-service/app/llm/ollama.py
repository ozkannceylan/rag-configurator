"""Ollama LLM implementation for local models."""

import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from app.llm.base import (
    BaseLLM,
    LLMConfig,
    LLMResponse,
    LLMUsage,
    LLMError,
    Message,
)

logger = logging.getLogger(__name__)


class OllamaLLM(BaseLLM):
    """Ollama LLM client for local model inference."""

    # Common local models
    POPULAR_MODELS = [
        "llama3.2",
        "llama3.1",
        "llama3",
        "mistral",
        "mixtral",
        "codellama",
        "phi3",
        "gemma2",
        "qwen2.5",
        "deepseek-coder-v2",
    ]

    DEFAULT_BASE_URL = "http://localhost:11434"

    def __init__(self, config: Optional[LLMConfig] = None):
        """
        Initialize Ollama LLM.

        Args:
            config: LLM configuration
        """
        super().__init__(config)
        self._provider_name = "ollama"
        self._client = None

        # Set default model if not specified
        if self.config.model == "gpt-4o-mini":
            self.config.model = "llama3.2"

        # Set default base URL
        if not self.config.base_url:
            try:
                from app.core.settings import settings
                self.config.base_url = settings.ollama_base_url
            except Exception:
                self.config.base_url = self.DEFAULT_BASE_URL

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url,
                timeout=self.config.timeout_seconds,
            )
        return self._client

    async def generate(
        self,
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate a response using Ollama.

        Args:
            messages: List of messages
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional arguments (e.g., options)

        Returns:
            LLMResponse with generated content
        """
        client = self._get_client()
        temp = self._get_temperature(temperature)
        max_tok = self._get_max_tokens(max_tokens)

        try:
            # Build request payload
            payload = {
                "model": self.config.model,
                "messages": self._format_messages(messages),
                "stream": False,
                "options": {
                    "temperature": temp,
                    "num_predict": max_tok,
                    "top_p": self.config.top_p,
                },
            }

            # Add extra options if provided
            if "options" in kwargs:
                payload["options"].update(kwargs["options"])

            # Add format if specified (e.g., "json")
            if "format" in kwargs:
                payload["format"] = kwargs["format"]

            response = await client.post("/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract usage if available
            usage = None
            if "prompt_eval_count" in data or "eval_count" in data:
                usage = LLMUsage(
                    prompt_tokens=data.get("prompt_eval_count", 0),
                    completion_tokens=data.get("eval_count", 0),
                    total_tokens=(
                        data.get("prompt_eval_count", 0) + data.get("eval_count", 0)
                    ),
                )

            # Get content from response
            content = data.get("message", {}).get("content", "")

            return LLMResponse(
                content=content,
                model=data.get("model", self.config.model),
                usage=usage,
                finish_reason=data.get("done_reason", "stop" if data.get("done") else None),
                metadata={
                    "total_duration": data.get("total_duration"),
                    "load_duration": data.get("load_duration"),
                    "eval_duration": data.get("eval_duration"),
                },
            )

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
        except httpx.RequestError as e:
            raise LLMError(
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
        messages: List[Message],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream a response from Ollama.

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
                "stream": True,
                "options": {
                    "temperature": temp,
                    "num_predict": max_tok,
                    "top_p": self.config.top_p,
                },
            }

            if "options" in kwargs:
                payload["options"].update(kwargs["options"])

            if "format" in kwargs:
                payload["format"] = kwargs["format"]

            async with client.stream("POST", "/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        import json
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                content = data["message"]["content"]
                                if content:
                                    yield content
                            if data.get("done"):
                                break
                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            self._handle_http_error(e)
        except httpx.RequestError as e:
            raise LLMError(
                message=f"Connection error: {str(e)}",
                provider=self.provider,
            )
        except Exception as e:
            raise LLMError(
                message=str(e),
                provider=self.provider,
            )

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models in Ollama.

        Returns:
            List of model information dictionaries
        """
        client = self._get_client()

        try:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def pull_model(self, model_name: str) -> bool:
        """
        Pull a model from Ollama library.

        Args:
            model_name: Name of the model to pull

        Returns:
            True if successful
        """
        client = self._get_client()

        try:
            response = await client.post(
                "/api/pull",
                json={"name": model_name},
                timeout=600.0,  # 10 minutes for large models
            )
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to pull model {model_name}: {e}")
            return False

    async def is_available(self) -> bool:
        """
        Check if Ollama is available.

        Returns:
            True if Ollama server is reachable
        """
        client = self._get_client()

        try:
            response = await client.get("/")
            return response.status_code == 200
        except Exception:
            return False

    def _handle_http_error(self, error: httpx.HTTPStatusError) -> None:
        """Handle HTTP errors from Ollama."""
        status_code = error.response.status_code

        if status_code == 404:
            raise LLMError(
                message=f"Model '{self.config.model}' not found. Pull it with: ollama pull {self.config.model}",
                provider=self.provider,
            )
        elif status_code == 500:
            raise LLMError(
                message="Ollama server error. Check server logs.",
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
