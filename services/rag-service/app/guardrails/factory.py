"""Factory for creating guardrail instances."""

import logging
from typing import Any

from app.guardrails.base import BaseGuardrail
from app.guardrails.llm_guard import LLMGuard
from app.llm.base import BaseLLM

logger = logging.getLogger(__name__)


def create_guardrail(
    guardrail_type: str = "llm",
    llm: BaseLLM | None = None,
    config: dict[str, Any] | None = None,
) -> BaseGuardrail:
    """
    Create a guardrail instance based on type.

    Args:
        guardrail_type: Type of guardrail ("llm" for LLM-based checks).
        llm: Language model instance (required for LLM guardrail).
        config: Guardrail configuration dict.

    Returns:
        Configured BaseGuardrail instance.

    Raises:
        ValueError: If required dependencies are missing.
    """
    guardrail_type = guardrail_type.lower()

    if guardrail_type in ("llm", "llm_guard", "default"):
        if llm is None:
            raise ValueError("LLM instance is required for LLM Guard guardrail")
        return LLMGuard(llm=llm, config=config)

    raise ValueError(
        f"Unknown guardrail type: '{guardrail_type}'. " f"Available types: llm"
    )
