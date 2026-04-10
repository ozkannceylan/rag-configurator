"""Langfuse integration for LLM observability.

Provides ``setup_langfuse`` to wire Langfuse tracing into a FastAPI app and
a ``trace_llm_call`` context manager for wrapping individual LLM calls with
generation spans (including token counts and latencies).

Gracefully degrades to no-ops when the ``langfuse`` package is not installed.
"""

from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager, contextmanager
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# Sentinel: is Langfuse available?
_langfuse_available = False
_langfuse_client = None

try:
    from langfuse import Langfuse  # type: ignore[import-untyped]

    _langfuse_available = True
except ImportError:
    pass


def setup_langfuse(
    app: Any = None,
    *,
    public_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    host: Optional[str] = None,
) -> None:
    """Initialise the global Langfuse client.

    Args:
        app: A FastAPI (or similar) application instance. Currently used only
             for logging; future versions may register shutdown hooks.
        public_key: Langfuse public key.
        secret_key: Langfuse secret key.
        host: Langfuse server URL (e.g., ``http://localhost:3003``).
    """
    global _langfuse_client  # noqa: PLW0603

    if not _langfuse_available:
        logger.info("Langfuse package not installed – tracing disabled.")
        return

    if not public_key or not secret_key:
        logger.info("Langfuse keys not provided – tracing disabled.")
        return

    try:
        _langfuse_client = Langfuse(
            public_key=public_key,
            secret_key=secret_key,
            host=host or "http://localhost:3003",
        )
        logger.info("Langfuse tracing initialised (host=%s).", host)
    except Exception as exc:
        logger.warning("Failed to initialise Langfuse: %s", exc)
        _langfuse_client = None


def get_langfuse():
    """Return the global Langfuse client, or ``None``."""
    return _langfuse_client


@contextmanager
def trace_llm_call(
    name: str = "llm-generation",
    *,
    model: Optional[str] = None,
    input_data: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    trace_id: Optional[str] = None,
    user_id: Optional[str] = None,
):
    """Synchronous context manager that wraps an LLM call with a Langfuse
    trace + generation span.

    Usage::

        with trace_llm_call(name="rag-gen", model="gpt-4o-mini",
                            input_data={"messages": [...]}) as span:
            response = llm.generate(...)
            span.update(output=response.content,
                        usage={"prompt_tokens": ..., "completion_tokens": ...})

    When Langfuse is unavailable the context manager yields a lightweight
    no-op object so callers never need conditional logic.
    """
    if _langfuse_client is None:
        yield _NoOpSpan()
        return

    start = time.time()
    trace = _langfuse_client.trace(
        name=name,
        id=trace_id,
        user_id=user_id,
        metadata=metadata or {},
        input=input_data,
    )
    generation = trace.generation(
        name=name,
        model=model,
        input=input_data,
        metadata=metadata or {},
    )
    span_wrapper = _LangfuseSpan(generation=generation, start_time=start)
    try:
        yield span_wrapper
    finally:
        elapsed_ms = (time.time() - start) * 1000
        try:
            generation.end(
                output=span_wrapper._output,
                usage=span_wrapper._usage,
                metadata={**(metadata or {}), "duration_ms": round(elapsed_ms, 2)},
            )
            _langfuse_client.flush()
        except Exception as exc:
            logger.debug("Langfuse flush error: %s", exc)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _NoOpSpan:
    """Drop-in replacement when Langfuse is not available."""

    def update(self, **kwargs: Any) -> None:  # noqa: D401
        pass


class _LangfuseSpan:
    """Thin wrapper around a Langfuse generation for deferred output."""

    def __init__(self, generation: Any, start_time: float) -> None:
        self._generation = generation
        self._start_time = start_time
        self._output: Optional[str] = None
        self._usage: Optional[Dict[str, Any]] = None

    def update(
        self,
        output: Optional[str] = None,
        usage: Optional[Dict[str, Any]] = None,
    ) -> None:
        if output is not None:
            self._output = output
        if usage is not None:
            self._usage = usage
