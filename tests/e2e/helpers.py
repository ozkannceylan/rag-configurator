"""Helper utilities for E2E tests."""

from typing import Any, Dict, Optional

import httpx


def get_data(response: httpx.Response) -> Any:
    """Extract data from API response, supporting both envelope and direct formats.

    Handles two response formats:
    - Envelope: {"data": {...}, "success": true, ...}
    - Direct: {...} (the data itself)
    """
    resp = response.json()
    if isinstance(resp, dict):
        return resp.get("data", resp)
    return resp


def get_id(data: dict) -> str:
    """Extract ID from response data, supporting both 'id' and '_id' field names."""
    return data.get("id") or data.get("_id")


DEFAULT_RAG_PROMPT = (
    "Use the following context to answer the question.\n\n"
    "Context: {context}\n\nQuestion: {query}\n\nAnswer:"
)


def make_config(
    name: str,
    description: str = "Test configuration",
    retrieval_method: str = "naive",
    agent_template: str = "naive_rag",
    max_iterations: Optional[int] = 3,
    **overrides: Any,
) -> Dict[str, Any]:
    """Build a valid config payload matching the current API schema."""
    config: Dict[str, Any] = {
        "name": name,
        "description": description,
        "data_source": {
            "type": "local",
            "base_path": "/test/data",
        },
        "models": {
            "llm": {
                "provider": "openai",
                "model_name": "gpt-4o-mini",
                "temperature": 0.7,
                "max_tokens": 2048,
            },
            "embedding": {
                "provider": "openai",
                "model_name": "text-embedding-3-small",
                "dimensions": 1536,
            },
        },
        "retrieval": {
            "method": retrieval_method,
        },
        "agent": {
            "template": agent_template,
            **({"max_iterations": max_iterations} if max_iterations is not None else {}),
        },
        "prompts": {
            "system_prompt": "You are a helpful assistant.",
            "rag_prompt_template": DEFAULT_RAG_PROMPT,
        },
    }
    config.update(overrides)
    return config
