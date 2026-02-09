"""Tests for LLM module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.base import (
    BaseLLM,
    Message,
    MessageRole,
    LLMConfig,
    LLMResponse,
    LLMUsage,
    LLMError,
    LLMRateLimitError,
    LLMAuthenticationError,
    LLMContextLengthError,
)
from app.llm.factory import (
    get_llm,
    get_llm_from_config,
    LLMProvider,
    create_llm_config,
    list_providers,
    DEFAULT_MODELS,
)


class TestMessage:
    """Tests for Message class."""

    def test_create_message(self):
        """Test creating a message."""
        msg = Message(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.name is None

    def test_message_to_dict(self):
        """Test converting message to dictionary."""
        msg = Message(role="assistant", content="Hi there")
        data = msg.to_dict()

        assert data["role"] == "assistant"
        assert data["content"] == "Hi there"
        assert "name" not in data

    def test_message_with_name(self):
        """Test message with name."""
        msg = Message(role="user", content="Hello", name="John")
        data = msg.to_dict()

        assert data["name"] == "John"

    def test_system_message_factory(self):
        """Test system message factory."""
        msg = Message.system("You are a helpful assistant.")

        assert msg.role == "system"
        assert msg.content == "You are a helpful assistant."

    def test_user_message_factory(self):
        """Test user message factory."""
        msg = Message.user("What is Python?")

        assert msg.role == "user"
        assert msg.content == "What is Python?"

    def test_assistant_message_factory(self):
        """Test assistant message factory."""
        msg = Message.assistant("Python is a programming language.")

        assert msg.role == "assistant"
        assert msg.content == "Python is a programming language."


class TestMessageRole:
    """Tests for MessageRole enum."""

    def test_role_values(self):
        """Test message role values."""
        assert MessageRole.SYSTEM.value == "system"
        assert MessageRole.USER.value == "user"
        assert MessageRole.ASSISTANT.value == "assistant"


class TestLLMUsage:
    """Tests for LLMUsage class."""

    def test_create_usage(self):
        """Test creating usage stats."""
        usage = LLMUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )

        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150

    def test_usage_to_dict(self):
        """Test converting usage to dictionary."""
        usage = LLMUsage(
            prompt_tokens=100,
            completion_tokens=50,
            total_tokens=150,
        )
        data = usage.to_dict()

        assert data["prompt_tokens"] == 100
        assert data["completion_tokens"] == 50
        assert data["total_tokens"] == 150

    def test_default_usage(self):
        """Test default usage values."""
        usage = LLMUsage()

        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0
        assert usage.total_tokens == 0


class TestLLMResponse:
    """Tests for LLMResponse class."""

    def test_create_response(self):
        """Test creating response."""
        response = LLMResponse(
            content="Hello, world!",
            model="gpt-4o-mini",
        )

        assert response.content == "Hello, world!"
        assert response.model == "gpt-4o-mini"
        assert response.usage is None

    def test_response_with_usage(self):
        """Test response with usage stats."""
        usage = LLMUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        response = LLMResponse(
            content="Test",
            model="gpt-4o-mini",
            usage=usage,
            finish_reason="stop",
        )

        assert response.usage.total_tokens == 15
        assert response.finish_reason == "stop"

    def test_response_to_dict(self):
        """Test converting response to dictionary."""
        response = LLMResponse(
            content="Test content",
            model="claude-3-5-sonnet-20241022",
            usage=LLMUsage(prompt_tokens=20, completion_tokens=10, total_tokens=30),
            finish_reason="end_turn",
        )
        data = response.to_dict()

        assert data["content"] == "Test content"
        assert data["model"] == "claude-3-5-sonnet-20241022"
        assert data["usage"]["total_tokens"] == 30
        assert data["finish_reason"] == "end_turn"


class TestLLMConfig:
    """Tests for LLMConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = LLMConfig()

        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048
        assert config.top_p == 1.0
        assert config.timeout_seconds == 60.0
        assert config.max_retries == 3

    def test_custom_config(self):
        """Test custom configuration."""
        config = LLMConfig(
            model="gpt-4",
            temperature=0.3,
            max_tokens=4096,
            api_key="sk-test",
            base_url="https://api.example.com",
        )

        assert config.model == "gpt-4"
        assert config.temperature == 0.3
        assert config.max_tokens == 4096
        assert config.api_key == "sk-test"
        assert config.base_url == "https://api.example.com"

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "model": "llama3.2",
            "temperature": 0.5,
            "max_tokens": 1024,
            "timeout_seconds": 120.0,
        }
        config = LLMConfig.from_dict(data)

        assert config.model == "llama3.2"
        assert config.temperature == 0.5
        assert config.max_tokens == 1024
        assert config.timeout_seconds == 120.0


class TestLLMErrors:
    """Tests for LLM error classes."""

    def test_base_error(self):
        """Test base LLM error."""
        error = LLMError("Test error", provider="openai")

        assert "Test error" in str(error)
        assert error.provider == "openai"

    def test_rate_limit_error(self):
        """Test rate limit error."""
        error = LLMRateLimitError(
            message="Rate limit exceeded",
            provider="openai",
            retry_after=30.0,
        )

        assert error.retry_after == 30.0
        assert "Rate limit" in str(error)

    def test_auth_error(self):
        """Test authentication error."""
        error = LLMAuthenticationError(
            message="Invalid API key",
            provider="anthropic",
        )

        assert "Invalid API key" in str(error)
        assert error.provider == "anthropic"

    def test_context_length_error(self):
        """Test context length error."""
        error = LLMContextLengthError(
            message="Context too long",
            provider="openai",
            max_tokens=128000,
        )

        assert error.max_tokens == 128000
        assert "Context too long" in str(error)


class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_provider_values(self):
        """Test provider values."""
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"
        assert LLMProvider.OLLAMA.value == "ollama"
        assert LLMProvider.VLLM.value == "vllm"

    def test_all_providers_have_default_models(self):
        """Test all providers have default models."""
        for provider in LLMProvider:
            assert provider in DEFAULT_MODELS


class TestGetLLM:
    """Tests for get_llm factory function."""

    def test_get_openai_llm(self):
        """Test getting OpenAI LLM."""
        from app.llm.openai import OpenAILLM

        llm = get_llm(LLMProvider.OPENAI)

        assert isinstance(llm, OpenAILLM)
        assert llm.provider == "openai"

    def test_get_anthropic_llm(self):
        """Test getting Anthropic LLM."""
        from app.llm.anthropic import AnthropicLLM

        llm = get_llm(LLMProvider.ANTHROPIC)

        assert isinstance(llm, AnthropicLLM)
        assert llm.provider == "anthropic"

    def test_get_ollama_llm(self):
        """Test getting Ollama LLM."""
        from app.llm.ollama import OllamaLLM

        llm = get_llm(LLMProvider.OLLAMA)

        assert isinstance(llm, OllamaLLM)
        assert llm.provider == "ollama"

    def test_get_vllm(self):
        """Test getting vLLM."""
        from app.llm.vllm import VLLMLlm

        llm = get_llm(LLMProvider.VLLM)

        assert isinstance(llm, VLLMLlm)
        assert llm.provider == "vllm"

    def test_get_llm_with_config(self):
        """Test getting LLM with custom config."""
        config = LLMConfig(model="gpt-4", temperature=0.3)
        llm = get_llm(LLMProvider.OPENAI, config=config)

        assert llm.config.model == "gpt-4"
        assert llm.config.temperature == 0.3

    def test_get_llm_with_kwargs(self):
        """Test getting LLM with kwargs."""
        llm = get_llm(
            LLMProvider.OPENAI,
            model="gpt-4-turbo",
            api_key="sk-test",
            temperature=0.5,
        )

        assert llm.config.model == "gpt-4-turbo"
        assert llm.config.api_key == "sk-test"
        assert llm.config.temperature == 0.5


class TestGetLLMFromConfig:
    """Tests for get_llm_from_config function."""

    def test_from_openai_config(self):
        """Test creating LLM from OpenAI config."""
        from app.llm.openai import OpenAILLM

        config = {
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "temperature": 0.7,
            }
        }
        llm = get_llm_from_config(config)

        assert isinstance(llm, OpenAILLM)
        assert llm.config.model == "gpt-4o-mini"

    def test_from_anthropic_config(self):
        """Test creating LLM from Anthropic config."""
        from app.llm.anthropic import AnthropicLLM

        config = {
            "llm": {
                "provider": "anthropic",
                "model": "claude-3-5-sonnet-20241022",
            }
        }
        llm = get_llm_from_config(config)

        assert isinstance(llm, AnthropicLLM)

    def test_from_ollama_config(self):
        """Test creating LLM from Ollama config."""
        from app.llm.ollama import OllamaLLM

        config = {
            "llm": {
                "provider": "ollama",
                "model": "llama3.2",
                "base_url": "http://localhost:11434",
            }
        }
        llm = get_llm_from_config(config)

        assert isinstance(llm, OllamaLLM)
        assert llm.config.model == "llama3.2"

    def test_from_empty_config(self):
        """Test creating LLM from empty config defaults to OpenAI."""
        from app.llm.openai import OpenAILLM

        config = {}
        llm = get_llm_from_config(config)

        assert isinstance(llm, OpenAILLM)

    def test_unknown_provider_defaults_to_openai(self):
        """Test unknown provider defaults to OpenAI."""
        from app.llm.openai import OpenAILLM

        config = {"llm": {"provider": "unknown_provider"}}
        llm = get_llm_from_config(config)

        assert isinstance(llm, OpenAILLM)


class TestCreateLLMConfig:
    """Tests for create_llm_config helper."""

    def test_default_config(self):
        """Test creating config with defaults."""
        config = create_llm_config()

        assert config.model == "gpt-4o-mini"
        assert config.temperature == 0.7
        assert config.max_tokens == 2048

    def test_custom_config(self):
        """Test creating config with custom values."""
        config = create_llm_config(
            model="llama3.2",
            temperature=0.5,
            max_tokens=4096,
            api_key="test-key",
            base_url="http://localhost:11434",
        )

        assert config.model == "llama3.2"
        assert config.temperature == 0.5
        assert config.max_tokens == 4096
        assert config.api_key == "test-key"


class TestListProviders:
    """Tests for list_providers function."""

    def test_list_providers(self):
        """Test listing all providers."""
        providers = list_providers()

        assert "openai" in providers
        assert "anthropic" in providers
        assert "ollama" in providers
        assert "vllm" in providers

    def test_provider_info(self):
        """Test provider information."""
        providers = list_providers()

        assert providers["openai"]["default_model"] == "gpt-4o-mini"
        assert "description" in providers["openai"]


class TestOpenAILLM:
    """Tests for OpenAI LLM."""

    def test_create_openai_llm(self):
        """Test creating OpenAI LLM."""
        from app.llm.openai import OpenAILLM

        llm = OpenAILLM()

        assert llm.provider == "openai"
        assert llm.config.model == "gpt-4o-mini"

    def test_openai_supported_models(self):
        """Test OpenAI supported models."""
        from app.llm.openai import OpenAILLM

        assert "gpt-4o" in OpenAILLM.SUPPORTED_MODELS
        assert "gpt-4o-mini" in OpenAILLM.SUPPORTED_MODELS
        assert "gpt-3.5-turbo" in OpenAILLM.SUPPORTED_MODELS


class TestAnthropicLLM:
    """Tests for Anthropic LLM."""

    def test_create_anthropic_llm(self):
        """Test creating Anthropic LLM."""
        from app.llm.anthropic import AnthropicLLM

        config = LLMConfig(model="claude-3-5-sonnet-20241022")
        llm = AnthropicLLM(config=config)

        assert llm.provider == "anthropic"
        assert llm.config.model == "claude-3-5-sonnet-20241022"

    def test_anthropic_supported_models(self):
        """Test Anthropic supported models."""
        from app.llm.anthropic import AnthropicLLM

        assert "claude-3-5-sonnet-20241022" in AnthropicLLM.SUPPORTED_MODELS
        assert "claude-3-opus-20240229" in AnthropicLLM.SUPPORTED_MODELS

    def test_anthropic_message_preparation(self):
        """Test Anthropic message preparation."""
        from app.llm.anthropic import AnthropicLLM

        llm = AnthropicLLM()
        messages = [
            Message.system("You are helpful."),
            Message.user("Hello"),
        ]

        system_content, conversation = llm._prepare_messages(messages)

        assert system_content == "You are helpful."
        assert len(conversation) == 1
        assert conversation[0]["role"] == "user"


class TestOllamaLLM:
    """Tests for Ollama LLM."""

    def test_create_ollama_llm(self):
        """Test creating Ollama LLM."""
        from app.llm.ollama import OllamaLLM

        llm = OllamaLLM()

        assert llm.provider == "ollama"
        assert llm.config.base_url == "http://localhost:11434"

    def test_ollama_default_model(self):
        """Test Ollama default model."""
        from app.llm.ollama import OllamaLLM

        llm = OllamaLLM()

        assert llm.config.model == "llama3.2"

    def test_ollama_custom_base_url(self):
        """Test Ollama with custom base URL."""
        from app.llm.ollama import OllamaLLM

        config = LLMConfig(base_url="http://192.168.1.100:11434")
        llm = OllamaLLM(config=config)

        assert llm.config.base_url == "http://192.168.1.100:11434"


class TestVLLM:
    """Tests for vLLM."""

    def test_create_vllm(self):
        """Test creating vLLM."""
        from app.llm.vllm import VLLMLlm

        llm = VLLMLlm()

        assert llm.provider == "vllm"
        assert llm.config.base_url == "http://localhost:8000"

    def test_vllm_custom_config(self):
        """Test vLLM with custom config."""
        from app.llm.vllm import VLLMLlm

        config = LLMConfig(
            model="meta-llama/Llama-2-7b-chat-hf",
            base_url="http://gpu-server:8000",
            api_key="vllm-api-key",
        )
        llm = VLLMLlm(config=config)

        assert llm.config.model == "meta-llama/Llama-2-7b-chat-hf"
        assert llm.config.base_url == "http://gpu-server:8000"


class TestBaseLLM:
    """Tests for BaseLLM abstract class."""

    def test_cannot_instantiate_base(self):
        """Test that BaseLLM cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseLLM()

    def test_format_messages(self):
        """Test message formatting."""
        from app.llm.openai import OpenAILLM

        llm = OpenAILLM()
        messages = [
            Message.system("System prompt"),
            Message.user("User message"),
        ]

        formatted = llm._format_messages(messages)

        assert len(formatted) == 2
        assert formatted[0]["role"] == "system"
        assert formatted[1]["role"] == "user"

    def test_get_temperature(self):
        """Test temperature getter."""
        from app.llm.openai import OpenAILLM

        config = LLMConfig(temperature=0.5)
        llm = OpenAILLM(config=config)

        # Override should be used
        assert llm._get_temperature(0.8) == 0.8
        # Config default should be used
        assert llm._get_temperature(None) == 0.5

    def test_get_max_tokens(self):
        """Test max tokens getter."""
        from app.llm.openai import OpenAILLM

        config = LLMConfig(max_tokens=1024)
        llm = OpenAILLM(config=config)

        # Override should be used
        assert llm._get_max_tokens(2048) == 2048
        # Config default should be used
        assert llm._get_max_tokens(None) == 1024


class TestVLLMCompletions:
    """Tests for vLLM completions API."""

    def test_messages_to_prompt(self):
        """Test converting messages to prompt."""
        from app.llm.vllm import VLLMCompletionsLLM

        llm = VLLMCompletionsLLM()
        messages = [
            Message.system("You are helpful."),
            Message.user("Hello"),
            Message.assistant("Hi there!"),
            Message.user("How are you?"),
        ]

        prompt = llm._messages_to_prompt(messages)

        assert "System: You are helpful." in prompt
        assert "User: Hello" in prompt
        assert "Assistant: Hi there!" in prompt
        assert "User: How are you?" in prompt
        assert prompt.endswith("Assistant:")
