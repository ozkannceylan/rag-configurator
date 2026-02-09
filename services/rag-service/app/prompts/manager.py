"""Prompt manager for template loading and variable substitution."""

import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)

# Default templates directory
TEMPLATES_DIR = Path(__file__).parent / "templates"


class PromptError(Exception):
    """Error in prompt management."""

    pass


@dataclass
class PromptTemplate:
    """A prompt template with metadata."""

    name: str
    content: str
    category: str = "default"
    variables: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    description: Optional[str] = None
    created_at: Optional[str] = None

    def __post_init__(self):
        """Extract variables from template."""
        if not self.variables:
            self.variables = self._extract_variables()
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def _extract_variables(self) -> List[str]:
        """Extract variable names from template."""
        # Match {variable_name} patterns
        pattern = r"\{(\w+)\}"
        return list(set(re.findall(pattern, self.content)))

    def format(self, **kwargs: Any) -> str:
        """
        Format template with variable substitution.

        Args:
            **kwargs: Variables to substitute

        Returns:
            Formatted prompt string
        """
        try:
            # Use safe substitution - missing vars stay as {var}
            result = self.content
            for key, value in kwargs.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result
        except Exception as e:
            raise PromptError(f"Failed to format template '{self.name}': {e}")

    def validate_variables(self, **kwargs: Any) -> List[str]:
        """
        Check for missing required variables.

        Returns:
            List of missing variable names
        """
        return [var for var in self.variables if var not in kwargs]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "content": self.content,
            "category": self.category,
            "variables": self.variables,
            "version": self.version,
            "description": self.description,
            "created_at": self.created_at,
        }


@dataclass
class PromptConfig:
    """Configuration for prompt management."""

    # System prompt settings
    system_prompt: Optional[str] = None
    system_prompt_name: str = "default"

    # RAG prompt settings
    rag_prompt: Optional[str] = None
    rag_prompt_name: str = "default"

    # Custom templates directory
    templates_dir: Optional[str] = None

    # Enable MLflow tracking
    track_prompts: bool = False
    mlflow_experiment: Optional[str] = None

    # Custom templates (name -> content)
    custom_templates: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PromptConfig":
        """Create config from dictionary."""
        return cls(
            system_prompt=data.get("system_prompt"),
            system_prompt_name=data.get("system_prompt_name", "default"),
            rag_prompt=data.get("rag_prompt"),
            rag_prompt_name=data.get("rag_prompt_name", "default"),
            templates_dir=data.get("templates_dir"),
            track_prompts=data.get("track_prompts", False),
            mlflow_experiment=data.get("mlflow_experiment"),
            custom_templates=data.get("custom_templates", {}),
        )


class PromptManager:
    """
    Manages prompt templates with variable substitution and optional tracking.

    Features:
    - Load prompts from YAML files or config
    - Variable substitution ({context}, {query}, {history}, etc.)
    - Optional MLflow tracking for versioning
    - Support for multiple prompt categories (system, rag, judge, agent)
    """

    def __init__(
        self,
        config: Optional[PromptConfig] = None,
        track: bool = False,
    ):
        """
        Initialize prompt manager.

        Args:
            config: Prompt configuration
            track: Enable MLflow tracking
        """
        self.config = config or PromptConfig()
        self.track = track or self.config.track_prompts

        # Template storage by category
        self._templates: Dict[str, Dict[str, PromptTemplate]] = {
            "system": {},
            "rag": {},
            "judge": {},
            "agent": {},
        }

        # MLflow client (lazy initialized)
        self._mlflow_client = None

        # Load default templates
        self._load_default_templates()

        # Load custom templates from config
        self._load_custom_templates()

    def _load_default_templates(self) -> None:
        """Load default templates from YAML files."""
        templates_dir = Path(self.config.templates_dir or TEMPLATES_DIR)

        for category in ["system", "rag", "judge", "agent"]:
            yaml_path = templates_dir / f"{category}.yaml"
            if yaml_path.exists():
                try:
                    with open(yaml_path, "r", encoding="utf-8") as f:
                        templates = yaml.safe_load(f) or {}

                    for name, content in templates.items():
                        self._templates[category][name] = PromptTemplate(
                            name=name,
                            content=content,
                            category=category,
                        )
                except Exception as e:
                    logger.warning(f"Failed to load {category} templates: {e}")

    def _load_custom_templates(self) -> None:
        """Load custom templates from config."""
        for name, content in self.config.custom_templates.items():
            # Determine category from name prefix (e.g., "rag_custom" -> "rag")
            category = "rag"  # default
            for cat in ["system", "rag", "judge", "agent"]:
                if name.startswith(f"{cat}_"):
                    category = cat
                    break

            self._templates[category][name] = PromptTemplate(
                name=name,
                content=content,
                category=category,
            )

    def get_system_prompt(self, name: Optional[str] = None) -> str:
        """
        Get system prompt.

        Args:
            name: Template name (default: from config or "default")

        Returns:
            System prompt string
        """
        # Use explicit override from config first
        if self.config.system_prompt:
            return self.config.system_prompt

        # Get named template
        template_name = name or self.config.system_prompt_name
        template = self._templates["system"].get(template_name)

        if template is None:
            template = self._templates["system"].get("default")

        if template is None:
            return "You are a helpful assistant."

        if self.track:
            self._track_prompt("system", template_name, template.content)

        return template.content

    def get_rag_prompt(
        self,
        context: str,
        query: str,
        name: Optional[str] = None,
        history: Optional[str] = None,
        **kwargs: Any,
    ) -> str:
        """
        Get RAG prompt with variable substitution.

        Args:
            context: Retrieved context
            query: User query
            name: Template name (default: from config)
            history: Conversation history (optional)
            **kwargs: Additional variables

        Returns:
            Formatted RAG prompt
        """
        # Use explicit override from config first
        if self.config.rag_prompt:
            content = self.config.rag_prompt
        else:
            template_name = name or self.config.rag_prompt_name
            template = self._templates["rag"].get(template_name)

            if template is None:
                template = self._templates["rag"].get("default")

            if template is None:
                # Fallback default
                content = "Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
            else:
                content = template.content

        # Build substitution dict
        variables = {
            "context": context,
            "query": query,
            "history": history or "",
            **kwargs,
        }

        # Substitute variables
        result = content
        for key, value in variables.items():
            result = result.replace(f"{{{key}}}", str(value))

        if self.track:
            self._track_prompt("rag", name or self.config.rag_prompt_name, content)

        return result

    def get_judge_prompt(
        self,
        prompt_type: str,
        **kwargs: Any,
    ) -> str:
        """
        Get evaluation/judge prompt.

        Args:
            prompt_type: Type of evaluation (relevance, faithfulness, etc.)
            **kwargs: Variables for substitution

        Returns:
            Formatted judge prompt
        """
        template = self._templates["judge"].get(prompt_type)

        if template is None:
            raise PromptError(f"Unknown judge prompt type: {prompt_type}")

        result = template.format(**kwargs)

        if self.track:
            self._track_prompt("judge", prompt_type, template.content)

        return result

    def get_agent_prompt(
        self,
        agent_type: str,
        **kwargs: Any,
    ) -> str:
        """
        Get agent-specific prompt.

        Args:
            agent_type: Type of agent (query_rewriter, router, etc.)
            **kwargs: Variables for substitution

        Returns:
            Formatted agent prompt
        """
        template = self._templates["agent"].get(agent_type)

        if template is None:
            raise PromptError(f"Unknown agent type: {agent_type}")

        result = template.format(**kwargs)

        if self.track:
            self._track_prompt("agent", agent_type, template.content)

        return result

    def get_template(
        self,
        category: str,
        name: str,
    ) -> Optional[PromptTemplate]:
        """
        Get a specific template.

        Args:
            category: Template category
            name: Template name

        Returns:
            PromptTemplate or None
        """
        return self._templates.get(category, {}).get(name)

    def list_templates(
        self,
        category: Optional[str] = None,
    ) -> Dict[str, List[str]]:
        """
        List available templates.

        Args:
            category: Filter by category (optional)

        Returns:
            Dictionary of category -> template names
        """
        if category:
            return {category: list(self._templates.get(category, {}).keys())}

        return {
            cat: list(templates.keys())
            for cat, templates in self._templates.items()
        }

    def add_template(
        self,
        name: str,
        content: str,
        category: str = "rag",
        description: Optional[str] = None,
    ) -> PromptTemplate:
        """
        Add a custom template.

        Args:
            name: Template name
            content: Template content
            category: Template category
            description: Template description

        Returns:
            Created PromptTemplate
        """
        template = PromptTemplate(
            name=name,
            content=content,
            category=category,
            description=description,
        )

        if category not in self._templates:
            self._templates[category] = {}

        self._templates[category][name] = template

        logger.info(f"Added template '{name}' to category '{category}'")
        return template

    def format_context(
        self,
        chunks: List[Dict[str, Any]],
        format_type: str = "numbered",
        max_length: Optional[int] = None,
    ) -> str:
        """
        Format retrieved chunks as context string.

        Args:
            chunks: List of chunk dictionaries
            format_type: Format type (numbered, bullet, plain, xml)
            max_length: Maximum context length

        Returns:
            Formatted context string
        """
        if not chunks:
            return "No relevant context found."

        parts = []

        for i, chunk in enumerate(chunks, 1):
            content = chunk.get("content", "")
            source = chunk.get("source", chunk.get("document_id", ""))
            score = chunk.get("score", 0)

            if format_type == "numbered":
                parts.append(f"[{i}] {content}")
                if source:
                    parts.append(f"    Source: {source}")
            elif format_type == "bullet":
                parts.append(f"• {content}")
            elif format_type == "xml":
                parts.append(f"<source id=\"{i}\" score=\"{score:.3f}\">\n{content}\n</source>")
            else:  # plain
                parts.append(content)

        result = "\n\n".join(parts)

        # Truncate if needed
        if max_length and len(result) > max_length:
            result = result[:max_length] + "..."

        return result

    def format_history(
        self,
        messages: List[Dict[str, str]],
        max_turns: Optional[int] = None,
    ) -> str:
        """
        Format conversation history.

        Args:
            messages: List of message dicts with role and content
            max_turns: Maximum number of turns to include

        Returns:
            Formatted history string
        """
        if not messages:
            return ""

        if max_turns:
            messages = messages[-max_turns * 2:]  # Each turn = user + assistant

        parts = []
        for msg in messages:
            role = msg.get("role", "user").capitalize()
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")

        return "\n".join(parts)

    def _track_prompt(
        self,
        category: str,
        name: str,
        content: str,
    ) -> None:
        """Track prompt usage with MLflow."""
        if not self.track:
            return

        try:
            if self._mlflow_client is None:
                import mlflow

                self._mlflow_client = mlflow

                if self.config.mlflow_experiment:
                    mlflow.set_experiment(self.config.mlflow_experiment)

            # Log prompt as artifact or param
            self._mlflow_client.log_param(f"prompt_{category}_{name}", name)

        except ImportError:
            logger.warning("MLflow not installed, prompt tracking disabled")
            self.track = False
        except Exception as e:
            logger.warning(f"Failed to track prompt: {e}")

    def validate_template(
        self,
        category: str,
        name: str,
        variables: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Validate a template with given variables.

        Args:
            category: Template category
            name: Template name
            variables: Variables to check

        Returns:
            Validation result dict
        """
        template = self.get_template(category, name)

        if template is None:
            return {
                "valid": False,
                "error": f"Template '{name}' not found in category '{category}'",
            }

        missing = template.validate_variables(**variables)

        return {
            "valid": len(missing) == 0,
            "missing_variables": missing,
            "template_variables": template.variables,
            "provided_variables": list(variables.keys()),
        }

    def export_templates(
        self,
        category: Optional[str] = None,
        format: str = "yaml",
    ) -> str:
        """
        Export templates to string.

        Args:
            category: Category to export (None for all)
            format: Output format (yaml or json)

        Returns:
            Exported templates string
        """
        data = {}

        categories = [category] if category else self._templates.keys()

        for cat in categories:
            if cat in self._templates:
                data[cat] = {
                    name: template.to_dict()
                    for name, template in self._templates[cat].items()
                }

        if format == "yaml":
            return yaml.dump(data, default_flow_style=False, allow_unicode=True)
        else:
            import json
            return json.dumps(data, indent=2)

    def import_templates(
        self,
        content: str,
        format: str = "yaml",
    ) -> int:
        """
        Import templates from string.

        Args:
            content: Template content
            format: Input format (yaml or json)

        Returns:
            Number of templates imported
        """
        if format == "yaml":
            data = yaml.safe_load(content)
        else:
            import json
            data = json.loads(content)

        count = 0
        for category, templates in data.items():
            if category not in self._templates:
                self._templates[category] = {}

            for name, template_data in templates.items():
                if isinstance(template_data, str):
                    # Simple format: name -> content
                    self._templates[category][name] = PromptTemplate(
                        name=name,
                        content=template_data,
                        category=category,
                    )
                else:
                    # Full format with metadata
                    self._templates[category][name] = PromptTemplate(
                        name=name,
                        content=template_data.get("content", ""),
                        category=category,
                        version=template_data.get("version", "1.0.0"),
                        description=template_data.get("description"),
                    )
                count += 1

        return count
