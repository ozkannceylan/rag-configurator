"""Tests for prompt management module."""

import pytest
from unittest.mock import patch, MagicMock

from app.prompts.manager import (
    PromptManager,
    PromptConfig,
    PromptTemplate,
    PromptError,
)


class TestPromptTemplate:
    """Tests for PromptTemplate class."""

    def test_create_template(self):
        """Test creating a template."""
        template = PromptTemplate(
            name="test",
            content="Hello {name}!",
            category="system",
        )

        assert template.name == "test"
        assert template.content == "Hello {name}!"
        assert template.category == "system"

    def test_extract_variables(self):
        """Test variable extraction."""
        template = PromptTemplate(
            name="test",
            content="Context: {context}\nQuery: {query}",
        )

        assert "context" in template.variables
        assert "query" in template.variables
        assert len(template.variables) == 2

    def test_format_template(self):
        """Test template formatting."""
        template = PromptTemplate(
            name="test",
            content="Hello {name}, you are {age} years old.",
        )

        result = template.format(name="Alice", age=30)

        assert result == "Hello Alice, you are 30 years old."

    def test_format_missing_variable(self):
        """Test formatting with missing variable."""
        template = PromptTemplate(
            name="test",
            content="Hello {name}, welcome to {place}.",
        )

        # Missing variables should stay as placeholders
        result = template.format(name="Bob")

        assert result == "Hello Bob, welcome to {place}."

    def test_validate_variables(self):
        """Test variable validation."""
        template = PromptTemplate(
            name="test",
            content="Context: {context}, Query: {query}",
        )

        # All provided
        missing = template.validate_variables(context="ctx", query="q")
        assert len(missing) == 0

        # Missing one
        missing = template.validate_variables(context="ctx")
        assert "query" in missing

    def test_to_dict(self):
        """Test converting to dictionary."""
        template = PromptTemplate(
            name="test",
            content="Test content",
            category="rag",
            version="2.0.0",
            description="A test template",
        )

        data = template.to_dict()

        assert data["name"] == "test"
        assert data["content"] == "Test content"
        assert data["category"] == "rag"
        assert data["version"] == "2.0.0"
        assert data["description"] == "A test template"


class TestPromptConfig:
    """Tests for PromptConfig class."""

    def test_default_config(self):
        """Test default configuration."""
        config = PromptConfig()

        assert config.system_prompt is None
        assert config.system_prompt_name == "default"
        assert config.rag_prompt_name == "default"
        assert config.track_prompts is False

    def test_custom_config(self):
        """Test custom configuration."""
        config = PromptConfig(
            system_prompt="Custom system",
            rag_prompt_name="with_history",
            track_prompts=True,
            mlflow_experiment="test_exp",
        )

        assert config.system_prompt == "Custom system"
        assert config.rag_prompt_name == "with_history"
        assert config.track_prompts is True
        assert config.mlflow_experiment == "test_exp"

    def test_config_from_dict(self):
        """Test creating config from dictionary."""
        data = {
            "system_prompt_name": "detailed",
            "rag_prompt_name": "structured",
            "track_prompts": True,
            "custom_templates": {"my_prompt": "Custom content"},
        }

        config = PromptConfig.from_dict(data)

        assert config.system_prompt_name == "detailed"
        assert config.rag_prompt_name == "structured"
        assert config.track_prompts is True
        assert "my_prompt" in config.custom_templates


class TestPromptManager:
    """Tests for PromptManager class."""

    def test_create_manager(self):
        """Test creating prompt manager."""
        manager = PromptManager()

        assert manager.config is not None
        assert manager.track is False

    def test_create_manager_with_config(self):
        """Test creating manager with config."""
        config = PromptConfig(
            system_prompt_name="technical",
            track_prompts=True,
        )
        manager = PromptManager(config=config)

        assert manager.config.system_prompt_name == "technical"

    def test_get_system_prompt_default(self):
        """Test getting default system prompt."""
        manager = PromptManager()
        prompt = manager.get_system_prompt()

        assert len(prompt) > 0
        assert "helpful" in prompt.lower() or "assistant" in prompt.lower()

    def test_get_system_prompt_named(self):
        """Test getting named system prompt."""
        manager = PromptManager()
        prompt = manager.get_system_prompt("technical")

        assert "technical" in prompt.lower()

    def test_get_system_prompt_override(self):
        """Test system prompt config override."""
        config = PromptConfig(system_prompt="Custom system prompt")
        manager = PromptManager(config=config)
        prompt = manager.get_system_prompt()

        assert prompt == "Custom system prompt"

    def test_get_rag_prompt(self):
        """Test getting RAG prompt."""
        manager = PromptManager()
        prompt = manager.get_rag_prompt(
            context="Python is a programming language.",
            query="What is Python?",
        )

        assert "Python is a programming language" in prompt
        assert "What is Python" in prompt

    def test_get_rag_prompt_with_history(self):
        """Test RAG prompt with history."""
        manager = PromptManager()
        prompt = manager.get_rag_prompt(
            context="Context here",
            query="Follow-up question",
            name="with_history",
            history="User: Hello\nAssistant: Hi there!",
        )

        assert "Context here" in prompt
        assert "Follow-up question" in prompt
        # History should be substituted
        assert "{history}" not in prompt

    def test_get_rag_prompt_override(self):
        """Test RAG prompt config override."""
        config = PromptConfig(
            rag_prompt="Custom: {context}\nQ: {query}"
        )
        manager = PromptManager(config=config)
        prompt = manager.get_rag_prompt(
            context="Test context",
            query="Test query",
        )

        assert prompt == "Custom: Test context\nQ: Test query"

    def test_get_judge_prompt(self):
        """Test getting judge prompt."""
        manager = PromptManager()
        prompt = manager.get_judge_prompt(
            prompt_type="relevance",
            query="What is Python?",
            context="Python is a language.",
        )

        assert "What is Python" in prompt
        assert "Python is a language" in prompt

    def test_get_judge_prompt_unknown_type(self):
        """Test unknown judge prompt type raises error."""
        manager = PromptManager()

        with pytest.raises(PromptError):
            manager.get_judge_prompt(
                prompt_type="unknown_type",
                query="test",
            )

    def test_get_agent_prompt(self):
        """Test getting agent prompt."""
        manager = PromptManager()
        prompt = manager.get_agent_prompt(
            agent_type="query_rewriter",
            query="What is ML?",
            history="",
        )

        assert "What is ML" in prompt

    def test_get_agent_prompt_unknown_type(self):
        """Test unknown agent type raises error."""
        manager = PromptManager()

        with pytest.raises(PromptError):
            manager.get_agent_prompt(
                agent_type="unknown_agent",
                query="test",
            )

    def test_list_templates(self):
        """Test listing templates."""
        manager = PromptManager()
        templates = manager.list_templates()

        assert "system" in templates
        assert "rag" in templates
        assert "judge" in templates
        assert "agent" in templates
        assert "default" in templates["system"]

    def test_list_templates_by_category(self):
        """Test listing templates by category."""
        manager = PromptManager()
        templates = manager.list_templates(category="judge")

        assert "judge" in templates
        assert "system" not in templates
        assert "relevance" in templates["judge"]

    def test_add_template(self):
        """Test adding custom template."""
        manager = PromptManager()
        template = manager.add_template(
            name="custom_rag",
            content="Custom: {context} | {query}",
            category="rag",
            description="A custom RAG template",
        )

        assert template.name == "custom_rag"
        assert "custom_rag" in manager.list_templates("rag")["rag"]

    def test_get_template(self):
        """Test getting specific template."""
        manager = PromptManager()
        template = manager.get_template("system", "default")

        assert template is not None
        assert template.name == "default"

    def test_get_template_not_found(self):
        """Test getting non-existent template."""
        manager = PromptManager()
        template = manager.get_template("system", "nonexistent")

        assert template is None


class TestPromptManagerFormatting:
    """Tests for context and history formatting."""

    def test_format_context_numbered(self):
        """Test numbered context formatting."""
        manager = PromptManager()
        chunks = [
            {"content": "First chunk", "source": "doc1.pdf"},
            {"content": "Second chunk", "source": "doc2.pdf"},
        ]

        result = manager.format_context(chunks, format_type="numbered")

        assert "[1]" in result
        assert "[2]" in result
        assert "First chunk" in result
        assert "Second chunk" in result

    def test_format_context_bullet(self):
        """Test bullet context formatting."""
        manager = PromptManager()
        chunks = [
            {"content": "First chunk"},
            {"content": "Second chunk"},
        ]

        result = manager.format_context(chunks, format_type="bullet")

        assert "•" in result
        assert "First chunk" in result

    def test_format_context_xml(self):
        """Test XML context formatting."""
        manager = PromptManager()
        chunks = [
            {"content": "Test content", "score": 0.95},
        ]

        result = manager.format_context(chunks, format_type="xml")

        assert "<source" in result
        assert "</source>" in result
        assert "score=" in result

    def test_format_context_empty(self):
        """Test formatting empty context."""
        manager = PromptManager()
        result = manager.format_context([])

        assert "No relevant context" in result

    def test_format_context_max_length(self):
        """Test context truncation."""
        manager = PromptManager()
        chunks = [{"content": "A" * 1000}]

        result = manager.format_context(chunks, max_length=100)

        assert len(result) <= 103  # 100 + "..."
        assert result.endswith("...")

    def test_format_history(self):
        """Test history formatting."""
        manager = PromptManager()
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]

        result = manager.format_history(messages)

        assert "User: Hello" in result
        assert "Assistant: Hi there!" in result
        assert "User: How are you?" in result

    def test_format_history_empty(self):
        """Test formatting empty history."""
        manager = PromptManager()
        result = manager.format_history([])

        assert result == ""

    def test_format_history_max_turns(self):
        """Test history with max turns."""
        manager = PromptManager()
        messages = [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Response 1"},
            {"role": "user", "content": "Second"},
            {"role": "assistant", "content": "Response 2"},
            {"role": "user", "content": "Third"},
            {"role": "assistant", "content": "Response 3"},
        ]

        result = manager.format_history(messages, max_turns=1)

        assert "Third" in result
        assert "Response 3" in result
        # Earlier messages should be truncated
        assert "First" not in result


class TestPromptManagerValidation:
    """Tests for template validation."""

    def test_validate_template_valid(self):
        """Test validating template with all variables."""
        manager = PromptManager()
        manager.add_template(
            name="test_template",
            content="Context: {context}, Query: {query}",
            category="rag",
        )

        result = manager.validate_template(
            "rag",
            "test_template",
            {"context": "ctx", "query": "q"},
        )

        assert result["valid"] is True
        assert len(result["missing_variables"]) == 0

    def test_validate_template_missing_vars(self):
        """Test validating template with missing variables."""
        manager = PromptManager()
        manager.add_template(
            name="test_template",
            content="Context: {context}, Query: {query}",
            category="rag",
        )

        result = manager.validate_template(
            "rag",
            "test_template",
            {"context": "ctx"},
        )

        assert result["valid"] is False
        assert "query" in result["missing_variables"]

    def test_validate_template_not_found(self):
        """Test validating non-existent template."""
        manager = PromptManager()

        result = manager.validate_template(
            "rag",
            "nonexistent",
            {},
        )

        assert result["valid"] is False
        assert "error" in result


class TestPromptManagerExportImport:
    """Tests for template export/import."""

    def test_export_templates_yaml(self):
        """Test exporting templates to YAML."""
        manager = PromptManager()
        manager.add_template(
            name="export_test",
            content="Test content",
            category="rag",
        )

        result = manager.export_templates(category="rag", format="yaml")

        assert "export_test" in result
        assert "Test content" in result

    def test_export_templates_json(self):
        """Test exporting templates to JSON."""
        manager = PromptManager()
        manager.add_template(
            name="export_test",
            content="Test content",
            category="rag",
        )

        result = manager.export_templates(category="rag", format="json")

        import json
        data = json.loads(result)
        assert "rag" in data
        assert "export_test" in data["rag"]

    def test_import_templates_yaml(self):
        """Test importing templates from YAML."""
        manager = PromptManager()
        yaml_content = """
rag:
  imported_template: "Imported content {var}"
  another_template: "Another {var}"
"""

        count = manager.import_templates(yaml_content, format="yaml")

        assert count == 2
        template = manager.get_template("rag", "imported_template")
        assert template is not None
        assert "Imported content" in template.content

    def test_import_templates_json(self):
        """Test importing templates from JSON."""
        manager = PromptManager()
        json_content = """
{
    "system": {
        "imported_system": "System prompt content"
    }
}
"""

        count = manager.import_templates(json_content, format="json")

        assert count == 1
        template = manager.get_template("system", "imported_system")
        assert template is not None


class TestPromptManagerCustomTemplates:
    """Tests for custom templates from config."""

    def test_custom_templates_loaded(self):
        """Test custom templates are loaded from config."""
        config = PromptConfig(
            custom_templates={
                "rag_custom": "Custom RAG: {context}",
                "system_custom": "Custom system prompt",
            }
        )
        manager = PromptManager(config=config)

        # Custom templates should be available
        template = manager.get_template("rag", "rag_custom")
        assert template is not None
        assert "Custom RAG" in template.content


class TestPromptManagerTracking:
    """Tests for MLflow tracking."""

    def test_tracking_disabled_by_default(self):
        """Test tracking is disabled by default."""
        manager = PromptManager()
        assert manager.track is False

    def test_tracking_enabled_via_config(self):
        """Test tracking enabled via config."""
        config = PromptConfig(track_prompts=True)
        manager = PromptManager(config=config)

        assert manager.track is True

    def test_tracking_enabled_via_param(self):
        """Test tracking enabled via parameter."""
        manager = PromptManager(track=True)

        assert manager.track is True

    @patch("app.prompts.manager.PromptManager._track_prompt")
    def test_tracking_called_on_get_prompt(self, mock_track):
        """Test tracking is called when getting prompts."""
        manager = PromptManager(track=True)
        manager.get_system_prompt()

        mock_track.assert_called_once()


class TestJudgePromptTypes:
    """Tests for available judge prompt types."""

    def test_relevance_prompt(self):
        """Test relevance judge prompt."""
        manager = PromptManager()
        prompt = manager.get_judge_prompt(
            "relevance",
            query="What is AI?",
            context="AI is artificial intelligence.",
        )

        assert "relevance" in prompt.lower() or "relevant" in prompt.lower()
        assert "What is AI" in prompt

    def test_faithfulness_prompt(self):
        """Test faithfulness judge prompt."""
        manager = PromptManager()
        prompt = manager.get_judge_prompt(
            "faithfulness",
            query="What is AI?",
            context="AI is artificial intelligence.",
            answer="AI stands for artificial intelligence.",
        )

        assert "faithful" in prompt.lower()
        assert "AI stands for artificial intelligence" in prompt

    def test_answer_relevance_prompt(self):
        """Test answer relevance judge prompt."""
        manager = PromptManager()
        prompt = manager.get_judge_prompt(
            "answer_relevance",
            query="What is Python?",
            answer="Python is a programming language.",
        )

        assert "What is Python" in prompt
        assert "Python is a programming language" in prompt

    def test_coherence_prompt(self):
        """Test coherence judge prompt."""
        manager = PromptManager()
        prompt = manager.get_judge_prompt(
            "coherence",
            answer="This is a test answer.",
        )

        assert "This is a test answer" in prompt
        assert "coherence" in prompt.lower() or "structured" in prompt.lower()


class TestAgentPromptTypes:
    """Tests for available agent prompt types."""

    def test_query_rewriter_prompt(self):
        """Test query rewriter agent prompt."""
        manager = PromptManager()
        prompt = manager.get_agent_prompt(
            "query_rewriter",
            query="what is ml",
            history="",
        )

        assert "what is ml" in prompt
        assert "rewrite" in prompt.lower()

    def test_query_decomposer_prompt(self):
        """Test query decomposer agent prompt."""
        manager = PromptManager()
        prompt = manager.get_agent_prompt(
            "query_decomposer",
            query="Compare Python and JavaScript for web development",
        )

        assert "Compare Python and JavaScript" in prompt
        assert "sub-quer" in prompt.lower()

    def test_router_prompt(self):
        """Test router agent prompt."""
        manager = PromptManager()
        prompt = manager.get_agent_prompt(
            "router",
            query="What is machine learning?",
        )

        assert "What is machine learning" in prompt
        assert "vector" in prompt.lower()
        assert "keyword" in prompt.lower()

    def test_summarizer_prompt(self):
        """Test summarizer agent prompt."""
        manager = PromptManager()
        prompt = manager.get_agent_prompt(
            "summarizer",
            context="Chunk 1: Info. Chunk 2: More info.",
            query="What is the topic?",
        )

        assert "Chunk 1" in prompt
        assert "What is the topic" in prompt
